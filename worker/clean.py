import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

INTENTS = {
    "alarm_set", "alarm_query", "calendar_set", "calendar_query",
    "calendar_remove", "weather_query", "datetime_query", "recommendation_events",
}
KEYS = ["intent", "date", "time", "place"]


def classify(raw, command):
    """Return (reason, parsed). reason is None when the record is good."""
    try:
        obj = json.loads(raw)
    except Exception:
        return "a", None
    if not isinstance(obj, dict):
        return "a", None
    if sorted(obj.keys()) != sorted(KEYS):
        return "b", None
    if obj["intent"] not in INTENTS:
        return "c", None
    for slot in ("date", "time", "place"):
        v = obj[slot]
        if v is not None and not (isinstance(v, str) and v in command):
            return "d", None
    return None, obj


def clean(records):
    records = sorted(records, key=lambda r: r["id"])
    counts = {"input": len(records), "a": 0, "b": 0, "c": 0, "d": 0, "duplicates": 0, "kept": 0}
    seen, kept = set(), []
    for r in records:
        reason, _ = classify(r["teacher_raw"], r["text"])
        if reason:
            counts[reason] += 1
            continue
        if r["text"] in seen:
            counts["duplicates"] += 1
            continue
        seen.add(r["text"])
        kept.append({"id": r["id"], "text": r["text"], "teacher_raw": r["teacher_raw"]})
    counts["kept"] = len(kept)
    return kept, counts


def serialise(kept):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in kept).encode("utf-8")


def main():
    from s3util import client
    s3 = client()
    records = []
    for i in range(int(os.environ.get("SHARD_COUNT", "2"))):
        body = s3.get_object(Bucket="datasets", Key=f"teacher/shard-{i}.jsonl")["Body"].read().decode("utf-8")
        records += [json.loads(x) for x in body.splitlines() if x.strip()]
    kept, counts = clean(records)
    data = serialise(kept)
    digest = hashlib.sha256(data).hexdigest()
    s3.put_object(Bucket="datasets", Key="v1/train.jsonl", Body=data)
    s3.put_object(Bucket="datasets", Key="v1/train.sha256", Body=f"{digest}  train.jsonl\n".encode())
    os.makedirs("results", exist_ok=True)
    with open("results/clean_counts.json", "w") as f:
        json.dump(counts, f, indent=2)
    print(json.dumps(counts, indent=2))
    print("sha256:", digest)
    total = sum(counts[k] for k in ("a", "b", "c", "d", "duplicates", "kept"))
    assert total == counts["input"], "counts do not add up"


if __name__ == "__main__":
    main()
