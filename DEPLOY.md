# Deploying Recon on a Raspberry Pi

This guide covers running Recon as a persistent background service on a Raspberry Pi using `systemd`.

## Prerequisites

- Raspberry Pi running Raspberry Pi OS (Bookworm or later recommended)
- Python 3.11 or later (`python3 --version` to check)
- `git` installed (`sudo apt install git` if not present)
- Outbound internet access from the Pi

## Step 1 - Clone the Repository

```bash
git clone https://github.com/your-username/recon.git
cd recon
```

## Step 2 - Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3 - Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4 - Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in:
- `DISCORD_BOT_TOKEN` - your bot token from the Discord developer portal
- `DISCORD_MOD_ROLE` - the role name that can manage Recon (e.g. `recon-admin`)

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X` in nano).

## Step 5 - Test Manually

Before setting up the service, confirm the bot starts correctly:

```bash
python bot.py
```

You should see `Recon is online as <BotName>#<discriminator>` in the terminal. Press `Ctrl+C` to stop once confirmed.

## Step 6 - Create a systemd Service

Create the service file:

```bash
sudo nano /etc/systemd/system/recon.service
```

Paste the following, replacing the paths with your actual username and project location:

```ini
[Unit]
Description=Recon Discord Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/recon
ExecStart=/home/pi/recon/.venv/bin/python bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save and exit.

## Step 7 - Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable recon
sudo systemctl start recon
```

Check the status:

```bash
sudo systemctl status recon
```

## Viewing Logs

Stream live logs from Recon:

```bash
journalctl -u recon -f
```

View the last 100 lines:

```bash
journalctl -u recon -n 100
```

## Keeping the Clock in Sync

Recon uses UTC timestamps for poll records and embed footers. Confirm your Pi's clock is synced:

```bash
timedatectl
```

NTP sync should show `NTP service: active`. If not, enable it:

```bash
sudo timedatectl set-ntp true
```

## Updating Recon

To pull the latest code and restart the service:

```bash
cd /home/pi/recon
git pull
sudo systemctl restart recon
```

## Stopping or Disabling the Service

Stop without disabling auto-start:

```bash
sudo systemctl stop recon
```

Disable auto-start on boot:

```bash
sudo systemctl disable recon
```
