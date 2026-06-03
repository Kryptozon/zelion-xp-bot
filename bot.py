import sqlite3
import time
from threading import Thread

from flask import Flask
import telebot

BOT_TOKEN = "8861951102:AAGzVtuCA1oYgShCkfP1vB_IbQNnfwkMmKA"

REQUIRED_CHANNEL = -1003423593105
REQUIRED_CHANNEL_LINK = "https://t.me/zelionglobal"

# Your personal Telegram user ID
ADMIN_IDS = [1087968824]

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
    last_message INTEGER DEFAULT 0,
    claimed_x INTEGER DEFAULT 0,
    claimed_linkedin INTEGER DEFAULT 0,
    claimed_instagram INTEGER DEFAULT 0,
    claimed_whatsapp INTEGER DEFAULT 0,
    claimed_tiktok INTEGER DEFAULT 0,
    claimed_youtube INTEGER DEFAULT 0,
    claimed_facebook INTEGER DEFAULT 0,
    pending_x INTEGER DEFAULT 0,
    pending_linkedin INTEGER DEFAULT 0,
    pending_instagram INTEGER DEFAULT 0,
    pending_whatsapp INTEGER DEFAULT 0,
    pending_tiktok INTEGER DEFAULT 0,
    pending_youtube INTEGER DEFAULT 0,
    pending_facebook INTEGER DEFAULT 0
)
""")
conn.commit()

for column in [
    "claimed_x", "claimed_linkedin", "claimed_instagram", "claimed_whatsapp",
    "claimed_tiktok", "claimed_youtube", "claimed_facebook",
    "pending_x", "pending_linkedin", "pending_instagram", "pending_whatsapp",
    "pending_tiktok", "pending_youtube", "pending_facebook",
]:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {column} INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

XP_PER_MESSAGE = 2
COOLDOWN = 0
MIN_MESSAGE_LENGTH = 10
SOCIAL_XP_PER_FOLLOW = 30

LEVEL_THRESHOLDS = {
    1: 0,
    2: 1000,
    3: 2500,
    4: 4500,
    5: 7000,
    6: 10000,
    7: 14000,
    8: 19000,
    9: 25000,
    10: 32000,
    15: 92000,
    20: 220000,
    25: 450000,
    30: 800000,
    40: 1500000,
    50: 2500000,
    75: 6000000,
    100: 12000000,
}

SOCIALS = {
    "x": {
        "label": "X",
        "url": "https://x.com/zelion_tech",
        "claimed": "claimed_x",
        "pending": "pending_x",
        "submit": "submitx",
        "approve": "approvex",
        "reject": "rejectx",
    },
    "linkedin": {
        "label": "LinkedIn",
        "url": "https://www.linkedin.com/company/zeliontech/",
        "claimed": "claimed_linkedin",
        "pending": "pending_linkedin",
        "submit": "submitlinkedin",
        "approve": "approvelinkedin",
        "reject": "rejectlinkedin",
    },
    "instagram": {
        "label": "Instagram",
        "url": "https://www.instagram.com/zeliontech_zev",
        "claimed": "claimed_instagram",
        "pending": "pending_instagram",
        "submit": "submitinstagram",
        "approve": "approveinstagram",
        "reject": "rejectinstagram",
    },
    "whatsapp": {
        "label": "WhatsApp",
        "url": "https://whatsapp.com/channel/0029VbCfgk34tRrtdCdS392k",
        "claimed": "claimed_whatsapp",
        "pending": "pending_whatsapp",
        "submit": "submitwhatsapp",
        "approve": "approvewhatsapp",
        "reject": "rejectwhatsapp",
    },
    "tiktok": {
        "label": "TikTok",
        "url": "https://www.tiktok.com/@zeliontech_zev",
        "claimed": "claimed_tiktok",
        "pending": "pending_tiktok",
        "submit": "submittiktok",
        "approve": "approvetiktok",
        "reject": "rejecttiktok",
    },
    "youtube": {
        "label": "YouTube",
        "url": "https://www.youtube.com/@ZelionTech",
        "claimed": "claimed_youtube",
        "pending": "pending_youtube",
        "submit": "submityoutube",
        "approve": "approveyoutube",
        "reject": "rejectyoutube",
    },
    "facebook": {
        "label": "Facebook",
        "url": "https://www.facebook.com/share/17ikJfJe84/",
        "claimed": "claimed_facebook",
        "pending": "pending_facebook",
        "submit": "submitfacebook",
        "approve": "approvefacebook",
        "reject": "rejectfacebook",
    },
}

def is_joined(user_id):
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"JOIN CHECK ERROR for {user_id}: {e}")
        return False

def force_join(message):
    bot.reply_to(
        message,
        f"🚀 To use this bot, you must join Zelion Global first:\n\n{REQUIRED_CHANNEL_LINK}\n\nAfter joining, try again."
    )

def require_join(message):
    if not is_joined(message.from_user.id):
        force_join(message)
        return False
    return True

def is_admin(message):
    # Hardcoded owner/admin ID check.
    if message.from_user.id in ADMIN_IDS:
        return True

    # Backup: allow real Telegram admins in the current group.
    try:
        member = bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        print("ADMIN CHECK ERROR:", e)
        return False

def require_admin(message):
    if not is_admin(message):
        bot.reply_to(
            message,
            f"❌ Admin only command.\nYour Telegram ID is: {message.from_user.id}\nAsk the owner to add this ID to ADMIN_IDS."
        )
        return False
    return True

def ensure_user(user):
    username = user.first_name or user.username or "User"
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(user_id, username, xp, last_message) VALUES (?, ?, 0, 0)",
            (user.id, username)
        )
        conn.commit()

def ensure_user_id(user_id):
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users(user_id, username, xp, last_message) VALUES (?, ?, 0, 0)",
            (user_id, f"User {user_id}")
        )
        conn.commit()

def get_level(xp):
    level = 1
    for lvl, required_xp in sorted(LEVEL_THRESHOLDS.items()):
        if xp >= required_xp:
            level = lvl
        else:
            break
    return level

def xp_needed_for_next_level(xp):
    current_level = get_level(xp)
    higher = [(lvl, req) for lvl, req in sorted(LEVEL_THRESHOLDS.items()) if lvl > current_level]
    if not higher:
        return 0, None
    next_level, next_required = higher[0]
    return max(0, next_required - xp), next_level

def parse_user_id(message):
    parts = message.text.split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None

def get_user_display(user_id):
    cur.execute("SELECT username FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return row[0] if row and row[0] else f"User {user_id}"

def social_status_text(user):
    ensure_user(user)
    columns = []
    for data in SOCIALS.values():
        columns.append(data["claimed"])
        columns.append(data["pending"])

    cur.execute(f"SELECT {', '.join(columns)} FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()
    status = dict(zip(columns, row or []))

    lines = []
    for data in SOCIALS.values():
        claimed = status.get(data["claimed"], 0) == 1
        pending = status.get(data["pending"], 0) == 1
        mark = "✅ Approved" if claimed else ("⏳ Pending admin approval" if pending else "⬜ Not submitted")
        lines.append(f"{mark}\n{data['label']}: {data['url']}\nSubmit proof: /{data['submit']}")

    total_possible = len(SOCIALS) * SOCIAL_XP_PER_FOLLOW
    return (
        "🌐 ZelionTech Social XP Tasks\n\n"
        f"Each approved follow = +{SOCIAL_XP_PER_FOLLOW} XP\n"
        f"Total possible = +{total_possible} XP\n\n"
        + "\n\n".join(lines)
        + "\n\n📸 After submitting, send screenshot proof. Admin approval is required before XP is added."
    )

def submit_social(message, key):
    if not require_join(message):
        return

    data = SOCIALS[key]
    user = message.from_user
    ensure_user(user)

    cur.execute(f"SELECT {data['claimed']}, {data['pending']} FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()
    claimed = row[0] if row else 0
    pending = row[1] if row else 0

    if claimed == 1:
        bot.reply_to(message, f"✅ Your {data['label']} follow was already approved.")
        return

    if pending == 1:
        bot.reply_to(message, f"⏳ Your {data['label']} follow is already pending admin approval.")
        return

    cur.execute(f"UPDATE users SET {data['pending']}=1 WHERE user_id=?", (user.id,))
    conn.commit()

    bot.reply_to(
        message,
        f"⏳ {data['label']} follow submitted for admin approval.\n\n"
        f"User ID: {user.id}\n"
        f"Reward after approval: +{SOCIAL_XP_PER_FOLLOW} XP\n\n"
        f"Admin command: /{data['approve']} {user.id}"
    )

def approve_social(message, key):
    if not require_admin(message):
        return

    user_id = parse_user_id(message)
    if user_id is None:
        bot.reply_to(message, f"Usage: /{SOCIALS[key]['approve']} USER_ID")
        return

    ensure_user_id(user_id)
    data = SOCIALS[key]

    cur.execute(f"SELECT xp, {data['claimed']} FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    xp, claimed = row if row else (0, 0)

    if claimed == 1:
        bot.reply_to(message, f"✅ {data['label']} was already approved for this user.")
        return

    xp += SOCIAL_XP_PER_FOLLOW
    cur.execute(
        f"UPDATE users SET xp=?, {data['claimed']}=1, {data['pending']}=0 WHERE user_id=?",
        (xp, user_id)
    )
    conn.commit()

    bot.reply_to(
        message,
        f"✅ Approved {data['label']} for {get_user_display(user_id)}.\n"
        f"+{SOCIAL_XP_PER_FOLLOW} XP added.\nTotal XP: {xp}\nLevel: {get_level(xp)}"
    )

def reject_social(message, key):
    if not require_admin(message):
        return

    user_id = parse_user_id(message)
    if user_id is None:
        bot.reply_to(message, f"Usage: /{SOCIALS[key]['reject']} USER_ID")
        return

    ensure_user_id(user_id)
    data = SOCIALS[key]
    cur.execute(f"UPDATE users SET {data['pending']}=0 WHERE user_id=?", (user_id,))
    conn.commit()
    bot.reply_to(message, f"❌ Rejected {data['label']} claim for {get_user_display(user_id)}.")

def pending_socials_text():
    lines = ["⏳ Pending Social Approvals\n"]
    found = False
    for data in SOCIALS.values():
        cur.execute(
            f"SELECT user_id, username FROM users WHERE {data['pending']}=1 AND {data['claimed']}=0"
        )
        rows = cur.fetchall()
        if rows:
            found = True
            lines.append(f"\n{data['label']}:")
            for user_id, username in rows:
                lines.append(
                    f"• {username or 'User'} — ID: {user_id}\n  Approve: /{data['approve']} {user_id}\n  Reject: /{data['reject']} {user_id}"
                )
    return "\n".join(lines) if found else "✅ No pending social approvals."

def level_table_text():
    return "\n".join([
        "📈 ZelionTech Level Requirements\n",
        "Level 1: 0 XP",
        "Level 2: 1,000 XP",
        "Level 3: 2,500 XP",
        "Level 4: 4,500 XP",
        "Level 5: 7,000 XP",
        "Level 10: 32,000 XP",
        "Level 20: 220,000 XP",
        "Level 50: 2,500,000 XP",
        "Level 100: 12,000,000 XP",
        "\nThe higher you climb, the harder it gets."
    ])

@bot.message_handler(commands=["myid"])
def myid(message):
    bot.reply_to(message, f"Your Telegram ID: {message.from_user.id}")

@bot.message_handler(commands=["start"])
def start(message):
    if not require_join(message):
        return
    bot.reply_to(
        message,
        "🚀 Welcome to ZelionTech Rewards!\n\n"
        "Commands:\n/rank\n/top\n/invite\n/socials\n/levels\n/myid"
    )

@bot.message_handler(commands=["rank"])
def rank(message):
    if not require_join(message):
        return
    user = message.from_user
    ensure_user(user)
    cur.execute("SELECT xp FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()
    xp = row[0] if row else 0
    level = get_level(xp)
    needed, next_level = xp_needed_for_next_level(xp)
    next_text = "Max level reached" if next_level is None else f"{needed} XP needed for Level {next_level}"
    bot.reply_to(message, f"🏆 {user.first_name}\n\nLevel: {level}\nXP: {xp}\nNext: {next_text}\nUser ID: {user.id}")

@bot.message_handler(commands=["levels"])
def levels(message):
    if not require_join(message):
        return
    bot.reply_to(message, level_table_text())

@bot.message_handler(commands=["top"])
def top(message):
    if not require_join(message):
        return
    cur.execute("SELECT username, xp FROM users ORDER BY xp DESC LIMIT 10")
    rows = cur.fetchall()
    if not rows:
        bot.reply_to(message, "Nobody has XP yet. Start chatting to earn XP.")
        return
    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 Zelion Leaderboard\n\n"
    for i, row in enumerate(rows):
        medal = medals[i] if i < 3 else "🔹"
        text += f"{medal} {row[0] or 'User'} — Level {get_level(row[1])} — {row[1]} XP\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=["invite"])
def invite(message):
    if not require_join(message):
        return
    try:
        link = bot.create_chat_invite_link(chat_id=message.chat.id, creates_join_request=False)
        bot.reply_to(message, f"🚀 Your invite link:\n{link.invite_link}")
    except Exception as e:
        print("INVITE ERROR:", e)
        bot.reply_to(message, "❌ I need admin permission with Invite Users enabled.")

@bot.message_handler(commands=["socials"])
def socials(message):
    if not require_join(message):
        return
    bot.reply_to(message, social_status_text(message.from_user))

@bot.message_handler(commands=["pendingsocials"])
def pending_socials(message):
    if not require_admin(message):
        return
    bot.reply_to(message, pending_socials_text())

# Submit commands
@bot.message_handler(commands=["submitx"])
def submit_x(message): submit_social(message, "x")
@bot.message_handler(commands=["submitlinkedin"])
def submit_linkedin(message): submit_social(message, "linkedin")
@bot.message_handler(commands=["submitinstagram"])
def submit_instagram(message): submit_social(message, "instagram")
@bot.message_handler(commands=["submitwhatsapp"])
def submit_whatsapp(message): submit_social(message, "whatsapp")
@bot.message_handler(commands=["submittiktok"])
def submit_tiktok(message): submit_social(message, "tiktok")
@bot.message_handler(commands=["submityoutube"])
def submit_youtube(message): submit_social(message, "youtube")
@bot.message_handler(commands=["submitfacebook"])
def submit_facebook(message): submit_social(message, "facebook")

# Approval commands
@bot.message_handler(commands=["approvex"])
def approve_x(message): approve_social(message, "x")
@bot.message_handler(commands=["approvelinkedin"])
def approve_linkedin(message): approve_social(message, "linkedin")
@bot.message_handler(commands=["approveinstagram"])
def approve_instagram(message): approve_social(message, "instagram")
@bot.message_handler(commands=["approvewhatsapp"])
def approve_whatsapp(message): approve_social(message, "whatsapp")
@bot.message_handler(commands=["approvetiktok"])
def approve_tiktok(message): approve_social(message, "tiktok")
@bot.message_handler(commands=["approveyoutube"])
def approve_youtube(message): approve_social(message, "youtube")
@bot.message_handler(commands=["approvefacebook"])
def approve_facebook(message): approve_social(message, "facebook")

# Reject commands
@bot.message_handler(commands=["rejectx"])
def reject_x(message): reject_social(message, "x")
@bot.message_handler(commands=["rejectlinkedin"])
def reject_linkedin(message): reject_social(message, "linkedin")
@bot.message_handler(commands=["rejectinstagram"])
def reject_instagram(message): reject_social(message, "instagram")
@bot.message_handler(commands=["rejectwhatsapp"])
def reject_whatsapp(message): reject_social(message, "whatsapp")
@bot.message_handler(commands=["rejecttiktok"])
def reject_tiktok(message): reject_social(message, "tiktok")
@bot.message_handler(commands=["rejectyoutube"])
def reject_youtube(message): reject_social(message, "youtube")
@bot.message_handler(commands=["rejectfacebook"])
def reject_facebook(message): reject_social(message, "facebook")

@bot.message_handler(func=lambda message: True, content_types=["text"])
def handle_message(message):
    if not require_join(message):
        return
    if not message.text:
        return
    text = message.text.strip()
    if text.startswith("/") or len(text) < MIN_MESSAGE_LENGTH:
        return

    user = message.from_user
    now = int(time.time())
    username = user.first_name or user.username or "User"
    ensure_user(user)

    cur.execute("SELECT xp, last_message FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    if row:
        xp, last = row
        if now - last < COOLDOWN:
            return
        xp += XP_PER_MESSAGE
        cur.execute(
            "UPDATE users SET xp=?, last_message=?, username=? WHERE user_id=?",
            (xp, now, username, user.id)
        )
    else:
        cur.execute(
            "INSERT INTO users(user_id, username, xp, last_message) VALUES (?, ?, ?, ?)",
            (user.id, username, XP_PER_MESSAGE, now)
        )
    conn.commit()

def main():
    keep_alive()
    print("🚀 Zelion XP Bot running...")
    print(f"Admin IDs: {ADMIN_IDS}")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == "__main__":
    main()
