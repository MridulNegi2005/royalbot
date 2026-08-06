# Cosmic Bot

Cosmic Bot is a Discord bot for community servers. It combines music, ranking, moderation, and
engagement features in one application. The bot has run a live community server since 2023. It
contains about 6,000 lines of Python in 25 modular cogs and more than 70 commands.

## Features

### Music
- The bot plays audio through a Lavalink node with the wavelink client.
- It supports a queue, a loop mode, and a play history.
- It shows a "now playing" message and updates the progress bar in real time.

### Ranking
- The bot awards experience points for chat messages and voice activity.
- It generates rank cards as images with Pillow.
- A user unlocks card themes at higher levels.

### Moderation and safety
- The bot provides mute, ban, and slow-mode commands.
- It records each moderation action in an embed log.
- A captcha verification step protects the server against bot raids.

### Engagement and administration
- The bot runs giveaways, welcome messages, button roles, a starboard, and a casino game.
- An administrator loads, unloads, or reloads each cog without a restart.
- A small Flask dashboard shows the bot status.

## Architecture
- The bot uses asynchronous Python. This keeps the event loop responsive under load.
- The database layer changed from synchronous `psycopg2` to asynchronous pooling with `aiopg` and
  `asyncpg`.
- PostgreSQL stores the ranking and economy data. SQLite stores the help data.
- A custom `wavelink.Player` subclass holds the queue, the history, and the loop state.
- The bot reads all credentials from environment variables. Secrets stay in a `.env` file.

## Technology
- Python, py-cord
- Lavalink, wavelink
- PostgreSQL (aiopg, asyncpg), SQLite
- Pillow
- Flask

## Installation

1. Clone the repository.
   ```bash
   git clone https://github.com/MridulNegi2005/royalbot
   cd royalbot
   ```
2. Create a virtual environment and install the dependencies.
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. Copy the environment template and set the values.
   ```bash
   cp .env.example .env
   ```
   Set `DISCORD_BOT_TOKEN`, the `POSTGRES_*` values, the `LAVALINK_*` values, and the API keys.
4. Start the bot.
   ```bash
   python main.py
   ```

The music feature needs a Lavalink node. Set `LAVALINK_URI` and `LAVALINK_PASSWORD` in the `.env` file.
