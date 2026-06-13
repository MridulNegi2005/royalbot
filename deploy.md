# Cosmic Bot — Deployment Guide (Ubuntu VM)

This guide covers deploying the Cosmic Bot with Lavalink on an Ubuntu VM.

## Prerequisites

- Ubuntu 20.04+ (AMD64)
- Python 3.10+
- Docker & Docker Compose
- Git

---

## 1. Install Docker

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group (avoids needing sudo)
sudo usermod -aG docker $USER

# Log out and back in, then verify
docker --version
docker compose version
```

---

## 2. Clone the Repository

```bash
git clone https://github.com/MridulNegi2005/royalbot.git
cd royalbot
```

---

## 3. Configure Environment

Edit `.env` with your actual values:

```bash
nano .env
```

Key variables to verify:
- `DISCORD_BOT_TOKEN` — Your bot token
- `LAVALINK_URI` — `http://127.0.0.1:2333` (default, no change needed)
- `LAVALINK_PASSWORD` — Must match `application.yml` (default: `youshallnotpass`)
- `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` — Already in `lavalink/application.yml`

> **Security Note**: Change `youshallnotpass` to a strong password in both `.env` (LAVALINK_PASSWORD) and `lavalink/application.yml` (lavalink.server.password) if the VM is publicly accessible.

---

## 4. Start Lavalink Server

```bash
cd lavalink
docker compose up -d
cd ..
```

Verify it's running:
```bash
docker compose -f lavalink/docker-compose.yml logs -f
```

You should see:
```
Lavalink is ready to accept connections.
```

The first start will take a minute as it downloads the YouTube and LavaSrc plugins automatically.

---

## 5. Install Python Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 6. Start the Bot

```bash
python main.py
```

You should see:
```
[main.py] Connected to Lavalink node!
[LAVALINK] Node 'CosmicNode' is ready!
We have logged in as CosmicBot#1234
All cogs loaded!
```

---

## 7. Run as a Service (Optional)

To keep the bot running after you close your SSH session:

### Option A: Using `systemd`

Create `/etc/systemd/system/cosmicbot.service`:

```ini
[Unit]
Description=Cosmic Discord Bot
After=network.target docker.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/royalbot
ExecStart=/home/your_username/royalbot/venv/bin/python main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/your_username/royalbot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable cosmicbot
sudo systemctl start cosmicbot
sudo systemctl status cosmicbot
```

### Option B: Using `screen`

```bash
screen -S bot
python main.py
# Press Ctrl+A then D to detach
# Re-attach later: screen -r bot
```

---

## Troubleshooting

### Lavalink won't start
```bash
# Check logs
docker compose -f lavalink/docker-compose.yml logs

# Restart
docker compose -f lavalink/docker-compose.yml restart
```

### Bot can't connect to Lavalink
- Ensure Lavalink is running: `docker ps | grep lavalink`
- Check port: `curl http://localhost:2333/version`
- Verify `.env` values match `application.yml`

### YouTube tracks fail to load
- YouTube may be rate-limiting the server IP
- Enable OAuth in `lavalink/application.yml` under `plugins.youtube.oauth`
- Restart Lavalink after changes: `docker compose -f lavalink/docker-compose.yml restart`

### Spotify tracks fail to load
- Verify Spotify credentials in `lavalink/application.yml`
- Check LavaSrc plugin loaded: look for `LavaSrc` in Lavalink logs
