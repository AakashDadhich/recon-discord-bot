import asyncio
import logging
import os
import struct
import zlib
import discord
from discord.ext import commands

import config
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def _generate_placeholder_png(path: str) -> None:
    """Write a minimal 16x16 grey PNG if the file does not exist."""
    if os.path.exists(path):
        return

    width, height = 16, 16
    grey = 0x80

    raw_rows = b""
    for _ in range(height):
        row = bytes([0] + [grey] * width)
        raw_rows += row

    compressed = zlib.compress(raw_rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        c += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return c

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    idat_data = compressed
    png = (
        signature
        + chunk(b"IHDR", ihdr_data)
        + chunk(b"IDAT", idat_data)
        + chunk(b"IEND", b"")
    )

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    logger.info("Generated placeholder.png")


class ReconBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        db.init_db()
        logger.info("Database initialised")

        _generate_placeholder_png(os.path.join("assets", "placeholder.png"))

        await self.load_extension("cogs.poller")
        await self.load_extension("cogs.feeds")
        await self.load_extension("cogs.admin")
        logger.info("Cogs loaded")

        await self.tree.sync()
        logger.info("Slash commands synced")

    async def on_ready(self) -> None:
        logger.info("Recon is online as %s", self.user)


def main() -> None:
    bot = ReconBot()
    asyncio.run(bot.start(config.BOT_TOKEN))


if __name__ == "__main__":
    main()
