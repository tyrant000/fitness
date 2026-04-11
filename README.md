# Ash Fitness Bot

Telegram fitness coaching bot powered by Claude. Private bot for Ash only.

## Features
- Responds as a personal fitness coach with full knowledge of Ash's profile
- Remembers conversation history within a session
- Sunday 8pm reminder to do weekly check-in
- Mon/Wed/Fri 5:30pm nudge to train
- /reset command to start a fresh conversation

## Deploy to Railway

### 1. Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. Create Railway project
- Go to railway.app
- New Project → Deploy from GitHub repo → select this repo

### 3. Set environment variables in Railway
Go to your service → Variables → add these:

| Variable | Value |
|----------|-------|
| BOT_TOKEN | Your Telegram bot token from BotFather |
| ANTHROPIC_API_KEY | Your Anthropic API key from console.anthropic.com |
| ASH_TELEGRAM_ID | 6698532921 |

### 4. Deploy
Railway will auto-deploy. Check logs to confirm bot is running.

## Commands
- `/start` — initialise the bot
- `/reset` — clear conversation history, fresh start

## Adding Sasa later
Duplicate bot.py, change the system prompt to Sasa's profile, set her Telegram ID as a separate env variable.
