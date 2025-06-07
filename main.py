import os
import json
import uuid
from flask import Flask
import telebot
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_NAME = "TelegramOrders"

if not TELEGRAM_TOKEN or not GOOGLE_CREDS_JSON:
    raise ValueError("Missing TELEGRAM_BOT_TOKEN or GOOGLE_CREDENTIALS_JSON")

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

bot = telebot.TeleBot(TELEGRAM_TOKEN)
user_data = {}

# Handlers (оставь свои функции тут — start, ask_name и т.д.)

# Dummy endpoint for Railway
@app.route("/")
def index():
    return "Bot is running!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    bot.polling(none_stop=True)
    app.run(host="0.0.0.0", port=port)

