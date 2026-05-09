```python
import random
import asyncio
import json
import os

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
# TIMEZONE
# =====================================================
IST = ZoneInfo("Asia/Kolkata")

# =====================================================
# DAILY LIMIT
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
BOT_VERSION = "v4.0"

# =====================================================
# LAST UPDATE TIME
# =====================================================
LAST_UPDATE_TIME = datetime.now(IST)

# =====================================================
# STORAGE
# =====================================================
channel_queues = {}
running_workers = set()

approved_today = 0

daily_limit = random.randint(
    DAILY_MIN,
    DAILY_MAX
)

last_reset_date = datetime.now(
    IST
).date()

# =====================================================
# LOAD DATABASE
# =====================================================
def load_database():

    global channel_queues
    global approved_today
    global daily_limit

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

            approved_today = data.get(
                "approved_today",
                0
            )

            daily_limit = data.get(
                "daily_limit",
                random.randint(
                    DAILY_MIN,
                    DAILY_MAX
                )
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

        "approved_today": approved_today,

        "daily_limit": daily_limit

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

    global approved_today
    global daily_limit
    global last_reset_date

    now = datetime.now(IST)

    if (
        5 <= now.hour <= 6
        and now.date() != last_reset_date
    ):

        approved_today = 0

        daily_limit = random.randint(
            DAILY_MIN,
            DAILY_MAX
        )

        last_reset_date = now.date()

        save_database()

        print(
            f"🔄 Daily Reset "
            f"| New Limit: "
            f"{daily_limit}"
        )

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
def get_dynamic_delay():

    now = datetime.now(IST)

    current_hour = now.hour

    pending_users = total_pending_users()

    # =================================================
    # TARGET SYSTEM
    # =================================================
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

    # =================================================
    # IF TARGET NOT COMPLETED
    # =================================================
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

    # =================================================
    # TARGET COMPLETED
    # =================================================
    else:

        # DAY
        if 6 <= current_hour < 13:

            return random.choice([
                300,
                420,
                600,
                900,
            ])

        # EVENING
        elif 13 <= current_hour < 24:

            return random.choice([
                900,
                1200,
                1800,
                2400,
                3600,
            ])

        # NIGHT
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

    global approved_today

    while True:

        reset_daily()

        queue = channel_queues.get(
            str(channel_id),
            []
        )

        # =============================================
        # EMPTY QUEUE
        # =============================================
        if not queue:

            await asyncio.sleep(30)

            continue

        # =============================================
        # DAILY LIMIT
        # =============================================
        if approved_today >= daily_limit:

            print(
                f"🚫 Daily Limit "
                f"Reached "
                f"{approved_today}/"
                f"{daily_limit}"
            )

            await asyncio.sleep(600)

            continue

        # =============================================
        # GET USER
        # =============================================
        data = queue.pop(0)

        save_database()

        user_id = data["user_id"]
        user_name = data["user_name"]
        channel_name = data["channel_name"]

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
            f"{minutes} min "
            f"| Queue: "
            f"{total_pending_users()}"
        )

        await asyncio.sleep(delay)

        # =============================================
        # APPROVE USER
        # =============================================
        try:

            await context.bot.approve_chat_join_request(
                chat_id=int(channel_id),
                user_id=user_id
            )

            approved_today += 1

            save_database()

            print(
                f"✅ Approved "
                f"{user_name} "
                f"in "
                f"{channel_name} "
                f"| Today "
                f"{approved_today}/"
                f"{daily_limit}"
            )

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

    # =============================================
    # CREATE QUEUE
    # =============================================
    if channel_id not in channel_queues:

        channel_queues[channel_id] = []

    # =============================================
    # ADD USER
    # =============================================
    channel_queues[channel_id].append({

        "user_id": user_id,

        "user_name": user_name,

        "channel_name": channel_name

    })

    save_database()

    # =============================================
    # START WORKER
    # =============================================
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

        f"✅ Bot Working Properly\n"

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
```
