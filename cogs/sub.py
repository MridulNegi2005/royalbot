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
import psycopg2
def get_connection():
    try:
        return psycopg2.connect(
            database="postgres",
            user="postgres",
            password="cosmicbot",
            host="35.223.191.80",
            port=5432,
        )
    except:
        return False
con2 = get_connection()
query2 = con.cursor()
api_key = "AIzaSyCzeRWqsVGVUzBGhC-m030YGF-EA0G91QI"
channel_id = "UCEZqqxc-NMD7uGCod8N0gOw"
upload_id="UUEZqqxc-NMD7uGCod8N0gOw"
class sub(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.sub_count_previous=0
		self.video_id_previous=[]
		self.video_chan = self.bot.get_channel(767591735295213586)
		self.sub_chan = self.bot.get_channel(781207856295706635)
		self.member_chan =self.bot.get_channel(824170799178580008)
		self.guild = self.bot.get_guild(767591734841835540)
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
		guild =self.guild
		chan = self.member_chan
		count = guild.member_count
		name = f"Members: {count}"
		if chan.name == name:
			return
		await chan.edit(name=name,reason="Scheduled Member Count Update")

	@tasks.loop(seconds=5.0)
	async def temprole(self):
		guild = self.guild
		try:
			sql='SELECT * FROM gconfig'
			query.execute(sql)
			myresult = query.fetchall()
			for x in myresult:
				time2 = x[0]
				if int(time2)<=int(time.time()):
					await giveaway.end2(self,x[1])
		except:
			pass
		sql='SELECT * FROM temprole'
		query.execute(sql)
		myresult = query.fetchall()
		for x in myresult:
			a = str(x)
			y = ast.literal_eval(a)
			if y[2] <= int(time.time()):
				user = guild.get_member(y[0])
				role = guild.get_role(y[1])
				await user.remove_roles(role)
				sql = 'DELETE FROM temprole WHERE "user" = %s AND "role" = %s'
				val=(y[0],y[1])
				query.execute(sql,val)
				con.commit()
def setup(bot):
	bot.add_cog(sub(bot))