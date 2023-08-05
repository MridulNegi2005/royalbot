import discord
from discord.ext import commands
import wikipediaapi

wiki = wikipediaapi.Wikipedia('en')

class Wikipedia(commands.Cog):
    def __init__(self,bot):
        self.bot = bot

    @commands.command(aliases=['wiki'])
    async def wikipedia(self,ctx,*,search):
        page = wiki.page(search)
        if page.exists() == True:
            result = discord.Embed(title=page.title,description="**"+page.summary[0:1000]+" .... **",color=0xeb8c34,url=page.fullurl)
            await ctx.send(embed=result)
        else:
            await ctx.send("No information available on Wikipedia")

def setup(bot):
  bot.add_cog(Wikipedia(bot))