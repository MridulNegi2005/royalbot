import discordSuperUtils
from discord.ext import commands
from discordSuperUtils import MusicManager, PageManager
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
import ffmpeg
import discord
import asyncio
import json
from yt_dlp import YoutubeDL
class Music(commands.Cog, discordSuperUtils.CogManager.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.vote={}
        self.client_secret = "6ee356b084e445bbbf878dfa1f5c26fd"
        self.client_id = "7bff23b27d3244f28fcae1a938ab89b6"
        self.MusicManager = MusicManager(self.bot,inactivity_timeout=None,spotify_support=True,client_id=self.client_id,client_secret=self.client_secret)
        self.ImageManager = discordSuperUtils.ImageManager()
        super().__init__()

          
    @discordSuperUtils.CogManager.event(discordSuperUtils.MusicManager)
    async def on_music_error(self, ctx, error):
        if isinstance(error, discordSuperUtils.NotPlaying):
            await ctx.respond("No song is being played currently!")
            raise error
        elif isinstance(error, discordSuperUtils.SkipError):
            await ctx.respond("This is the last song being played!")
            raise error
        elif isinstance(error, discordSuperUtils.QueueEmpty):
            if ctx.command.name == 'leave':
                return
            await ctx.respond("Queue is Empty")
            raise commands.CommandError()
        else:raise error  # Add error handling here
    async def play_cmd(self, ctx, query):
        await ctx.defer()  # Defer immediately to prevent timeout

        join_message = None
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            vc = await self.MusicManager.join(ctx)
            join_message = f"<:call_connect:918875388527145091> Joined <#{vc.id}>"

        async with ctx.typing():
            players = await self.MusicManager.create_player(query, ctx.author)

        if players:
            if await self.MusicManager.queue_add(players=players, ctx=ctx) and not await self.MusicManager.play(ctx):
                msg = f"{players[-1].title}\nAdded to queue"
            else:
                msg = None
        else:
            msg = "Query not found."

        # Send all responses as followups after deferring
        if join_message:
            await ctx.send_followup(join_message)
        if msg:
            await ctx.send_followup(msg)
            
    @discordSuperUtils.CogManager.event(discordSuperUtils.MusicManager)
    async def on_play(self, ctx, player):
        if player.requester==None:
            requester = "Autoplay"
        else:
            requester = player.requester.mention
        ydl_opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'verbose': True
        }
        try:
            with YoutubeDL(ydl_opts) as yt:
                info = yt.extract_info(player.url, download=False)
                thumbnail_url = info.get('thumbnail')
                author = info.get('uploader')
                channel_url = info.get('uploader_url')
        except Exception as e:
            await ctx.send_followup(f"Download error: {str(e)}. Please make sure the video is public and available, and that yt-dlp is up to date.")
            return
        embed = discord.Embed(title="<:play:918874928219050094> Now Playing", description=f"**{player.title}**", color=0xfa0a12)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.add_field(name="Duration:", value=f"{convert(int(player.duration))}", inline=True)
        embed.add_field(name="Requested By:", value=f"{requester}", inline=True)
        embed.add_field(name="URL", value=f"[Click Here]({player.url})", inline=True)
        if author and channel_url:
            embed.add_field(name="Uploaded By:", value=f"[{author}]({channel_url})", inline=True)
        embed.set_footer(text=f"Music By Cosmic Bot", icon_url="https://i.ibb.co/fNkh1QD/avatr.png")
        await ctx.respond(embed=embed)

    
    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Disconnects the bot from VC")
    async def leave(self, ctx):
        try:
            if queue := await self.MusicManager.get_queue(ctx):
                loop = queue.loop
                if loop == discordSuperUtils.Loops.LOOP:
                    await self.MusicManager.loop(ctx)
                elif loop == discordSuperUtils.Loops.QUEUE_LOOP:
                    await self.MusicManager.queueloop(ctx)
                queue.clear()
        except:pass
        await self.MusicManager.leave(ctx)
        await ctx.respond("<:call_disconnect:918875403567910933> Left Voice Channel")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Gives information about currently playing song!")
    async def now_playing(self, ctx):
        if player := await self.MusicManager.now_playing(ctx):
            if queue := await self.MusicManager.get_queue(ctx):
                loop = queue.loop
                loop_status = None
                if loop == discordSuperUtils.Loops.LOOP:
                    loop_status = "Enabled."
                elif loop == discordSuperUtils.Loops.QUEUE_LOOP:
                    loop_status = "Queue Loop Enabled."
                elif loop == discordSuperUtils.Loops.NO_LOOP:
                    loop_status = "Disabled"
            if player.requester == None:
                requester = "Autoplay"
            else:
                requester = player.requester.mention
            ydl_opts = {
                'format': 'bestaudio/best',
                'noplaylist': True,
                'quiet': True,
                'nocheckcertificate': True,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'verbose': True
            }
            try:
                with YoutubeDL(ydl_opts) as yt:
                    info = yt.extract_info(player.url, download=False)
                    thumbnail_url = info.get('thumbnail')
                    author = info.get('uploader')
                    channel_url = info.get('uploader_url')
                    views = info.get('view_count')
            except Exception as e:
                await ctx.send_followup(f"Download error: {str(e)}. Please make sure the video is public and available, and that yt-dlp is up to date.")
                return
            played = await self.MusicManager.get_player_played_duration(ctx, player)
            embed = discord.Embed(title="<:play:918874928219050094> Now Playing", description=f"**{player.data['title']}**", color=0xfa0a12)
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)
            embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar.url)
            embed.add_field(name="Played:", value=f"{convert(played)}", inline=True)
            embed.add_field(name="Duration:", value=f"{convert(int(player.duration))}", inline=True)
            embed.add_field(name="Looping:", value=f"{loop_status}", inline=True)
            embed.add_field(name="Requested By:", value=f"{requester}", inline=True)
            embed.add_field(name="URL", value=f"[Click Here]({player.url})", inline=True)
            if author and channel_url:
                embed.add_field(name="Uploaded By:", value=f"[{author}]({channel_url})", inline=True)
            if views:
                embed.add_field(name="\u200b", value=f"<:views:918875283526942790> {convert2(int(views))}")
            embed.set_image(url=f"https://i.imgur.com/ufxvZ0j.gif")
            embed.set_footer(text=f"Music By Cosmic Bot", icon_url="https://media.discordapp.net/attachments/780650657811267595/835143738749616178/PicsArt_04-23-06.53.52.jpg")
            await ctx.respond(embed=embed)
    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Joins the VC you are currently in.")
    async def join(self, ctx):
        if vc :=await self.MusicManager.join(ctx):
            await ctx.respond(f"<:call_connect:918875388527145091> Joined <#{vc.id}>")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Searches for the song and plays it if available.")
    async def play(self, ctx,query:Option(str,"Song name or Song/Playlist link from YT or Spotify")):
        await Music.play_cmd(self,ctx,query)


    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Changes the volume of the player.")
    async def volume(self, ctx, volume:Option(int,"Volume number [0-100]")):
        await self.MusicManager.volume(ctx, volume)
        await ctx.respond("Volume changed successfully!")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Toggles loop")
    async def loop(self, ctx):
        is_loop = await self.MusicManager.loop(ctx)
        if is_loop == True:
            loop ="Enabled"
        elif is_loop == False:
            loop = "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756>Looping {loop}")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Toggles queue looping")
    async def queueloop(self, ctx):
        is_loop = await self.MusicManager.queueloop(ctx)
        if is_loop == True:
            loop ="Enabled"
        elif is_loop == False:
            loop = "Disabled"
        await ctx.respond(f"<:Loop:956597783744372756>Queue Looping {loop}")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Shows recently playes songs")
    async def history(self, ctx):
        formatted_history = [
            f"Title: '{x.title}'\nRequester: {x.requester.mention}" for x in ((await self.MusicManager.get_queue(ctx)).history)
        ]
        embeds = discordSuperUtils.generate_embeds(formatted_history,
                                                   "Song History",
                                                   "Shows all played songs",
                                                   10,
                                                   string_format="{}")

        page_manager = discordSuperUtils.PageManager(ctx, embeds, public=True)
        await page_manager.run()

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Skips the song")
    async def skip(self, ctx, index:Option(int,"Song index number",required=False,default=1)):
        if player := await self.MusicManager.now_playing(ctx):
            if queue := await self.MusicManager.get_queue(ctx):
                
                loop = queue.loop
                loop_status = None
                if loop == discordSuperUtils.Loops.LOOP:
                    loop_status = True
                elif loop == discordSuperUtils.Loops.NO_LOOP:
                    loop_status = False
            if loop_status==True:
                await ctx.respond("Disable loop first!")
                return
            if await self.MusicManager.skip(ctx, index-1):
                pass
            '''elif voter != player.requester.id:
            
                count = len(ctx.author.voice.channel.members)
                print(count)
                if count <= 3:
                    if await self.MusicManager.skip(ctx, index):
                        await ctx.message.add_reaction("<:next:887770665250345021>")
                elif count > 3 and count < 8:
                    if voter not in self.vote:
                        self.vote.append(voter)
                        print(len(self.vote))
                        if len(self.vote) >=(count-2):
                            if await self.MusicManager.skip(ctx, index):
                                await ctx.message.add_reaction("<:next:887770665250345021>")
                elif count >= 8:
                    if voter not in self.vote:
                        self.vote.append(voter)
                        print(len(self.vote))
                        if len(self.vote) >=(count-2):
                            if await self.MusicManager.skip(ctx, index):
                                await ctx.message.add_reaction("<:next:887770665250345021>")'''



    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Shows the song queue")
    async def queue(self, ctx):
        if await self.MusicManager.get_queue(ctx):
            formatted_queue = [
            f"Title: '{x.title}\nRequester: {x.requester.mention}"
            for x in (await self.MusicManager.get_queue(ctx)).queue
        ]

        embeds = discordSuperUtils.generate_embeds(
            formatted_queue,
            "Queue",
            f"Now Playing: {await self.MusicManager.now_playing(ctx)}",
            10,
            string_format="{}",
        )

        page_manager = discordSuperUtils.PageManager(ctx, embeds, public=True,emojis=["<:fast_backward:918877900109914122>","<:backward:918872031796277320>", "<:forward:918871999596617790>","<:fast_forward:918872194099077191>"])
        await page_manager.run()
    @queue.error
    async def queue_error(self,ctx,error):
        if isinstance(error, discordSuperUtils.QueueEmpty):
            await ctx.respond("Queue is Empty")
            raise commands.CommandError()

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Deletes the particular song from the queue")
    async def delete(self, ctx,index:Option(str,"Write 'all' to clear or put a number to delete particular song")):
        if index == 'all':
            queue = await self.MusicManager.get_queue(ctx)
            queue.clear()
        elif index.isnumeric() : 
            await self.MusicManager.queue_remove(ctx, (int(index)-1))
        else:
            await ctx.respond("Please enter only number or type `all` to clear")
    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Pauses the song")
    async def pause(self, ctx):
        await self.MusicManager.pause(ctx)
        await ctx.respond(f"<:pause:918871873650053162> Song Paused!")
		
    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Resumes the song")
    async def resume(self, ctx):
        await self.MusicManager.resume(ctx)
        await ctx.respond(f"<:play:918874928219050094> Song was resumed!")

    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Shows lyrics if available")
    async def lyrics(self,ctx, query:Option(str,"Song name to search lyrics for",required=False,default=None)):
        if response := await self.MusicManager.lyrics(ctx, query):
            title, author, query_lyrics = response

            splitted = query_lyrics.split("\n")
            res = []
            current = ""
            for i, split in enumerate(splitted):
                if len(splitted) <= i + 1 or len(current) + len(splitted[i + 1]) > 1024:
                    res.append(current)
                    current = ""
                    continue
                current += split + "\n"

            page_manager = discordSuperUtils.PageManager(
                ctx,
                [
                    discord.Embed(
                        title=f"Lyrics for '{title}' by '{author}', (Page {i + 1}/{len(res)})",
                        description=x,
                    )
                    for i, x in enumerate(res)
                ],
                public=True,
            )
            await page_manager.run()
        else:
            await ctx.respond("No lyrics found.")

    # Spotify song details of a user
    @slash_command(guild_ids=[767591734841835540,1102496776700833825],description="Shows Spotify song details, user is listening to")
    async def spotifyinfo(self, ctx, member:Option(discord.Member,"Specify member",required=False,default=None)):
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

        image = await self.ImageManager.create_spotify_card(
            spotify_activity=spotify_result, font_path=None
        )

        await ctx.respond(file=image)

    @skip.before_invoke
    @leave.before_invoke
    @resume.before_invoke
    @pause.before_invoke
    @loop.before_invoke
    @queueloop.before_invoke
    @delete.before_invoke
    @volume.before_invoke
    async def voice_state(self,ctx):
    
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id!=1102496776700833825 :
            if not ctx.author.voice or not ctx.author.voice.channel:
                msg = await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id !=888410427896242194 and ctx.channel.id!=1205935346899095552:
                msg = await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            elif ctx.author.voice.channel.id !=  888315285629722624 or ctx.author.voice.channel.id !=  1205935289269493842:
                msg = await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()
            elif not ctx.author.voice or not ctx.author.voice.channel:
                msg = await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            elif ctx.author.voice.channel != ctx.voice_client.channel :
                msg = await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to Bot's Voice Channel.")
                raise commands.CommandError()
    @join.before_invoke
    @play.before_invoke
    async def voice_channel(self,ctx):
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id!=1102496776700833825:
            if not ctx.author.voice or not ctx.author.voice.channel:
                raise commands.CommandError()
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id !=888410427896242194 and ctx.channel.id!=1205935346899095552:
                msg = await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
            elif not ctx.author.voice or not ctx.author.voice.channel:
                msg = await ctx.respond("<:call_disconnect:918875403567910933> You are not connected to a Voice Channel.")
                raise commands.CommandError()
            elif ctx.author.voice.channel.id !=  888315285629722624 or ctx.author.voice.channel.id !=  1205935289269493842:
                msg = await ctx.respond("I can play music only in <#888315285629722624>")
                raise commands.CommandError()
    @queue.before_invoke
    @now_playing.before_invoke
    async def bruh(self,ctx):
    
        if ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540 or ctx.guild.id!=1102496776700833825:
            pass
        else:
            if ctx.channel.id != 767591735693410370 and ctx.channel.id !=888410427896242194 and ctx.channel.id!=1205935346899095552:
                msg = await ctx.respond("You can use this command only in <#767591735693410370>")
                raise commands.CommandError()
def convert2(like):
        if like>1000000000:
            like_2 = str((like//10000000)/100)+"B"
        elif like > 1000000 :
            like_2 = str((like//10000)/100)+"M"
        elif like > 1000 :
            like_2 = str((like//10)/100)+"K"
        else :
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
    else:return "%02d:%02d:%02d" % (hour,minutes, seconds)
def setup(bot):
    bot.add_cog(Music(bot))