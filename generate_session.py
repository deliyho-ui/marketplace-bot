#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
מריץ פעם אחת על המחשב שלך – יוצר סשן פייסבוק להעלאה ל-Railway
"""

import json
import base64
import os
from playwright.sync_api import sync_playwright

SESSION_FILE = os.path.join("data", "fb_session.json")


def main():
    os.makedirs("data", exist_ok=True)

    print("=" * 55)
    print("  יצירת סשן פייסבוק – פעם אחת בלבד")
    print("=" * 55)
    print("מה יקרה:")
    print("  1. ייפתח חלון דפדפן Chrome")
    print("  2. תתחבר לפייסבוק שלך")
    print("  3. תחזור לכאן וללחוץ Enter")
    print("  4. הסקריפט ייתן לך קוד להדביק ב-Railway")
    print("=" * 55 + "\n")

    input("לחץ Enter כדי לפתוח את הדפדפן...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(viewport=None)
        page    = context.new_page()
        page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")

        print("\nהדפדפן נפתח – התחבר לפייסבוק שלך.")
        input("לאחר ההתחברות, חזור לכאן ולחץ Enter... ")

        # שמירה לקובץ
        storage = context.storage_state()
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(storage, f)

        # קידוד ל-base64 לשימוש ב-Railway
        b64 = base64.b64encode(json.dumps(storage).encode()).decode()

        browser.close()

    print("\n" + "=" * 55)
    print("✅ הסשן נשמר בהצלחה!")
    print("=" * 55)
    print()
    print("📋 העתק את כל השורה הארוכה למטה")
    print("   ושמור אותה – תצטרך אותה ב-Railway:")
    print()
    print(b64)
    print()
    print("=" * 55)
    print("הסשן נשמר גם בקובץ: data/fb_session.json")
    print("=" * 55)


if __name__ == "__main__":
    main()
