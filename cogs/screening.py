import discord
from discord.ext import commands
from cogs.levelling import query,con
class screening(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.event
    async def on_member_update(self,before,after):
        if before.pending == True:
            if after.pending == False:
                guild = self.bot.get_guild(767591734841835540)
                role = guild.get_role(804028250997260308)
                await after.add_roles(role)
def get_temp():
    query
def setup(bot):
  bot.add_cog(screening(bot))