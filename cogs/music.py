import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import asyncio
import subprocess
import functools
import re
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
            # Handle pagination for playlists > 100 tracks? 
            # For now limit to 100 for speed, users can re-run.
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

    async def _play_song(self, song: Song):
        """Play a song by piping yt-dlp audio through FFmpeg."""
        async with self._play_lock:
            self.current = song

            if not self.voice_client or not self.voice_client.is_connected():
                return

            # Kill any existing yt-dlp process
            self._kill_ytdlp()

            # Spawn yt-dlp to pipe audio — bypasses YouTube IP blocking
            # Enforce bestaudio and standard options
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
        total = len(tracks)
        for i, track_query in enumerate(tracks):
            try:
                # Search one by one — respecting ratelimits implicitly by serializing
                songs = await Song.from_query_list(track_query, requester)
                if songs:
                    player.queue.append(songs[0])
            except Exception:
                continue
            
            # Optional: Log progress or yield to loop
            await asyncio.sleep(0.1)

        await ctx.send_followup(f"✅ Finished loading **{total}** additional tracks from Spotify.")

    # ─── Play ─────────────────────────────────────────────

    @slash_command(guild_ids=[767591734841835540, 1102496776700833825], description="Searches for the song and plays it if available.")
    async def play(self, ctx, query: Option(str, "Song name or Song/Playlist link from YT or Spotify")):
        await ctx.defer()
        await ctx.send_followup(f"🔍 Searching for **{query}**...")

        # 1. Check for Spotify URL
        spotify_tracks = await asyncio.to_thread(_get_spotify_tracks, query)
        
        songs = []
        background_task = None

        if spotify_tracks:
            # We found Spotify tracks!
            first_track_query = spotify_tracks.pop(0)
            await ctx.send_followup(f"🎵 Found **{len(spotify_tracks) + 1}** Spotify track(s). Playing first, queuing rest...")
            
            # Resolve the first song immediately
            try:
                songs = await Song.from_query_list(first_track_query, ctx.author)
            except Exception as e:
                await ctx.send_followup(f"❌ Error searching first Spotify track: {e}")
                return

            if spotify_tracks:
                # Schedule the rest to be loaded in background
                background_task = self._queue_spotify_tracks(ctx, spotify_tracks, ctx.author)

        else:
            # 2. Standard YouTube Search (or URL)
            try:
                songs = await Song.from_query_list(query, ctx.author)
            except Exception as e:
                await ctx.send_followup(f"❌ Error searching: {e}")
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
                    await asyncio.sleep(1)
                    if vc.is_connected():
                        break
                    else:
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
                await ctx.send_followup("❌ Failed to connect to voice channel. Please try again.")
                return

            await ctx.send_followup(f"<:call_connect:918875388527145091> Joined <#{channel.id}>")

        # 4. Play the first song(s)
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

            # 5. Start background task if pending
            if background_task:
                asyncio.create_task(background_task)
            
            # 6. Notify if multiple YT songs added (only for non-background playlist)
            if len(songs) > 1 and not background_task:
                await ctx.send_followup(f"📋 Added **{len(songs) - 1}** more song(s) to the queue.")
        else:
            if len(songs) == 1:
                await ctx.send_followup(f"📋 **{songs[0].title}** added to queue.")
            elif not background_task:
                await ctx.send_followup(f"📋 Added **{len(songs)}** song(s) to the queue.")
            
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
                color=0xfa0a12
            )
            embed.set_footer(text=f"Page {i // items_per_page + 1}/{(len(player.queue) - 1) // items_per_page + 1} • {len(player.queue)} song(s)")
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
            player.queue_loop = False
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
            player.loop = False
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