from ctypes import Union
import discord
import asyncio
from discord.ext import commands
import typing
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
class fake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @slash_command(guild_ids=[767591734841835540],description="Send message as a particular user!")
    async def fake(self,ctx,user:Option(discord.Member,"User you want to disguise."),message:Option(str,"Message to send!"),channel:Option(discord.TextChannel,"Channel to send message to",required=False,default=None)):
        chan=channel
        member=user
        if chan == None:
            chan = ctx.channel
        webhook = await chan.webhooks()
        for x in webhook:
            if x.user == self.bot.get_user(823112553051193357):
                await x.send(str(message), username=member.display_name, avatar_url=member.avatar.url)
                return
        webhook = await chan.create_webhook(name="Cosmic Bot")
        await webhook.send(str(message), username=member.display_name, avatar_url=member.avatar.url)
        await ctx.respond("Message sent!",ephemeral=True)
                               
			

def setup(bot):
  bot.add_cog(fake(bot))