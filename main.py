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
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # например: https://yourdomain.com/webhook

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

# ==== Handlers ====

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    bot.send_message(user_id, "👋 Hello! What would you like to order?")
    bot.register_next_step_handler(message, ask_name)

def ask_name(message):
    user_id = message.chat.id
    user_data[user_id]['order'] = message.text
    bot.send_message(user_id, "👤 Your name?")
    bot.register_next_step_handler(message, ask_phone)

def ask_phone(message):
    user_id = message.chat.id
    user_data[user_id]['name'] = message.text
    bot.send_message(user_id, "📞 Your phone number?")
    bot.register_next_step_handler(message, ask_email)

def ask_email(message):
    user_id = message.chat.id
    user_data[user_id]['phone'] = message.text
    bot.send_message(user_id, "📧 Your email?")
    bot.register_next_step_handler(message, ask_address)

def ask_address(message):
    user_id = message.chat.id
    user_data[user_id]['email'] = message.text
    bot.send_message(user_id, "📍 Delivery address or pickup?")
    bot.register_next_step_handler(message, ask_comment)

def ask_comment(message):
    user_id = message.chat.id
    user_data[user_id]['address'] = message.text
    bot.send_message(user_id, "💬 Any comments for the order?")
    bot.register_next_step_handler(message, save_data)

def save_data(message):
    user_id = message.chat.id
    user_data[user_id]['comment'] = message.text
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

# ==== Установка Webhook и запуск сервера ====

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))


