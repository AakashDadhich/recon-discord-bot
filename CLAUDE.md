# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the bot

```bash
python bot.py
```

Requires a `.env` file in the project root (see `.env.example`). The two required/relevant env vars are:

```
DISCORD_BOT_TOKEN=...
DISCORD_MOD_ROLE=ReconRSS      # name of the Discord role that can use slash commands
```

There are no tests or a linter configured. The only dependency install step is:

```bash
pip install -r requirements.txt
```

## Deployment

Production runs on a Hetzner VPS as a systemd service. To deploy a code change:

```bash
git pull && sudo systemctl restart recon
```

Service file: `/etc/systemd/system/recon.service`. Logs via `sudo journalctl -u recon -f`.

## Architecture

```
bot.py          — entry point; loads cogs, syncs slash commands, generates placeholder PNG
config.py       — reads BOT_TOKEN and MOD_ROLE from environment
db.py           — all SQLite logic (single `feeds` table, file: feeds.db)
cogs/
  poller.py     — background poll loop (@tasks.loop every 5 min)
  feeds.py      — feed management slash commands
  admin.py      — status/moderation slash commands
```

Slash commands are synced globally on every startup (`tree.sync()` in `setup_hook`).

## Key design decisions

**Single-server bot.** There is no `guild_id` column in the database and no guild-scoping anywhere in the code. Do not add one.

**Position-based article detection.** The poller does not compare timestamps. It stores the ID of the most recently posted article as `last_seen` in the DB, then on each poll finds that entry's position in the (timestamp-sorted) feed and posts everything above it. The helper `_entry_id(entry)` in `poller.py` prefers `entry.id` (RSS guid) over `entry.link` — this is intentional for stability. Both `poller.py` and `feeds.py` use `_entry_id`; `feeds.py` imports it directly from `cogs.poller`.

**Feed entries are sorted before comparison.** In `_poll_feed`, entries are sorted by `published_parsed` descending before the `last_seen` lookup. This normalises feeds that don't return entries in chronological order.

**`removefeed` and `renamefeed` match by display name**, not URL. The `db.py` functions are `remove_feed_by_name` and `update_display_name`.

**Bozo handling.** Feeds served with the wrong content-type (e.g. GitHub raw XML files) trigger feedparser's bozo flag but still return valid entries. The poller logs a warning and continues. Only `bozo=True AND entries=[]` (or `entries=[]` alone) marks a feed inactive.

**No binary assets in the repo.** `bot.py` generates `assets/placeholder.png` at runtime if it doesn't exist. The `assets/` directory is not tracked by git.

## Database

Single table `feeds` — key columns: `channel_id`, `channel_name`, `feed_url`, `display_name`, `colour` (hex string e.g. `"0x00FF00"`), `last_seen` (entry guid or link URL), `active` (0/1).

`db.py` uses `_connect()` (not a context-manager pool) — each function opens and closes its own connection.
