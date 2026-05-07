import random
import asyncio

from datetime import datetime, time
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    ContextTypes,
)

# =========================
# BOT TOKEN
# =========================
TOKEN = "8762342325:AAEB5kalMTloqqeTySjUKxjAeKDJpsAzy4U"

# =========================
# INDIA TIMEZONE
# =========================
IST = ZoneInfo("Asia/Kolkata")

# =========================
# DAILY LIMIT
# =========================
DAILY_MIN = 60
DAILY_MAX = 90

# =========================
# ACTIVE TIME
# 5:30 AM -> 12:00 AM
# =========================
START_HOUR = 5
START_MINUTE = 30

END_HOUR = 23
END_MINUTE = 59

# =========================
# RANDOM DELAY POOL
# (SECONDS)
# =========================
DELAY_POOL = [
    120,   # 2 min
    240,   # 4 min
    360,   # 6 min
    480,   # 8 min
    900,   # 15 min
    1800,  # 30 min
    2700,  # 45 min
]

# =========================
# STORAGE
# =========================
channel_queues = {}
running_workers = set()

approved_today = 0

daily_limit = random.randint(
    DAILY_MIN,
    DAILY_MAX
)

last_reset_date = datetime.now(IST).date()

# =========================
# ACTIVE HOURS CHECK
# =========================
def active_hours():

    now = datetime.now(IST).time()

    start = time(
        START_HOUR,
        START_MINUTE
    )

    end = time(
        END_HOUR,
        END_MINUTE
    )

    return start <= now <= end


# =========================
# DAILY RESET
# RESET BETWEEN 5-6 AM
# =========================
def reset_daily():

    global approved_today
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

        daily_limit = random.randint(
            DAILY_MIN,
            DAILY_MAX
        )

        last_reset_date = now.date()

        print(
            f"🔄 Daily Reset | "
            f"New Limit: {daily_limit}"
        )


# =========================
# DYNAMIC DELAY
# =========================
def get_dynamic_delay():

    now = datetime.now(IST)

    # ACTIVE WINDOW
    start_minutes = 5 * 60 + 30
    end_minutes = 24 * 60

    total_minutes = (
        end_minutes - start_minutes
    )

    current_minutes = (
        now.hour * 60 + now.minute
    ) - start_minutes

    current_minutes = max(
        current_minutes,
        1
    )

    # EXPECTED APPROVALS
    expected = (
        daily_limit *
        (
            current_minutes /
            total_minutes
        )
    )

    # FAST MODE IF LOW
    if approved_today < expected:

        delay = random.choice([
            120,
            240,
            360,
            480,
            600,
        ])

    # NORMAL RANDOM
    else:

        delay = random.choice(
            DELAY_POOL
        )

    return delay


# =========================
# CHANNEL WORKER
# =========================
async def channel_worker(
    channel_id,
    context
):

    global approved_today

    while channel_queues[channel_id]:

        reset_daily()

        # NIGHT MODE
        while not active_hours():

            print(
                "🌙 Night Mode Active"
            )

            await asyncio.sleep(60)

        # DAILY LIMIT
        if approved_today >= daily_limit:

            print(
                f"⛔ Daily Limit Reached "
                f"{approved_today}/"
                f"{daily_limit}"
            )

            await asyncio.sleep(300)

            continue

        # GET FIRST USER
        data = channel_queues[
            channel_id
        ].pop(0)

        user_id = data["user_id"]
        user_name = data["user_name"]
        channel_name = data["channel_name"]

        # RANDOM DELAY
        delay = get_dynamic_delay()

        minutes = round(delay / 60, 1)

        print(
            f"⏳ [{channel_name}] "
            f"{user_name} waiting "
            f"{minutes} min"
        )

        await asyncio.sleep(delay)

        try:

            await context.bot.approve_chat_join_request(
                chat_id=channel_id,
                user_id=user_id
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


# =========================
# JOIN REQUEST HANDLER
# =========================
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

    # CREATE QUEUE
    if channel_id not in channel_queues:

        channel_queues[
            channel_id
        ] = []

    # ADD USER
    channel_queues[
        channel_id
    ].append({

        "user_id": user_id,
        "user_name": user_name,
        "channel_name": channel_name

    })

    # START WORKER
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


# =========================
# START APP
# =========================
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

print(
    "🚀 Smart Human-Like "
    "Multi-Channel Bot Started..."
)

app.run_polling(
    drop_pending_updates=True,
    close_loop=False
)
