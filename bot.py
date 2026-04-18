import os
import logging
import random
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import pytz

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
ASH_TELEGRAM_ID = int(os.environ.get("ASH_TELEGRAM_ID", "6698532921"))

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are Ash's personal fitness coach on Telegram. Be concise — this is a chat app, not an essay.
Use short paragraphs. Never use excessive bullet points. Be warm, direct, and encouraging without being cheesy.

Here is everything you need to know about Ash. Never ask him to re-explain this.

PROFILE
Name: Ash (Ashutosh)
Age: 25 | Height: 172cm | Weight: 89kg
Goal: Look strong and confident. Lose fat, build visible muscle over time.
Location: Hornsby, Sydney

SCHEDULE
- Wakes around 7am, leaves home by 7:20am
- At work 8:30am-4:30pm
- Home by 5:20pm
- Cooks dinner, eats when wife (Sasa) gets home, sleeps after
- PRIMARY TRAINING WINDOW: 5:20pm-7:30pm (before dinner)
- Morning training is possible some days but unreliable, especially June-August (Sydney winter)

GYM SITUATION
- Gym membership cancelled, about 1 month left — use it while he can
- After that: 100% home bodyweight training + walking/running outdoors
- Start building bodyweight habits now so the transition is smooth

WHAT HE LIKES
- Walking and running outdoors
- Current running capacity: ~3km max before fatigue

DIET
- Strict vegetarian: no meat, no eggs, no fish
- Eats dairy: milk, paneer, Greek yogurt, cheese
- Daily protein target: 130-140g
- Keep food advice simple and practical — he cooks at home after work
- Never suggest calorie counting unless he asks
- Grocery shopping: shops at Chinese grocery stores and Aldi to save cost
- Prioritise cheap ingredients available at Aldi or Asian grocery stores
- Good cheap protein sources: tofu, canned chickpeas/lentils, Greek yogurt (Aldi), milk, frozen edamame, peanut butter

WHAT HAS FAILED BEFORE
- Late nights on phone then missed gym then guilt then quit
- Plans too hard to complete felt like failure so stopped
- No clear achievable target made gym feel pointless

COACHING RULES:
1. MINIMUM EFFECTIVE DOSE — smallest plan that produces real progress
2. SESSIONS MUST BE COMPLETABLE — if he has 30 min, give a 25-min plan
3. NO STREAK GUILT — if he misses days, give a simple recovery plan, no lecture
4. WINTER CONTINGENCY (June-August) — always have indoor bodyweight alternative ready
5. PROGRESS OVER PERFECTION — a 20-min walk is a win, say so
6. WEEKLY CHECK-IN — respond with: (a) what went well, (b) one adjustment, (c) next week's plan
7. MAX 3 sessions/week unless he asks for more
8. RUNNING PROGRESSION — add no more than 0.5km every 2 weeks

BASELINE PLAN (start here, reset to this if he falls off):
- Mon: 30 min walk or light jog
- Wed: 30 min gym (while membership lasts) or 20 min home bodyweight circuit
- Fri: 30 min walk/run

HOME BODYWEIGHT CIRCUIT:
3 rounds: 10 pushups, 15 squats, 20 sec plank, 10 glute bridges. Total ~20 minutes."""

MICRO_NUDGES = [
    "Quick one — drop and do 10 pushups right now. Just 10. 💪",
    "Stand up. 10 squats. Go. You can sit back down after.",
    "Stretch break — reach arms above your head, hold 10 seconds. Then neck rolls.",
    "30 second plank. Right now. Floor is right there.",
    "Stand up and do 10 calf raises while you read this.",
    "Shoulders tight from the screen? Roll them back 5 times. Do it now.",
    "10 slow glute bridges if you're home. Or 10 squats if you're at work. Pick one.",
    "Wall sit for 20 seconds. Find a wall. Go.",
]

WATER_REMINDERS = [
    "Water check — when did you last drink? Go get a glass now. 🥤",
    "Drink water. Not later. Now.",
    "Have you had enough water today? Go fill your bottle.",
    "Your body is probably more dehydrated than you think. Water. Now.",
]

PHONE_REMINDER = "Hey — it's nearly 10pm. Put the phone down. Your body recovers when you sleep, not when you scroll. Good night Ash. 📵"

conversation_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ASH_TELEGRAM_ID:
        await update.message.reply_text("Sorry, this is a private bot.")
        return
    conversation_history[user_id] = []
    await update.message.reply_text(
        "Hey Ash! I'm your fitness coach. I know your profile, your schedule, and what has failed before.\n\n"
        "What's happening today — are you training or checking in?"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ASH_TELEGRAM_ID:
        return
    conversation_history[user_id] = []
    await update.message.reply_text("Fresh start. What's up?")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ASH_TELEGRAM_ID:
        await update.message.reply_text("Sorry, this is a private bot.")
        return

    user_message = update.message.text

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "content": user_message})

    if len(conversation_history[user_id]) > 20:
        conversation_history[user_id] = conversation_history[user_id][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        max_tokens=600,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history[user_id]
    )

    reply = response.choices[0].message.content
    conversation_history[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply)

async def send_weekly_reminder(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text="Hey Ash — weekly check-in time 📋\n\nHow many sessions did you do? How did you feel? Anything get in the way? Tell me and I'll sort next week's plan."
        )
    except Exception as e:
        logger.error(f"Weekly reminder failed: {e}")

async def send_evening_nudge(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text="Hey — it's 5:30pm. You're home. 30 minutes is all it takes today 🚶"
        )
    except Exception as e:
        logger.error(f"Evening nudge failed: {e}")

async def send_micro_nudge(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text=random.choice(MICRO_NUDGES)
        )
    except Exception as e:
        logger.error(f"Micro nudge failed: {e}")

async def send_water_reminder(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text=random.choice(WATER_REMINDERS)
        )
    except Exception as e:
        logger.error(f"Water reminder failed: {e}")

async def send_phone_reminder(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text=PHONE_REMINDER
        )
    except Exception as e:
        logger.error(f"Phone reminder failed: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    sydney_tz = pytz.timezone("Australia/Sydney")
    scheduler = AsyncIOScheduler(timezone=sydney_tz)

    # Sunday 8pm — weekly check-in
    scheduler.add_job(send_weekly_reminder, "cron", day_of_week="sun", hour=20, minute=0, args=[app])

    # Mon/Wed/Fri 5:30pm — train today nudge
    scheduler.add_job(send_evening_nudge, "cron", day_of_week="mon,wed,fri", hour=17, minute=30, args=[app])

    # Micro movement nudges — 10am and 2pm weekdays
    scheduler.add_job(send_micro_nudge, "cron", day_of_week="mon-fri", hour=10, minute=0, args=[app])
    scheduler.add_job(send_micro_nudge, "cron", day_of_week="mon-fri", hour=14, minute=0, args=[app])

    # Water reminders — 9am, 12pm, 3pm, 6pm every day
    scheduler.add_job(send_water_reminder, "cron", hour=9, minute=0, args=[app])
    scheduler.add_job(send_water_reminder, "cron", hour=12, minute=0, args=[app])
    scheduler.add_job(send_water_reminder, "cron", hour=15, minute=0, args=[app])
    scheduler.add_job(send_water_reminder, "cron", hour=18, minute=0, args=[app])

    # Phone off reminder — 9:45pm every night
    scheduler.add_job(send_phone_reminder, "cron", hour=21, minute=45, args=[app])

    scheduler.start()
    logger.info("Bot started. All schedulers running.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()