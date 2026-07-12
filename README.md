# Royalbot (Cosmic Bot)

Royalbot is a feature-rich, multi-purpose Discord bot built with Python. Originally developed for the "Cosmic's Universe" server, it includes a wide range of modules spanning from moderation and levelling to high-quality music streaming and a dedicated modmail system.

## Features

- **Music System**: High-quality music streaming using Lavalink and Wavelink.
- **Moderation**: Comprehensive moderation tools to keep your community safe.
- **Levelling**: Both text and voice chat (VC) XP tracking and levelling systems.
- **Modmail**: A dedicated ticketing system allowing users to privately contact server staff.
- **Giveaways**: Automated giveaway creation and management.
- **Economy & Games**: Casino, games, and an economy system to keep the community engaged.
- **Web Dashboard Integration**: A Flask-based web backend for potential dashboard features and statistics.
- **Starboard**: Highlight the best messages in your server.

## Tech Stack

- **Language**: Python 3
- **Discord Library**: [Pycord](https://pycord.dev/)
- **Audio Library**: [Wavelink](https://github.com/PythonistaGuild/Wavelink) (Requires Lavalink)
- **Database**: PostgreSQL (main data) and SQLite (help menus)
- **Web Server**: Flask
- **Other Services**: Firebase Admin

## Installation

### Prerequisites

- Python 3.8 or higher
- A PostgreSQL database
- A running Lavalink server for music capabilities

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MridulNegi2005/royalbot.git
   cd royalbot
   ```

2. **Install dependencies:**
   Due to dependency conflicts between Pycord and Wavelink, strict installation order is required:
   ```bash
   pip install -r requirements.txt
   pip install wavelink --no-deps
   ```

3. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add the following variables:
   ```env
   POSTGRES_DB=your_database_name
   POSTGRES_USER=your_username
   POSTGRES_PASSWORD=your_password
   POSTGRES_HOST=your_host
   POSTGRES_PORT=5432
   LAVALINK_URI=http://127.0.0.1:2333
   LAVALINK_PASSWORD=youshallnotpass
   ```
   *(Note: The bot also utilizes a `firestore.json` file for Firebase integration if needed).*

4. **Run the bot:**
   The bot consists of multiple entry points depending on the service you are running.
   - For the main bot: `python main.py`
   - For the modmail system: `python modmail.py`
   - For the web server: `python app.py`

## Note
This bot was originally tailored for a specific community. Some features, roles, and channel configurations are hardcoded and may require modification to work seamlessly in a new server environment.
