from flask import Flask, request
import requests
import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

app = Flask(__name__)

# Get values from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data)

    print("Telegram response:", response.text)

    return response.text


@app.route("/", methods=["GET"])
def home():
    return "Webhook is running"


# TEST ROUTE
@app.route("/test", methods=["GET"])
def test():
    result = send_telegram("✅ Test message from Render")

    return {
        "status": "test sent",
        "telegram_response": result
    }


# WEBHOOK ROUTE
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}

    print("Received data:", data)

    message = data.get("message", "No message")

    result = send_telegram(message)

    return {
        "status": "ok",
        "telegram_response": result
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
