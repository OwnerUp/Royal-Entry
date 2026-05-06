import random
import asyncio

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    ContextTypes,
)

TOKEN = "8762342325:AAEB5kalMTloqqeTySjUKxjAeKDJpsAzy4U"

# RANDOM DELAY
MIN_DELAY = 100
MAX_DELAY = 300

# CHANNEL-WISE QUEUES
channel_queues = {}

# RUNNING CHANNEL WORKERS
running_workers = set()


# CHANNEL WORKER
async def channel_worker(channel_id, context):

    while channel_queues[channel_id]:

        data = channel_queues[channel_id].pop(0)

        user_id = data["user_id"]
        user_name = data["user_name"]
        channel_name = data["channel_name"]

        delay = random.randint(MIN_DELAY, MAX_DELAY)

        print(f"⏳ [{channel_name}] Waiting {delay}s for {user_name}")

        await asyncio.sleep(delay)

        try:
            await context.bot.approve_chat_join_request(
                chat_id=channel_id,
                user_id=user_id
            )

            print(f"✅ Approved {user_name} in {channel_name}")

        except Exception as e:
            print(f"❌ Error in {channel_name}: {e}")

    # WORKER STOP
    running_workers.remove(channel_id)

    print(f"🛑 Worker stopped for {channel_name}")


# HANDLE REQUEST
async def handle_request(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.chat_join_request.from_user
    channel = update.chat_join_request.chat

    user_id = user.id
    user_name = user.full_name

    channel_id = channel.id
    channel_name = channel.title

    print(f"📥 New Request: {user_name} -> {channel_name}")

    # CREATE CHANNEL QUEUE
    if channel_id not in channel_queues:
        channel_queues[channel_id] = []

    # ADD TO CHANNEL QUEUE
    channel_queues[channel_id].append({
        "user_id": user_id,
        "user_name": user_name,
        "channel_name": channel_name
    })

    # START WORKER IF NOT RUNNING
    if channel_id not in running_workers:

        running_workers.add(channel_id)

        asyncio.create_task(
            channel_worker(channel_id, context)
        )


# APP
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(
    ChatJoinRequestHandler(handle_request)
)

print("🚀 Smart Multi-Channel Bot Started...")

app.run_polling(
    drop_pending_updates=True,
    close_loop=False
)