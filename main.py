import telebot
import gspread
import uuid
import json
import os
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials

# ==== Настройки ====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_NAME = "TelegramOrders"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ==== Google Sheets ====
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ==== Telegram Bot ====
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_data = {}
user_state = {}

# ==== Старт ====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    user_state[user_id] = 'order'
    bot.send_message(user_id, "👋 Hello! What would you like to order?")

# ==== Главный обработчик ====
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text

    if user_id not in user_state:
        bot.send_message(user_id, "Please type /start to begin.")
        return

    state = user_state[user_id]

    if state == 'order':
        user_data[user_id]['order'] = text
        user_state[user_id] = 'name'
        bot.send_message(user_id, "👤 Your name?")
    elif state == 'name':
        user_data[user_id]['name'] = text
        user_state[user_id] = 'phone'
        bot.send_message(user_id, "📞 Your phone number?")
    elif state == 'phone':
        user_data[user_id]['phone'] = text
        user_state[user_id] = 'email'
        bot.send_message(user_id, "📧 Your email?")
    elif state == 'email':
        user_data[user_id]['email'] = text
        user_state[user_id] = 'address'
        bot.send_message(user_id, "📍 Delivery address or pickup?")
    elif state == 'address':
        user_data[user_id]['address'] = text
        user_state[user_id] = 'comment'
        bot.send_message(user_id, "💬 Any comments for the order?")
    elif state == 'comment':
        user_data[user_id]['comment'] = text
        order_id = str(uuid.uuid4())[:8]
        row = [
            order_id,
            user_data[user_id].get('order'),
            user_data[user_id].get('name'),
            user_data[user_id].get('phone'),
            user_data[user_id].get('email'),
            user_data[user_id].get('address'),
            user_data[user_id].get('comment'),
        ]
        sheet.append_row(row)
        bot.send_message(user_id, f"✅ Thank you! Your order (ID: {order_id}) has been saved.")
        # Очистка
        user_state.pop(user_id, None)
        user_data.pop(user_id, None)

# ==== Webhook endpoint ====
@app.route("/webhook", methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Unsupported Media Type', 415

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

# ==== Запуск ====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))

