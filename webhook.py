from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

app = Flask(__name__)

# Background workers.
# TradingView must receive HTTP 200 fast, so Telegram + AutoBot forwarding run in background.
executor = ThreadPoolExecutor(max_workers=20)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

EDGE_BOT_TOKEN = os.getenv("EDGE_BOT_TOKEN", BOT_TOKEN)
EDGE_CHAT_ID = os.getenv("EDGE_CHAT_ID", CHAT_ID)

AUTOBOT_BASE = os.getenv("AUTOBOT_BASE", "http://184.174.35.98:5050")

# Active AutoBot URLs only.
AUTOBOT_SWING_URL = os.getenv("AUTOBOT_SWING_URL", AUTOBOT_BASE + "/webhook_swing")
AUTOBOT_EQ_REJECTION_URL = os.getenv("AUTOBOT_EQ_REJECTION_URL", AUTOBOT_BASE + "/webhook_eq_rejection")
AUTOBOT_EDGE_ALGO_URL = os.getenv("AUTOBOT_EDGE_ALGO_URL", AUTOBOT_BASE + "/webhook_edge_algo")

VALID_EDGE_TIMEFRAMES = ["5m", "15m"]


def normalize_timeframe(value):
    tf = str(value or "").strip().lower()
    tf = tf.replace("minutes", "m").replace("minute", "m").replace("mins", "m").replace("min", "m")

    if tf in ["5", "5m", "m5"]:
        return "5m"

    if tf in ["15", "15m", "m15"]:
        return "15m"

    if tf in ["1", "1m", "m1"]:
        return "1m"

    return tf


def send_telegram(message, bot_token, chat_id):
    if not bot_token or not chat_id:
        print("Telegram skipped: missing token/chat id")
        return "Missing Telegram bot token or chat id"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }

    try:
        response = requests.post(url, data=data, timeout=4)
        print("Telegram response:", response.status_code, response.text[:500])
        return response.text
    except Exception as e:
        print("Telegram send error:", str(e))
        return str(e)


def forward_to_autobot(data, url):
    try:
        response = requests.post(url, json=data, timeout=4)
        print("AutoBot URL:", url)
        print("AutoBot response:", response.status_code, response.text[:500])

        return {
            "success": 200 <= response.status_code < 300,
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


def process_strategy(data, strategy_name, bot_token, chat_id, autobot_url, telegram_only=False):
    message = data.get("message", "No message")

    # Background only. Never block TradingView.
    executor.submit(run_telegram_background, message, bot_token, chat_id)

    if not telegram_only:
        executor.submit(run_autobot_background, data, autobot_url)

    return jsonify({
        "status": "accepted",
        "strategy": strategy_name,
        "telegram_only": telegram_only,
        "autobot_url": None if telegram_only else autobot_url,
        "message": "Alert received instantly. Processing in background."
    }), 200


def process_edge_algo(symbol, timeframe):
    timeframe = normalize_timeframe(timeframe)

    if timeframe not in VALID_EDGE_TIMEFRAMES:
        # Still answer fast, but reject unsupported 1m.
        return jsonify({
            "status": "rejected",
            "strategy": "edge_algo",
            "symbol": symbol,
            "timeframe": timeframe,
            "message": "Edge Algo 1m removed. Only 5m and 15m are supported."
        }), 200

    data = request.get_json(silent=True) or {}

    data["bot"] = "edge_algo"
    data["symbol"] = symbol
    data["timeframe"] = timeframe

    original_message = data.get("message", "No message")
    data["message"] = f"⚡ Edge Algo | {symbol} | {timeframe}\\n{original_message}"

    print(f"Received EDGE ALGO data: {symbol} {timeframe}", data)

    return process_strategy(
        data=data,
        strategy_name=f"edge_algo_{symbol.lower()}_{timeframe}",
        bot_token=EDGE_BOT_TOKEN,
        chat_id=EDGE_CHAT_ID,
        autobot_url=AUTOBOT_EDGE_ALGO_URL
    )


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "Webhook is running",
        "active_bots": ["swing", "eq_rejection", "edge_algo"],
        "routes": {
            "swing": "/webhook_swing",
            "eq_rejection": "/webhook_eq_rejection",
            "edge_xauusd_5m": "/webhook_edge_xauusd_5m",
            "edge_xauusd_15m": "/webhook_edge_xauusd_15m",
            "edge_btc_5m": "/webhook_edge_btc_5m",
            "edge_btc_15m": "/webhook_edge_btc_15m"
        }
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "message": "Render webhook is healthy"
    })


@app.route("/webhook", methods=["POST"])
@app.route("/webhook_swing", methods=["POST"])
def webhook_swing():
    data = request.get_json(silent=True) or {}
    print("Received SWING data:", data)
    return process_strategy(
        data=data,
        strategy_name="swing",
        bot_token=BOT_TOKEN,
        chat_id=CHAT_ID,
        autobot_url=AUTOBOT_SWING_URL
    )


@app.route("/webhook_eq_rejection", methods=["POST"])
def webhook_eq_rejection():
    data = request.get_json(silent=True) or {}
    print("Received EQ REJECTION data:", data)
    return process_strategy(
        data=data,
        strategy_name="eq_rejection",
        bot_token=BOT_TOKEN,
        chat_id=CHAT_ID,
        autobot_url=AUTOBOT_EQ_REJECTION_URL
    )


@app.route("/webhook_edge_algo", methods=["POST"])
def webhook_edge_algo():
    data = request.get_json(silent=True) or {}

    symbol = str(data.get("symbol", "XAUUSD")).upper().strip()
    timeframe = normalize_timeframe(data.get("timeframe") or data.get("tf") or data.get("interval"))

    if not timeframe:
        return jsonify({
            "status": "rejected",
            "strategy": "edge_algo",
            "message": "Missing timeframe. Edge Algo supports only 5m and 15m."
        }), 200

    if timeframe not in VALID_EDGE_TIMEFRAMES:
        return jsonify({
            "status": "rejected",
            "strategy": "edge_algo",
            "symbol": symbol,
            "timeframe": timeframe,
            "message": "Edge Algo 1m removed. Only 5m and 15m are supported."
        }), 200

    data["bot"] = "edge_algo"
    data["symbol"] = symbol
    data["timeframe"] = timeframe

    message = data.get("message", "No message")
    data["message"] = f"⚡ Edge Algo | {symbol} | {timeframe}\\n{message}"

    print("Received EDGE ALGO generic data:", data)

    return process_strategy(
        data=data,
        strategy_name=f"edge_algo_{symbol.lower()}_{timeframe}",
        bot_token=EDGE_BOT_TOKEN,
        chat_id=EDGE_CHAT_ID,
        autobot_url=AUTOBOT_EDGE_ALGO_URL
    )


@app.route("/webhook_edge_xauusd_5m", methods=["POST"])
def webhook_edge_xauusd_5m():
    return process_edge_algo("XAUUSD", "5m")


@app.route("/webhook_edge_xauusd_15m", methods=["POST"])
def webhook_edge_xauusd_15m():
    return process_edge_algo("XAUUSD", "15m")


@app.route("/webhook_edge_btc_5m", methods=["POST"])
def webhook_edge_btc_5m():
    return process_edge_algo("BTCUSD", "5m")


@app.route("/webhook_edge_btc_15m", methods=["POST"])
def webhook_edge_btc_15m():
    return process_edge_algo("BTCUSD", "15m")


# Old removed routes.
# Keep them so TradingView does not timeout if an old alert still uses them.
# They return fast but do NOT forward to AutoBot.
@app.route("/webhook_pd_scalp", methods=["POST"])
@app.route("/webhook_limit_order", methods=["POST"])
@app.route("/webhook_ema_scalping", methods=["POST"])
@app.route("/webhook_edge_xauusd_1m", methods=["POST"])
@app.route("/webhook_edge_btc_1m", methods=["POST"])
def removed_routes():
    return jsonify({
        "status": "rejected",
        "message": "This route was removed. Active bots: swing, eq_rejection, edge_algo 5m/15m only."
    }), 200


@app.route("/test_all", methods=["GET"])
def test_all():
    tests = {
        "swing": send_telegram("✅ Test Swing Bot", BOT_TOKEN, CHAT_ID),
        "eq_rejection": send_telegram("✅ Test EQ Rejection Bot", BOT_TOKEN, CHAT_ID),
        "edge_algo": send_telegram("✅ Test Edge Algo", EDGE_BOT_TOKEN, EDGE_CHAT_ID)
    }

    return jsonify({
        "status": "tests sent",
        "results": tests
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
