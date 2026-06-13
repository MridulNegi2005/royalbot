import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import asyncio
import re
import time
import os
import wavelink


# ─── Spotify URL regex (used to detect Spotify links) ─────
SPOTIFY_REGEX = re.compile(r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)')


# ─── Song Wrapper ─────────────────────────────────────────

class Song:
    """Wraps a wavelink.Playable to provide a consistent interface
    that matches the old yt-dlp-based Song class."""

    def __init__(self, track: wavelink.Playable, requester: discord.Member = None):
        self.track = track
        self.title = track.title or 'Unknown'
        self.url = getattr(track, 'uri', '') or ''
        self.duration = (track.length or 0) / 1000  # Wavelink gives ms, we use seconds
        self.thumbnail = getattr(track, 'artwork', '') or ''
        self.uploader = getattr(track, 'author', '') or ''
        self.uploader_url = ''
        self.view_count = 0
        self.requester = requester

    @classmethod
    async def from_query(cls, query: str, requester: discord.Member = None) -> list['Song']:
        """Search for tracks and return a list of Song objects.
        Handles YouTube URLs, YouTube search, Spotify URLs (via LavaSrc),
        and YouTube playlists."""

        tracks: wavelink.Search = await wavelink.Playable.search(query)

        if not tracks:
            return []

        songs = []
        # If it's a playlist, tracks will be a Playlist object
        if isinstance(tracks, wavelink.Playlist):
            for track in tracks.tracks:
                songs.append(cls(track, requester))
        else:
            # Single track or search results — take the first result
            # Unless it's a direct URL which returns exactly one track
            if _is_url(query):
                # Direct URL — add all returned tracks (usually 1)
                for track in tracks:
                    songs.append(cls(track, requester))
            else:
                # Search query — take only the first result
                songs.append(cls(tracks[0], requester))

        return songs


def _is_url(query: str) -> bool:
    """Check if a query looks like a URL."""
    return query.startswith(('http://', 'https://'))


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


# ─── Custom Player ────────────────────────────────────────

class CosmicPlayer(wavelink.Player):
    """Custom Wavelink Player that adds queue, history, and loop state."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue_list: list[Song] = []
        self.history: list[Song] = []
        self.current_song: Song | None = None
        self.song_loop: bool = False
        self.queue_loop: bool = False
        self.text_channel: discord.TextChannel | None = None
        self.playback_start_time: float | None = None

    async def play_song(self, song: Song):
        """Play a Song object on this player."""
        self.current_song = song
        self.playback_start_time = time.time()

        # Volume is 0-1000 in Lavalink. We store as 0-100 user-facing.
        await self.play(song.track)

    async def play_next(self):
        """Advance to the next song in the queue."""
        # If looping current song, replay it
        if self.song_loop and self.current_song:
            await self.play_song(self.current_song)
            return

        # If queue looping, push current song to end of queue
        if self.queue_loop and self.current_song:
            self.queue_list.append(self.current_song)

        # Add current song to history
        if self.current_song:
            self.history.append(self.current_song)

        # Play next song in queue
        if self.queue_list:
            next_song = self.queue_list.pop(0)
            await self.play_song(next_song)
        else:
            self.current_song = None
            self.playback_start_time = None

    async def add_and_play(self, songs: list[Song]) -> Song | None:
        """Add songs to the queue. If nothing is playing, start playback."""
        if not songs:
            return None

        if self.current_song is None or (not self.playing and not self.paused):
            # Nothing playing => play the first song immediately, queue the rest
            first = songs[0]
            self.queue_list.extend(songs[1:])
            await self.play_song(first)
            return first
        else:
            # Something is playing => queue everything
            self.queue_list.extend(songs)
            return None

    def clear_queue(self):
        """Clear the queue and reset state."""
        self.queue_list.clear()
        self.current_song = None
        self.song_loop = False
        self.queue_loop = False
        self.playback_start_time = None


# Global reference for the NowPlayingView to access players
# (wavelink.Player is accessed via guild.voice_client)
def _get_cosmic_player(guild: discord.Guild) -> CosmicPlayer | None:
    """Get the CosmicPlayer for a guild, if it exists."""
    vc = guild.voice_client
    if isinstance(vc, CosmicPlayer):
        return vc
    return None


# ─── Now Playing Embed Builder ────────────────────────────

def build_now_playing_embed(player: CosmicPlayer, *, for_command: bool = False) -> discord.Embed:
    """Build a Spotify-card-style now-playing embed."""
    song = player.current_song
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
    if player.song_loop:
        loop_text = "Song Loop"
    elif player.queue_loop:
        loop_text = "Queue Loop"
    else:
        loop_text = "Off"
    embed.add_field(name="Loop", value=loop_text, inline=True)

    # Queue info
    queue_len = len(player.queue_list)
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

    def _get_player(self, interaction: discord.Interaction) -> CosmicPlayer | None:
        guild = interaction.guild
        if guild:
            return _get_cosmic_player(guild)
        return None

    async def _check_vc(self, interaction: discord.Interaction) -> bool:
        """Verify the user is in the same VC as the bot."""
        player = self._get_player(interaction)
        if not player or not player.is_connected():
            await interaction.response.send_message("Bot is not connected to a voice channel.", ephemeral=True)
            return False
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You are not in a voice channel.", ephemeral=True)
            return False
        if interaction.user.voice.channel != player.channel:
            await interaction.response.send_message("You must be in the same voice channel as the bot.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Prev", style=discord.ButtonStyle.secondary, row=0)
    async def prev_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player(interaction)
        if not player or not player.history:
            await interaction.response.send_message("No previous song in history.", ephemeral=True)
            return
        # Pop from history and insert at front of queue, then skip current
        prev_song = player.history.pop()
        player.queue_list.insert(0, prev_song)
        # Respond BEFORE stopping — player.stop() may interfere with interaction state
        await interaction.response.send_message(f"Playing previous: **{prev_song.title}**", ephemeral=True)
        await player.stop()

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary, row=0)
    async def pause_resume_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player(interaction)
        if not player:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        if player.playing and not player.paused:
            button.label = "Resume"
            button.style = discord.ButtonStyle.success
            await interaction.response.edit_message(view=self)
            await player.pause(True)
        elif player.paused:
            button.label = "Pause"
            button.style = discord.ButtonStyle.primary
            await interaction.response.edit_message(view=self)
            await player.pause(False)
        else:
            await interaction.response.send_message("Nothing to pause or resume.", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, row=0)
    async def skip_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player(interaction)
        if not player or not player.current_song:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        if player.song_loop:
            await interaction.response.send_message("Disable loop first.", ephemeral=True)
            return
        # Respond BEFORE stopping
        await interaction.response.send_message("Skipped!", ephemeral=True)
        await player.stop()

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player(interaction)
        # Respond BEFORE disconnecting
        await interaction.response.send_message("Stopped and disconnected.", ephemeral=True)
        if player:
            player.clear_queue()
            await player.disconnect()
        self.stop()

    @discord.ui.button(label="Loop: Off", style=discord.ButtonStyle.secondary, row=1)
    async def loop_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        if not await self._check_vc(interaction):
            return
        player = self._get_player(interaction)
        if not player:
            await interaction.response.send_message("No active player.", ephemeral=True)
            return

        # Cycle: Off -> Song -> Queue -> Off
        if not player.song_loop and not player.queue_loop:
            player.song_loop = True
            player.queue_loop = False
            button.label = "Loop: Song"
            button.style = discord.ButtonStyle.success
        elif player.song_loop:
            player.song_loop = False
            player.queue_loop = True
            button.label = "Loop: Queue"
            button.style = discord.ButtonStyle.primary
        else:
            player.song_loop = False
            player.queue_loop = False
            button.label = "Loop: Off"
            button.style = discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=self)


# ─── Music Cog ────────────────────────────────────────────

class Music(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot

    def _get_player(self, ctx) -> CosmicPlayer | None:
        return _get_cosmic_player(ctx.guild)

    # ─── Wavelink Events ──────────────────────────────────

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"[LAVALINK] Node '{payload.node.identifier}' is ready! "
              f"(Resumed: {payload.resumed}, Session: {payload.session_id})")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Called when a track finishes. Advance the queue."""
        player = payload.player
        if not isinstance(player, CosmicPlayer):
            return

        # Advance on FINISHED (natural end), LOAD_FAILED (error), and STOPPED (skip)
        # Do NOT advance on REPLACED (a new track was already started via player.play())
        if str(payload.reason).upper() in ("FINISHED", "LOAD_FAILED", "STOPPED"):
            await player.play_next()

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """Called when a track starts playing. Update playback time."""
        player = payload.player
        if isinstance(player, CosmicPlayer):
            player.playback_start_time = time.time()

    # ─── Play ─────────────────────────────────────────────

    @slash_command(description="Searches for the song and plays it if available.")
    async def play(self, ctx, query: Option(str, "Song name or Song/Playlist link from YT or Spotify")):
        await ctx.defer()

        # 1. Check if user is in a voice channel
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send_followup("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
            return

        channel = ctx.author.voice.channel

        # 2. Connect or get existing player
        player: CosmicPlayer | None = self._get_player(ctx)
        if not player:
            try:
                player = await channel.connect(cls=CosmicPlayer)
                player.text_channel = ctx.channel
                await ctx.send_followup(f"<:call_connect:918875388527145091> Joined <#{channel.id}>")
            except Exception as e:
                print(f"[MUSIC] Failed to connect: {e}")
                await ctx.send_followup("Failed to connect to voice channel. Please try again.")
                return
        elif not player.is_connected():
            try:
                await player.connect(timeout=60.0)
                player.text_channel = ctx.channel
                await ctx.send_followup(f"<:call_connect:918875388527145091> Joined <#{channel.id}>")
            except Exception as e:
                print(f"[MUSIC] Failed to reconnect: {e}")
                await ctx.send_followup("Failed to connect to voice channel. Please try again.")
                return

        # 3. Search for tracks
        await ctx.send_followup(f"Searching for **{query}**...")

        # Detect Spotify URL and prefix for LavaSrc
        spotify_match = SPOTIFY_REGEX.search(query)
        if spotify_match and not query.startswith(('http://', 'https://')):
            # Shouldn't happen but just in case
            pass

        try:
            songs = await Song.from_query(query, ctx.author)
        except Exception as e:
            print(f"[MUSIC] Search error: {e}")
            await ctx.send_followup(f"Error searching: {e}")
            return

        if not songs:
            await ctx.send_followup("Query not found.")
            return

        # 4. Play
        first_played = await player.add_and_play(songs)

        if first_played:
            embed = build_now_playing_embed(player)
            view = NowPlayingView(ctx.guild.id)
            await ctx.send_followup(embed=embed, view=view)

            if len(songs) > 1:
                await ctx.send_followup(f"Added **{len(songs) - 1}** more song(s) to the queue.")
        else:
            if len(songs) == 1:
                await ctx.send_followup(f"**{songs[0].title}** added to queue.")
            else:
                await ctx.send_followup(f"Added **{len(songs)}** song(s) to the queue.")

    # ─── Join ─────────────────────────────────────────────

    @slash_command(description="Joins the VC you are currently in.")
    async def join(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
            return

        player = self._get_player(ctx)
        if player and player.is_connected():
            await player.move_to(ctx.author.voice.channel)
        else:
            await ctx.author.voice.channel.connect(cls=CosmicPlayer)

        await ctx.respond(f"<:call_connect:918875388527145091> Joined <#{ctx.author.voice.channel.id}>")

    # ─── Leave ────────────────────────────────────────────

    @slash_command(description="Disconnects the bot from VC")
    async def leave(self, ctx):
        player = self._get_player(ctx)
        if player:
            player.clear_queue()
            await player.disconnect()
            await ctx.respond("<:call_disconnect:918875403567910933> Left Voice Channel")
        else:
            await ctx.respond("I'm not connected to a voice channel!")

    # ─── Now Playing ──────────────────────────────────────

    @slash_command(description="Shows the currently playing song with controls.")
    async def now_playing(self, ctx):
        player = self._get_player(ctx)
        if not player or not player.current_song:
            await ctx.respond("No song is being played currently!")
            return

        embed = build_now_playing_embed(player, for_command=True)
        view = NowPlayingView(ctx.guild.id)
        await ctx.respond(embed=embed, view=view)

    # ─── Skip ─────────────────────────────────────────────

    @slash_command(description="Skips the song")
    async def skip(self, ctx, index: Option(int, "Song index number", required=False, default=1)):
        player = self._get_player(ctx)
        if not player or not player.current_song:
            await ctx.respond("No song is being played currently!")
            return

        if player.song_loop:
            await ctx.respond("Disable loop first!")
            return

        if index > 1 and index - 1 < len(player.queue_list):
            for _ in range(index - 1):
                skipped = player.queue_list.pop(0)
                player.history.append(skipped)

        # Stop triggers track_end which calls play_next
        await player.stop()
        await ctx.respond("<:next:887770665250345021> Skipped!")

    # ─── Queue ────────────────────────────────────────────

    @slash_command(description="Shows the song queue")
    async def queue(self, ctx):
        player = self._get_player(ctx)
        if not player or not player.queue_list:
            await ctx.respond("Queue is Empty")
            return

        pages = []
        items_per_page = 10
        for i in range(0, len(player.queue_list), items_per_page):
            chunk = player.queue_list[i:i + items_per_page]
            desc = "\n".join(
                f"**{i + j + 1}.** {s.title} — {s.requester.mention if s.requester else 'Unknown'}"
                for j, s in enumerate(chunk)
            )
            embed = discord.Embed(
                title="Queue",
                description=f"Now Playing: **{player.current_song.title}**\n\n{desc}" if player.current_song else desc,
                color=0x2b2d31
            )
            embed.set_footer(text=f"Page {i // items_per_page + 1}/{(len(player.queue_list) - 1) // items_per_page + 1} | {len(player.queue_list)} song(s)")
            pages.append(embed)

        if len(pages) == 1:
            await ctx.respond(embed=pages[0])
        else:
            await ctx.respond(embed=pages[0])

    # ─── History ──────────────────────────────────────────

    @slash_command(description="Shows recently played songs")
    async def history(self, ctx):
        player = self._get_player(ctx)
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

    @slash_command(description="Deletes a particular song from the queue")
    async def delete(self, ctx, index: Option(str, "Write 'all' to clear or put a number to delete particular song")):
        player = self._get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        if index == 'all':
            player.queue_list.clear()
            await ctx.respond("Queue cleared!")
        elif index.isnumeric():
            idx = int(index) - 1
            if 0 <= idx < len(player.queue_list):
                removed = player.queue_list.pop(idx)
                await ctx.respond(f"Removed **{removed.title}** from queue.")
            else:
                await ctx.respond("Invalid index!")
        else:
            await ctx.respond("Please enter only a number or type `all` to clear.")

    # ─── Pause ────────────────────────────────────────────

    @slash_command(description="Pauses the song")
    async def pause(self, ctx):
        player = self._get_player(ctx)
        if player and player.playing and not player.paused:
            await player.pause(True)
            await ctx.respond("<:pause:918871873650053162> Song Paused!")
        else:
            await ctx.respond("Nothing is playing!")

    # ─── Resume ───────────────────────────────────────────

    @slash_command(description="Resumes the song")
    async def resume(self, ctx):
        player = self._get_player(ctx)
        if player and player.paused:
            await player.pause(False)
            await ctx.respond("<:play:918874928219050094> Song was resumed!")
        else:
            await ctx.respond("Nothing is paused!")

    # ─── Volume ───────────────────────────────────────────

    @slash_command(description="Changes the volume of the player.")
    async def volume(self, ctx, volume: Option(int, "Volume number [0-100]")):
        player = self._get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        vol = max(0, min(100, volume))
        # Lavalink volume range is 0-1000, but 0-100 maps nicely as percentage
        # wavelink's set_volume() accepts 0-1000
        await player.set_volume(vol * 10)

        await ctx.respond(f"Volume set to **{vol}%**")

    # ─── Loop ─────────────────────────────────────────────

    @slash_command(description="Toggles loop")
    async def loop(self, ctx):
        player = self._get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.song_loop = not player.song_loop
        if player.song_loop:
            player.queue_loop = False
        status = "Enabled" if player.song_loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756> Looping {status}")

    # ─── Queue Loop ───────────────────────────────────────

    @slash_command(description="Toggles queue looping")
    async def queueloop(self, ctx):
        player = self._get_player(ctx)
        if not player:
            await ctx.respond("No active player!")
            return

        player.queue_loop = not player.queue_loop
        if player.queue_loop:
            player.song_loop = False
        status = "Enabled" if player.queue_loop else "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756> Queue Looping {status}")

    # ─── Spotify Info ─────────────────────────────────────

    @slash_command(description="Shows Spotify song details, user is listening to")
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