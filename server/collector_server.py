# server/collector_server.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import os
import uuid
import json
import base64
import datetime

app = FastAPI()

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'data', 'collected'))
os.makedirs(DATA_DIR, exist_ok=True)
JSONL_PATH = os.path.join(DATA_DIR, 'samples.jsonl')

class Sample(BaseModel):
    challenge: str | None = None
    response: str | float | None = None
    image_b64: str | None = None
    meta: dict = {}
    consent: bool = True

@app.post('/collect')
async def collect(sample: Sample, request: Request):
    if not sample.consent:
        return {'ok': False, 'reason': 'no_consent'}

    item = {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
        'challenge': sample.challenge,
        'response': sample.response,
        'image_b64': sample.image_b64,
        'meta': sample.meta
    }

    with open(JSONL_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

    if sample.image_b64:
        try:
            raw = base64.b64decode(sample.image_b64)
            image_path = os.path.join(DATA_DIR, f"{item['id']}.png")
            with open(image_path, 'wb') as out:
                out.write(raw)
        except Exception as e:
            print('save image failed:', e)

    return {'ok': True, 'id': item['id']}
