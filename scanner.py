#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
סורק Facebook Marketplace ברקע – שולח התראות לוואטסאפ
"""

import json
import os
import time
import base64
from urllib.parse import quote
from datetime import datetime
from playwright.sync_api import sync_playwright

from storage import get_all_searches, load_seen, save_seen
from whatsapp_api import send_message

SESSION_FILE   = "data/fb_session.json"
SCAN_INTERVAL  = 10 * 60   # כל 10 דקות


# ──────────────────────────────────────────
#  טעינת סשן פייסבוק
# ──────────────────────────────────────────

def load_fb_session() -> dict | None:
    """
    מנסה לטעון סשן פייסבוק:
    1. מ-environment variable FB_SESSION (base64) – לשרת ב-Railway
    2. מקובץ data/fb_session.json – לבדיקה מקומית
    """
    b64 = os.environ.get("FB_SESSION", "")
    if b64:
        try:
            session_json = base64.b64decode(b64).decode("utf-8")
            return json.loads(session_json)
        except Exception as e:
            print(f"❌ שגיאה בטעינת FB_SESSION: {e}")

    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    print("❌ לא נמצא סשן פייסבוק!")
    return None


# ──────────────────────────────────────────
#  סריקת Marketplace
# ──────────────────────────────────────────

def scan_marketplace(page, query: str, max_price: str = "", location: str = "", radius: str = "") -> list:
    """מחזיר רשימה של פריטים (id, url, text)."""
    
    # בניית ה-URL לפי מיקום ורדיוס
    if location:
        base_url = f"https://www.facebook.com/marketplace/{location}/search/"
    else:
        base_url = "https://www.facebook.com/marketplace/search/"
        
    url = f"{base_url}?query={quote(query)}&sortBy=creation_time_descend"
    
    if max_price:
        url += f"&maxPrice={max_price}"
    if radius:
        url += f"&radius={radius}"

    print(f"  🔍 סורק: \"{query}\" | אזור: {location or 'Default'} | רדיוס: {radius or 'Default'} ק\"מ")

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(5_000)   # המתנה לטעינת התוצאות

        items = page.evaluate("""
            () => {
                const results = [];
                const seenIds = new Set();
                const links   = document.querySelectorAll('a[href*="/marketplace/item/"]');

                links.forEach(link => {
                    const href  = link.getAttribute('href') || '';
                    const match = href.match(/\\/marketplace\\/item\\/([0-9]+)/);
                    if (!match) return;

                    const id = match[1];
                    if (seenIds.has(id)) return;
                    seenIds.add(id);

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

        items = items or []
        print(f"  📦 נמצאו {len(items)} פריטים")
        return items

    except Exception as e:
        print(f"  ❌ שגיאה בסריקה: {e}")
        return []


# ──────────────────────────────────────────
#  עיצוב הודעת התראה
# ──────────────────────────────────────────

def format_alert(item: dict, query: str) -> str:
    lines = [l.strip() for l in item["text"].strip().splitlines() if l.strip()]
    title = lines[0] if lines else "פריט חדש"

    price = ""
    for line in lines[1:6]:
        if any(c in line for c in ("₪", "$", "€")) or (
            any(c.isdigit() for c in line) and len(line) < 30
        ):
            price = line
            break

    msg  = "🛍️ *מוצר חדש ב-Marketplace!*\n"
    msg += f"🔎 חיפוש: _{query}_\n"
    msg += f"📌 {title}\n"
    if price:
        msg += f"💰 {price}\n"
    msg += f"🔗 {item['url']}"
    return msg


# ──────────────────────────────────────────
#  לולאת סריקה ראשית
# ──────────────────────────────────────────

def run_scanner():
    """מריץ סריקה כל 10 דקות ברקע."""
    print("\n🤖 סורק הופעל")

    session = load_fb_session()
    if not session:
        print("⛔ הסורק לא יפעל ללא סשן פייסבוק")
        return

    seen     = load_seen()
    scan_num = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session)
        page    = context.new_page()

        while True:
            scan_num += 1
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{ts}] ── סריקה #{scan_num} ──")

            all_searches = get_all_searches()
            if not all_searches:
                print("  (אין חיפושים פעילים)")

            new_total = 0

            for phone, searches in all_searches.items():
                for s in searches:
                    query     = s["query"]
                    max_price = s.get("max_price", "")
                    location  = s.get("location", "")
                    radius    = s.get("radius", "")
                    
                    items = scan_marketplace(page, query, max_price, location, radius)

                    for item in items:
                        key = f"{phone}::{query}::{item['id']}"
                        if key not in seen:
                            seen.add(key)
                            if scan_num > 1:
                                new_total += 1
                                print(f"  🆕 שולח התראה ל-{phone}")
                                send_message(phone, format_alert(item, query))
                                time.sleep(2)

                    time.sleep(3)

            save_seen(seen)
            print(f"✅ סריקה #{scan_num} הושלמה. נמצאו {new_total} פריטים חדשים.")
            print(f"💤 ממתין {SCAN_INTERVAL // 60} דקות…")
            time.sleep(SCAN_INTERVAL)
