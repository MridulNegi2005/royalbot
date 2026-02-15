import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import asyncio
import functools
import time
from yt_dlp import YoutubeDL


# yt-dlp options for searching and extracting stream URLs (no download)
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'source_address': '0.0.0.0',
    'default_search': 'ytsearch',
    'extract_flat': False,
}

# FFmpeg options for streaming audio
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}


class Song:
    """Represents a single song with its metadata."""

    def __init__(self, data: dict, requester: discord.Member = None):
        self.data = data
        self.title = data.get('title', 'Unknown')
        self.url = data.get('webpage_url', data.get('url', ''))
        self.stream_url = data.get('url', '')
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')
        self.uploader = data.get('uploader', '')
        self.uploader_url = data.get('uploader_url', '')
        self.view_count = data.get('view_count', 0)
        self.requester = requester
        self._extracted_at = time.time()  # Track when the stream URL was extracted

    @classmethod
    async def from_query(cls, query: str, requester: discord.Member = None):
        """Search and extract song info from a query string or URL."""
        loop = asyncio.get_event_loop()
        with YoutubeDL(YDL_OPTIONS) as ydl:
            data = await loop.run_in_executor(
                None, functools.partial(ydl.extract_info, query, download=False)
            )

        if 'entries' in data:
            # Take the first search result
            data = data['entries'][0]

        return cls(data, requester)

    @classmethod
    async def from_query_list(cls, query: str, requester: discord.Member = None):
        """Search and return a list of songs (handles playlists)."""
        loop = asyncio.get_running_loop()

        # Only enable playlist mode for actual playlist URLs
        is_playlist_url = 'playlist' in query.lower() or 'list=' in query.lower()

        opts = YDL_OPTIONS.copy()
        if is_playlist_url:
            opts['noplaylist'] = False

        with YoutubeDL(opts) as ydl:
            data = await loop.run_in_executor(
                None, functools.partial(ydl.extract_info, query, download=False)
            )

        songs = []
        if 'entries' in data:
            for entry in data['entries']:
                if entry:
                    songs.append(cls(entry, requester))
        else:
            songs.append(cls(data, requester))

        return songs

    def is_stream_fresh(self, max_age=600):
        """Check if the stream URL is still fresh (default: 10 minutes)."""
        return (time.time() - self._extracted_at) < max_age

    async def refresh_stream_url(self):
        """Re-extract the stream URL (they expire). Skips if still fresh."""
        if self.stream_url and self.is_stream_fresh():
            return self.stream_url

        loop = asyncio.get_event_loop()
        with YoutubeDL(YDL_OPTIONS) as ydl:
            data = await loop.run_in_executor(
                None, functools.partial(ydl.extract_info, self.url, download=False)
            )
        if 'entries' in data:
            data = data['entries'][0]
        self.stream_url = data.get('url', '')
        self._extracted_at = time.time()
        return self.stream_url


class MusicPlayer:
    """Per-guild music player managing the queue and playback."""

    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.queue: list[Song] = []
        self.history: list[Song] = []
        self.current: Song | None = None
        self.voice_client: discord.VoiceClient | None = ctx.voice_client
        self.loop = False
        self.queue_loop = False
        self.volume = 0.5
        self._play_lock = asyncio.Lock()

    async def play_next(self, error=None):
        """Callback invoked when the current song ends. Plays the next song."""
        if error:
            print(f"Player error: {error}")

        # If looping current song, replay it
        if self.loop and self.current:
            await self._play_song(self.current)
            return

        # If queue looping, push current song to end of queue
        if self.queue_loop and self.current:
            self.queue.append(self.current)

        # Add current song to history
        if self.current:
            self.history.append(self.current)

        # Play next song in queue
        if self.queue:
            next_song = self.queue.pop(0)
            await self._play_song(next_song)
        else:
            self.current = None

    async def _play_song(self, song: Song):
        """Actually play a song through the voice client."""
        async with self._play_lock:
            self.current = song

            try:
                # Refresh the stream URL in case it expired
                await song.refresh_stream_url()
            except Exception as e:
                print(f"Failed to refresh stream URL: {e}")
                # Try playing next
                await self.play_next()
                return

            if not self.voice_client or not self.voice_client.is_connected():
                return

            source = discord.FFmpegPCMAudio(song.stream_url, **FFMPEG_OPTIONS)
            source = discord.PCMVolumeTransformer(source, volume=self.volume)

            def after_callback(err):
                # Schedule play_next on the event loop
                fut = asyncio.run_coroutine_threadsafe(
                    self.play_next(err), self.bot.loop
                )
                try:
                    fut.result()
                except Exception as e:
                    print(f"Error in after callback: {e}")

            self.voice_client.play(source, after=after_callback)

    async def add_and_play(self, songs: list[Song]):
        """Add songs to the queue. If nothing is playing, start playback."""
        if not songs:
            return None

        if self.current is None or (self.voice_client and not self.voice_client.is_playing() and not self.voice_client.is_paused()):
            # Nothing playing => play the first song immediately, queue the rest
            first = songs[0]
            self.queue.extend(songs[1:])
            await self._play_song(first)
            return first
        else:
            # Something is playing => queue everything
            self.queue.extend(songs)
            return None  # indicates songs were queued, not immediately played

    def clear(self):
        self.queue.clear()
        self.current = None
        self.loop = False
        self.queue_loop = False


# Global dict of guild_id -> MusicPlayer
players: dict[int, MusicPlayer] = {}


def get_player(ctx) -> MusicPlayer | None:
    return players.get(ctx.guild.id)


class Music(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.client_secret = "6ee356b084e445bbbf878dfa1f5c26fd"
        self.client_id = "7bff23b27d3244f28fcae1a938ab89b6"

    def _get_or_create_player(self, ctx) -> MusicPlayer:
        if ctx.guild.id not in players:
            players[ctx.guild.id] = MusicPlayer(ctx)
        player = players[ctx.guild.id]
        player.voice_client = ctx.voice_client
        return player

    # ─── Play ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Searches for the song and plays it if available.")
    async def play(self, ctx, query: Option(str, "Song name or Song/Playlist link from YT or Spotify")):
        await ctx.defer()

        await ctx.send_followup(f"🔍 Searching for **{query}**...")

        # Search FIRST (before joining VC, so we don't sit idle in voice)
        try:
            songs = await Song.from_query_list(query, ctx.author)
        except Exception as e:
            await ctx.send_followup(f"❌ Error searching: {e}")
            return

        if not songs:
            await ctx.send_followup("Query not found.")
            return

        # Now join voice channel (search is done, playback will start immediately)
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send_followup("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                return
            vc = await ctx.author.voice.channel.connect(self_deaf=True)
            await ctx.send_followup(f"<:call_connect:918875388527145091> Joined <#{vc.channel.id}>")

        player = self._get_or_create_player(ctx)
        first_played = await player.add_and_play(songs)

        if first_played:
            embed = discord.Embed(
                title="<:play:918874928219050094> Now Playing",
                description=f"**{first_played.title}**",
                color=0xfa0a12
            )
            if first_played.thumbnail:
                embed.set_thumbnail(url=first_played.thumbnail)
            embed.add_field(name="Duration:", value=f"{convert(int(first_played.duration))}", inline=True)
            embed.add_field(name="Requested By:", value=f"{first_played.requester.mention if first_played.requester else 'Unknown'}", inline=True)
            embed.add_field(name="URL", value=f"[Click Here]({first_played.url})", inline=True)
            if first_played.uploader and first_played.uploader_url:
                embed.add_field(name="Uploaded By:", value=f"[{first_played.uploader}]({first_played.uploader_url})", inline=True)
            embed.set_footer(text="Music By Cosmic Bot", icon_url="https://i.ibb.co/fNkh1QD/avatr.png")
            await ctx.send_followup(embed=embed)

            if len(songs) > 1:
                await ctx.send_followup(f"📋 Added **{len(songs) - 1}** more song(s) to the queue.")
        else:
            if len(songs) == 1:
                await ctx.send_followup(f"📋 **{songs[0].title}** added to queue.")
            else:
                await ctx.send_followup(f"📋 Added **{len(songs)}** song(s) to the queue.")

    # ─── Join ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Joins the VC you are currently in.")
    async def join(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
            return
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect()
        await ctx.respond(f"<:call_connect:918875388527145091> Joined <#{ctx.author.voice.channel.id}>")

    # ─── Leave ────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Disconnects the bot from VC")
    async def leave(self, ctx):
        if ctx.voice_client:
            player = get_player(ctx)
            if player:
                player.clear()
            await ctx.voice_client.disconnect()
            if ctx.guild.id in players:
                del players[ctx.guild.id]
            await ctx.respond("<:call_disconnect:918875403567910933> Left Voice Channel")
        else:
            await ctx.respond("I'm not connected to a voice channel!")

    # ─── Now Playing ──────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Gives information about currently playing song!")
    async def now_playing(self, ctx):
        player = get_player(ctx)
        if not player or not player.current:
            await ctx.respond("No song is being played currently!")
            return

        song = player.current
        requester = song.requester.mention if song.requester else "Unknown"

        loop_status = "Disabled"
        if player.loop:
            loop_status = "Enabled"
        elif player.queue_loop:
            loop_status = "Queue Loop Enabled"

        embed = discord.Embed(
            title="<:play:918874928219050094> Now Playing",
            description=f"**{song.title}**",
            color=0xfa0a12
        )
        if song.thumbnail:
            embed.set_thumbnail(url=song.thumbnail)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url if ctx.author.avatar else discord.Embed.Empty)
        embed.add_field(name="Duration:", value=f"{convert(int(song.duration))}", inline=True)
        embed.add_field(name="Looping:", value=f"{loop_status}", inline=True)
        embed.add_field(name="Requested By:", value=f"{requester}", inline=True)
        embed.add_field(name="URL", value=f"[Click Here]({song.url})", inline=True)
        if song.uploader and song.uploader_url:
            embed.add_field(name="Uploaded By:", value=f"[{song.uploader}]({song.uploader_url})", inline=True)
        if song.view_count:
            embed.add_field(name="\u200b", value=f"<:views:918875283526942790> {convert2(int(song.view_count))}")
        embed.set_image(url="https://i.imgur.com/ufxvZ0j.gif")
        embed.set_footer(text="Music By Cosmic Bot", icon_url="https://media.discordapp.net/attachments/780650657811267595/835143738749616178/PicsArt_04-23-06.53.52.jpg")
        await ctx.respond(embed=embed)

    # ─── Skip ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Skips the song")
    async def skip(self, ctx, index: Option(int, "Song index number", required=False, default=1)):
        player = get_player(ctx)
        if not player or not player.current:
            await ctx.respond("No song is being played currently!")
            return

        if player.loop:
            await ctx.respond("Disable loop first!")
            return

        if index > 1 and index - 1 < len(player.queue):
            # Skip to a specific position — remove songs before that index
            for _ in range(index - 1):
                skipped = player.queue.pop(0)
                player.history.append(skipped)

        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()  # This triggers the after callback → play_next
        await ctx.respond("<:next:887770665250345021> Skipped!")

    # ─── Queue ────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Shows the song queue")
    async def queue(self, ctx):
        player = get_player(ctx)
        if not player or not player.queue:
            await ctx.respond("Queue is Empty")
            return

        pages = []
        items_per_page = 10
        for i in range(0, len(player.queue), items_per_page):
            chunk = player.queue[i:i + items_per_page]
            desc = "\n".join(
                f"**{i + j + 1}.** {s.title} — {s.requester.mention if s.requester else 'Unknown'}"
                for j, s in enumerate(chunk)
            )
            embed = discord.Embed(
                title="Queue",
                description=f"Now Playing: **{player.current.title}**\n\n{desc}" if player.current else desc,
                color=0xfa0a12
            )
            embed.set_footer(text=f"Page {i // items_per_page + 1}/{(len(player.queue) - 1) // items_per_page + 1} • {len(player.queue)} song(s)")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.respond(embed=pages[0])
        else:
            # Simple paginator — send first page
            await ctx.respond(embed=pages[0])

    # ─── History ──────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Shows recently played songs")
    async def history(self, ctx):
        player = get_player(ctx)
        if not player or not player.history:
            await ctx.respond("No history yet!")
            return

        recent = player.history[-10:]  # Last 10
        desc = "\n".join(
            f"**{i + 1}.** {s.title} — {s.requester.mention if s.requester else 'Unknown'}"
            for i, s in enumerate(reversed(recent))
        )
        embed = discord.Embed(
            title="Song History",
            description=desc,
            color=0xfa0a12
        )
        embed.set_footer(text=f"Showing last {len(recent)} song(s)")
        await ctx.respond(embed=embed)

    # ─── Delete ───────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Deletes a particular song from the queue")
    async def delete(self, ctx, index: Option(str, "Write 'all' to clear or put a number to delete particular song")):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        if index == 'all':
            player.queue.clear()
            await ctx.respond("🗑️ Queue cleared!")
        elif index.isnumeric():
            idx = int(index) - 1
            if 0 <= idx < len(player.queue):
                removed = player.queue.pop(idx)
                await ctx.respond(f"🗑️ Removed **{removed.title}** from queue.")
            else:
                await ctx.respond("Invalid index!")
        else:
            await ctx.respond("Please enter only a number or type `all` to clear.")

    # ─── Pause ────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Pauses the song")
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.respond("<:pause:918871873650053162> Song Paused!")
        else:
            await ctx.respond("Nothing is playing!")

    # ─── Resume ───────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Resumes the song")
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.respond("<:play:918874928219050094> Song was resumed!")
        else:
            await ctx.respond("Nothing is paused!")

    # ─── Volume ───────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Changes the volume of the player.")
    async def volume(self, ctx, volume: Option(int, "Volume number [0-100]")):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        vol = max(0, min(100, volume)) / 100.0
        player.volume = vol

        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source.volume = vol

        await ctx.respond(f"🔊 Volume set to **{volume}%**")

    # ─── Loop ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Toggles loop")
    async def loop(self, ctx):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.loop = not player.loop
        if player.loop:
            player.queue_loop = False  # Disable queue loop when enabling loop
        status = "Enabled" if player.loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756>Looping {status}")

    # ─── Queue Loop ───────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Toggles queue looping")
    async def queueloop(self, ctx):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.queue_loop = not player.queue_loop
        if player.queue_loop:
            player.loop = False  # Disable single loop when enabling queue loop
        status = "Enabled" if player.queue_loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756>Queue Looping {status}")

    # ─── Spotify Info ─────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Shows Spotify song details, user is listening to")
    async def spotifyinfo(self, ctx, member: Option(discord.Member, "Specify member", required=False, default=None)):
        member = member if member else ctx.author
        spotify_result = next(
            (
                activity
                for activity in member.activities
                if isinstance(activity, discord.Spotify)
            ),
            None,
        )

        if spotify_result is None:
            await ctx.respond(f"{member.display_name} is not listening to Spotify.")
            return

        embed = discord.Embed(
            title=f"🎵 {spotify_result.title}",
            description=f"by **{', '.join(spotify_result.artists)}**",
            color=spotify_result.color,
        )
        embed.set_thumbnail(url=spotify_result.album_cover_url)
        embed.add_field(name="Album", value=spotify_result.album, inline=True)

        # Duration
        duration = spotify_result.duration
        minutes = duration.seconds // 60
        seconds = duration.seconds % 60
        embed.add_field(name="Duration", value=f"{minutes}:{seconds:02d}", inline=True)

        embed.set_footer(text=f"Listening by {member.display_name}", icon_url=member.avatar.url if member.avatar else discord.Embed.Empty)
        await ctx.respond(embed=embed)

    # ─── Before Invoke Checks ─────────────────────────────

    @skip.before_invoke
    @leave.before_invoke
    @resume.before_invoke
    @pause.before_invoke
    @loop.before_invoke
    @queueloop.before_invoke
    @delete.before_invoke
    @volume.before_invoke
    async def voice_state(self, ctx):
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id != 1102496776700833825:
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id != 888410427896242194 and ctx.channel.id != 1205935346899095552:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            elif ctx.author.voice.channel.id != 888315285629722624 or ctx.author.voice.channel.id != 1205935289269493842:
                await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()
            elif not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            elif ctx.author.voice.channel != ctx.voice_client.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to Bot's Voice Channel.")
                raise commands.CommandError()

    @join.before_invoke
    async def voice_channel(self, ctx):
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id != 1102496776700833825:
            if not ctx.author.voice or not ctx.author.voice.channel:
                raise commands.CommandError()
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id != 888410427896242194 and ctx.channel.id != 1205935346899095552:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            elif not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            elif ctx.author.voice.channel.id != 888315285629722624 or ctx.author.voice.channel.id != 1205935289269493842:
                await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()

    @queue.before_invoke
    @now_playing.before_invoke
    async def bruh(self, ctx):
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id != 1102496776700833825:
            pass
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id != 888410427896242194 and ctx.channel.id != 1205935346899095552:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()


def convert2(like):
    if like > 1000000000:
        like_2 = str((like // 10000000) / 100) + "B"
    elif like > 1000000:
        like_2 = str((like // 10000) / 100) + "M"
    elif like > 1000:
        like_2 = str((like // 10) / 100) + "K"
    else:
        like_2 = str(like)
    return like_2


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        return "%02d:%02d" % (minutes, seconds)
    else:
        return "%02d:%02d:%02d" % (hour, minutes, seconds)


def setup(bot):
    bot.add_cog(Music(bot))