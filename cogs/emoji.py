import discord
import asyncio
from discord.ext import commands
import typing

class emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

def setup(bot):
  bot.add_cog(emoji(bot))