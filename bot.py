import sqlite3
import time
from threading import Thread

from flask import Flask
import telebot

BOT_TOKEN = "8861951102:AAEEAVH_P3E533ljMepn8qbzBMLG-4vXq0g"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Zelion XP Bot is running!"

def run_web():
    web_app.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

conn = sqlite3.connect("xp.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    xp INTEGER DEFAULT 0,
    invites INTEGER DEFAULT 0,
    last_message INTEGER DEFAULT 0
)
""")
conn.commit()

XP_PER_MESSAGE = 2
COOLDOWN = 60
MIN_MESSAGE_LENGTH = 5

def get_level(xp: int) -> int:
    return int((xp / 100) ** 0.5) + 1

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "🚀 Zelion XP Bot is online!\n\nUse /rank, /top, and /invite."
    )

@bot.message_handler(commands=["rank"])
def rank(message):
    user = message.from_user
    cur.execute("SELECT xp FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    xp = row[0] if row else 0
    level = get_level(xp)
    name = user.first_name or user.username or "User"

    bot.reply_to(message, f"🏆 {name}\nLevel: {level}\nXP: {xp}")

@bot.message_handler(commands=["top"])
def top(message):
    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, "No XP yet. Start chatting to earn XP.")
        return

    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 Zelion Leaderboard\n\n"

    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else "🔹"
        username = row[0] or "User"
        text += f"{medal} {username} — {row[1]} XP\n"

    bot.reply_to(message, text)

@bot.message_handler(commands=["invite"])
def invite(message):
    try:
        link = bot.create_chat_invite_link(
            chat_id=message.chat.id,
            creates_join_request=False
        )
        bot.reply_to(message, f"🚀 Your invite link:\n{link.invite_link}")
    except Exception as e:
        bot.reply_to(
            message,
            "I could not create an invite link. Make me admin and give me Invite Users permission."
        )
        print("Invite error:", e)

@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message):
    if not message.text:
        return

    text = message.text.strip()

    if text.startswith("/"):
        return

    if len(text) < MIN_MESSAGE_LENGTH:
        return

    user = message.from_user
    now = int(time.time())
    name = user.first_name or user.username or "User"

    cur.execute("SELECT xp, last_message FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    if row:
        xp, last = row

        if now - last < COOLDOWN:
            return

        xp += XP_PER_MESSAGE

        cur.execute("""
        UPDATE users
        SET xp=?, last_message=?, username=?
        WHERE user_id=?
        """, (xp, now, name, user.id))

    else:
        cur.execute("""
        INSERT INTO users(user_id, username, xp, last_message)
        VALUES (?, ?, ?, ?)
        """, (user.id, name, XP_PER_MESSAGE, now))

    conn.commit()

def main():
    keep_alive()
    print("🚀 Zelion XP Bot running on Render with TeleBot...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    main()
