import os
import requests
import json
import uuid
from flask import Flask, request
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = f"https://api.telegram.org/bot{TOKEN}"
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "TelegramOrders")

# ===== Google Sheets подключение =====
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS_JSON"))
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
gs_client = gspread.authorize(creds)
sheet = gs_client.open(SPREADSHEET_NAME).sheet1

app = Flask(__name__)

# In-memory state (будет сбрасываться при каждом рестарте!)
user_state = {}
user_data = {}

questions = [
    ("order",   "📝 What would you like to order?"),
    ("name",    "👤 Your name?"),
    ("phone",   "📞 Your phone number?"),
    ("email",   "📧 Your email?"),
    ("address", "🏠 Delivery address or pickup?"),
    ("comment", "💬 Any comments for the order?")
]

def next_question(state):
    idx = [q[0] for q in questions].index(state)
    return questions[idx+1][0] if idx+1 < len(questions) else None

def next_prompt(state):
    idx = [q[0] for q in questions].index(state)
    return questions[idx+1][1] if idx+1 < len(questions) else None

@app.route("/webhook", methods=['POST'])
def webhook():
    data = request.get_json()
    if not data or "message" not in data:
        return '', 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").strip()

    # Новый пользователь или /start — начинаем опрос
    if text == "/start" or chat_id not in user_state:
        user_state[chat_id] = "order"
        user_data[chat_id] = {}
        send_message(chat_id, questions[0][1])
        return '', 200

    state = user_state.get(chat_id, "order")
    user_data[chat_id][state] = text

    # Переходим к следующему вопросу
    nxt = next_question(state)
    if nxt:
        user_state[chat_id] = nxt
        send_message(chat_id, next_prompt(state))
    else:
        # Опрос окончен — сохраняем в Google Sheets!
        order_id = str(uuid.uuid4())[:8]
        row = [
            order_id,
            user_data[chat_id].get('order', ''),
            user_data[chat_id].get('name', ''),
            user_data[chat_id].get('phone', ''),
            user_data[chat_id].get('email', ''),
            user_data[chat_id].get('address', ''),
            user_data[chat_id].get('comment', '')
        ]
        try:
            sheet.append_row(row)
            send_message(chat_id, f"✅ Thank you! Your order (ID: {order_id}) has been saved.")
        except Exception as e:
            send_message(chat_id, f"❌ Error while saving your order: {e}")

        # Чистим данные пользователя
        user_state.pop(chat_id, None)
        user_data.pop(chat_id, None)
    return '', 200

def send_message(chat_id, text):
    try:
        requests.post(
            f"{API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print("Ошибка при отправке сообщения:", e)

@app.route("/", methods=["GET"])
def index():
    return "✅ Flask Telegram-GSheets Order Bot работает!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))



