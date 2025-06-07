import telebot
import gspread
import uuid
import json
import os
from flask import Flask, request
from oauth2client.service_account import ServiceAccountCredentials

# ==== Настройки ====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SPREADSHEET_NAME = "TelegramOrders"

# ==== Проверка переменных ====
print(f"✅ TELEGRAM_TOKEN: {'Set' if TELEGRAM_TOKEN else 'Missing'}")
print(f"✅ WEBHOOK_URL: {WEBHOOK_URL}")
print(f"✅ GOOGLE_CREDENTIALS_JSON (start): {GOOGLE_CREDENTIALS_JSON[:100]}...")  # Логируем первые 100 символов

if not TELEGRAM_TOKEN or not GOOGLE_CREDENTIALS_JSON or not WEBHOOK_URL:
    raise ValueError("❌ Одна из переменных окружения отсутствует")

# ==== Google Sheets ====
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ==== Telegram Bot ====
bot = telebot.TeleBot(TELEGRAM_TOKEN)
app = Flask(__name__)
user_data = {}
user_state = {}

# ==== Команда /start ====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    user_data[user_id] = {}
    user_state[user_id] = 'order'
    bot.send_message(user_id, "👋 Hello! What would you like to order?")
    print(f"👉 /start от {user_id}")

# ==== Обработка всех сообщений ====
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text
    print(f"📩 Получено сообщение от {user_id}: {text}")

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
        print(f"📦 Order saved: {row}")
        user_state.pop(user_id, None)
        user_data.pop(user_id, None)

# ==== Webhook endpoint ====
@app.route("/webhook", methods=['POST'])
def webhook():
    print("🌐 Webhook triggered")
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        print(f"📨 Incoming update: {json_string[:200]}...")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        print("⚠️ Unsupported content-type")
        return 'Unsupported Media Type', 415

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

# ==== Установка Webhook ====
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)
print(f"📡 Webhook set to: {WEBHOOK_URL}")



