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

AUTOBOT_SWING_URL = os.getenv(
    "AUTOBOT_SWING_URL",
    "http://184.174.35.98:5050/autobot/webhook"
)

AUTOBOT_SCALPING_URL = os.getenv(
    "AUTOBOT_SCALPING_URL",
    "http://184.174.35.98:5050/autobot/webhook_scalping"
)


def send_telegram(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message
    }

    response = requests.post(url, data=data, timeout=10)
    print("Telegram response:", response.text)

    return response.text


def forward_to_autobot(data, url):
    try:
        response = requests.post(url, json=data, timeout=10)
        print("AutoBot response:", response.text)

        return {
            "success": True,
            "status_code": response.status_code,
            "response": response.text
        }

    except Exception as e:
        print("AutoBot forward error:", str(e))

        return {
            "success": False,
            "error": str(e)
        }


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
    result = send_telegram(
        "✅ Test message from Render to Scalping channel",
        SCALPING_BOT_TOKEN,
        SCALPING_CHAT_ID
    )

    return {
        "status": "test sent to scalping channel",
        "telegram_response": result
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("Received 4H data:", data)

    message = data.get("message", "No message")

    telegram_result = send_telegram(message, BOT_TOKEN, CHAT_ID)

    autobot_result = forward_to_autobot(data, AUTOBOT_SWING_URL)

    return {
        "status": "ok",
        "strategy": "swing",
        "telegram_response": telegram_result,
        "autobot_response": autobot_result
    }


@app.route("/webhook_scalping", methods=["POST"])
def webhook_scalping():
    data = request.json or {}
    print("Received scalping data:", data)

    message = data.get("message", "No message")

    telegram_result = send_telegram(
        message,
        SCALPING_BOT_TOKEN,
        SCALPING_CHAT_ID
    )

    autobot_result = forward_to_autobot(data, AUTOBOT_SCALPING_URL)

    return {
        "status": "ok",
        "strategy": "scalping",
        "telegram_response": telegram_result,
        "autobot_response": autobot_result
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
