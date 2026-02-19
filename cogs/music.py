import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import asyncio
import subprocess
import functools
import re
import time
from yt_dlp import YoutubeDL
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# Spotify API
SPOTIFY_CLIENT_ID = "7bff23b27d3244f28fcae1a938ab89b6"
SPOTIFY_CLIENT_SECRET = "6ee356b084e445bbbf878dfa1f5c26fd"
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))
SPOTIFY_REGEX = re.compile(r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)')


def _get_spotify_tracks(query: str) -> list[str] | None:
    """If query is a Spotify URL, return 'artist - title' search strings. None otherwise."""
    match = SPOTIFY_REGEX.search(query)
    if not match:
        return None

    spotify_type, spotify_id = match.group(1), match.group(2)
    tracks = []

    try:
        if spotify_type == 'track':
            t = sp.track(spotify_id)
            tracks.append(f"{t['artists'][0]['name']} - {t['name']}")
        elif spotify_type == 'album':
            for item in sp.album_tracks(spotify_id, limit=50)['items']:
                tracks.append(f"{item['artists'][0]['name']} - {item['name']}")
        elif spotify_type == 'playlist':
            for item in sp.playlist_tracks(spotify_id, limit=100)['items']:
                t = item.get('track')
                if t:
                    tracks.append(f"{t['artists'][0]['name']} - {t['name']}")
    except Exception as e:
        print(f"Spotify API error: {e}")
        return None

    return tracks if tracks else None


# yt-dlp options for metadata extraction (search + info, no download)
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


class Song:
    """Represents a single song with its metadata."""

    def __init__(self, data: dict, requester: discord.Member = None):
        self.data = data
        self.title = data.get('title', 'Unknown')
        self.url = data.get('webpage_url', data.get('url', ''))
        self.duration = data.get('duration', 0)
        self.thumbnail = data.get('thumbnail', '')
        self.uploader = data.get('uploader', '')
        self.uploader_url = data.get('uploader_url', '')
        self.view_count = data.get('view_count', 0)
        self.requester = requester

    @classmethod
    async def from_query_list(cls, query: str, requester: discord.Member = None):
        """Search and return a list of songs (handles playlists)."""
        loop = asyncio.get_running_loop()

        # Only enable playlist mode for actual playlist URLs
        is_playlist_url = 'playlist' in query.lower() or 'list=' in query.lower()

        opts = YDL_OPTIONS.copy()
        if is_playlist_url:
            opts['noplaylist'] = False

        try:
            with YoutubeDL(opts) as ydl:
                data = await loop.run_in_executor(
                    None, functools.partial(ydl.extract_info, query, download=False)
                )
        except Exception:
            return []

        songs = []
        if 'entries' in data:
            for entry in data['entries']:
                if entry:
                    songs.append(cls(entry, requester))
        else:
            songs.append(cls(data, requester))

        return songs


# ─── Progress Bar Helper ──────────────────────────────────

def _progress_bar(elapsed: int, total: int, length: int = 12) -> str:
    """Build a text-based progress bar like: ▬▬▬▬🔘▬▬▬▬▬ 2:30 / 5:00"""
    if total <= 0:
        return f"{'▬' * length}  {_fmt_time(elapsed)} / LIVE"

    ratio = min(elapsed / total, 1.0)
    pos = int(ratio * length)
    bar = '▬' * pos + '🔘' + '▬' * (length - pos)
    return f"{bar}  {_fmt_time(elapsed)} / {_fmt_time(total)}"


def _fmt_time(seconds: int) -> str:
    """Format seconds into MM:SS or HH:MM:SS."""
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _format_views(count: int) -> str:
    """Format large view counts into human-readable strings."""
    if count > 1_000_000_000:
        return f"{(count // 10_000_000) / 100}B views"
    elif count > 1_000_000:
        return f"{(count // 10_000) / 100}M views"
    elif count > 1_000:
        return f"{(count // 10) / 100}K views"
    return f"{count} views"


# ─── Now Playing Embed Builder ────────────────────────────

def build_now_playing_embed(player, *, for_command: bool = False) -> discord.Embed:
    """Build a Spotify-card-style now-playing embed."""
    song = player.current
    if not song:
        return discord.Embed(title="Nothing Playing", color=0x2b2d31)

    elapsed = int(time.time() - player.playback_start_time) if player.playback_start_time else 0

    # Dark theme embed
    embed = discord.Embed(color=0x1DB954)

    # Title & description
    embed.title = song.title
    if song.uploader:
        if song.uploader_url:
            embed.description = f"[{song.uploader}]({song.uploader_url})"
        else:
            embed.description = song.uploader

    # Large album art
    if song.thumbnail:
        embed.set_thumbnail(url=song.thumbnail)

    # Progress bar
    progress = _progress_bar(elapsed, int(song.duration))
    embed.add_field(name="\u200b", value=f"```{progress}```", inline=False)

    # Info row
    requester_text = song.requester.mention if song.requester else "Unknown"
    embed.add_field(name="Requested by", value=requester_text, inline=True)

    # Loop status
    if player.loop:
        loop_text = "Song Loop"
    elif player.queue_loop:
        loop_text = "Queue Loop"
    else:
        loop_text = "Off"
    embed.add_field(name="Loop", value=loop_text, inline=True)

    # Queue info
    queue_len = len(player.queue)
    embed.add_field(name="Queue", value=f"{queue_len} song{'s' if queue_len != 1 else ''}", inline=True)

    # Views
    if song.view_count:
        embed.add_field(name="\u200b", value=f"<:views:918875283526942790> {_format_views(int(song.view_count))}", inline=True)

    # URL
    if song.url:
        embed.add_field(name="Link", value=f"[Open]({song.url})", inline=True)

    embed.set_footer(text="Cosmic Bot Music")

    return embed


# ─── Now Playing View (Buttons) ──────────────────────────

class NowPlayingView(discord.ui.View):
    """Interactive music controls attached to the now-playing message."""

    def __init__(self, guild_id: int):
        super().__init__(timeout=None)
        self.guild_id = guild_id

    def _get_player(self):
        return players.get(self.guild_id)

    async def _check_vc(self, interaction: discord.Interaction) -> bool:
        """Verify the user is in the same VC as the bot."""
        player = self._get_player()
        if not player or not player.voice_client or not player.voice_client.is_connected():
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return False
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You are not in a voice channel.", ephemeral=True)
            return False
        if interaction.user.voice.channel != player.voice_client.channel:
            await interaction.response.send_message("You must be in the same voice channel as the bot.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player()
        if not player or not player.history:
            await interaction.response.send_message("No previous song in history.", ephemeral=True)
            return
        # Pop from history and insert at front of queue, then skip current
        prev_song = player.history.pop()
        player.queue.insert(0, prev_song)
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
        await interaction.response.send_message(f"Playing previous: **{prev_song.title}**", ephemeral=True)

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player()
        if not player or not player.voice_client:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        if player.voice_client.is_playing():
            player.voice_client.pause()
            button.label = "Resume"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
        elif player.voice_client.is_paused():
            player.voice_client.resume()
            button.label = "Pause"
            button.style = discord.ButtonStyle.primary
            await interaction.response.edit_message(view=self)
        else:
            await interaction.response.send_message("Nothing to pause or resume.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player()
        if not player or not player.current:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        if player.loop:
            await interaction.response.send_message("Disable loop first.", ephemeral=True)
            return
        if player.voice_client and player.voice_client.is_playing():
            player.voice_client.stop()
        await interaction.response.send_message("Skipped!", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player()
        if player:
            player.clear()
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        if self.guild_id in players:
            del players[self.guild_id]
        await interaction.response.send_message("Stopped and disconnected.", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player()
        if not player:
            await interaction.response.send_message("No active player.", ephemeral=True)
            return

        # Cycle: Off -> Song -> Queue -> Off
        if not player.loop and not player.queue_loop:
            player.loop = True
            player.queue_loop = False
            button.label = "Loop: Song"
            button.style = discord.ButtonStyle.success
        elif player.loop:
            player.loop = False
            player.queue_loop = True
            button.label = "Loop: Queue"
            button.style = discord.ButtonStyle.primary
        else:
            player.loop = False
            player.queue_loop = False
            button.label = "Loop: Off"
            button.style = discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=self)


# ─── Music Player ─────────────────────────────────────────

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
        self.playback_start_time: float | None = None
        self._play_lock = asyncio.Lock()
        self._ytdlp_process = None

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
            self.playback_start_time = None

    async def _play_song(self, song: Song):
        """Play a song by piping yt-dlp audio through FFmpeg."""
        async with self._play_lock:
            self.current = song

            if not self.voice_client or not self.voice_client.is_connected():
                return

            # Kill any existing yt-dlp process
            self._kill_ytdlp()

            # Spawn yt-dlp to pipe audio
            ytdlp_cmd = [
                'yt-dlp', '-f', 'bestaudio',
                '-o', '-', '--quiet', '--no-warnings',
                song.url
            ]
            try:
                self._ytdlp_process = subprocess.Popen(
                    ytdlp_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"Failed to spawn yt-dlp: {e}")
                await self.play_next()
                return

            source = discord.FFmpegPCMAudio(self._ytdlp_process.stdout, pipe=True)
            source = discord.PCMVolumeTransformer(source, volume=self.volume)

            self.playback_start_time = time.time()

            def after_callback(err):
                self._kill_ytdlp()
                # Schedule play_next on the event loop
                fut = asyncio.run_coroutine_threadsafe(
                    self.play_next(err), self.bot.loop
                )
                try:
                    fut.result()
                except Exception as e:
                    print(f"Error in after callback: {e}")

            self.voice_client.play(source, after=after_callback)

    def _kill_ytdlp(self):
        """Kill the yt-dlp subprocess if it's still running."""
        try:
            if self._ytdlp_process and self._ytdlp_process.poll() is None:
                self._ytdlp_process.kill()
                self._ytdlp_process = None
        except Exception:
            pass

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
            return None

    def clear(self):
        self._kill_ytdlp()
        self.queue.clear()
        self.current = None
        self.loop = False
        self.queue_loop = False
        self.playback_start_time = None


# Global dict of guild_id -> MusicPlayer
players: dict[int, MusicPlayer] = {}


def get_player(ctx) -> MusicPlayer | None:
    return players.get(ctx.guild.id)


class Music(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot

    def _get_or_create_player(self, ctx) -> MusicPlayer:
        if ctx.guild.id not in players:
            players[ctx.guild.id] = MusicPlayer(ctx)
        player = players[ctx.guild.id]
        player.voice_client = ctx.voice_client
        return player

    async def _queue_spotify_tracks(self, ctx, tracks: list[str], requester: discord.Member):
        """Background task to load remaining Spotify tracks."""
        player = self._get_or_create_player(ctx)
        loaded = 0
        for track_query in tracks:
            try:
                songs = await Song.from_query_list(track_query, requester)
                if songs:
                    player.queue.append(songs[0])
                    loaded += 1
            except Exception:
                continue
            await asyncio.sleep(0.1)

        await ctx.send_followup(f"Finished loading **{loaded}** additional tracks from Spotify.")

    # ─── Play ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Searches for the song and plays it if available.")
    async def play(self, ctx, query: Option(str, "Song name or Song/Playlist link from YT or Spotify")):
        await ctx.defer()
        await ctx.send_followup(f"Searching for **{query}**...")

        # 1. Check for Spotify URL
        spotify_tracks = await asyncio.to_thread(_get_spotify_tracks, query)

        songs = []
        background_task = None

        if spotify_tracks:
            first_track_query = spotify_tracks.pop(0)
            await ctx.send_followup(f"Found **{len(spotify_tracks) + 1}** Spotify track(s). Playing first, queuing rest in background...")

            try:
                songs = await Song.from_query_list(first_track_query, ctx.author)
            except Exception as e:
                await ctx.send_followup(f"Error searching first Spotify track: {e}")
                return

            if spotify_tracks:
                background_task = self._queue_spotify_tracks(ctx, spotify_tracks, ctx.author)
        else:
            # 2. Standard YouTube Search (or URL)
            try:
                songs = await Song.from_query_list(query, ctx.author)
            except Exception as e:
                await ctx.send_followup(f"Error searching: {e}")
                return

        if not songs:
            await ctx.send_followup("Query not found.")
            return

        # 3. Join Voice Channel
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.send_followup("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                return

            # Clean up zombie VC
            if ctx.voice_client:
                try:
                    await ctx.voice_client.disconnect(force=True)
                except Exception:
                    pass

            channel = ctx.author.voice.channel
            vc = None
            for attempt in range(3):
                try:
                    vc = await asyncio.wait_for(channel.connect(), timeout=15)
                    # Wait for the WebSocket handshake to finish (up to 5s)
                    for _ in range(10):
                        if vc.is_connected():
                            break
                        await asyncio.sleep(0.5)
                    if vc.is_connected():
                        break
                    # Still not connected — clean up and retry
                    try:
                        await vc.disconnect(force=True)
                    except Exception:
                        pass
                    vc = None
                except asyncio.TimeoutError:
                    if ctx.guild.voice_client:
                        try:
                            await ctx.guild.voice_client.disconnect(force=True)
                        except Exception:
                            pass
                    vc = None
                except Exception:
                    vc = None

            if not vc or not vc.is_connected():
                await ctx.send_followup("Failed to connect to voice channel. Please try again.")
                return

            await ctx.send_followup(f"<:call_connect:918875388527145091> Joined <#{channel.id}>")

        # 4. Play the first song(s)
        player = self._get_or_create_player(ctx)
        first_played = await player.add_and_play(songs)

        if first_played:
            embed = build_now_playing_embed(player)
            view = NowPlayingView(ctx.guild.id)
            await ctx.send_followup(embed=embed, view=view)

            # Start background task if pending
            if background_task:
                asyncio.create_task(background_task)

            # Notify if multiple YT songs added
            if len(songs) > 1 and not background_task:
                await ctx.send_followup(f"Added **{len(songs) - 1}** more song(s) to the queue.")
        else:
            if len(songs) == 1:
                await ctx.send_followup(f"**{songs[0].title}** added to queue.")
            elif not background_task:
                await ctx.send_followup(f"Added **{len(songs)}** song(s) to the queue.")

            if background_task:
                asyncio.create_task(background_task)

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

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Shows the currently playing song with controls.")
    async def now_playing(self, ctx):
        player = get_player(ctx)
        if not player or not player.current:
            await ctx.respond("No song is being played currently!")
            return

        embed = build_now_playing_embed(player, for_command=True)
        view = NowPlayingView(ctx.guild.id)
        await ctx.respond(embed=embed, view=view)

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
            for _ in range(index - 1):
                skipped = player.queue.pop(0)
                player.history.append(skipped)

        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
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
                color=0x2b2d31
            )
            embed.set_footer(text=f"Page {i // items_per_page + 1}/{(len(player.queue) - 1) // items_per_page + 1} | {len(player.queue)} song(s)")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.respond(embed=pages[0])
        else:
            await ctx.respond(embed=pages[0])

    # ─── History ──────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Shows recently played songs")
    async def history(self, ctx):
        player = get_player(ctx)
        if not player or not player.history:
            await ctx.respond("No history yet!")
            return

        recent = player.history[-10:]
        desc = "\n".join(
            f"**{i + 1}.** {s.title} — {s.requester.mention if s.requester else 'Unknown'}"
            for i, s in enumerate(reversed(recent))
        )
        embed = discord.Embed(
            title="Song History",
            description=desc,
            color=0x2b2d31
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
            await ctx.respond("Queue cleared!")
        elif index.isnumeric():
            idx = int(index) - 1
            if 0 <= idx < len(player.queue):
                removed = player.queue.pop(idx)
                await ctx.respond(f"Removed **{removed.title}** from queue.")
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

        await ctx.respond(f"Volume set to **{volume}%**")

    # ─── Loop ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Toggles loop")
    async def loop(self, ctx):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.loop = not player.loop
        if player.loop:
            player.queue_loop = False
        status = "Enabled" if player.loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756> Looping {status}")

    # ─── Queue Loop ───────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Toggles queue looping")
    async def queueloop(self, ctx):
        player = get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.queue_loop = not player.queue_loop
        if player.queue_loop:
            player.loop = False
        status = "Enabled" if player.queue_loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756> Queue Looping {status}")

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
            title=spotify_result.title,
            description=f"by **{', '.join(spotify_result.artists)}**",
            color=0x1DB954,
        )
        embed.set_thumbnail(url=spotify_result.album_cover_url)
        embed.add_field(name="Album", value=spotify_result.album, inline=True)

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
        # Allow if user has specific roles OR if in a non-restricted guild
        has_role = (
            ctx.guild.get_role(767591734850879495) in ctx.author.roles
            or ctx.guild.get_role(816681109001207808) in ctx.author.roles
        )
        is_restricted_guild = ctx.guild.id in (767591734841835540, 1102496776700833825)

        if has_role or not is_restricted_guild:
            # Just check that user is in a VC
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
        else:
            # Restricted guild, non-privileged user
            allowed_channels = (767591735693410370, 888410427896242194, 1205935346899095552)
            allowed_vcs = (888315285629722624, 1205935289269493842)

            if ctx.channel.id not in allowed_channels:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            if ctx.author.voice.channel.id not in allowed_vcs:
                await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()
            if ctx.voice_client and ctx.author.voice.channel != ctx.voice_client.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to Bot's Voice Channel.")
                raise commands.CommandError()

    @join.before_invoke
    async def voice_channel(self, ctx):
        has_role = (
            ctx.guild.get_role(767591734850879495) in ctx.author.roles
            or ctx.guild.get_role(816681109001207808) in ctx.author.roles
        )
        is_restricted_guild = ctx.guild.id in (767591734841835540, 1102496776700833825)

        if has_role or not is_restricted_guild:
            if not ctx.author.voice or not ctx.author.voice.channel:
                raise commands.CommandError()
        else:
            allowed_channels = (767591735693410370, 888410427896242194, 1205935346899095552)
            allowed_vcs = (888315285629722624, 1205935289269493842)

            if ctx.channel.id not in allowed_channels:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            if not ctx.author.voice or not ctx.author.voice.channel:
                await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            if ctx.author.voice.channel.id not in allowed_vcs:
                await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()

    @queue.before_invoke
    @now_playing.before_invoke
    async def bruh(self, ctx):
        has_role = (
            ctx.guild.get_role(767591734850879495) in ctx.author.roles
            or ctx.guild.get_role(816681109001207808) in ctx.author.roles
        )
        is_restricted_guild = ctx.guild.id in (767591734841835540, 1102496776700833825)

        if has_role or not is_restricted_guild:
            pass
        else:
            allowed_channels = (767591735693410370, 888410427896242194, 1205935346899095552)
            if ctx.channel.id not in allowed_channels:
                await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()


def setup(bot):
    bot.add_cog(Music(bot))