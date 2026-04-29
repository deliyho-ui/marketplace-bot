#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import threading
import re
from flask import Flask, request, jsonify
from whatsapp_api import send_message
from storage import add_search, remove_search, list_searches
from scanner import run_scanner

app = Flask(__name__)
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "marketplace_bot_token")

@app.route("/webhook", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook אומת בהצלחה")
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    try:
        value   = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value: return jsonify({"status": "ok"})
        msg      = value["messages"][0]
        phone    = msg["from"]
        msg_type = msg.get("type", "")

        if msg_type == "text":
            text = msg["text"]["body"].strip()
            handle_message(phone, text)
    except Exception as e:
        pass
    return jsonify({"status": "ok"})

def handle_message(phone: str, text: str):
    t = text.strip()
    tl = t.lower()

    if tl in ("עזרה", "/עזרה", "help", "/help", "היי", "הי", "שלום"):
        send_message(phone, help_text())
        return

    if tl in ("רשימה", "/רשימה", "חיפושים", "/חיפושים"):
        searches = list_searches(phone)
        if not searches:
            send_message(phone, "אין לך חיפושים פעילים כרגע.")
        else:
            lines = ["📋 *החיפושים הפעילים שלך:*\n"]
            for i, s in enumerate(searches, 1):
                line = f"{i}. {s['query']}"
                if s.get("min_price") and s.get("max_price"): line += f" ({s['min_price']}-{s['max_price']}₪)"
                elif s.get("max_price"): line += f" (עד {s['max_price']}₪)"
                if s.get("min_year") and s.get("max_year"): line += f" [{s['min_year']}-{s['max_year']}]"
                lines.append(line)
            lines.append("\nלעצור חיפוש: *עצור [שם החיפוש]*")
            send_message(phone, "\n".join(lines))
        return

    if tl.startswith("חפש ") or tl.startswith("/חפש "):
        rest = t[4:].strip()
        if not rest:
            send_message(phone, "כתוב מה לחפש.")
            return

        query = rest
        min_price, max_price, min_year, max_year = "", "", "", ""

        # חילוץ שנתונים: מ-1990 עד 1998
        year_match = re.search(r'(?:משנת|מ-)?\s*(19\d{2}|20\d{2})\s*עד\s*(19\d{2}|20\d{2})', query)
        if year_match:
            min_year, max_year = year_match.groups()
            query = query.replace(year_match.group(0), "")

        # חילוץ טווח מחירים: מ-20000 עד 40000
        price_range_match = re.search(r'(?:במחיר|מ-)?\s*(\d{3,})\s*עד\s*(\d{3,})', query)
        if price_range_match:
            min_price, max_price = price_range_match.groups()
            query = query.replace(price_range_match.group(0), "")
        else:
            # חילוץ מחיר מקסימום בלבד: עד 40000
            price_max_match = re.search(r'עד\s*(\d{3,})', query)
            if price_max_match:
                max_price = price_max_match.group(1)
                query = query.replace(price_max_match.group(0), "")

        # ניקוי שאריות
        query = re.sub(r'(במחיר|משנת|בשנים|שנים|מ-|עד)', '', query).strip()
        query = re.sub(r'\s+', ' ', query) # מסיר רווחים כפולים

        added = add_search(phone, query, min_price, max_price, min_year, max_year)
        if added:
            msg = f"✅ הוספתי חיפוש: *{query}*"
            if min_price and max_price: msg += f"\n💰 טווח מחיר: {min_price}-{max_price}₪"
            elif max_price: msg += f"\n💰 מחיר: עד {max_price}₪"
            if min_year and max_year: msg += f"\n📅 שנתונים: {min_year}-{max_year}"
        else:
            msg = f"החיפוש *{query}* כבר קיים."
        send_message(phone, msg)
        return

    if tl.startswith("עצור ") or tl.startswith("/עצור "):
        query = t[5:].strip()
        removed = remove_search(phone, query)
        if removed: send_message(phone, f"🛑 עצרתי את החיפוש: *{query}*")
        else: send_message(phone, f"לא מצאתי חיפוש בשם \"{query}\".")
        return

    send_message(phone, f"לא הבנתי 😅\n\n{help_text()}")

def help_text() -> str:
    return (
        "👋 *שלום! אני בוט Marketplace*\n\n"
        "📝 *דוגמאות לחיפושים חכמים:*\n"
        "חפש אייפון 13 עד 2000\n"
        "חפש מיאטה מ-30000 עד 50000 מ-1990 עד 1998\n"
        "חפש טנדר קיי משנת 1990 עד 2005\n\n"
        "• *רשימה* – לראות מה אני מחפש\n"
        "• *עצור [שם]* – לעצור חיפוש"
    )

def start_scanner():
    t = threading.Thread(target=run_scanner, daemon=True)
    t.start()

if __name__ == "__main__":
    start_scanner()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
