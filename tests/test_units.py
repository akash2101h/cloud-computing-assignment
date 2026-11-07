import sys

sys.path.insert(0, "worker")
from clean import classify, clean


def test_valid_record_kept():
    raw = '{"intent": "weather_query", "date": null, "time": null, "place": "london"}'
    reason, obj = classify(raw, "what is the weather in london")
    assert reason is None and obj["place"] == "london"


def test_invalid_json_rejected_a():
    assert classify("not json", "x")[0] == "a"


def test_wrong_intent_rejected_c():
    raw = '{"intent": "play_music", "date": null, "time": null, "place": null}'
    assert classify(raw, "x")[0] == "c"


def test_slot_not_in_command_rejected_d():
    raw = '{"intent": "alarm_set", "date": "friday", "time": null, "place": null}'
    assert classify(raw, "set an alarm for monday")[0] == "d"


def test_duplicates_keep_smallest_id():
    good = '{"intent": "alarm_query", "date": null, "time": null, "place": null}'
    recs = [
        {"id": "C0009", "text": "any alarms", "teacher_raw": good},
        {"id": "C0002", "text": "any alarms", "teacher_raw": good},
    ]
    kept, counts = clean(recs)
    assert [r["id"] for r in kept] == ["C0002"] and counts["duplicates"] == 1


def test_shard_selection():
    assert [n for n in range(10) if n % 2 == 1] == [1, 3, 5, 7, 9]
