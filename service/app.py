import json
import os
import threading

import boto3
import torch
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_URI = os.environ["MODEL_URI"]  # e.g. s3://models/v1
MODEL_VERSION = os.environ.get("MODEL_VERSION", "unknown")
S3_ENDPOINT = os.environ["S3_ENDPOINT"]
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "60"))
FAULT_INJECT = os.environ.get("FAULT_INJECT", "0") == "1"
POD = os.environ.get("HOSTNAME", "local")
LOCAL_DIR = "/tmp/model"

INTENTS = {
    "alarm_set", "alarm_query", "calendar_set", "calendar_query",
    "calendar_remove", "weather_query", "datetime_query", "recommendation_events",
}
KEYS = {"intent", "date", "time", "place"}
FILES = ["config.json", "generation_config.json", "model.safetensors",
         "tokenizer.json", "tokenizer_config.json"]

app = FastAPI()
state = {"ready": False, "tok": None, "model": None}


class Req(BaseModel):
    text: str


def load_model():
    bucket, _, prefix = MODEL_URI.removeprefix("s3://").partition("/")
    s3 = boto3.client(
        "s3", endpoint_url=S3_ENDPOINT, region_name="us-east-1",
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )
    os.makedirs(LOCAL_DIR, exist_ok=True)
    for name in FILES:
        print(f"downloading {MODEL_URI}/{name}", flush=True)
        s3.download_file(bucket, f"{prefix}/{name}", f"{LOCAL_DIR}/{name}")
    torch.set_num_threads(int(os.environ.get("NUM_THREADS", "1")))
    state["tok"] = AutoTokenizer.from_pretrained(LOCAL_DIR)
    state["model"] = AutoModelForCausalLM.from_pretrained(LOCAL_DIR, dtype=torch.float32).eval()
    state["ready"] = True
    print("model loaded, ready", flush=True)


def valid(obj):
    if not isinstance(obj, dict) or set(obj.keys()) != KEYS:
        return False
    if obj["intent"] not in INTENTS:
        return False
    return all(obj[k] is None or isinstance(obj[k], str) for k in ("date", "time", "place"))


@app.on_event("startup")
def startup():
    threading.Thread(target=load_model, daemon=True).start()


@app.get("/healthz")
def healthz():
    return {"status": "alive"}


@app.get("/readyz")
def readyz():
    if state["ready"]:
        return {"status": "ready"}
    return JSONResponse({"status": "loading"}, status_code=503)


@app.post("/parse")
def parse(req: Req):
    if not state["ready"]:
        return JSONResponse({"error": "model_not_ready"}, status_code=503)
    tok, model = state["tok"], state["model"]
    enc = tok(f"Command: {req.text}\nJSON:", return_tensors="pt")
    with torch.no_grad():
        out = model.generate(**enc, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                             pad_token_id=tok.eos_token_id)
    text = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
    text = text.strip().split("\n")[0].strip()
    if FAULT_INJECT:
        text = "not json"
    try:
        obj = json.loads(text)
    except Exception:
        obj = None
    headers = {"X-Model-Version": MODEL_VERSION, "X-Served-By": POD}
    if obj is None or not valid(obj):
        return Response(content='{"error": "invalid_model_output"}', status_code=500,
                        media_type="application/json", headers=headers)
    return Response(content=json.dumps(obj), media_type="application/json", headers=headers)
