import schedule
import discord
from discord.ext import commands
import typing
import asyncio
import time
import psycopg2
import datetime
title = "Cosmic Bot"
#-------------------------------------------------------------------------

con = psycopg2.connect('postgres://balxuonbzytruy:2be081d80c21d0869d500f997e19ff385ad5278d020402608fc23ac1f8d71bc6@ec2-52-73-184-24.compute-1.amazonaws.com:5432/des0u9rjq76pq', sslmode='require')
query = con.cursor()
print(con)

#-------------------------------------------------------------------------


class banappeal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



def setup(bot):
    bot.add_cog(banappeal(bot))
    