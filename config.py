from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
MOD_ROLE: str = os.getenv("DISCORD_MOD_ROLE", "recon-admin")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set. Check your .env file.")
