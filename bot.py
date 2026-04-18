import os
import logging
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
- At work 8:30am–4:30pm
- Home by 5:20pm
- Cooks dinner, eats when wife (Sasa) gets home, sleeps after
- PRIMARY TRAINING WINDOW: 5:20pm–7:30pm (before dinner)
- Morning training is possible some days but unreliable, especially June–August (Sydney winter)

WHAT HE LIKES
- Walking and running outdoors
- Current running capacity: ~3km max before fatigue
- Has active gym membership, 15 min walk from home

DIET
- Strict vegetarian: no meat, no eggs, no fish
- Eats dairy: milk, paneer, Greek yogurt, cheese
- Daily protein target: 130–140g
- Good sources: lentils, chickpeas, tofu, paneer, Greek yogurt, milk, whey protein
- Keep food advice simple and practical — he cooks at home after work
- Never suggest calorie counting unless he asks

WHAT HAS FAILED BEFORE
- Late nights on phone → missed gym → guilt → quit
- Plans too hard to complete → felt like failure → stopped
- No clear achievable target made gym feel pointless

COACHING RULES — follow strictly:
1. MINIMUM EFFECTIVE DOSE — smallest plan that produces real progress
2. SESSIONS MUST BE COMPLETABLE — if he has 30 min, give a 25-min plan
3. NO STREAK GUILT — if he misses days, give a simple recovery plan, no lecture
4. WINTER CONTINGENCY (June–August) — always have indoor alternative ready
5. PROGRESS OVER PERFECTION — a 20-min walk is a win, say so
6. WEEKLY CHECK-IN — respond with: (a) what went well, (b) one adjustment, (c) next week's plan
7. MAX 3 sessions/week unless he asks for more
8. RUNNING PROGRESSION — add no more than 0.5km every 2 weeks

BASELINE PLAN (start here, reset to this if he falls off):
- Mon: 30 min walk or light jog
- Wed: 30 min gym — 3 exercises only, full body, light weights
- Fri: 30 min walk/run"""

conversation_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ASH_TELEGRAM_ID:
        await update.message.reply_text("Sorry, this is a private bot.")
        return
    conversation_history[user_id] = []
    await update.message.reply_text(
        "Hey Ash! 💪 I'm your fitness coach. I know your profile, your schedule, and what's failed before.\n\n"
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

    # Keep last 20 messages to avoid token bloat
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
            text="Hey Ash — weekly check-in time 📋\n\nJust tell me: how many sessions did you do this week, how did you feel, and anything that got in the way? I'll sort next week's plan."
        )
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")

async def send_evening_nudge(app):
    try:
        await app.bot.send_message(
            chat_id=ASH_TELEGRAM_ID,
            text="Hey — it's 5:30pm. You're home. 30 minutes is all it takes today 🚶"
        )
    except Exception as e:
        logger.error(f"Failed to send nudge: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    sydney_tz = pytz.timezone("Australia/Sydney")
    scheduler = AsyncIOScheduler(timezone=sydney_tz)

    # Sunday 8pm Sydney — weekly check-in reminder
    scheduler.add_job(
        send_weekly_reminder,
        trigger="cron",
        day_of_week="sun",
        hour=20,
        minute=0,
        args=[app]
    )

    # Monday, Wednesday, Friday 5:30pm — evening nudge
    scheduler.add_job(
        send_evening_nudge,
        trigger="cron",
        day_of_week="mon,wed,fri",
        hour=17,
        minute=30,
        args=[app]
    )

    scheduler.start()
    logger.info("Bot started. Schedulers running.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()