import discord
from discord.commands import slash_command, Option
from discord.ext import commands, tasks
from discord.ext.commands.cog import Cog
import math
import datetime
import asyncio
import io
import ast
import aiopg
from PIL import Image, ImageFont, ImageDraw
from easy_pil import Editor, Canvas, load_image_async


# ─── DATABASE CONFIG ─────────────────────────────────────────
import os
DSN = f"dbname={os.getenv('POSTGRES_DB')} user={os.getenv('POSTGRES_USER')} password={os.getenv('POSTGRES_PASSWORD')} host={os.getenv('POSTGRES_HOST')} port={os.getenv('POSTGRES_PORT', 5432)} sslmode=require"


# ─── XP RATES ───────────────────────────────────────────────
BASE_XP_PER_MIN = 2        # Just sitting in VC (muted)
MIC_XP_PER_MIN = 5         # Mic unmuted (replaces base)
STREAM_BONUS_PER_MIN = 3   # Bonus on top for streaming

GUILD_ID = 767591734841835540


def vc_level_from_xp(xp):
    """Same formula as chat levelling: level = int(0.2 * sqrt(xp))"""
    return int(0.2 * math.sqrt(xp))


def xp_for_level(level):
    """Inverse: XP needed to reach a given level."""
    return int((level / 0.2) ** 2)


def human_format(num):
    num = float('{:.4g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', ' K', ' M', ' B', ' T'][magnitude])


def format_duration(seconds):
    """Convert seconds to a human-readable duration string."""
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        days = hours // 24
        hrs = hours % 24
        if days > 0:
            return f"{days}d {hrs}h {mins}m"
        return f"{hrs}h {mins}m"
    return f"{mins}m"


class VCLevelling(commands.Cog):
    """Voice Chat levelling system — tracks VC time, mic usage, streaming, and awards XP."""

    def __init__(self, bot):
        self.bot = bot
        self.pool = None  # aiopg connection pool, created async in before_xp_tick

        # In-memory tracking for active VC sessions
        # {user_id: {"joined_at": datetime, "mic_on": bool, "streaming": bool,
        #            "last_tick": datetime, "mic_on_since": datetime|None, "streaming_since": datetime|None}}
        self.active_sessions = {}

        # Start the XP loop (pool + table creation happens in before_xp_tick)
        self.xp_tick_loop.start()

    # ─── DATABASE HELPERS (aiopg) ────────────────────────────

    async def _ensure_pool(self):
        """Create the connection pool if it doesn't exist or is closed."""
        if self.pool is None or self.pool.closed:
            self.pool = await aiopg.create_pool(DSN, minsize=1, maxsize=5)
            print("[vc_levelling] DB connection pool created.")

    async def _db_execute(self, sql, params=None):
        """Execute a query and return nothing."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)

    async def _db_fetchone(self, sql, params=None):
        """Execute a query and return one row."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchone()

    async def _db_fetchall(self, sql, params=None):
        """Execute a query and return all rows."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    async def _ensure_table(self):
        """Create the vc_levelling table if it doesn't exist."""
        await self._db_execute("""
            CREATE TABLE IF NOT EXISTS vc_levelling (
                user_id BIGINT PRIMARY KEY,
                vc_xp INTEGER DEFAULT 0,
                total_vc_time INTEGER DEFAULT 0,
                total_mic_time INTEGER DEFAULT 0,
                total_stream_time INTEGER DEFAULT 0,
                total_sessions INTEGER DEFAULT 0,
                current_streak INTEGER DEFAULT 0,
                longest_streak INTEGER DEFAULT 0,
                last_vc_date DATE
            )
        """)

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        self.xp_tick_loop.cancel()
        if self.pool and not self.pool.closed:
            self.pool.close()
            print("[vc_levelling] DB connection pool closed.")

    def _is_eligible(self, member, voice_state):
        """Check if a member is eligible for XP (not deafened, not alone/only bots)."""
        if voice_state is None or voice_state.channel is None:
            return False
        # Self-deafened = 0 XP
        if voice_state.self_deaf or voice_state.deaf:
            return False
        # Check if alone or only with bots
        human_members = [m for m in voice_state.channel.members if not m.bot]
        if len(human_members) <= 1:
            return False
        return True

    async def _get_user_data(self, user_id):
        """Fetch user data from DB, returns dict or None."""
        row = await self._db_fetchone('SELECT * FROM vc_levelling WHERE user_id = %s', (user_id,))
        if row:
            return {
                "user_id": row[0],
                "vc_xp": row[1],
                "total_vc_time": row[2],
                "total_mic_time": row[3],
                "total_stream_time": row[4],
                "total_sessions": row[5],
                "current_streak": row[6],
                "longest_streak": row[7],
                "last_vc_date": row[8],
            }
        return None

    async def _update_streak(self, user_id):
        """Update the streak for a user based on today's date."""
        today = datetime.date.today()
        data = await self._get_user_data(user_id)

        if data is None:
            return

        last_date = data["last_vc_date"]
        current_streak = data["current_streak"]
        longest_streak = data["longest_streak"]

        if last_date is None:
            current_streak = 1
        elif last_date == today:
            return
        elif last_date == today - datetime.timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1

        if current_streak > longest_streak:
            longest_streak = current_streak

        await self._db_execute(
            'UPDATE vc_levelling SET current_streak = %s, longest_streak = %s, last_vc_date = %s WHERE user_id = %s',
            (current_streak, longest_streak, today, user_id)
        )

    # ─── VOICE STATE LISTENER ─────────────────────────────────

    @Cog.listener("on_voice_state_update")
    async def on_voice_state_update(self, member, before, after):
        """Track when users join/leave VC, mute/unmute, start/stop streaming."""
        if member.bot:
            return
        if member.guild.id != GUILD_ID:
            return

        now = datetime.datetime.utcnow()

        # User joined a voice channel
        if before.channel is None and after.channel is not None:
            self.active_sessions[member.id] = {
                "joined_at": now,
                "last_tick": now,
                "mic_on": not (after.self_mute or after.mute),
                "mic_on_since": now if not (after.self_mute or after.mute) else None,
                "streaming": after.self_stream,
                "streaming_since": now if after.self_stream else None,
            }
            # Ensure user exists in DB
            data = await self._get_user_data(member.id)
            if data is None:
                await self._db_execute(
                    'INSERT INTO vc_levelling (user_id, vc_xp, total_vc_time, total_mic_time, total_stream_time, total_sessions, current_streak, longest_streak, last_vc_date) VALUES (%s, 0, 0, 0, 0, 1, 0, 0, NULL)',
                    (member.id,)
                )
            else:
                await self._db_execute(
                    'UPDATE vc_levelling SET total_sessions = total_sessions + 1 WHERE user_id = %s',
                    (member.id,)
                )
            # Update streak
            await self._update_streak(member.id)
            return

        # User left voice channel
        if before.channel is not None and after.channel is None:
            if member.id in self.active_sessions:
                # Final tick before removing
                await self._process_user_tick(member, now)
                del self.active_sessions[member.id]
            return

        # User changed state within VC (mute/unmute/stream)
        if member.id in self.active_sessions:
            session = self.active_sessions[member.id]
            mic_now_on = not (after.self_mute or after.mute)
            stream_now_on = after.self_stream

            # Mic state changed
            if session["mic_on"] and not mic_now_on:
                # Mic turned off — flush remaining mic time since last tick
                if session["mic_on_since"]:
                    mic_secs = int((now - session["mic_on_since"]).total_seconds())
                    if mic_secs > 0:
                        await self._db_execute(
                            'UPDATE vc_levelling SET total_mic_time = total_mic_time + %s WHERE user_id = %s',
                            (mic_secs, member.id)
                        )
                session["mic_on_since"] = None
            elif not session["mic_on"] and mic_now_on:
                # Mic turned on
                session["mic_on_since"] = now
            session["mic_on"] = mic_now_on

            # Stream state changed
            if session["streaming"] and not stream_now_on:
                # Stream stopped — flush remaining stream time since last tick
                if session["streaming_since"]:
                    stream_secs = int((now - session["streaming_since"]).total_seconds())
                    if stream_secs > 0:
                        await self._db_execute(
                            'UPDATE vc_levelling SET total_stream_time = total_stream_time + %s WHERE user_id = %s',
                            (stream_secs, member.id)
                        )
                session["streaming_since"] = None
            elif not session["streaming"] and stream_now_on:
                # Stream started
                session["streaming_since"] = now
            session["streaming"] = stream_now_on

    # ─── BACKGROUND XP TASK ──────────────────────────────────

    @tasks.loop(seconds=60)
    async def xp_tick_loop(self):
        """Every 60 seconds, award XP to eligible users in VC."""
        now = datetime.datetime.utcnow()
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return

        for member_id in list(self.active_sessions.keys()):
            member = guild.get_member(member_id)
            if member is None:
                # Member left or unavailable
                self.active_sessions.pop(member_id, None)
                continue
            await self._process_user_tick(member, now)

    @xp_tick_loop.before_loop
    async def before_xp_tick(self):
        await self.bot.wait_until_ready()
        # Create the pool and ensure table exists
        await self._ensure_pool()
        await self._ensure_table()
        # On startup, populate active_sessions from current VC members
        guild = self.bot.get_guild(GUILD_ID)
        if guild is None:
            return
        now = datetime.datetime.utcnow()
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                vs = member.voice
                if vs and vs.channel:
                    self.active_sessions[member.id] = {
                        "joined_at": now,
                        "last_tick": now,
                        "mic_on": not (vs.self_mute or vs.mute),
                        "mic_on_since": now if not (vs.self_mute or vs.mute) else None,
                        "streaming": vs.self_stream,
                        "streaming_since": now if vs.self_stream else None,
                    }
                    # Ensure user exists in DB
                    data = await self._get_user_data(member.id)
                    if data is None:
                        await self._db_execute(
                            'INSERT INTO vc_levelling (user_id, vc_xp, total_vc_time, total_mic_time, total_stream_time, total_sessions, current_streak, longest_streak, last_vc_date) VALUES (%s, 0, 0, 0, 0, 0, 0, 0, NULL)',
                            (member.id,)
                        )

    async def _process_user_tick(self, member, now):
        """Process a single user's XP tick."""
        session = self.active_sessions.get(member.id)
        if session is None:
            return

        vs = member.voice
        elapsed_secs = int((now - session["last_tick"]).total_seconds())
        if elapsed_secs <= 0:
            return

        # Update total VC time regardless of eligibility
        await self._db_execute(
            'UPDATE vc_levelling SET total_vc_time = total_vc_time + %s WHERE user_id = %s',
            (elapsed_secs, member.id)
        )

        # Track mic on time separately (incremental every tick)
        if session["mic_on"] and session["mic_on_since"]:
            mic_elapsed = int((now - session["mic_on_since"]).total_seconds())
            if mic_elapsed > 0:
                await self._db_execute(
                    'UPDATE vc_levelling SET total_mic_time = total_mic_time + %s WHERE user_id = %s',
                    (mic_elapsed, member.id)
                )
            session["mic_on_since"] = now  # Reset reference point

        # Track stream time separately (incremental every tick)
        if session["streaming"] and session["streaming_since"]:
            stream_elapsed = int((now - session["streaming_since"]).total_seconds())
            if stream_elapsed > 0:
                await self._db_execute(
                    'UPDATE vc_levelling SET total_stream_time = total_stream_time + %s WHERE user_id = %s',
                    (stream_elapsed, member.id)
                )
            session["streaming_since"] = now  # Reset reference point

        # Check eligibility for XP
        eligible = self._is_eligible(member, vs)
        xp_earned = 0

        if eligible:
            elapsed_mins = elapsed_secs / 60.0

            # Base or mic XP
            if session["mic_on"]:
                xp_earned += MIC_XP_PER_MIN * elapsed_mins
            else:
                xp_earned += BASE_XP_PER_MIN * elapsed_mins

            # Stream bonus
            if session["streaming"]:
                xp_earned += STREAM_BONUS_PER_MIN * elapsed_mins

            xp_earned = int(xp_earned)

            if xp_earned > 0:
                # Get current XP for level-up check
                data = await self._get_user_data(member.id)
                old_xp = data["vc_xp"] if data else 0
                new_xp = old_xp + xp_earned
                level_before = vc_level_from_xp(old_xp)
                level_after = vc_level_from_xp(new_xp)

                await self._db_execute(
                    'UPDATE vc_levelling SET vc_xp = vc_xp + %s WHERE user_id = %s',
                    (xp_earned, member.id)
                )

                # Level up announcement (same style as chat levelling)
                if level_after > level_before and vs and vs.channel:
                    try:
                        announce_channel = member.guild.system_channel
                        if announce_channel is None:
                            for ch in member.guild.text_channels:
                                if ch.permissions_for(member.guild.me).send_messages:
                                    announce_channel = ch
                                    break
                        if announce_channel:
                            await announce_channel.send(f"Congratulations {member.mention}, you just reached VC level {level_after}!")
                    except Exception:
                        pass

        session["last_tick"] = now

    # ─── RANK CARD GENERATOR ──────────────────────────────────

    async def _get_user_theme(self, user_id):
        """Get the user's theme and overlay preference from the chat levelling table."""
        try:
            row = await self._db_fetchone('SELECT "theme", "overlay" FROM levelling WHERE "user" = %s', (user_id,))
            if row:
                return int(row[0]), str(row[1])
        except Exception:
            pass
        return 1, "True"  # Default theme

    async def _generate_vc_level_card(self, user, xp, level, rank, percentage, interval_2, theme, overlay_option):
        """Generate a rank card image — same visual style as chat levelling."""
        # Theme backgrounds / colors (same as levelling.py)
        backgrounds = {
            1: ("cogs/assests/background1.png", '#17F3F6', "cogs/assests/overlay1.png", '#ffffff'),
            2: ("cogs/assests/background2.png", '#ff1f97', "cogs/assests/overlay1.png", '#11ebf2'),
            3: ("cogs/assests/background3.png", '#ff1f97', "cogs/assests/overlay1.png", '#11ebf2'),
            4: ("cogs/assests/background4.png", '#ff5145', "cogs/assests/overlay1.png", '#11ebf2'),
            5: ("cogs/assests/background5.png", '#ff1f97', "cogs/assests/overlay2.png", '#11ebf2'),
        }
        bg_path, bcolor, overlay_path, name_color = backgrounds.get(theme, backgrounds[1])

        background = Editor(bg_path)
        overlay = Editor(overlay_path)
        avatar = await load_image_async(str(user.display_avatar.url))
        avatar = Editor(avatar).resize((177, 177)).circle_image()
        overlay = Editor(overlay).resize((230, 230))

        square = Canvas((500, 500), "#06FFBF")
        square = Editor(square)
        square.rotate(30, expand=True)

        background.paste(square.image, (600, -250))
        background.paste(avatar.image, (38, 40))
        if overlay_option == "True":
            background.paste(overlay.image, (10, 15))

        background.rectangle((265, 210), width=710, height=30, fill="white", radius=20)
        background.bar(
            (265, 210),
            max_width=710,
            height=30,
            percentage=percentage,
            fill="#FF4242",
            radius=20,
        )
        background.rectangle((240, 20), width=5, height=211, fill=bcolor)

        # Progress bar positions
        bar_offset_x = 265
        bar_offset_y = 210

        background = Image.open(background.image_bytes)
        draw = ImageDraw.Draw(background)

        # Fonts (same as levelling.py)
        big_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 60)
        xp_font = ImageFont.FreeTypeFont("cogs/assests/LemonMilk.ttf", 25)
        small_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 30)
        name_font = ImageFont.FreeTypeFont("cogs/assests/seguiemj.ttf", 35)

        # Right upper part — Level
        text_bbox = draw.textbbox((0, 0), str(level), font=big_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x = 1000 - 15 - text_size[0]
        offset_y = 10
        draw.text((offset_x, offset_y), str(level), font=big_font, fill="#11ebf2")

        text_bbox = draw.textbbox((0, 0), "LEVEL", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 5
        draw.text((offset_x, offset_y + 27), "LEVEL", font=small_font, fill="#11ebf2")

        # Rank
        text_bbox = draw.textbbox((0, 0), f"#{rank}", font=big_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 15
        draw.text((offset_x, offset_y), f"#{rank}", font=big_font, fill="#fff")

        text_bbox = draw.textbbox((0, 0), "RANK", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 5
        draw.text((offset_x, offset_y + 27), "RANK", font=small_font, fill="#fff")

        # XP text
        text_bbox = draw.textbbox((0, 0), f"/ {human_format(interval_2)} XP", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x = 980 - text_size[0]
        offset_y = bar_offset_y - text_size[1] - 10
        draw.text((offset_x, offset_y), f"/ {human_format(interval_2)} XP", font=xp_font, fill="#727175")

        text_bbox = draw.textbbox((0, 0), f"{human_format(xp)}", font=xp_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 8
        draw.text((offset_x, offset_y), f"{human_format(xp)}", font=xp_font, fill="#fff")

        # Name
        text_bbox = draw.textbbox((0, 0), user.name, font=name_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x = bar_offset_x
        offset_y = bar_offset_y - text_size[1] - 5
        draw.text((offset_x, offset_y), user.name, font=name_font, fill='#FF4242', stroke_width=1, stroke_fill='#FF4242')

        # Save to buffer
        with io.BytesIO() as image_binary:
            background.save(image_binary, 'PNG')
            image_binary.seek(0)
            return discord.File(fp=image_binary, filename='VC_Level.png')

    # ─── SLASH COMMANDS ───────────────────────────────────────

    @slash_command(description="Check your VC level!")
    async def vclevel(self, ctx, user: Option(discord.Member, "Member whose VC rank you want to see", required=False, default=None)):
        await ctx.defer()
        if user is None:
            user = ctx.author

        data = await self._get_user_data(user.id)
        if data is None:
            await ctx.send_followup(f"{user.mention} hasn't spent any time in VC yet!")
            return

        xp = data["vc_xp"]
        level = vc_level_from_xp(xp)

        # Calculate progress (same formula as levelling.py)
        if level == 0:
            percentage = (xp / 75) * 100
            interval_1 = 0
            interval_2 = (int((level + 1) * 5) ** 2)
        else:
            xp_diff = (int((level + 1) * 5) ** 2) - (int((level) / 0.2) ** 2)
            interval_1 = (int((level) * 5) ** 2)
            interval_2 = (int((level + 1) / 0.2) ** 2)
            percentage = ((xp - interval_1) / xp_diff) * 100

        # Get rank
        all_users = await self._db_fetchall('SELECT user_id FROM vc_levelling ORDER BY vc_xp DESC')
        rank = 1
        for row in all_users:
            if row[0] == user.id:
                break
            rank += 1

        # Get user theme from chat levelling table
        theme, overlay_option = await self._get_user_theme(user.id)

        # Generate rank card image
        file = await self._generate_vc_level_card(user, xp, level, rank, percentage, interval_2, theme, overlay_option)
        await ctx.send_followup(file=file)

    @slash_command(description="View detailed VC stats!")
    async def vcstats(self, ctx, user: Option(discord.Member, "Member whose VC stats you want to see", required=False, default=None)):
        await ctx.defer()
        if user is None:
            user = ctx.author

        data = await self._get_user_data(user.id)
        if data is None:
            await ctx.send_followup(f"{user.mention} hasn't spent any time in VC yet!")
            return

        xp = data["vc_xp"]
        level = vc_level_from_xp(xp)

        embed = discord.Embed(
            title=f"🎧 VC Stats — {user.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        # Level & XP
        embed.add_field(name="🏅 VC Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ Total XP", value=f"**{human_format(xp)}**", inline=True)
        embed.add_field(name="📊 Sessions", value=f"**{data['total_sessions']}**", inline=True)

        # Time stats
        embed.add_field(name="⏱️ Total VC Time", value=f"`{format_duration(data['total_vc_time'])}`", inline=True)
        embed.add_field(name="🎤 Mic On Time", value=f"`{format_duration(data['total_mic_time'])}`", inline=True)
        embed.add_field(name="📺 Stream Time", value=f"`{format_duration(data['total_stream_time'])}`", inline=True)

        # Streaks
        embed.add_field(name="🔥 Current Streak", value=f"**{data['current_streak']}** day{'s' if data['current_streak'] != 1 else ''}", inline=True)
        embed.add_field(name="🏆 Longest Streak", value=f"**{data['longest_streak']}** day{'s' if data['longest_streak'] != 1 else ''}", inline=True)

        # Percentages
        if data["total_vc_time"] > 0:
            mic_pct = (data["total_mic_time"] / data["total_vc_time"]) * 100
            stream_pct = (data["total_stream_time"] / data["total_vc_time"]) * 100
            embed.add_field(
                name="📈 Activity Breakdown",
                value=f"Mic on: **{mic_pct:.1f}%** of VC time\nStreaming: **{stream_pct:.1f}%** of VC time",
                inline=False
            )

        await ctx.send_followup(embed=embed)

    @slash_command(description="View VC XP leaderboard!")
    async def vcleaderboard(self, ctx):
        await ctx.defer()

        all_rows = await self._db_fetchall('SELECT user_id, vc_xp FROM vc_levelling ORDER BY vc_xp DESC')

        if not all_rows:
            await ctx.send_followup("No one has earned VC XP yet!")
            return

        # Find user's rank
        user_rank = 0
        for idx, row in enumerate(all_rows):
            if row[0] == ctx.author.id:
                user_rank = idx + 1
                break

        # Build paginated embeds
        pages = []
        page_size = 10
        for page_start in range(0, len(all_rows), page_size):
            page_rows = all_rows[page_start:page_start + page_size]
            desc = ""
            for i, row in enumerate(page_rows):
                rank = page_start + i + 1
                uid, xp = row
                level = vc_level_from_xp(xp)
                try:
                    member = ctx.guild.get_member(uid)
                    name = f"**{member.display_name}**" if member else f"**Unknown** ({uid})"
                except:
                    name = f"**Unknown** ({uid})"

                # Medal emojis for top 3
                medal = ""
                if rank == 1:
                    medal = "🥇 "
                elif rank == 2:
                    medal = "🥈 "
                elif rank == 3:
                    medal = "🥉 "

                desc += f"{medal}`{rank}` {name}\n　└─ Level **{level}** • {human_format(xp)} XP\n"

            page_num = (page_start // page_size) + 1
            total_pages = math.ceil(len(all_rows) / page_size)
            embed = discord.Embed(
                title="🎤 VC Leaderboard",
                description=desc,
                color=discord.Color.gold(),
                timestamp=datetime.datetime.utcnow()
            )
            footer_txt = f"Page {page_num}/{total_pages}"
            if user_rank > 0:
                footer_txt += f" • Your rank: #{user_rank}"
            embed.set_footer(text=footer_txt, icon_url=ctx.author.display_avatar.url)
            pages.append(embed)

        if len(pages) == 1:
            await ctx.send_followup(embed=pages[0])
        else:
            # Use paginator view
            view = LeaderboardPaginator(ctx, pages)
            await ctx.send_followup(embed=pages[0], view=view)


class LeaderboardPaginator(discord.ui.View):
    """Simple paginator for VC leaderboard."""
    def __init__(self, ctx, pages):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.pages = pages
        self.current = 0

        # Disable back buttons initially
        self.first_btn.disabled = True
        self.back_btn.disabled = True
        if len(pages) <= 1:
            self.next_btn.disabled = True
            self.last_btn.disabled = True

    def _update_buttons(self):
        self.first_btn.disabled = self.current == 0
        self.back_btn.disabled = self.current == 0
        self.next_btn.disabled = self.current >= len(self.pages) - 1
        self.last_btn.disabled = self.current >= len(self.pages) - 1

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.grey)
    async def first_btn(self, button, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return
        self.current = 0
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[0], view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.grey)
    async def back_btn(self, button, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return
        if self.current > 0:
            self.current -= 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.grey)
    async def next_btn(self, button, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return
        if self.current < len(self.pages) - 1:
            self.current += 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[self.current], view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.grey)
    async def last_btn(self, button, interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You can't use this!", ephemeral=True)
            return
        self.current = len(self.pages) - 1
        self._update_buttons()
        await interaction.response.edit_message(embed=self.pages[-1], view=self)


def setup(bot):
    bot.add_cog(VCLevelling(bot))
