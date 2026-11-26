import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
import asyncio
import time
import psycopg2
from discord.ext.commands.cog import Cog
from datetime import datetime
from main import con,query
import numpy as np
afk2={}
temp=[]
class role(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sponsor=[860546626065924117,860546754944434186,860549321987981353,860549322546085950,860546759587659776,860546637541277716,860551736917360710,860549325665730580,860549323658100762,860549324244647936,860549324794101810,783322708736868362]
        self.casino=[783038419147161650,783308376339513345,783314459019313152,783317796317691946,783318887939833886,897401951816417310,897402749321379852]
    @Cog.listener("on_member_update")
    async def on_member_update(self,before,after):
        if before.roles != after.roles:
            yt_member = before.guild.get_role(896352016144691230)
            booster = before.guild.get_role(780999224153473054)
            lost_perk = ((yt_member in before.roles and yt_member not in after.roles)
                         or (booster in before.roles and booster not in after.roles))
            if lost_perk:
                # One request for the whole set. The old loop sent 12 separate
                # role edits and each one waited on its own rate limit.
                sponsor_roles = [r for r in (before.guild.get_role(x) for x in self.sponsor)
                                 if r is not None and r in after.roles]
                if sponsor_roles:
                    await after.remove_roles(*sponsor_roles,reason="Perk role removed")

            li1=after.roles
            li2=before.roles
            if len(li1)>len(li2):
                role = [i for i in li1 + li2 if i not in li1 or i not in li2]
                role=role[0]
                if role.id in self.casino:
                    sql = 'INSERT INTO temprole ("user","role","time") VALUES ( %s,%s,%s)'
                    val = (before.id,role.id,int(time.time()+5184000))
                    query.execute(sql, val)
    @commands.command()
    async def casino_init(self,ctx):
        await ctx.send("Process started")
        casino_role = ctx.guild.get_role(783180543155109919)
        for x in ctx.guild.members:
            print(x)
            if casino_role not in x.roles:
                continue
            for role in x.roles:
                if role.id in self.casino:
                    sql = 'INSERT INTO temprole ("user","role","time") VALUES ( %s,%s,%s)'
                    val = (x.id,role.id,int(time.time()+5184000))
                    query.execute(sql, val)
                    con.commit()
        await ctx.send("Process completed")
def setup(bot):
    bot.add_cog(role(bot))