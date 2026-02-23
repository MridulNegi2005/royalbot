import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
import asyncio
import time
import psycopg2
from discord.ext.commands.cog import Cog
from datetime import datetime
afk2={}
temp=[]
class afk(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @slash_command(default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def afk(self,ctx,message:Option(str,"AFK Message",required=False,default="")):
        message=message+f" *-*<t:{int(datetime.now().timestamp())}:R>"
        await ctx.respond("AFK set successfully! Goodbye!")
        afk2[ctx.author.id]=message
        temp.append(ctx.author.id)
        await asyncio.sleep(30)
        temp.remove(ctx.author.id)

    @Cog.listener("on_message")
    async def on_message(self,message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.author.id in afk2.keys():
            if message.author.id in temp:
                pass
            else:
                await message.channel.send(f"Welcome back <@{message.author.id}>! Your afk status has been removed!",delete_after=10)
                afk2.pop(message.author.id)
        for x in message.mentions:
            if int(x.id) == int(message.author.id):
                continue
            if x.id in afk2.keys():
                await message.channel.send(f"**{x.display_name} is AFK** : {afk2[x.id]}",allowed_mentions=discord.AllowedMentions().none())
def setup(bot):
    bot.add_cog(afk(bot)) 