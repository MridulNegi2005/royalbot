import requests
import json
import discord
from discord.ext import commands,tasks
import asyncio
import aiohttp
import psycopg2
import ast,time
from main import query,con
from dateutil import parser
import datetime
import cogs.giveaway as giveaway
import os
api_key = os.getenv("YOUTUBE_API_KEY")
channel_id = "UCEZqqxc-NMD7uGCod8N0gOw"
upload_id="UUEZqqxc-NMD7uGCod8N0gOw"
class sub(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.sub_count_previous=0
		self.video_id_previous=[]
		#self.getSubscriberCount.start()
		self.mem_update.start()
		#self.getVideo.start()
		self.temprole.start()
		'''sql = 'SELECT * FROM config'
		self.query=query
		self.con=con
		query.execute(sql)
		myresult = query.fetchall()
		for x in myresult:
			a = str(x)
			a = a.replace('(','')
			a = a.replace(')','')
			a = a.replace(',','')
			a = a.replace("'",'')
			self.video_id_previous.append(a)'''
	
	'''@tasks.loop(seconds=15.0)
	async def getVideo(self):
		async with aiohttp.ClientSession() as yt:
			async with yt.get(f'https://www.googleapis.com/youtube/v3/playlistItems?playlistId={upload_id}&key={api_key}&part=snippet&maxResults=5&sort=date') as r:
				
				res = await r.json()
				items = res.get('items', {})
				video_id = items[0].get('snippet').get('resourceId', {}).get('videoId')
				title = items[0].get('snippet').get('title')
				date = items[0].get('snippet').get('publishedAt')
				time = parser.parse(date)
				x = datetime.datetime.now(datetime.timezone.utc)
				delta = x - time
				if str(video_id) not in self.video_id_previous:
					if '#shorts' in title:
						return
					self.video_id_previous.append(video_id)
					sql = 'INSERT INTO config ("video_id") VALUES (%s)'
					val = (video_id,)
					query.execute(sql,val)
					con.commit()
					print(delta.total_seconds())
					if delta.total_seconds()>-1:
						chan = self.video_chan
						msg = await chan.send(f"> Hey <@&802048451318775818>, **Cosmic Shock** just uploaded a new video!\nGo check it out and dont forget to like and comment.\nhttps://www.youtube.com/watch?v={video_id}")
						await msg.add_reaction("<a:CS_CosmicOP:792007397966610492>")
						await msg.add_reaction("<a:CosmicShockOP_2:860390129608818719>")
						await msg.publish()
	@tasks.loop(seconds=1800.0)
	async def getSubscriberCount(self):
		async with aiohttp.ClientSession() as cs:
			async with cs.get(f'https://youtube.googleapis.com/youtube/v3/channels?part=snippet%2CcontentDetails%2Cstatistics&id={channel_id}&key={api_key}') as r:
				res = await r.json()
				items = res.get('items', {})
				sub_count = int(items[0].get('statistics', {}).get('subscriberCount'))

			if sub_count != self.sub_count_previous:
				chan = self.sub_chan
				await chan.edit(name=f"YT Subscribers: {int(sub_count)//1000} K",reason="Sub count Update!")
				self.sub_count_previous = sub_count'''

	@tasks.loop(seconds=600.0)
	async def mem_update(self):
		# Resolved here, not in __init__ — the cache is not filled yet at load time.
		guild = self.bot.get_guild(767591734841835540)
		chan = self.bot.get_channel(824170799178580008)
		if guild is None or chan is None:
			return
		name = f"Members: {guild.member_count}"
		if chan.name == name:
			return
		try:
			await chan.edit(name=name,reason="Scheduled Member Count Update")
		except discord.HTTPException as e:
			print(f"[sub] member count update failed: {e}")

	@mem_update.before_loop
	async def before_mem_update(self):
		await self.bot.wait_until_ready()

	# Both queries filter on time in SQL, so an idle server transfers no rows at all.
	@tasks.loop(seconds=30.0)
	async def temprole(self):
		guild = self.bot.get_guild(767591734841835540)
		if guild is None:
			return
		now = int(time.time())
		try:
			query.execute('SELECT "message" FROM gconfig WHERE "time" <= %s',(now,))
			for x in query.fetchall():
				await giveaway.end2(self.bot,x[0])
		except Exception as e:
			print(f"[sub] giveaway end failed: {e}")

		try:
			query.execute('SELECT "user","role" FROM temprole WHERE "time" <= %s',(now,))
			expired = query.fetchall()
		except Exception as e:
			print(f"[sub] temprole lookup failed: {e}")
			return

		for user_id,role_id in expired:
			member = guild.get_member(user_id)
			role = guild.get_role(role_id)
			if member is not None and role is not None:
				try:
					await member.remove_roles(role,reason="Temporary role expired")
				except discord.HTTPException as e:
					print(f"[sub] could not remove role {role_id} from {user_id}: {e}")
					continue
			query.execute('DELETE FROM temprole WHERE "user" = %s AND "role" = %s',(user_id,role_id))

	@temprole.before_loop
	async def before_temprole(self):
		await self.bot.wait_until_ready()

	@temprole.error
	async def temprole_error(self,error):
		# Without this a single exception silently kills the loop until a restart.
		print(f"[sub] temprole loop crashed: {error!r}")
		self.temprole.restart()
def setup(bot):
	bot.add_cog(sub(bot))