import random
import asyncio
import json
import os

from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.error import RetryAfter
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
# TIMEZONE
# =====================================================

IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# DAILY LIMIT RANGE
# =====================================================

DAILY_MIN = 70
DAILY_MAX = 90

# =====================================================
# DATABASE FILE
# =====================================================

DB_FILE = "queue_data.json"

# =====================================================
# BOT VERSION
# =====================================================

BOT_VERSION = "v5.0"

# =====================================================
# LAST UPDATE TIME
# =====================================================

LAST_UPDATE_TIME = datetime.now(IST)

# =====================================================
# STORAGE
# =====================================================

channel_queues = {}
running_workers = set()
channel_stats = {}

last_reset_date = datetime.now(IST).date()

# =====================================================
# LOAD DATABASE
# =====================================================

def load_database():

    global channel_queues
    global channel_stats

    if not os.path.exists(DB_FILE):
        save_database()

    try:

        with open(
            DB_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            channel_queues = data.get(
                "queues",
                {}
            )

            channel_stats = data.get(
                "channel_stats",
                {}
            )

        print("✅ Database Loaded")

    except Exception as e:

        print(f"❌ DB Load Error: {e}")

# =====================================================
# SAVE DATABASE
# =====================================================

def save_database():

    data = {

        "queues": channel_queues,

        "channel_stats": channel_stats
    }

    with open(
        DB_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )

# =====================================================
# RESET DAILY
# =====================================================

def reset_daily():

    global last_reset_date

    now = datetime.now(IST)

    if (
        5 <= now.hour <= 6
        and now.date() != last_reset_date
    ):

        for channel_id in channel_stats:

            channel_stats[channel_id][
                "approved_today"
            ] = 0

            channel_stats[channel_id][
                "daily_limit"
            ] = random.randint(
                DAILY_MIN,
                DAILY_MAX
            )

        last_reset_date = now.date()

        save_database()

        print("🔄 All Channel Limits Reset")

# =====================================================
# TOTAL PENDING USERS
# =====================================================

def total_pending_users():

    total = 0

    for queue in channel_queues.values():

        total += len(queue)

    return total

# =====================================================
# SMART DELAY SYSTEM
# =====================================================

def get_dynamic_delay(channel_id):

    now = datetime.now(IST)

    current_hour = now.hour

    pending_users = total_pending_users()

    stats = channel_stats[channel_id]

    approved_today = stats[
        "approved_today"
    ]

    daily_limit = stats[
        "daily_limit"
    ]

    if current_hour < 13:

        target_now = 40

    elif current_hour < 18:

        target_now = int(
            daily_limit * 0.70
        )

    elif current_hour < 22:

        target_now = int(
            daily_limit * 0.90
        )

    else:

        target_now = daily_limit

    if approved_today < target_now:

        if pending_users > 20:

            return random.choice([
                60,
                120,
                180,
                240,
                300,
            ])

        elif pending_users > 10:

            return random.choice([
                120,
                180,
                240,
                300,
                420,
            ])

        else:

            return random.choice([
                180,
                240,
                300,
                420,
                600,
            ])

    else:

        if 6 <= current_hour < 13:

            return random.choice([
                300,
                420,
                600,
                900,
            ])

        elif 13 <= current_hour < 24:

            return random.choice([
                900,
                1200,
                1800,
                2400,
                3600,
            ])

        else:

            return random.choice([
                3600,
                5400,
                7200,
                10800,
            ])

# =====================================================
# CHANNEL WORKER
# =====================================================

async def channel_worker(
    channel_id,
    context
):

    while True:

        reset_daily()

        queue = channel_queues.get(
            str(channel_id),
            []
        )

        stats = channel_stats[channel_id]

        if not queue:

            await asyncio.sleep(30)

            continue

        if (
            stats["approved_today"]
            >=
            stats["daily_limit"]
        ):

            print(
                f"🚫 [{channel_id}] Daily Limit "
                f"Reached "
                f'{stats["approved_today"]}/'
                f'{stats["daily_limit"]}'
            )

            await asyncio.sleep(600)

            continue

        data = queue.pop(0)

        save_database()

        user_id = data["user_id"]
        user_name = data["user_name"]
        channel_name = data["channel_name"]

        delay = get_dynamic_delay(channel_id)

        minutes = round(
            delay / 60,
            1
        )

        print(
            f"⏳ [{channel_name}] "
            f"{user_name} waiting "
            f"{minutes} min "
            f"| Queue: "
            f"{total_pending_users()}"
        )

        await asyncio.sleep(delay)

        try:

            await context.bot.approve_chat_join_request(
                chat_id=int(channel_id),
                user_id=user_id
            )

            stats["approved_today"] += 1

            save_database()

            print(
                f"✅ Approved "
                f"{user_name} "
                f"in "
                f"{channel_name} "
                f"| Today "
                f'{stats["approved_today"]}/'
                f'{stats["daily_limit"]}'
            )

            if not queue:
                channel_queues[channel_id] = []

        except RetryAfter as e:

            wait_time = int(e.retry_after)

            print(
                f"⏳ FloodWait "
                f"{wait_time}s"
            )

            await asyncio.sleep(wait_time)

        except Exception as e:

            error_text = str(e)

            if (
                "USER_ALREADY_PARTICIPANT"
                in error_text.upper()
            ):

                print(
                    f"⚠️ Already Joined: "
                    f"{user_name}"
                )

            else:

                print(
                    f"❌ Error in "
                    f"{channel_name}: "
                    f"{e}"
                )

# =====================================================
# START ALL WORKERS
# =====================================================

async def start_all_workers(context):

    for channel_id in channel_queues.keys():

        if channel_id not in running_workers:

            running_workers.add(channel_id)

            asyncio.create_task(

                channel_worker(
                    channel_id,
                    context
                )

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

    chat = (
        update.chat_join_request
        .chat
    )

    user_id = user.id
    user_name = user.full_name

    channel_id = str(chat.id)
    channel_name = chat.title

    print(
        f"📥 New Request: "
        f"{user_name} "
        f"-> "
        f"{channel_name}"
    )

    if channel_id not in channel_queues:

        channel_queues[channel_id] = []

    if channel_id not in channel_stats:

        channel_stats[channel_id] = {

            "approved_today": 0,

            "daily_limit": random.randint(
                DAILY_MIN,
                DAILY_MAX
            )
        }

    already_exists = any(
        x["user_id"] == user_id
        for x in channel_queues[channel_id]
    )

    if already_exists:
        return

    channel_queues[channel_id].append({

        "user_id": user_id,

        "user_name": user_name,

        "channel_name": channel_name

    })

    save_database()

    if channel_id not in running_workers:

        running_workers.add(channel_id)

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

    user_name = update.effective_user.first_name

    now = datetime.now(IST)

    diff = now - LAST_UPDATE_TIME

    hours = int(
        diff.total_seconds() // 3600
    )

    minutes = int(
        (diff.total_seconds() % 3600) // 60
    )

    await update.message.reply_text(

        f"Hello {user_name} Sir 👋\n\n"

        f"🤖 Bot Version: {BOT_VERSION}\n"

        f"✅ Multi Channel System Active\n"

        f"🔄 Last Updated:\n"
        f"{hours}h {minutes}m ago"

    )

# =====================================================
# MAIN
# =====================================================

load_database()

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

# =====================================================
# STARTUP
# =====================================================

async def on_startup(app):

    print(
        "🚀 Adaptive Smart "
        "Queue Bot Started..."
    )

    await start_all_workers(app)

app.post_init = on_startup

# =====================================================
# RUN BOT
# =====================================================

app.run_polling(
    drop_pending_updates=False,
    close_loop=False,
    timeout=60,
    read_timeout=60,
    write_timeout=60,
    connect_timeout=60,
    pool_timeout=60,
)
