import requests
import os

def notify_discord(message):
    url = os.getenv("DISCORD_WEBHOOK")
    if url:
        try:
            requests.post(url, json={"content": message}, timeout=10)
        except Exception as e:
            print(f"Discord Notify Error: {e}")

def notify_telegram(message):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHATID")
    if token and chat_id:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, data={"chat_id": chat_id, "text": message}, timeout=10)
        except Exception as e:
            print(f"Telegram Notify Error: {e}")

def notify_all(message):
    notify_discord(message)
    notify_telegram(message)