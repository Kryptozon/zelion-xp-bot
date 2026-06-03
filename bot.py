import sqlite3
import time
from threading import Thread

from flask import Flask
import telebot

BOT_TOKEN = "8861951102:AAGzVtuCA1oYgShCkfP1vB_IbQNnfwkMmKA"

# Users must be members of this Telegram group/channel before using the bot.
REQUIRED_CHANNEL = "-1003423593105"
REQUIRED_CHANNEL_LINK = "https://t.me/zelionglobal"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# =========================
# KEEP RENDER ALIVE
# =========================

web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Zelion XP Bot is running!"

def run_web():
    web_app.run(host="0.0.0.0", port=10000)

def keep_alive():
    Thread(target=run_web, daemon=True).start()

# =========================
# DATABASE
# =========================

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

# =========================
# REQUIRED GROUP / CHANNEL CHECK
# =========================

def is_joined(user_id):
    """
    Returns True only if the user is inside @zelionglobal.
    Important: the bot must be added to @zelionglobal, preferably as admin,
    otherwise Telegram may block membership checks.
    """
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        print(f"JOIN CHECK: user_id={user_id}, status={member.status}")

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:
        print(f"JOIN CHECK ERROR for user_id={user_id}: {e}")
        return False

def force_join(message):
    bot.reply_to(
        message,
        f"🚀 To use this bot, you must join Zelion Global first:\n\n{REQUIRED_CHANNEL_LINK}\n\nAfter joining, try the command again."
    )

def require_join(message):
    if not is_joined(message.from_user.id):
        force_join(message)
        return False
    return True

# =========================
# LEVEL SYSTEM
# =========================

def get_level(xp):
    return int((xp / 100) ** 0.5) + 1

# =========================
# COMMANDS
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    if not require_join(message):
        return

    bot.reply_to(
        message,
        "🚀 Welcome to Zelion XP Rewards!\n\n"
        "Use:\n"
        "/rank — view your XP\n"
        "/top — view leaderboard\n"
        "/invite — get your invite link"
    )

@bot.message_handler(commands=["rank"])
def rank(message):
    if not require_join(message):
        return

    user = message.from_user

    cur.execute(
        "SELECT xp FROM users WHERE user_id=?",
        (user.id,)
    )

    row = cur.fetchone()

    xp = row[0] if row else 0
    level = get_level(xp)
    name = user.first_name or user.username or "User"

    bot.reply_to(
        message,
        f"🏆 {name}\n\nLevel: {level}\nXP: {xp}"
    )

@bot.message_handler(commands=["top"])
def top(message):
    if not require_join(message):
        return

    cur.execute("""
    SELECT username, xp
    FROM users
    ORDER BY xp DESC
    LIMIT 10
    """)

    rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, "Nobody has XP yet. Start chatting to earn XP.")
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
    if not require_join(message):
        return

    try:
        link = bot.create_chat_invite_link(
            chat_id=message.chat.id,
            creates_join_request=False
        )

        bot.reply_to(
            message,
            f"🚀 Your invite link:\n{link.invite_link}"
        )

    except Exception as e:
        print("INVITE ERROR:", e)

        bot.reply_to(
            message,
            "❌ I need admin permission with Invite Users enabled to create invite links."
        )

# =========================
# XP SYSTEM
# =========================

@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message):
    if not require_join(message):
        return

    if not message.text:
        return

    text = message.text.strip()

    if text.startswith("/"):
        return

    if len(text) < MIN_MESSAGE_LENGTH:
        return

    user = message.from_user
    now = int(time.time())
    username = user.first_name or user.username or "User"

    cur.execute("""
    SELECT xp, last_message
    FROM users
    WHERE user_id=?
    """, (user.id,))

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
        """, (xp, now, username, user.id))

    else:
        cur.execute("""
        INSERT INTO users(user_id, username, xp, last_message)
        VALUES (?, ?, ?, ?)
        """, (
            user.id,
            username,
            XP_PER_MESSAGE,
            now
        ))

    conn.commit()

# =========================
# MAIN
# =========================

def main():
    keep_alive()

    print("🚀 Zelion XP Bot running...")
    print(f"🔒 Required join: {REQUIRED_CHANNEL}")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60
    )

if __name__ == "__main__":
    main()
