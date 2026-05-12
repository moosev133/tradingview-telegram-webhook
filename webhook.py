from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SCALPING_BOT_TOKEN = os.getenv("SCALPING_BOT_TOKEN")
SCALPING_CHAT_ID = os.getenv("SCALPING_CHAT_ID")


def send_telegram(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message
    }

    response = requests.post(url, data=data)
    print("Telegram response:", response.text)

    return response.text


@app.route("/", methods=["GET"])
def home():
    return "Webhook is running"


@app.route("/test", methods=["GET"])
def test():
    result = send_telegram("✅ Test message from Render", BOT_TOKEN, CHAT_ID)

    return {
        "status": "test sent to 4H channel",
        "telegram_response": result
    }


@app.route("/test_scalping", methods=["GET"])
def test_scalping():
    result = send_telegram("✅ Test message from Render to Scalping channel", SCALPING_BOT_TOKEN, SCALPING_CHAT_ID)

    return {
        "status": "test sent to scalping channel",
        "telegram_response": result
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("Received 4H data:", data)

    message = data.get("message", "No message")
    result = send_telegram(message, BOT_TOKEN, CHAT_ID)

    return {
        "status": "ok",
        "telegram_response": result
    }


@app.route("/webhook_scalping", methods=["POST"])
def webhook_scalping():
    data = request.json or {}
    print("Received scalping data:", data)

    message = data.get("message", "No message")
    result = send_telegram(message, SCALPING_BOT_TOKEN, SCALPING_CHAT_ID)

    return {
        "status": "ok",
        "telegram_response": result
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
