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

LIMIT_ORDER_BOT_TOKEN = os.getenv("LIMIT_ORDER_BOT_TOKEN", SCALPING_BOT_TOKEN)
LIMIT_ORDER_CHAT_ID = os.getenv("LIMIT_ORDER_CHAT_ID", SCALPING_CHAT_ID)

EDGE_BOT_TOKEN = os.getenv("EDGE_BOT_TOKEN", SCALPING_BOT_TOKEN)
EDGE_CHAT_ID = os.getenv("EDGE_CHAT_ID", SCALPING_CHAT_ID)

AUTOBOT_BASE = os.getenv("AUTOBOT_BASE", "http://184.174.35.98:5050")

AUTOBOT_SWING_URL = os.getenv("AUTOBOT_SWING_URL", AUTOBOT_BASE + "/webhook")
AUTOBOT_PD_SCALP_URL = os.getenv("AUTOBOT_PD_SCALP_URL", AUTOBOT_BASE + "/webhook_pd_scalp")
AUTOBOT_LIMIT_ORDER_URL = os.getenv("AUTOBOT_LIMIT_ORDER_URL", AUTOBOT_BASE + "/webhook_limit_order")
AUTOBOT_EMA_SCALPING_URL = os.getenv("AUTOBOT_EMA_SCALPING_URL", AUTOBOT_BASE + "/webhook_ema_scalping")
AUTOBOT_EQ_REJECTION_URL = os.getenv("AUTOBOT_EQ_REJECTION_URL", AUTOBOT_BASE + "/webhook_eq_rejection")

AUTOBOT_EDGE_ALGO_URL = os.getenv("AUTOBOT_EDGE_ALGO_URL", AUTOBOT_BASE + "/webhook_edge_algo")


def send_telegram(message, bot_token, chat_id):
    if not bot_token or not chat_id:
        print("Telegram error: missing token/chat id")
        return "Missing Telegram bot token or chat id"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {"chat_id": chat_id, "text": message}

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
            "success": 200 <= response.status_code < 300,
            "status_code": response.status_code,
            "response": response.text
        }
    except Exception as e:
        print("AutoBot forward error:", str(e))
        return {"success": False, "error": str(e)}


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


def process_strategy(data, strategy_name, bot_token, chat_id, autobot_url, telegram_only=False):
    message = data.get("message", "No message")

    executor.submit(run_telegram_background, message, bot_token, chat_id)

    if not telegram_only:
        executor.submit(run_autobot_background, data, autobot_url)

    return {
        "status": "accepted",
        "strategy": strategy_name,
        "telegram_only": telegram_only,
        "autobot_url": None if telegram_only else autobot_url,
        "message": "Alert received and processing in background."
    }, 200


def process_edge_algo(symbol, timeframe):
    data = request.json or {}

    data["bot"] = "edge_algo"
    data["symbol"] = symbol
    data["timeframe"] = timeframe

    original_message = data.get("message", "No message")
    data["message"] = f"⚡ Edge Algo | {symbol} | {timeframe}\n{original_message}"

    print(f"Received EDGE ALGO data: {symbol} {timeframe}", data)

    return process_strategy(
        data,
        f"edge_algo_{symbol.lower()}_{timeframe}",
        EDGE_BOT_TOKEN,
        EDGE_CHAT_ID,
        AUTOBOT_EDGE_ALGO_URL
    )


@app.route("/", methods=["GET"])
def home():
    return {
        "status": "Webhook is running",
        "routes": {
            "strategy_1_swing": "/webhook_swing",
            "strategy_2_pd_scalp": "/webhook_pd_scalp",
            "strategy_3_limit_order": "/webhook_limit_order",
            "strategy_4_ema_scalping": "/webhook_ema_scalping",
            "strategy_5_eq_rejection": "/webhook_eq_rejection",

            "edge_xauusd_1m": "/webhook_edge_xauusd_1m",
            "edge_xauusd_5m": "/webhook_edge_xauusd_5m",
            "edge_xauusd_15m": "/webhook_edge_xauusd_15m",
            "edge_btc_1m": "/webhook_edge_btc_1m",
            "edge_btc_5m": "/webhook_edge_btc_5m",
            "edge_btc_15m": "/webhook_edge_btc_15m"
        }
    }


@app.route("/webhook", methods=["POST"])
@app.route("/webhook_swing", methods=["POST"])
def webhook_swing():
    data = request.json or {}
    print("Received STRATEGY 1 swing data:", data)
    return process_strategy(data, "strategy_1_swing_4h_box_v7", BOT_TOKEN, CHAT_ID, AUTOBOT_SWING_URL)


@app.route("/webhook_pd_scalp", methods=["POST"])
def webhook_pd_scalp():
    data = request.json or {}
    print("Received STRATEGY 2 PD scalp data:", data)
    return process_strategy(data, "strategy_2_pd_early_confirmed_scalp", SCALPING_BOT_TOKEN, SCALPING_CHAT_ID, AUTOBOT_PD_SCALP_URL)


@app.route("/webhook_limit_order", methods=["POST"])
def webhook_limit_order():
    data = request.json or {}
    print("Received STRATEGY 3 limit order data:", data)
    return process_strategy(data, "strategy_3_pd_predictive_limit_order", LIMIT_ORDER_BOT_TOKEN, LIMIT_ORDER_CHAT_ID, AUTOBOT_LIMIT_ORDER_URL)


@app.route("/webhook_ema_scalping", methods=["POST"])
def webhook_ema_scalping():
    data = request.json or {}
    print("Received STRATEGY 4 EMA scalping data:", data)
    return process_strategy(data, "strategy_4_ema_scalping", SCALPING_BOT_TOKEN, SCALPING_CHAT_ID, AUTOBOT_EMA_SCALPING_URL)


@app.route("/webhook_eq_rejection", methods=["POST"])
def webhook_eq_rejection():
    data = request.json or {}
    print("Received STRATEGY 5 EQ rejection data:", data)
    return process_strategy(data, "strategy_5_4h_eq_rejection", BOT_TOKEN, CHAT_ID, AUTOBOT_EQ_REJECTION_URL)


@app.route("/webhook_edge_xauusd_1m", methods=["POST"])
def webhook_edge_xauusd_1m():
    return process_edge_algo("XAUUSD", "1m")


@app.route("/webhook_edge_xauusd_5m", methods=["POST"])
def webhook_edge_xauusd_5m():
    return process_edge_algo("XAUUSD", "5m")


@app.route("/webhook_edge_xauusd_15m", methods=["POST"])
def webhook_edge_xauusd_15m():
    return process_edge_algo("XAUUSD", "15m")


@app.route("/webhook_edge_btc_1m", methods=["POST"])
def webhook_edge_btc_1m():
    return process_edge_algo("BTCUSD", "1m")


@app.route("/webhook_edge_btc_5m", methods=["POST"])
def webhook_edge_btc_5m():
    return process_edge_algo("BTCUSD", "5m")


@app.route("/webhook_edge_btc_15m", methods=["POST"])
def webhook_edge_btc_15m():
    return process_edge_algo("BTCUSD", "15m")


@app.route("/test_all", methods=["GET"])
def test_all():
    tests = {
        "swing": send_telegram("✅ Test Strategy 1 Swing", BOT_TOKEN, CHAT_ID),
        "pd_scalp": send_telegram("✅ Test Strategy 2 PD Scalp", SCALPING_BOT_TOKEN, SCALPING_CHAT_ID),
        "limit_order": send_telegram("✅ Test Strategy 3 Limit Order", LIMIT_ORDER_BOT_TOKEN, LIMIT_ORDER_CHAT_ID),
        "ema_scalping": send_telegram("✅ Test Strategy 4 EMA Scalping", SCALPING_BOT_TOKEN, SCALPING_CHAT_ID),
        "eq_rejection": send_telegram("✅ Test Strategy 5 EQ Rejection", BOT_TOKEN, CHAT_ID),
        "edge_algo": send_telegram("✅ Test Edge Algo", EDGE_BOT_TOKEN, EDGE_CHAT_ID)
    }

    return {"status": "tests sent", "results": tests}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
