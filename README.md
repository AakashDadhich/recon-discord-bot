# Recon

Recon is a Discord bot that automatically polls RSS feeds and posts new articles as embeds to designated channels, organised by topic. It is managed entirely through Discord slash commands by authorised users, with no need to edit config files after initial setup.

## Features

- Polls RSS feeds every 5 minutes and posts new articles as rich Discord embeds
- Organise feeds into any channel, each with a custom accent colour
- Automatic feed-down detection - pauses unreachable feeds and posts an alert to the channel
- All management via slash commands: add, remove, pause, resume, and manually trigger checks
- Role-based access control - only users with the designated mod role can use commands
- All responses are ephemeral (private to the invoking user)
- Stores state in a local SQLite database - no external services required

## Self-Hosting

### Prerequisites

- Python 3.11 or later
- A Discord account with access to the [Discord Developer Portal](https://discord.com/developers/applications)

### Setup

1. **Create a Discord application and bot token:**
   - Go to [discord.com/developers/applications](https://discord.com/developers/applications) and click **New Application**
   - Navigate to the **Bot** tab and create a bot user
   - Under **Privileged Gateway Intents**, enable **Server Members Intent** and **Message Content Intent**
   - Click **Reset Token**, copy the token - you will need it in step 4

2. **Clone this repository:**
   ```
   git clone https://github.com/AakashDadhich/recon-discord-bot.git
   cd recon-discord-bot
   ```

3. **Create and activate a virtual environment:**
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   On Windows: `.venv\Scripts\activate`

4. **Copy `.env.example` to `.env` and fill in your values:**
   ```
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `DISCORD_BOT_TOKEN` - the token copied from the Discord developer portal
   - `DISCORD_MOD_ROLE` - the name of the Discord role that can manage the bot (e.g. `recon-admin`)

5. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

6. **Run the bot:**
   ```
   python bot.py
   ```

### Inviting the Bot to Your Server

- In the Discord developer portal, go to **OAuth2 > URL Generator**
- Select scopes: `bot` and `applications.commands`
- Select permissions: **Send Messages**, **Embed Links**, **Read Message History**
- Copy the generated URL, open it in a browser, and select your server

## Required Permissions

| Permission | Purpose |
|---|---|
| Send Messages | Post article embeds and feed alerts |
| Embed Links | Required for rich embed formatting |
| Read Message History | Required for Discord.py |

## OAuth2 Scopes

- `bot`
- `applications.commands`

## Commands

| Command | Description |
|---|---|
| `/addfeed [channel] [url] [colour]` | Add an RSS feed to a channel |
| `/removefeed [channel] [url]` | Remove a feed from a channel |
| `/listfeeds` | Show all registered feeds and their status |
| `/pause [channel]` | Pause all feeds in a channel |
| `/resume [channel]` | Resume all feeds in a channel |
| `/check [channel?]` | Manually trigger a feed check |
| `/recon` | Show bot status and uptime |
| `/help` | Show all available commands |

## Hosting

Recon can be hosted on any always-on server or device, including cloud platforms such as [Railway](https://railway.app) and self-hosted options such as a Raspberry Pi. See [DEPLOY.md](DEPLOY.md) for Raspberry Pi deployment instructions.

The bot requires no open ports or external services - only outbound HTTP access to Discord's API and your RSS feed URLs.
