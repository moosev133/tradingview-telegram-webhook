from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

app = Flask(__name__)

executor = ThreadPoolExecutor(max_workers=10)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

SCALPING_BOT_TOKEN = os.getenv("SCALPING_BOT_TOKEN")
SCALPING_CHAT_ID = os.getenv("SCALPING_CHAT_ID")

AUTOBOT_SWING_URL = os.getenv(
    "AUTOBOT_SWING_URL",
    "http://184.174.35.98:5050/webhook"
)

AUTOBOT_SCALPING_URL = os.getenv(
    "AUTOBOT_SCALPING_URL",
    "http://184.174.35.98:5050/webhook_scalping"
)


def send_telegram(message, bot_token, chat_id):
    if not bot_token or not chat_id:
        print("Telegram error: missing BOT_TOKEN or CHAT_ID")
        return "Missing Telegram bot token or chat id"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, data=data, timeout=8)
        print("Telegram response:", response.text)
        return response.text
    except Exception as e:
        print("Telegram send error:", str(e))
        return str(e)


def forward_to_autobot(data, url):
    try:
        response = requests.post(url, json=data, timeout=8)
        print("AutoBot URL:", url)
        print("AutoBot response:", response.text)

        return {
            "success": response.status_code >= 200 and response.status_code < 300,
            "status_code": response.status_code,
            "response": response.text
        }

    except Exception as e:
        print("AutoBot forward error:", str(e))

        return {
            "success": False,
            "error": str(e)
        }


def run_telegram_background(message, bot_token, chat_id):
    try:
        send_telegram(message, bot_token, chat_id)
    except Exception as e:
        print("Background Telegram error:", str(e))


def run_autobot_background(data, url):
    try:
        forward_to_autobot(data, url)
    except Exception as e:
        print("Background AutoBot error:", str(e))


@app.route("/", methods=["GET"])
def home():
    return "Webhook is running"


@app.route("/test", methods=["GET"])
def test():
    result = send_telegram("✅ Test message from Render", BOT_TOKEN, CHAT_ID)

    return {
        "status": "test sent to main channel",
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


@app.route("/test_autobot", methods=["GET"])
def test_autobot():
    data = {
        "message": "LONG SIGNAL XAUUSD\nEntry: 4684\nStop Loss: 4678\nTP1: 4688\nTP2: 4691\nTP3: 4694\nTP4: 4697"
    }

    result = forward_to_autobot(data, AUTOBOT_SWING_URL)

    return {
        "status": "test sent to AutoBot swing",
        "autobot_url": AUTOBOT_SWING_URL,
        "autobot_response": result
    }


@app.route("/test_autobot_scalping", methods=["GET"])
def test_autobot_scalping():
    data = {
        "message": "SCALPING SHORT XAUUSD\nEntry: 4680\nStop Loss: 4690\nTP1: 4676\nTP2: 4673\nTP3: 4670\nTP4: 4667\nTP5: Open"
    }

    result = forward_to_autobot(data, AUTOBOT_SCALPING_URL)

    return {
        "status": "test sent to AutoBot scalping",
        "autobot_url": AUTOBOT_SCALPING_URL,
        "autobot_response": result
    }


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}
    print("Received swing data:", data)

    message = data.get("message", "No message")

    executor.submit(
        run_telegram_background,
        message,
        BOT_TOKEN,
        CHAT_ID
    )

    executor.submit(
        run_autobot_background,
        data,
        AUTOBOT_SWING_URL
    )

    return {
        "status": "accepted",
        "strategy": "swing",
        "message": "Alert received. Telegram and AutoBot are processing in background."
    }, 200


@app.route("/webhook_scalping", methods=["POST"])
def webhook_scalping():
    data = request.json or {}
    print("Received scalping data:", data)

    message = data.get("message", "No message")

    executor.submit(
        run_telegram_background,
        message,
        SCALPING_BOT_TOKEN,
        SCALPING_CHAT_ID
    )

    executor.submit(
        run_autobot_background,
        data,
        AUTOBOT_SCALPING_URL
    )

    return {
        "status": "accepted",
        "strategy": "scalping",
        "message": "Alert received. Telegram and AutoBot are processing in background."
    }, 200


@app.route("/webhook_telegram_only", methods=["POST"])
def webhook_telegram_only():
    data = request.json or {}
    print("Received main telegram-only data:", data)

    message = data.get("message", "No message")

    executor.submit(
        run_telegram_background,
        message,
        BOT_TOKEN,
        CHAT_ID
    )

    return {
        "status": "accepted",
        "strategy": "main_telegram_only",
        "message": "Alert received. Telegram is processing in background. AutoBot was NOT called."
    }, 200


@app.route("/webhook_scalping_telegram_only", methods=["POST"])
def webhook_scalping_telegram_only():
    data = request.json or {}
    print("Received scalping telegram-only data:", data)

    message = data.get("message", "No message")

    executor.submit(
        run_telegram_background,
        message,
        SCALPING_BOT_TOKEN,
        SCALPING_CHAT_ID
    )

    return {
        "status": "accepted",
        "strategy": "scalping_telegram_only",
        "message": "Alert received. Telegram is processing in background. AutoBot was NOT called."
    }, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
