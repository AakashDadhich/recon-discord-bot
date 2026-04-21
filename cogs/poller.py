import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import discord
import feedparser
from discord.ext import commands, tasks

import db

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
PLACEHOLDER_PATH = os.path.join(ASSETS_DIR, "placeholder.png")


def _get_entry_image(entry) -> Optional[str]:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "media_content") and entry.media_content:
        return entry.media_content[0].get("url")
    if hasattr(entry, "enclosures") and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/"):
                return enc.get("url")
    return None


def _truncate(text: str, limit: int = 300) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def _format_published(entry) -> str:
    if hasattr(entry, "published"):
        return entry.published
    if hasattr(entry, "updated"):
        return entry.updated
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M UTC")


def _build_article_embed(entry, feed_row: dict) -> discord.Embed:
    colour = int(feed_row["colour"], 16)
    title = getattr(entry, "title", "No title")
    link = getattr(entry, "link", "")
    summary = getattr(entry, "summary", "")

    embed = discord.Embed(
        title=title,
        url=link,
        description=_truncate(summary),
        colour=colour,
    )

    image_url = _get_entry_image(entry)
    if image_url:
        embed.set_thumbnail(url=image_url)

    display_name = feed_row["display_name"] or "Unknown Feed"
    embed.set_footer(text=f"{display_name} - {_format_published(entry)}")
    return embed


def _build_feed_down_embed(display_name: str, channel_name: str) -> discord.Embed:
    embed = discord.Embed(
        title="Feed Unreachable",
        description=(
            f"The '{display_name}' feed could not be reached and has been paused. "
            f"Use /resume {channel_name} to reactivate it once the feed is back online."
        ),
        colour=0xFF0000,
    )
    embed.set_footer(
        text=datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M UTC")
    )
    return embed


class PollerCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.start_time: datetime = datetime.now(timezone.utc)
        self.last_poll_time: Optional[datetime] = None
        self.poll_feeds.start()

    def cog_unload(self) -> None:
        self.poll_feeds.cancel()

    @tasks.loop(minutes=5)
    async def poll_feeds(self) -> None:
        await self.run_poll()

    @poll_feeds.before_loop
    async def before_poll(self) -> None:
        await self.bot.wait_until_ready()

    @poll_feeds.error
    async def on_poll_error(self, error: Exception) -> None:
        logger.error("Unhandled error in poll loop", exc_info=error)

    async def run_poll(self, channel_id: Optional[str] = None) -> None:
        feeds = db.get_active_feeds()
        if channel_id:
            feeds = [f for f in feeds if f["channel_id"] == channel_id]

        logger.info("Poll cycle starting - %d active feed(s)", len(feeds))

        for feed_row in feeds:
            await self._poll_feed(feed_row)

        self.last_poll_time = datetime.now(timezone.utc)
        logger.info("Poll cycle complete")

    async def _poll_feed(self, feed_row) -> None:
        display_name = feed_row["display_name"] or feed_row["feed_url"]
        logger.debug("Fetching %s", feed_row["feed_url"])

        loop = asyncio.get_running_loop()
        parsed = await loop.run_in_executor(
            None, feedparser.parse, feed_row["feed_url"]
        )

        if parsed.bozo and not parsed.entries:
            logger.warning(
                "%s - feed unreachable (bozo: %s), marking inactive",
                display_name,
                parsed.bozo_exception,
            )
            await self._handle_feed_down(feed_row)
            return

        if not parsed.entries:
            logger.warning("%s - feed returned no entries, marking inactive", display_name)
            await self._handle_feed_down(feed_row)
            return

        if parsed.bozo:
            logger.warning(
                "%s - feed parsed with bozo error but entries found, continuing (bozo: %s)",
                display_name,
                parsed.bozo_exception,
            )

        entries = parsed.entries
        last_seen = feed_row["last_seen"]

        if last_seen is None:
            new_entries = [entries[0]]
        else:
            last_seen_index = next(
                (i for i, e in enumerate(entries) if getattr(e, "link", None) == last_seen),
                None,
            )
            if last_seen_index is None:
                logger.info(
                    "%s - last_seen not found in feed (likely scrolled off), posting latest entry only",
                    display_name,
                )
                new_entries = [entries[0]]
            elif last_seen_index == 0:
                new_entries = []
            else:
                new_entries = list(reversed(entries[:last_seen_index]))

        if not new_entries:
            logger.info("%s - up to date", display_name)
            return

        logger.info("%s - %d new article(s)", display_name, len(new_entries))

        channel = self.bot.get_channel(int(feed_row["channel_id"]))
        if channel is None:
            logger.warning(
                "%s - channel ID %s not found, skipping",
                display_name,
                feed_row["channel_id"],
            )
            return

        for entry in new_entries:
            embed = _build_article_embed(entry, feed_row)
            thumbnail_url = _get_entry_image(entry)
            file = None
            title = getattr(entry, "title", "untitled")

            if not thumbnail_url:
                file = discord.File(PLACEHOLDER_PATH, filename="placeholder.png")
                embed.set_thumbnail(url="attachment://placeholder.png")

            try:
                if file:
                    await channel.send(file=file, embed=embed)
                else:
                    await channel.send(embed=embed)
            except discord.HTTPException as e:
                logger.warning(
                    "%s - failed to send article '%s' (%s), retrying in 5s",
                    display_name,
                    title,
                    e,
                )
                await asyncio.sleep(5)
                try:
                    if file:
                        file = discord.File(PLACEHOLDER_PATH, filename="placeholder.png")
                        await channel.send(file=file, embed=embed)
                    else:
                        await channel.send(embed=embed)
                except discord.HTTPException as e2:
                    logger.error(
                        "%s - retry failed for article '%s' (%s), skipping",
                        display_name,
                        title,
                        e2,
                    )

        newest_url = getattr(entries[0], "link", last_seen)
        db.update_last_seen(feed_row["id"], newest_url)

    async def _handle_feed_down(self, feed_row) -> None:
        display_name = feed_row["display_name"] or feed_row["feed_url"]
        db.set_feed_active_by_id(feed_row["id"], 0)
        logger.warning("%s - marked inactive", display_name)

        channel = self.bot.get_channel(int(feed_row["channel_id"]))
        if channel is None:
            return
        embed = _build_feed_down_embed(display_name, feed_row["channel_name"])
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as e:
            logger.error(
                "%s - failed to send feed-down alert (%s)", display_name, e
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollerCog(bot))
