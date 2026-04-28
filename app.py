#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================
  Marketplace WhatsApp Bot – Webhook Server
==============================================
"""

import os
import threading
from flask import Flask, request, jsonify
from whatsapp_api import send_message
from storage import add_search, remove_search, list_searches
from scanner import run_scanner

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "marketplace_bot_token")


# ──────────────────────────────────────────
#  Webhook – אימות ע"י Meta
# ──────────────────────────────────────────

@app.route("/webhook", methods=["GET"])
def verify():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Webhook אומת בהצלחה")
        return challenge, 200
    return "Forbidden", 403


# ──────────────────────────────────────────
#  Webhook – קבלת הודעות
# ──────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True) or {}
    
    # שימוש בלוגר הרשמי של האפליקציה במקום print רגיל
    app.logger.warning("=== הודעה נכנסת מ-META ===")
    app.logger.warning(data)

    try:
        value   = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            return jsonify({"status": "ok"})

        msg      = value["messages"][0]
        phone    = msg["from"]
        msg_type = msg.get("type", "")

        if msg_type == "text":
            text = msg["text"]["body"].strip()
            handle_message(phone, text)

    except (KeyError, IndexError) as e:
        app.logger.warning(f"⚠️ ההודעה נדחתה בגלל שגיאת מבנה: {e}")
    except Exception as e:
        app.logger.error(f"❌ שגיאה ב-webhook: {e}")

    return jsonify({"status": "ok"})

# ──────────────────────────────────────────
#  טיפול בהודעות נכנסות
# ──────────────────────────────────────────

def handle_message(phone: str, text: str):
    t = text.strip()
    tl = t.lower()

    # ── פקודת עזרה / ברכה ──
    if tl in ("עזרה", "/עזרה", "help", "/help", "היי", "הי", "שלום", "בוקר טוב", "ערב טוב"):
        send_message(phone, help_text())
        return

    # ── רשימת חיפושים ──
    if tl in ("רשימה", "/רשימה", "חיפושים", "/חיפושים"):
        searches = list_searches(phone)
        if not searches:
            send_message(phone, "אין לך חיפושים פעילים כרגע.\n\nהוסף אחד עם:\n*חפש [מה לחפש]*")
        else:
            lines = ["📋 *החיפושים הפעילים שלך:*\n"]
            for i, s in enumerate(searches, 1):
                line = f"{i}. {s['query']}"
                if s.get("max_price"):
                    line += f" (עד {s['max_price']} ₪)"
                lines.append(line)
            lines.append("\nלעצור חיפוש: *עצור [שם החיפוש]*")
            send_message(phone, "\n".join(lines))
        return

   # ── הוספת חיפוש ──
    if tl.startswith("חפש ") or tl.startswith("/חפש "):
        rest = t[4:].strip()
        if not rest:
            send_message(phone, "כתוב מה לחפש.\nלדוגמה: *חפש mazda mx-5 bronze, miami, 15000, 50*")
            return

        parts = [p.strip() for p in rest.split(",")]
        query = parts[0]
        location = parts[1].replace(" ", "").lower() if len(parts) > 1 else ""
        max_price = parts[2].replace("₪", "").replace("$", "").strip() if len(parts) > 2 else ""
        radius = parts[3].replace("km", "").replace("קמ", "").strip() if len(parts) > 3 else ""

        added = add_search(phone, query, max_price, location, radius)
        if added:
            msg = f"✅ הוספתי חיפוש: *{query}*"
            if location:
                msg += f"\n📍 אזור: {location}"
            if max_price:
                msg += f"\n💰 עד מחיר: {max_price}"
            if radius:
                msg += f" (רדיוס: {radius} ק״מ)"
            msg += "\n\nאעדכן אותך ברגע שימצא משהו חדש! 🔍"
        else:
            msg = f"החיפוש *{query}* כבר קיים ברשימה שלך."
        send_message(phone, msg)
        return

    # ── עצירת חיפוש ──
    if tl.startswith("עצור ") or tl.startswith("/עצור "):
        _, _, query = t.partition(" ")
        query = query.strip()
        if not query:
            send_message(phone, "כתוב איזה חיפוש לעצור.\nלדוגמה: *עצור אייפון 13*")
            return
        removed = remove_search(phone, query)
        if removed:
            send_message(phone, f"🛑 עצרתי את החיפוש: *{query}*")
        else:
            send_message(phone, f"לא מצאתי חיפוש בשם \"{query}\".\n\nשלח *רשימה* לראות את החיפושים הפעילים.")
        return

    # ── הודעה לא מזוהה ──
    send_message(phone, f"לא הבנתי 😅\n\n{help_text()}")


def help_text() -> str:
    return (
        "👋 *שלום! אני בוט Marketplace*\n\n"
        "אני סורק את Facebook Marketplace ומתריע כשמופיעים פריטים חדשים!\n\n"
        "📝 *פקודות:*\n"
        "• *חפש [מה לחפש]* – הוסף חיפוש\n"
        "• *חפש [מה] עד [מחיר]* – חיפוש עם מחיר מקסימום\n"
        "• *רשימה* – ראה חיפושים פעילים\n"
        "• *עצור [שם]* – עצור חיפוש\n\n"
        "💡 *דוגמאות:*\n"
        "חפש אייפון 13\n"
        "חפש ספה עד 500\n"
        "חפש אופניים עד 1500\n"
        "עצור אייפון 13"
    )


# ──────────────────────────────────────────
#  הפעלה
# ──────────────────────────────────────────

def start_scanner():
    t = threading.Thread(target=run_scanner, daemon=True)
    t.start()
    print("🤖 סורק הופעל ברקע")


if __name__ == "__main__":
    start_scanner()
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
