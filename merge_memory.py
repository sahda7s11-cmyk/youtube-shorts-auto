#!/usr/bin/env python3
"""يدمج ذاكرة هذا التشغيل مع أحدث نسخة من GitHub دون حذف أي سجل.

الاستعمال:  python mpt_daily/merge_memory.py GENERATED_DIR
(يُنفَّذ من جذر المستودع بعد git reset --hard origin/main)
"""
import json
import sys
from pathlib import Path

FILES = ("used_content.json", "used_pexels.json")


def load_list(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        print(f"WARNING: could not read {path}; treating as empty")
        return []
    return data if isinstance(data, list) else []


def key(item):
    try:
        return json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        return repr(item)

