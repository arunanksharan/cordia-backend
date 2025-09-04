import base64, json
from datetime import datetime
from typing import Any

def encode_cursor(obj: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(obj, separators=(",",":")).encode()).decode()

def decode_cursor(token: str | None) -> dict | None:
    if not token: return None
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())