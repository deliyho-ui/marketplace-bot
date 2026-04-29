#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

DATA_DIR     = "data"
SEARCHES_FILE = os.path.join(DATA_DIR, "searches.json")
SEEN_FILE     = os.path.join(DATA_DIR, "seen.json")

def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

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
    return _load_searches()

def add_search(phone: str, query: str, min_price: str = "", max_price: str = "", min_year: str = "", max_year: str = "") -> bool:
    data = _load_searches()
    if phone not in data:
        data[phone] = []

    for s in data[phone]:
        if s["query"].strip().lower() == query.strip().lower():
            return False

    data[phone].append({
        "query":      query,
        "min_price":  min_price,
        "max_price":  max_price,
        "min_year":   min_year,
        "max_year":   max_year,
        "created_at": datetime.now().isoformat()
    })
    _save_searches(data)
    return True

def remove_search(phone: str, query: str) -> bool:
    data = _load_searches()
    if phone not in data: return False
    before = len(data[phone])
    data[phone] = [s for s in data[phone] if query.strip().lower() not in s["query"].strip().lower()]
    if len(data[phone]) < before:
        _save_searches(data)
        return True
    return False

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
