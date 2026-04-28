#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
שמירת חיפושים ומעקב אחרי פריטים שנראו
"""

import json
import os
from datetime import datetime

DATA_DIR     = "data"
SEARCHES_FILE = os.path.join(DATA_DIR, "searches.json")
SEEN_FILE     = os.path.join(DATA_DIR, "seen.json")


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


# ──────────────────────────────────────────
#  חיפושים
# ──────────────────────────────────────────

def _load_searches() -> dict:
    _ensure_dir()
    try:
        with open(SEARCHES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_searches(data: dict):
    _ensure_dir()
    with open(SEARCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_searches(phone: str) -> list:
    return _load_searches().get(phone, [])


def get_all_searches() -> dict:
    """מחזיר את כל החיפושים של כל המשתמשים"""
    return _load_searches()


def add_search(phone: str, query: str, max_price: str = "", location: str = "", radius: str = "") -> bool:
    """מוסיף חיפוש. מחזיר False אם כבר קיים."""
    data = _load_searches()
    if phone not in data:
        data[phone] = []

    for s in data[phone]:
        if s["query"].strip().lower() == query.strip().lower():
            return False

    data[phone].append({
        "query":      query,
        "max_price":  max_price,
        "location":   location,
        "radius":     radius,
        "created_at": datetime.now().isoformat()
    })
    _save_searches(data)
    return True


def remove_search(phone: str, query: str) -> bool:
    """מסיר חיפוש. מחזיר False אם לא נמצא."""
    data = _load_searches()
    if phone not in data:
        return False

    before = len(data[phone])
    data[phone] = [
        s for s in data[phone]
        if query.strip().lower() not in s["query"].strip().lower()
    ]
    if len(data[phone]) < before:
        _save_searches(data)
        return True
    return False


# ──────────────────────────────────────────
#  מעקב פריטים שנראו
# ──────────────────────────────────────────

def load_seen() -> set:
    _ensure_dir()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen: set):
    _ensure_dir()
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f)
