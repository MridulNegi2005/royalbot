import psycopg2
import json
import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
from discord.ext.commands.cog import Cog
con = psycopg2.connect('postgres://balxuonbzytruy:2be081d80c21d0869d500f997e19ff385ad5278d020402608fc23ac1f8d71bc6@ec2-52-73-184-24.compute-1.amazonaws.com:5432/des0u9rjq76pq', sslmode='require')
query = con.cursor()
class Import(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def level_init(self,ctx):
        await ctx.send("Started!")
        f = open('output.json')
        data = json.load(f)
        for x in data:
            print(x)
            sql = 'INSERT INTO "levelling" ("user","xp","theme","overlay") values (%s,%s,%s,%s)'
            val=(x["user_id"],x["points"],1,"True")
            query.execute(sql,val)
            con.commit()
        await ctx.send("Completed!!")
    @Cog.listener("on_message")
    async def on_message(self,message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.guild.id != 767591734841835540:
            return
        if message.content=="!rank" or message.content=="!level":
            await message.channel.send("Use /level command")
        if message.content=="!leaderboard" or message.content=="!lb":
            await message.channel.send("Use /leaderboard command")
def setup(bot):
    bot.add_cog(Import(bot))