import asyncio
import logging
from typing import Optional

import discord
import feedparser
from discord import app_commands
from discord.ext import commands

import config
import db

logger = logging.getLogger(__name__)

COLOUR_CHOICES = [
    app_commands.Choice(name="green", value="0x00FF00"),
    app_commands.Choice(name="blue", value="0x0000FF"),
    app_commands.Choice(name="red", value="0xFF0000"),
    app_commands.Choice(name="pink", value="0xbc42f5"),
    app_commands.Choice(name="yellow", value="0xe3f542"),
    app_commands.Choice(name="purple", value="0x6c42f5"),
]


def _has_mod_role(interaction: discord.Interaction) -> bool:
    return any(r.name == config.MOD_ROLE for r in interaction.user.roles)


def _channel_list(guild: discord.Guild) -> str:
    return ", ".join(f"#{c.name}" for c in guild.text_channels)


def _find_channel(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    return next((c for c in guild.text_channels if c.name == name), None)


class FeedsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="addfeed", description="Add an RSS feed to a channel")
    @app_commands.describe(
        channel="Channel name without #",
        url="Full RSS feed URL",
        colour="Accent colour for article embeds",
    )
    @app_commands.choices(colour=COLOUR_CHOICES)
    async def addfeed(
        self,
        interaction: discord.Interaction,
        channel: str,
        url: str,
        colour: app_commands.Choice[str],
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target = _find_channel(interaction.guild, channel)
        if target is None:
            await interaction.response.send_message(
                f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        loop = asyncio.get_running_loop()
        parsed = await loop.run_in_executor(None, feedparser.parse, url)

        if (parsed.bozo and not parsed.entries) or not parsed.version:
            logger.warning("Could not parse feed: %s", url)
            await interaction.followup.send(
                "Could not reach that RSS feed. Please check the URL and try again. ❌",
                ephemeral=True,
            )
            return

        if db.feed_exists(str(target.id), url):
            await interaction.followup.send(
                f"That feed is already registered to #{channel}. ❌",
                ephemeral=True,
            )
            return

        display_name = parsed.feed.get("title") or url
        from cogs.poller import _entry_id
        last_seen = _entry_id(parsed.entries[0]) if parsed.entries else None

        db.add_feed(
            channel_id=str(target.id),
            channel_name=target.name,
            feed_url=url,
            display_name=display_name,
            colour=colour.value,
            last_seen=last_seen,
        )

        logger.info("Feed added: %s (%s) -> #%s", display_name, url, channel)
        if not parsed.entries:
            await interaction.followup.send(
                f"Feed added to #{channel}. No upcoming events are currently listed. ✅",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"Feed added to #{channel}. ✅", ephemeral=True
            )

    @app_commands.command(name="removefeed", description="Remove a feed from a channel")
    @app_commands.describe(
        channel="Channel name without #",
        name="Display name of the feed to remove",
    )
    async def removefeed(
        self,
        interaction: discord.Interaction,
        channel: str,
        name: str,
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target = _find_channel(interaction.guild, channel)
        if target is None:
            await interaction.response.send_message(
                f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                ephemeral=True,
            )
            return

        removed = db.remove_feed_by_name(str(target.id), name)
        if removed == 0:
            await interaction.response.send_message(
                f"No feed named '{name}' was found in #{channel}. ❌", ephemeral=True
            )
            return

        logger.info("Feed removed: '%s' from #%s", name, channel)
        await interaction.response.send_message(
            f"Feed removed from #{channel}. ✅", ephemeral=True
        )

    @app_commands.command(name="resumefeed", description="Reactivate a single paused feed")
    @app_commands.describe(
        channel="Channel name without #",
        name="Display name of the feed to reactivate",
    )
    async def resumefeed(
        self,
        interaction: discord.Interaction,
        channel: str,
        name: str,
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target = _find_channel(interaction.guild, channel)
        if target is None:
            await interaction.response.send_message(
                f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                ephemeral=True,
            )
            return

        updated = db.set_feed_active_by_name(str(target.id), name, 1)
        if updated == 0:
            await interaction.response.send_message(
                f"No feed named '{name}' was found in #{channel}. ❌", ephemeral=True
            )
            return

        logger.info("Feed '%s' in #%s reactivated by %s", name, channel, interaction.user)
        await interaction.response.send_message(
            f"**{name}** reactivated in #{channel}. ✅", ephemeral=True
        )

    @app_commands.command(name="renamefeed", description="Set a custom display name for a feed")
    @app_commands.describe(
        channel="Channel name without #",
        current_name="Current display name of the feed",
        new_name="New display name",
    )
    async def renamefeed(
        self,
        interaction: discord.Interaction,
        channel: str,
        current_name: str,
        new_name: str,
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target = _find_channel(interaction.guild, channel)
        if target is None:
            await interaction.response.send_message(
                f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                ephemeral=True,
            )
            return

        updated = db.update_display_name(str(target.id), current_name, new_name)
        if updated == 0:
            await interaction.response.send_message(
                f"No feed named '{current_name}' was found in #{channel}. ❌",
                ephemeral=True,
            )
            return

        logger.info("Feed renamed in #%s: '%s' -> '%s'", channel, current_name, new_name)
        await interaction.response.send_message(
            f"Feed renamed to **{new_name}**. ✅", ephemeral=True
        )

    @app_commands.command(name="listfeeds", description="Show all registered feeds")
    async def listfeeds(self, interaction: discord.Interaction) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        feeds = db.get_all_feeds()
        if not feeds:
            await interaction.response.send_message(
                "No feeds registered yet. Use /addfeed to get started. ❌",
                ephemeral=True,
            )
            return

        grouped: dict[str, list] = {}
        for feed in feeds:
            grouped.setdefault(feed["channel_name"], []).append(feed)

        embed = discord.Embed(title="Recon - Active Feeds", colour=0x808080)
        for channel_name, channel_feeds in grouped.items():
            lines = []
            for f in channel_feeds:
                icon = "✅" if f["active"] == 1 else "❌"
                name = f["display_name"] or f["feed_url"]
                lines.append(f"{icon} {name}")
            embed.add_field(
                name=f"#{channel_name}",
                value="\n".join(lines),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setautopause", description="Enable or disable auto-pausing of empty feeds in a channel")
    @app_commands.describe(
        channel="Channel name without #",
        enabled="True = pause after repeated empties (default). False = never auto-pause.",
    )
    async def setautopause(
        self,
        interaction: discord.Interaction,
        channel: str,
        enabled: bool,
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target = _find_channel(interaction.guild, channel)
        if target is None:
            await interaction.response.send_message(
                f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                ephemeral=True,
            )
            return

        count = db.set_never_auto_pause_by_channel(str(target.id), 0 if enabled else 1)
        if count == 0:
            await interaction.response.send_message(
                f"No feeds found in #{channel}. ❌", ephemeral=True
            )
            return

        state = "will auto-pause after repeated empty polls" if enabled else "will never auto-pause"
        logger.info("Auto-pause %s for #%s (%d feed(s))", "enabled" if enabled else "disabled", channel, count)
        await interaction.response.send_message(
            f"{count} feed(s) in #{channel} {state}. ✅", ephemeral=True
        )

    @app_commands.command(
        name="check", description="Manually trigger an immediate feed poll"
    )
    @app_commands.describe(channel="Channel name without # (optional - omit to check all)")
    async def check(
        self,
        interaction: discord.Interaction,
        channel: Optional[str] = None,
    ) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        target_channel_id = None
        if channel is not None:
            target = _find_channel(interaction.guild, channel)
            if target is None:
                await interaction.response.send_message(
                    f"Channel not found. Valid channels are: {_channel_list(interaction.guild)} ❌",
                    ephemeral=True,
                )
                return
            target_channel_id = str(target.id)

        logger.info(
            "/check triggered by %s for %s",
            interaction.user,
            f"#{channel}" if channel else "all channels",
        )
        await interaction.response.send_message("Checking feeds now... ✅", ephemeral=True)

        poller_cog = self.bot.cogs.get("PollerCog")
        if poller_cog is not None:
            await poller_cog.run_poll(target_channel_id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FeedsCog(bot))
