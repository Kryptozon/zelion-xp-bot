import telebot
from telebot.types import Message
from flask import Flask
from threading import Thread

BOT_TOKEN = "YOUR_BOT_TOKEN"

bot = telebot.TeleBot(BOT_TOKEN)

REQUIRED_CHANNEL = -1003423593105
ADMIN_IDS = [8883747941]

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web).start()

def is_admin(user_id):
    return user_id in ADMIN_IDS

@bot.message_handler(commands=['start'])
def start(message: Message):
    bot.reply_to(message, "🚀 Welcome to ZelionTech Rewards Bot")

@bot.message_handler(commands=['pendingsocials'])
def pending(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Admin only command.")
        return
    bot.reply_to(message, "📋 Pending socials list")

@bot.message_handler(commands=['approvex'])
def approve_x(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Admin only command.")
        return

    try:
        user_id = int(message.text.split()[1])
        bot.send_message(user_id, "✅ Your X follow was approved! +30 XP")
        bot.reply_to(message, "✅ Approved successfully.")
    except:
        bot.reply_to(message, "Usage: /approvex USER_ID")

keep_alive()

print("🚀 Bot running...")

bot.infinity_polling()
