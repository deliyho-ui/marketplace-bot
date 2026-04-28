#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
שליחת הודעות וואטסאפ דרך Meta Cloud API (חינמי)
"""

import os
import requests


def send_message(phone: str, message: str) -> bool:
    """
    שולח הודעה לטלפון נתון דרך WhatsApp Cloud API.

    env vars נדרשים:
      WHATSAPP_TOKEN    – Access token מ-Meta Developer
      WHATSAPP_PHONE_ID – Phone number ID מ-Meta Developer
    """
    token    = os.environ.get("WHATSAPP_TOKEN", "")
    phone_id = os.environ.get("WHATSAPP_PHONE_ID", "")

    if not token or not phone_id:
        print("❌ חסרים WHATSAPP_TOKEN או WHATSAPP_PHONE_ID בסביבה")
        return False

    url     = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to":   phone,
        "type": "text",
        "text": {"body": message, "preview_url": False},
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            return True
        print(f"❌ שגיאה בשליחה ({resp.status_code}): {resp.text[:200]}")
        return False
    except requests.RequestException as e:
        print(f"❌ שגיאת רשת: {e}")
        return False
