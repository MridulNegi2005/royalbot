import discord
from discord.ext import commands
import asyncio
import time
import psycopg2
import datetime
import random
	
class game(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command()
	async def rps(self,ctx,ch) :
		if ch == 'r' or 'rock':
			choice = 'r'
		elif ch == 'p' or 'paper':
			choice = 'p'
		elif ch == 's' or 'scissor':
			choice = 's'
		else : 
			await ctx.send("```*rps <choice> ```choice = r/p/s")
			return
		opt = ['r','p','s']
		b_choice = random.choice(opt)
		
		if choice == 'r' and b_choice == 'r':pass
			
	
def setup(bot):
	bot.add_cog(game(bot))