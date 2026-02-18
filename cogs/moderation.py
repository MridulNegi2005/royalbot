import discord
from discord.ext import commands
from discord.commands import slash_command
import datetime
import asyncio
import json
import os
from main import query, con

# ── Load config ──────────────────────────────────────────────

GUILD_ID = 767591734841835540
MOD_LOG_CHANNEL_ID = 849868729629016095
STAFF_ROLE_IDS = [767591734850879495, 767591734850879494]

# ── Helpers ──────────────────────────────────────────────────
def parse_duration(duration_str: str) -> int | str:
    """Parse a human duration string like '1d 12h 30m' into total seconds."""
    total = 0
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    for part in duration_str.split():
        unit = part[-1].lower()
        if unit not in units:
            return "error"
        try:
            total += int(part[:-1]) * units[unit]
        except ValueError:
            return "error"
    return total


def format_duration(seconds: int) -> str:
    """Format seconds into a human-readable string."""
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    return " ".join(parts)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ── Logging helper ───────────────────────────────────────
    async def _log(self, *, title: str, description: str, color: int = 0x2f3136,
                   moderator: discord.Member = None, target: discord.Member | discord.User = None,
                   fields: list[tuple[str, str]] | None = None):
        """Send a mod-action embed to the configured log channel."""
        channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if channel is None:
            return  # channel not found — silently skip

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        if moderator:
            embed.set_author(name=str(moderator), icon_url=moderator.display_avatar.url)
        if target:
            embed.set_thumbnail(url=target.display_avatar.url)
        if fields:
            for name, value in fields:
                embed.add_field(name=name, value=value, inline=False)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

    # ── /slowmode ────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def slowmode(self, ctx,
                       seconds: discord.Option(int, description="Slowmode time in seconds. '0' for none")):
        """Set the slowmode for the current channel."""
        try:
            await ctx.channel.edit(slowmode_delay=seconds)
            await ctx.respond(f"Slowmode set to **{seconds}s** in {ctx.channel.mention}.")
            await self._log(
                title="Slowmode Changed",
                description=f"{ctx.channel.mention} slowmode → **{seconds}s**",
                color=0x3498db,
                moderator=ctx.author,
                fields=[("Channel", ctx.channel.mention)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to change slowmode here.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /say ─────────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def say(self, ctx,
                  message: discord.Option(str, description="Text message to send"),
                  channel: discord.Option(discord.TextChannel, description="Channel to send to",
                                          required=False, default=None)):
        """Send a message as the bot."""
        try:
            channel = channel or ctx.channel
            await channel.send(message)
            await ctx.respond("Message sent!", ephemeral=True)
            await self._log(
                title="Say Command",
                description=f"Message sent in {channel.mention}",
                color=0x9b59b6,
                moderator=ctx.author,
                fields=[("Content", message[:1024])],
            )
        except discord.Forbidden:
            await ctx.respond("I can't send messages in that channel.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /nick ────────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def nick(self, ctx,
                   member: discord.Option(discord.Member, description="User whose nickname to change"),
                   nick: discord.Option(str, description="New nickname")):
        """Change a member's nickname."""
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.respond("You can't change the nickname of someone with an equal or higher role!", ephemeral=True)
            return
        try:
            old_nick = member.display_name
            await member.edit(nick=nick)
            await ctx.respond(f"Nickname changed for {member.mention}: **{old_nick}** → **{nick}**")
            await self._log(
                title="Nickname Changed",
                description=f"{member.mention}'s nickname was changed.",
                color=0xf1c40f,
                moderator=ctx.author,
                target=member,
                fields=[("Before", old_nick), ("After", nick)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to change that user's nickname.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /kick ────────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def kick(self, ctx,
                   member: discord.Option(discord.Member, description="Member to kick"),
                   reason: discord.Option(str, description="Reason for kick")):
        """Kick a member from the server."""
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.respond("You can't kick someone with an equal or higher role!", ephemeral=True)
            return
        try:
            await member.kick(reason=reason)
            await ctx.respond(f"**{member}** has been kicked.\n**Reason:** {reason}")
            await self._log(
                title="Member Kicked",
                description=f"**{member}** ({member.id}) was kicked.",
                color=0xe67e22,
                moderator=ctx.author,
                target=member,
                fields=[("Reason", reason)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to kick that member.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /mute (timeout) ─────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def mute(self, ctx,
                   member: discord.Option(discord.Member, description="Member to mute"),
                   duration: discord.Option(str, description="Duration, e.g. '1d 12h 30m'"),
                   reason: discord.Option(str, description="Reason for mute")):
        """Timeout / mute a member."""
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.respond("You can't mute someone with an equal or higher role!", ephemeral=True)
            return

        seconds = parse_duration(duration)
        if seconds == "error" or seconds <= 0:
            await ctx.respond("Invalid duration format. Use e.g. `1d 12h 30m 10s`.", ephemeral=True)
            return

        try:
            td = datetime.timedelta(seconds=seconds)
            await member.timeout_for(td, reason=reason)
            human = format_duration(seconds)
            await ctx.respond(f"**{member}** has been muted for **{human}**.\n**Reason:** {reason}")
            await self._log(
                title="Member Muted",
                description=f"**{member}** ({member.id}) was timed out.",
                color=0xe74c3c,
                moderator=ctx.author,
                target=member,
                fields=[("Duration", human), ("Reason", reason)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to timeout that member.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /unmute ──────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def unmute(self, ctx,
                     member: discord.Option(discord.Member, description="Member to unmute"),
                     reason: discord.Option(str, description="Reason", default="Not specified")):
        """Remove a timeout from a member."""
        try:
            await member.remove_timeout(reason=reason)
            await ctx.respond(f"**{member.mention}** has been unmuted.\n**Reason:** {reason}")
            await self._log(
                title="Member Unmuted",
                description=f"**{member}** ({member.id}) timeout removed.",
                color=0x2ecc71,
                moderator=ctx.author,
                target=member,
                fields=[("Reason", reason)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to unmute that member.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /ban ─────────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def ban(self, ctx,
                  member: discord.Option(discord.Member, description="Member to ban"),
                  reason: discord.Option(str, description="Reason for ban")):
        """Ban a member from the server."""
        if ctx.author.top_role <= member.top_role and ctx.author != ctx.guild.owner:
            await ctx.respond("You can't ban someone with an equal or higher role!", ephemeral=True)
            return
        try:
            # Try to DM the user before banning
            try:
                dm = await member.create_dm()
                await dm.send(
                    f"You were banned from **{ctx.guild.name}**!\n"
                    f"**Reason:** {reason}\n"
                )
            except discord.Forbidden:
                pass  # can't DM — proceed with ban anyway

            await member.ban(reason=reason)
            await ctx.respond(f"**{member}** has been banned.\n**Reason:** {reason}")
            await self._log(
                title="Member Banned",
                description=f"**{member}** ({member.id}) was banned.",
                color=0xe74c3c,
                moderator=ctx.author,
                target=member,
                fields=[("Reason", reason)],
            )
        except discord.Forbidden:
            await ctx.respond("I don't have permission to ban that member.", ephemeral=True)
        except Exception as e:
            await ctx.respond(f"An error occurred: {e}", ephemeral=True)

    # ── /warn ────────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def warn(self, ctx,
                   member: discord.Option(discord.Member, description="Member to warn"),
                   reason: discord.Option(str, description="Reason for warning")):
        """Warn a member and store it in the database."""
        try:
            now = datetime.datetime.now()
            date_str = now.strftime("%d %b %Y")

            sql = 'INSERT INTO warns ("user", "reason", "moderator", "date") VALUES (%s, %s, %s, %s)'
            query.execute(sql, (member.id, reason, ctx.author.id, date_str))
            con.commit()

            embed = discord.Embed(
                description=f"{member.mention} has been warned by {ctx.author.mention}.\n**Reason:** {reason}",
                color=member.color,
            )
            await ctx.respond(embed=embed)
            await self._log(
                title="Member Warned",
                description=f"**{member}** ({member.id}) was warned.",
                color=0xf39c12,
                moderator=ctx.author,
                target=member,
                fields=[("Reason", reason)],
            )
        except Exception as e:
            await ctx.respond(f"Failed to warn user: {e}", ephemeral=True)

    # ── /clear_warn ──────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def clear_warn(self, ctx,
                         member: discord.Option(discord.Member, description="Member whose warn(s) to clear"),
                         warn_id: discord.Option(str, description="Warn ID to clear, or 'all'"),
                         reason: discord.Option(str, description="Reason for clearing")):
        """Clear one or all warnings from a member."""
        try:
            # Check if user has any warnings
            query.execute('SELECT * FROM warns WHERE "user" = %s', (member.id,))
            results = query.fetchall()

            if not results:
                await ctx.respond(f"**{member.name}** has no warnings!", ephemeral=True)
                return

            if warn_id.lower() == "all":
                query.execute('DELETE FROM warns WHERE "user" = %s', (member.id,))
                con.commit()
                await ctx.respond(f"Cleared **all** warnings from **{member.name}**.")
                cleared = "All"
            else:
                try:
                    wid = int(warn_id)
                except ValueError:
                    await ctx.respond("Warn ID must be a number or 'all'.", ephemeral=True)
                    return
                query.execute('DELETE FROM warns WHERE "id" = %s', (wid,))
                con.commit()
                await ctx.respond(f"Cleared warn **#{wid}** from **{member.name}**.")
                cleared = f"#{wid}"

            await self._log(
                title="Warning Cleared",
                description=f"Warning(s) cleared from **{member}** ({member.id}).",
                color=0x1abc9c,
                moderator=ctx.author,
                target=member,
                fields=[("Cleared", cleared), ("Reason", reason)],
            )
        except Exception as e:
            await ctx.respond(f"Failed to clear warning: {e}", ephemeral=True)

    # ── /warnings ────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    async def warnings(self, ctx,
                       member: discord.Option(discord.Member, description="Member to check (leave empty for self)",
                                              required=False, default=None)):
        """View warnings for a member."""
        user = member or ctx.author

        # If checking someone else, require staff role
        if member is not None and member != ctx.author:
            is_staff = any(role.id in STAFF_ROLE_IDS for role in ctx.author.roles)
            if not is_staff:
                await ctx.respond("You can only check your own warnings!", ephemeral=True)
                return

        try:
            query.execute('SELECT * FROM warns WHERE "user" = %s', (user.id,))
            results = query.fetchall()
            count = len(results)

            pfp = user.display_avatar.url if user.display_avatar else user.default_avatar.url

            embed = discord.Embed(color=0xe83535)
            embed.set_author(name=f"{count} Warning(s) for {user.name} ({user.id})", icon_url=pfp)

            if count == 0:
                embed.description = "No warnings found."
            else:
                # Show warns in reverse order (newest first)
                for row in reversed(results):
                    # row format: (id, user, reason, moderator, date)  — adapt indices to your schema
                    warn_id = row[0]
                    warn_reason = row[1] if len(row) > 1 else "N/A"
                    mod_id = row[2] if len(row) > 2 else None
                    warn_date = row[3] if len(row) > 3 else "N/A"

                    mod_name = "Unknown"
                    if mod_id:
                        try:
                            mod_user = self.bot.get_user(int(mod_id)) or await self.bot.fetch_user(int(mod_id))
                            mod_name = mod_user.name
                        except Exception:
                            mod_name = f"ID: {mod_id}"

                    embed.add_field(
                        name=f"Warn #{warn_id}  •  Mod: {mod_name}",
                        value=f"**Reason:** {warn_reason}\n📅 {warn_date}",
                        inline=False,
                    )

            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"Failed to fetch warnings: {e}", ephemeral=True)

    # ── /purge ───────────────────────────────────────────────
    @slash_command(guild_ids=[GUILD_ID])
    @discord.default_permissions(ban_members=True)
    async def purge(self, ctx,
                    limit: discord.Option(int, description="Number of messages to purge")):
        """Bulk-delete messages from the current channel."""
        try:
            await ctx.defer(ephemeral=True)
            deleted = await ctx.channel.purge(limit=limit)
            await ctx.followup.send(f"Purged **{len(deleted)}** messages.")
            await self._log(
                title="Messages Purged",
                description=f"**{len(deleted)}** messages purged in {ctx.channel.mention}.",
                color=0x95a5a6,
                moderator=ctx.author,
                fields=[("Channel", ctx.channel.mention), ("Requested", str(limit))],
            )
        except discord.Forbidden:
            await ctx.followup.send("I don't have permission to delete messages here.")
        except Exception as e:
            await ctx.followup.send(f"An error occurred: {e}")


def setup(bot):
    bot.add_cog(Moderation(bot))