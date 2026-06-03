import logging
import sqlite3
import time
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "8861951102:AAEEAVH_P3E533ljMepn8qbzBMLG-4vXq0g"

logging.basicConfig(level=logging.INFO)

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

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    cur.execute("SELECT xp FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    xp = row[0] if row else 0
    level = int((xp / 100) ** 0.5) + 1

    await update.message.reply_text(
        f"🏆 {user.first_name}\nLevel: {level}\nXP: {xp}"
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = cur.fetchall()

    text = "🏆 Zelion Leaderboard\n\n"
    medals = ["🥇", "🥈", "🥉"]

    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else "🔹"
        text += f"{medal} {row[0]} — {row[1]} XP\n"

    await update.message.reply_text(text)

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = await context.bot.create_chat_invite_link(
        chat_id=update.effective_chat.id,
        creates_join_request=False
    )

    await update.message.reply_text(
        f"🚀 Your invite link:\n{link.invite_link}"
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    if text.startswith("/"):
        return

    if len(text) < 5:
        return

    user = update.effective_user
    now = int(time.time())

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
        """, (xp, now, user.first_name, user.id))

    else:
        cur.execute("""
        INSERT INTO users(user_id, username, xp, last_message)
        VALUES (?, ?, ?, ?)
        """, (user.id, user.first_name, XP_PER_MESSAGE, now))

    conn.commit()

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    print("🚀 Zelion XP Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
