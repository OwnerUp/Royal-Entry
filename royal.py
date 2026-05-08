import random
import asyncio

from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    ContextTypes,
    CommandHandler,
)

# =====================================================
# BOT TOKEN
# =====================================================
TOKEN = "8762342325:AAEB5kalMTloqqeTySjUKxjAeKDJpsAzy4U"

# =====================================================
# INDIA TIMEZONE
# =====================================================
IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# DAILY LIMIT
# =====================================================
DAILY_MIN = 60
DAILY_MAX = 90

# =====================================================
# STORAGE
# =====================================================
channel_queues = {}
running_workers = set()

approved_today = 0
approved_users = set()

daily_limit = random.randint(
    DAILY_MIN,
    DAILY_MAX
)

last_reset_date = datetime.now(
    IST
).date()

# =====================================================
# RESET DAILY
# 5 AM - 6 AM
# =====================================================
def reset_daily():

    global approved_today
    global approved_users
    global daily_limit
    global last_reset_date

    now = datetime.now(IST)

    reset_start = time(5, 0)
    reset_end = time(6, 0)

    if (
        reset_start <= now.time() <= reset_end
        and now.date() != last_reset_date
    ):

        approved_today = 0

        approved_users.clear()

        daily_limit = random.randint(
            DAILY_MIN,
            DAILY_MAX
        )

        last_reset_date = now.date()

        print(
            f"🔄 Daily Reset "
            f"| New Limit: {daily_limit}"
        )

# =====================================================
# SMART DELAY SYSTEM
# =====================================================
def get_dynamic_delay():

    now = datetime.now(IST)

    current_hour = now.hour

    # =================================================
    # FAST MODE
    # 6 AM -> 1 PM
    # =================================================
    if 6 <= current_hour < 13:

        if approved_today < 40:

            return random.choice([
                120,   # 2m
                180,   # 3m
                240,   # 4m
                300,   # 5m
                420,   # 7m
                600,   # 10m
            ])

    # =================================================
    # MEDIUM MODE
    # 1 PM -> 12 AM
    # =================================================
    elif 13 <= current_hour < 24:

        return random.choice([
            900,    # 15m
            1200,   # 20m
            1800,   # 30m
            2400,   # 40m
            2700,   # 45m
            3600,   # 60m
        ])

    # =================================================
    # NIGHT GHOST MODE
    # 12 AM -> 5 AM
    # =================================================
    else:

        return random.choice([
            3600,   # 1h
            5400,   # 1.5h
            7200,   # 2h
            10800,  # 3h
        ])

# =====================================================
# CHANNEL WORKER
# =====================================================
async def channel_worker(
    channel_id,
    context
):

    global approved_today

    while channel_queues[channel_id]:

        reset_daily()

        # =============================================
        # DAILY LIMIT
        # =============================================
        if approved_today >= daily_limit:

            print(
                f"🚫 Daily Limit Reached "
                f"{approved_today}/{daily_limit}"
            )

            await asyncio.sleep(600)

            continue

        # =============================================
        # GET USER
        # =============================================
        data = channel_queues[
            channel_id
        ].pop(0)

        user_id = data["user_id"]
        user_name = data["user_name"]
        channel_name = data["channel_name"]

        # =============================================
        # DUPLICATE PROTECTION
        # =============================================
        unique_key = (
            f"{channel_id}_{user_id}"
        )

        if unique_key in approved_users:

            print(
                f"⚠️ Duplicate Skipped "
                f"{user_name}"
            )

            continue

        # =============================================
        # RANDOM DELAY
        # =============================================
        delay = get_dynamic_delay()

        minutes = round(
            delay / 60,
            1
        )

        print(
            f"⏳ [{channel_name}] "
            f"{user_name} waiting "
            f"{minutes} min"
        )

        await asyncio.sleep(delay)

        # =============================================
        # APPROVE USER
        # =============================================
        try:

            await context.bot.approve_chat_join_request(
                chat_id=channel_id,
                user_id=user_id
            )

            approved_users.add(
                unique_key
            )

            approved_today += 1

            print(
                f"✅ Approved "
                f"{user_name} "
                f"in {channel_name} "
                f"| Today: "
                f"{approved_today}/"
                f"{daily_limit}"
            )

        except Exception as e:

            print(
                f"❌ Error "
                f"in {channel_name}: "
                f"{e}"
            )

    running_workers.remove(
        channel_id
    )

    print(
        f"🛑 Worker stopped "
        f"for {channel_id}"
    )

# =====================================================
# JOIN REQUEST HANDLER
# =====================================================
async def handle_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = (
        update.chat_join_request
        .from_user
    )

    channel = (
        update.chat_join_request
        .chat
    )

    user_id = user.id
    user_name = user.full_name

    channel_id = channel.id
    channel_name = channel.title

    print(
        f"📥 New Request: "
        f"{user_name} -> "
        f"{channel_name}"
    )

    # =============================================
    # CREATE CHANNEL QUEUE
    # =============================================
    if channel_id not in channel_queues:

        channel_queues[
            channel_id
        ] = []

    # =============================================
    # ADD USER
    # =============================================
    channel_queues[
        channel_id
    ].append({

        "user_id": user_id,
        "user_name": user_name,
        "channel_name": channel_name

    })

    # =============================================
    # START WORKER
    # =============================================
    if channel_id not in running_workers:

        running_workers.add(
            channel_id
        )

        asyncio.create_task(
            channel_worker(
                channel_id,
                context
            )
        )

# =====================================================
# START COMMAND
# =====================================================
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "Hello Sir 👋"
    )

# =====================================================
# START BOT
# =====================================================
app = (
    ApplicationBuilder()
    .token(TOKEN)
    .build()
)

app.add_handler(
    ChatJoinRequestHandler(
        handle_request
    )
)

app.add_handler(
    CommandHandler(
        "start",
        start_command
    )
)

print(
    "🚀 Smart Human-Like "
    "Multi-Channel Bot Started..."
)

app.run_polling(
    drop_pending_updates=True,
    close_loop=False
)
