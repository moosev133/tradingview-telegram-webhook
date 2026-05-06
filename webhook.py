from flask import Flask, request
import requests

app = Flask(__name__)

BOT_TOKEN = "8796444971:AAHGIrUfngVr6uUwaz-2N29KGmZZ1icCt0A"
CHAT_ID = "5948376811"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    response = requests.post(url, data=data)

    print(response.text)

@app.route("/", methods=["GET"])
def home():
    return "Webhook is running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json or {}

    message = data.get("message", "No message")

    send_telegram(message)

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
