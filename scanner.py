#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import os
import time
import base64
import re
from urllib.parse import quote
from datetime import datetime
from playwright.sync_api import sync_playwright

from storage import get_all_searches, load_seen, save_seen
from whatsapp_api import send_message

SESSION_FILE   = "data/fb_session.json"
SCAN_INTERVAL  = 10 * 60

TRANSLATIONS = {
    "מיאטה": "Miata MX5",
    "miata": "מיאטה",
    "לנד קרוזר": "Land Cruiser",
    "land cruiser": "לנד קרוזר",
    "קפואצ'ינו": "Suzuki Cappuccino",
    "cappuccino": "סוזוקי קפואצ'ינו",
    "טנדר קיי": "Kei Truck",
    "kei truck": "טנדר יפני"
}

def load_fb_session() -> dict | None:
    b64 = os.environ.get("FB_SESSION", "")
    if b64:
        try:
            return json.loads(base64.b64decode(b64).decode("utf-8"))
        except: pass
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def is_relevant_ad(item: dict, query: str, min_price_str: str, max_price_str: str, min_year: str, max_year: str) -> bool:
    text = item["text"].lower()
    
    blacklist = ["חלפים", "פירוק", "לחלקים", "שבור", "תקול", "תאונה", "parts", "bastler", "motorschaden"]
    if any(word in text for word in blacklist):
        return False

    ad_price = 0
    price_matches = re.findall(r'(?:₪|\$|€)?\s*(\d{1,3}(?:,\d{3})*)\s*(?:₪|\$|€)?', text)
    if price_matches:
        try: ad_price = int(price_matches[0].replace(",", ""))
        except: pass

    if ad_price > 0:
        if max_price_str and ad_price > int(max_price_str): return False
        if min_price_str and ad_price < int(min_price_str): return False
        
        # הטריק החכם פועל רק אם לא הגדרת מינימום ידנית
        if not min_price_str:
            is_car = any(w in query.lower() for w in ["מיאטה", "miata", "cruiser", "kei", "קפואצ'ינו", "טנדר"])
            if is_car and ad_price < 5000:
                return False

    years = re.findall(r'\b(19[7-9]\d|20[0-2]\d)\b', text)
    if years:
        ad_year = int(years[0])
        if min_year and ad_year < int(min_year): return False
        if max_year and ad_year > int(max_year): return False

    return True

def scan_marketplace(page, query: str, max_price: str = "") -> list:
    search_queries = [query]
    for key, val in TRANSLATIONS.items():
        if key in query.lower():
            search_queries.append(val)
            break

    all_items = []
    seen_urls = set()

    for q in search_queries:
        url = f"https://www.facebook.com/marketplace/search/?query={quote(q)}&sortBy=creation_time_descend"
        if max_price: url += f"&maxPrice={max_price}"

        print(f"  🔍 סורק: \"{q}\"")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(4_000) 

            items = page.evaluate("""
                () => {
                    const results = [];
                    const links   = document.querySelectorAll('a[href*="/marketplace/item/"]');
                    links.forEach(link => {
                        const href  = link.getAttribute('href') || '';
                        const match = href.match(/\/marketplace\/item\/([0-9]+)/);
                        if (!match) return;
                        const id = match[1];
                        const container = link.closest('div[class]') || link;
                        const text = (container.innerText || '').slice(0, 400);
                        const fullUrl = href.startsWith('http')
                            ? href.split('?')[0]
                            : 'https://www.facebook.com' + href.split('?')[0];
                        results.push({ id, url: fullUrl, text });
                    });
                    return results.slice(0, 20);
                }
            """)
            
            for item in (items or []):
                if item["url"] not in seen_urls:
                    seen_urls.add(item["url"])
                    all_items.append(item)
        except Exception as e:
            pass

    return all_items

def format_alert(item: dict, query: str) -> str:
    lines = [l.strip() for l in item["text"].strip().splitlines() if l.strip()]
    title = lines[0] if lines else "פריט חדש"

    price = ""
    for line in lines[1:6]:
        if any(c in line for c in ("₪", "$", "€")) or (any(c.isdigit() for c in line) and len(line) < 30):
            price = line
            break

    msg  = "🛍️ *מוצר חדש ב-Marketplace!*\n"
    msg += f"🔎 חיפוש: _{query}_\n"
    msg += f"📌 {title}\n"
    if price: msg += f"💰 {price}\n"
    msg += f"🔗 {item['url']}"
    return msg

def run_scanner():
    print("\n🤖 סורק מופעל")
    session = load_fb_session()
    if not session: return
    seen = load_seen()
    scan_num = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session)
        page = context.new_page()

        while True:
            scan_num += 1
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] ── סריקה #{scan_num} ──")

            all_searches = get_all_searches()
            for phone, searches in all_searches.items():
                for s in searches:
                    query = s["query"]
                    min_p = s.get("min_price", "")
                    max_p = s.get("max_price", "")
                    min_y = s.get("min_year", "")
                    max_y = s.get("max_year", "")
                    
                    items = scan_marketplace(page, query, max_p)

                    for item in items:
                        if not is_relevant_ad(item, query, min_p, max_p, min_y, max_y):
                            continue
                        
                        key = f"{phone}::{query}::{item['id']}"
                        if key not in seen:
                            seen.add(key)
                            if scan_num > 1:
                                send_message(phone, format_alert(item, query))
                                time.sleep(2)
                    time.sleep(3)
            save_seen(seen)
            time.sleep(SCAN_INTERVAL)
