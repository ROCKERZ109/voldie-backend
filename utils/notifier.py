import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(cafe_name: str, mood: str):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram credentials missing. Alert failed.")
        return False

    message = f"CODE RED: BIRTHDAY ALERT \n\nShe is feeling '{mood}'.\nShe wants you to join her at: *{cafe_name}* ☕\n\nPut your shoes on, Architect!"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Telegram Error: {e}")
        return False
