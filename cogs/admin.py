import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

import config
import db

logger = logging.getLogger(__name__)


def _has_mod_role(interaction: discord.Interaction) -> bool:
    return any(r.name == config.MOD_ROLE for r in interaction.user.roles)


def _channel_list(guild: discord.Guild) -> str:
    return ", ".join(f"#{c.name}" for c in guild.text_channels)


def _find_channel(guild: discord.Guild, name: str) -> Optional[discord.TextChannel]:
    return next((c for c in guild.text_channels if c.name == name), None)


def _format_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes and not days:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return ", ".join(parts) if parts else "less than a minute"


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="pause", description="Pause all feeds in a channel")
    @app_commands.describe(channel="Channel name without #")
    async def pause(self, interaction: discord.Interaction, channel: str) -> None:
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

        feeds = db.get_feeds_by_channel(str(target.id))
        active_feeds = [f for f in feeds if f["active"] == 1]
        if not active_feeds:
            await interaction.response.send_message(
                f"All feeds in #{channel} are already paused. ❌", ephemeral=True
            )
            return

        db.set_active(str(target.id), 0)
        logger.info("Feeds in #%s paused by %s", channel, interaction.user)
        await interaction.response.send_message(
            f"Feeds in #{channel} paused. ⏸️", ephemeral=True
        )

    @app_commands.command(name="resume", description="Resume all paused feeds in a channel")
    @app_commands.describe(channel="Channel name without #")
    async def resume(self, interaction: discord.Interaction, channel: str) -> None:
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

        feeds = db.get_feeds_by_channel(str(target.id))
        paused_feeds = [f for f in feeds if f["active"] == 0]
        if not paused_feeds:
            await interaction.response.send_message(
                f"All feeds in #{channel} are already active. ❌", ephemeral=True
            )
            return

        db.set_active(str(target.id), 1)
        logger.info("Feeds in #%s resumed by %s", channel, interaction.user)
        await interaction.response.send_message(
            f"Feeds in #{channel} resumed. ▶️", ephemeral=True
        )

    @app_commands.command(name="recon", description="Show bot status and uptime")
    async def recon(self, interaction: discord.Interaction) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        poller_cog = self.bot.cogs.get("PollerCog")
        now = datetime.now(timezone.utc)

        if poller_cog:
            uptime_delta = now - poller_cog.start_time
            last_poll = poller_cog.last_poll_time
        else:
            uptime_delta = timedelta(0)
            last_poll = None

        active_count, paused_count = db.get_feed_counts()

        last_poll_str = (
            last_poll.strftime("%a, %d %b %Y %H:%M UTC") if last_poll else "Not yet run"
        )
        if last_poll:
            next_poll_dt = last_poll + timedelta(minutes=5)
            next_poll_str = next_poll_dt.strftime("%a, %d %b %Y %H:%M UTC")
        else:
            next_poll_str = "Pending"

        embed = discord.Embed(title="Recon - Status", colour=0x808080)
        embed.add_field(name="Uptime", value=_format_duration(uptime_delta), inline=False)
        embed.add_field(name="Active Feeds", value=str(active_count), inline=True)
        embed.add_field(name="Paused Feeds", value=str(paused_count), inline=True)
        embed.add_field(name="Last Poll", value=last_poll_str, inline=False)
        embed.add_field(name="Next Poll", value=next_poll_str, inline=False)
        embed.set_footer(text="Type /help to see all available commands")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Show all available commands")
    async def help(self, interaction: discord.Interaction) -> None:
        if not _has_mod_role(interaction):
            await interaction.response.send_message(
                "You don't have permission to use this command. ❌", ephemeral=True
            )
            return

        embed = discord.Embed(title="Recon - Commands", colour=0x808080)
        commands_list = [
            ("/addfeed [channel] [url] [colour]", "Add an RSS feed to a channel with a chosen colour. Colour options: green, blue, red, pink, yellow, purple"),
            ("/removefeed [channel] [url]", "Remove a feed from a channel"),
            ("/listfeeds", "Show all registered feeds and their status"),
            ("/pause [channel]", "Pause all feeds in a channel"),
            ("/resume [channel]", "Resume all feeds in a channel"),
            ("/check [channel?]", "Manually trigger a feed check (omit channel to check all)"),
            ("/recon", "Show bot status and uptime"),
            ("/help", "Show this command list"),
        ]
        for name, description in commands_list:
            embed.add_field(name=name, value=description, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
