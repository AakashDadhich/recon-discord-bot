# Security

## Secrets

Recon uses two secrets:

- `DISCORD_BOT_TOKEN` - authenticates the bot with Discord's API
- `DISCORD_MOD_ROLE` - the name of the Discord role permitted to manage the bot

Neither value is committed to this repository.

## Local Development

Secrets are stored in a `.env` file in the project root. This file is listed in `.gitignore` and will never be committed. A `.env.example` file is provided with placeholder values to document the required variables.

To get started locally:
1. Copy `.env.example` to `.env`
2. Fill in your real values
3. Never commit `.env`

## Production

In production - whether on a cloud platform such as Railway or a self-hosted device such as a Raspberry Pi - set `DISCORD_BOT_TOKEN` and `DISCORD_MOD_ROLE` as environment variables rather than using a `.env` file.

## Database

`feeds.db` is a SQLite database file auto-generated at runtime. It contains channel IDs, feed URLs, and display names. It is listed in `.gitignore` and is not committed to the repository. In production, ensure the file is stored on a persistent volume or local disk depending on your hosting setup.

## What Is and Is Not Committed

| File | Committed |
|---|---|
| `.env` | No - gitignored |
| `.env.example` | Yes - contains placeholder values only |
| `feeds.db` | No - gitignored, auto-generated at runtime |
| `bot.py`, `config.py`, etc. | Yes - contains no secrets |
