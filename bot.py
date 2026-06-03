import sqlite3
import time
from threading import Thread

from flask import Flask
import telebot

BOT_TOKEN = "8861951102:AAGzVtuCA1oYgShCkfP1vB_IbQNnfwkMmKA"

# Users must join Zelion Global before using the bot.
REQUIRED_CHANNEL = -1003423593105
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
    last_message INTEGER DEFAULT 0,
    claimed_x INTEGER DEFAULT 0,
    claimed_linkedin INTEGER DEFAULT 0,
    claimed_instagram INTEGER DEFAULT 0,
    claimed_whatsapp INTEGER DEFAULT 0,
    claimed_tiktok INTEGER DEFAULT 0,
    claimed_youtube INTEGER DEFAULT 0,
    claimed_facebook INTEGER DEFAULT 0
)
""")
conn.commit()

for column in [
    "claimed_x",
    "claimed_linkedin",
    "claimed_instagram",
    "claimed_whatsapp",
    "claimed_tiktok",
    "claimed_youtube",
    "claimed_facebook",
]:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {column} INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass

# =========================
# XP SETTINGS
# =========================

XP_PER_MESSAGE = 2
COOLDOWN = 60
MIN_MESSAGE_LENGTH = 10
SOCIAL_XP_PER_FOLLOW = 30

# Variable XP thresholds.
# These are TOTAL XP required to reach each level.
# Example: Level 2 requires 1,000 total XP, Level 3 requires 2,500 total XP.
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
    11: 40000,
    12: 50000,
    13: 62000,
    14: 76000,
    15: 92000,
    16: 110000,
    17: 130000,
    18: 155000,
    19: 185000,
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
        "column": "claimed_x",
        "command": "claimx",
    },
    "linkedin": {
        "label": "LinkedIn",
        "url": "https://www.linkedin.com/company/zeliontech/",
        "column": "claimed_linkedin",
        "command": "claimlinkedin",
    },
    "instagram": {
        "label": "Instagram",
        "url": "https://www.instagram.com/zeliontech_zev",
        "column": "claimed_instagram",
        "command": "claiminstagram",
    },
    "whatsapp": {
        "label": "WhatsApp",
        "url": "https://whatsapp.com/channel/0029VbCfgk34tRrtdCdS392k",
        "column": "claimed_whatsapp",
        "command": "claimwhatsapp",
    },
    "tiktok": {
        "label": "TikTok",
        "url": "https://www.tiktok.com/@zeliontech_zev",
        "column": "claimed_tiktok",
        "command": "claimtiktok",
    },
    "youtube": {
        "label": "YouTube",
        "url": "https://www.youtube.com/@ZelionTech",
        "column": "claimed_youtube",
        "command": "claimyoutube",
    },
    "facebook": {
        "label": "Facebook",
        "url": "https://www.facebook.com/share/17ikJfJe84/",
        "column": "claimed_facebook",
        "command": "claimfacebook",
    },
}

# =========================
# REQUIRED GROUP / CHANNEL CHECK
# =========================

def is_joined(user_id):
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
# HELPERS
# =========================

def ensure_user(user):
    username = user.first_name or user.username or "User"

    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    if not row:
        cur.execute("""
        INSERT INTO users(user_id, username, xp, last_message)
        VALUES (?, ?, 0, 0)
        """, (user.id, username))
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

    higher_levels = [
        (lvl, required_xp)
        for lvl, required_xp in sorted(LEVEL_THRESHOLDS.items())
        if lvl > current_level
    ]

    if not higher_levels:
        return 0, None

    next_level, next_required_xp = higher_levels[0]
    return max(0, next_required_xp - xp), next_level

def add_xp(user, amount):
    ensure_user(user)
    username = user.first_name or user.username or "User"

    cur.execute("SELECT xp FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()
    current_xp = row[0] if row else 0
    new_xp = current_xp + amount

    cur.execute("""
    UPDATE users
    SET xp=?, username=?
    WHERE user_id=?
    """, (new_xp, username, user.id))
    conn.commit()

    return new_xp

def social_status_text(user):
    ensure_user(user)

    columns = ", ".join([data["column"] for data in SOCIALS.values()])
    cur.execute(f"SELECT {columns} FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    claimed = dict(zip([data["column"] for data in SOCIALS.values()], row or []))

    lines = []
    total_claimed = 0

    for key, data in SOCIALS.items():
        is_claimed = claimed.get(data["column"], 0) == 1
        if is_claimed:
            total_claimed += 1

        mark = "✅" if is_claimed else "⬜"
        lines.append(
            f"{mark} {data['label']}: {data['url']}\nClaim: /{data['command']}"
        )

    remaining = len(SOCIALS) - total_claimed
    total_possible = len(SOCIALS) * SOCIAL_XP_PER_FOLLOW

    return (
        "🌐 ZelionTech Social XP Tasks\n\n"
        f"Each follow = +{SOCIAL_XP_PER_FOLLOW} XP\n"
        f"Total possible = +{total_possible} XP\n\n"
        + "\n\n".join(lines)
        + f"\n\nProgress: {total_claimed}/{len(SOCIALS)} claimed"
        + f"\nRemaining: {remaining}"
        + "\n\n⚠️ One claim per platform. Admins may request proof manually."
    )

def claim_social(message, key):
    if not require_join(message):
        return

    data = SOCIALS[key]
    user = message.from_user
    ensure_user(user)

    column = data["column"]

    cur.execute(f"SELECT xp, {column} FROM users WHERE user_id=?", (user.id,))
    row = cur.fetchone()

    xp = row[0] if row else 0
    already_claimed = row[1] if row else 0

    if already_claimed == 1:
        bot.reply_to(
            message,
            f"✅ You already claimed XP for following {data['label']}."
        )
        return

    xp += SOCIAL_XP_PER_FOLLOW
    username = user.first_name or user.username or "User"

    cur.execute(f"""
    UPDATE users
    SET xp=?, username=?, {column}=1
    WHERE user_id=?
    """, (xp, username, user.id))
    conn.commit()

    needed, next_level = xp_needed_for_next_level(xp)
    next_text = "Max level reached" if next_level is None else f"{needed} XP to Level {next_level}"

    bot.reply_to(
        message,
        f"🎉 {data['label']} follow claimed!\n\n+{SOCIAL_XP_PER_FOLLOW} XP added.\nTotal XP: {xp}\nLevel: {get_level(xp)}\nNext: {next_text}"
    )

def level_table_text():
    rows = [
        "📈 ZelionTech Level Requirements\n",
        "Level 1: 0 XP",
        "Level 2: 1,000 XP",
        "Level 3: 2,500 XP",
        "Level 4: 4,500 XP",
        "Level 5: 7,000 XP",
        "Level 10: 32,000 XP",
        "Level 15: 92,000 XP",
        "Level 20: 220,000 XP",
        "Level 25: 450,000 XP",
        "Level 30: 800,000 XP",
        "Level 40: 1,500,000 XP",
        "Level 50: 2,500,000 XP",
        "Level 75: 6,000,000 XP",
        "Level 100: 12,000,000 XP",
        "\nThe higher you climb, the harder it gets."
    ]
    return "\n".join(rows)

# =========================
# COMMANDS
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    if not require_join(message):
        return

    bot.reply_to(
        message,
        "🚀 Welcome to ZelionTech Rewards!\n\n"
        "Earn XP by chatting, inviting members, and completing social tasks.\n\n"
        "Commands:\n"
        "/rank — view your XP\n"
        "/top — view leaderboard\n"
        "/invite — get your invite link\n"
        "/socials — view social follow tasks\n"
        "/levels — view XP needed per level"
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
    name = user.first_name or user.username or "User"

    next_text = "Max level reached" if next_level is None else f"{needed} XP needed for Level {next_level}"

    bot.reply_to(
        message,
        f"🏆 {name}\n\nLevel: {level}\nXP: {xp}\nNext: {next_text}"
    )

@bot.message_handler(commands=["levels"])
def levels(message):
    if not require_join(message):
        return

    bot.reply_to(message, level_table_text())

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
        level = get_level(row[1])
        text += f"{medal} {username} — Level {level} — {row[1]} XP\n"

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

@bot.message_handler(commands=["socials"])
def socials(message):
    if not require_join(message):
        return

    bot.reply_to(message, social_status_text(message.from_user))

@bot.message_handler(commands=["claimx"])
def claim_x(message):
    claim_social(message, "x")

@bot.message_handler(commands=["claimlinkedin"])
def claim_linkedin(message):
    claim_social(message, "linkedin")

@bot.message_handler(commands=["claiminstagram"])
def claim_instagram(message):
    claim_social(message, "instagram")

@bot.message_handler(commands=["claimwhatsapp"])
def claim_whatsapp(message):
    claim_social(message, "whatsapp")

@bot.message_handler(commands=["claimtiktok"])
def claim_tiktok(message):
    claim_social(message, "tiktok")

@bot.message_handler(commands=["claimyoutube"])
def claim_youtube(message):
    claim_social(message, "youtube")

@bot.message_handler(commands=["claimfacebook"])
def claim_facebook(message):
    claim_social(message, "facebook")

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

    ensure_user(user)

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
        xp = XP_PER_MESSAGE
        cur.execute("""
        INSERT INTO users(user_id, username, xp, last_message)
        VALUES (?, ?, ?, ?)
        """, (
            user.id,
            username,
            xp,
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
    print("📈 Variable level thresholds enabled")
    print(f"🌐 Social reward: {SOCIAL_XP_PER_FOLLOW} XP per platform")

    bot.infinity_polling(
        timeout=60,
        long_polling_timeout=60
    )

if __name__ == "__main__":
    main()
