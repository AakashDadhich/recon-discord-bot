import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

import discord
import feedparser
from discord.ext import commands, tasks

import db


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

    async def run_poll(self, channel_id: Optional[str] = None) -> None:
        feeds = db.get_active_feeds()
        if channel_id:
            feeds = [f for f in feeds if f["channel_id"] == channel_id]

        for feed_row in feeds:
            await self._poll_feed(feed_row)

        self.last_poll_time = datetime.now(timezone.utc)

    async def _poll_feed(self, feed_row) -> None:
        loop = asyncio.get_event_loop()
        parsed = await loop.run_in_executor(
            None, feedparser.parse, feed_row["feed_url"]
        )

        if parsed.bozo and not parsed.entries:
            await self._handle_feed_down(feed_row)
            return

        if not parsed.entries:
            await self._handle_feed_down(feed_row)
            return

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
                new_entries = [entries[0]]
            elif last_seen_index == 0:
                new_entries = []
            else:
                new_entries = list(reversed(entries[:last_seen_index]))

        channel = self.bot.get_channel(int(feed_row["channel_id"]))
        if channel is None:
            return

        for entry in new_entries:
            embed = _build_article_embed(entry, feed_row)
            thumbnail_url = _get_entry_image(entry)
            file = None

            if not thumbnail_url:
                file = discord.File(PLACEHOLDER_PATH, filename="placeholder.png")
                embed.set_thumbnail(url="attachment://placeholder.png")

            try:
                if file:
                    await channel.send(file=file, embed=embed)
                else:
                    await channel.send(embed=embed)
            except discord.HTTPException:
                await asyncio.sleep(5)
                try:
                    if file:
                        file = discord.File(PLACEHOLDER_PATH, filename="placeholder.png")
                        await channel.send(file=file, embed=embed)
                    else:
                        await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

        if new_entries:
            newest_url = getattr(entries[0], "link", last_seen)
            db.update_last_seen(feed_row["id"], newest_url)

    async def _handle_feed_down(self, feed_row) -> None:
        db.set_feed_active_by_id(feed_row["id"], 0)
        channel = self.bot.get_channel(int(feed_row["channel_id"]))
        if channel is None:
            return
        display_name = feed_row["display_name"] or feed_row["feed_url"]
        embed = _build_feed_down_embed(display_name, feed_row["channel_name"])
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PollerCog(bot))
