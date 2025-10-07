import json
import os
from datetime import datetime
from typing import Dict, Any
from .config import CFG

STATE_PATH = None

def _ensure_paths():
    global STATE_PATH
    os.makedirs(CFG.data_dir, exist_ok=True)
    STATE_PATH = os.path.join(CFG.data_dir, "state.json")
    if not os.path.exists(STATE_PATH):
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump({"counters": {}, "chat": {}}, f, ensure_ascii=False, indent=2)

def _load() -> Dict[str, Any]:
    _ensure_paths()
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _save(d: Dict[str, Any]):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def today_key(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def get_next_number(tag: str, dt: datetime) -> int:
    s = _load()
    day = today_key(dt)
    s["counters"].setdefault(day, {})
    s["counters"][day].setdefault(tag, 1)
    n = s["counters"][day][tag]
    s["counters"][day][tag] = n + 1
    _save(s)
    return n

def set_counter(tag: str, dt: datetime, n: int):
    s = _load()
    day = today_key(dt)
    s["counters"].setdefault(day, {})
    s["counters"][day][tag] = n
    _save(s)

def get_status(dt: datetime) -> Dict[str, int]:
    s = _load()
    day = today_key(dt)
    return s["counters"].get(day, {})

def set_chat_tag(chat_id: int, tag: str):
    s = _load()
    entry = s["chat"].setdefault(str(chat_id), {})
    entry["tag"] = tag
    tags = entry.setdefault("tags", [])
    if tag not in tags:
        tags.append(tag)
    _save(s)

def get_chat_tag(chat_id: int) -> str | None:
    s = _load()
    return s.get("chat", {}).get(str(chat_id), {}).get("tag")

def get_chat_tags(chat_id: int) -> list[str]:
    s = _load()
    entry = s.get("chat", {}).get(str(chat_id), {})
    tags = entry.get("tags", [])
    current = entry.get("tag")
    if current and current not in tags:
        tags = tags + [current]
    return list(tags)

def set_chat_mode(chat_id: int, mode: str):
    s = _load()
    entry = s["chat"].setdefault(str(chat_id), {})
    entry["mode"] = mode
    _save(s)

def get_chat_mode(chat_id: int) -> str:
    s = _load()
    entry = s.get("chat", {}).get(str(chat_id), {})
    return entry.get("mode", "auto")

def set_last_pack_info(chat_id: int, tag: str, n: int, day: str):
    s = _load()
    s["chat"].setdefault(str(chat_id), {})
    s["chat"][str(chat_id)]["last_pack"] = {"tag": tag, "n": n, "day": day}
    _save(s)

def get_last_pack_info(chat_id: int):
    s = _load()
    return s.get("chat", {}).get(str(chat_id), {}).get("last_pack")
