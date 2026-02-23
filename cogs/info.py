from datetime import datetime
from typing import Optional
import discord
import speedtest
from discord import Embed, Member
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
class Info(Cog):
	def __init__(self, bot):
		self.bot = bot

	@slash_command(description="Test the bot's internet speed!")
	async def speedtest(self,ctx):
		msg = await ctx.respond("Calculating <a:loading:886509142934683678>")
		s = speedtest.Speedtest()
		download = (s.download()//10000)/100
		upload = (s.upload()//10000)/100
		await ctx.send(f"Downloading Speed: {download} Mbps\nUploading Speed: {upload} Mbps")
		
	@slash_command(description="Check information regarding a user")
	async def user_info(self, ctx, target:Option(discord.Member,"Member whose info you wanted to check",required=False)):
		if target==None:target=ctx.author

		embed = Embed(title=f"{str(target)}  [{target.id}]",
					  colour=target.colour,
					  timestamp=datetime.utcnow())

		embed.set_thumbnail(url=target.avatar.url)
		fields = [("Name", str(target), True),
				  ("ID", target.id, True),
				  ("Avatar :",f"[Click here]({target.avatar.url})",True),
				  ("Bot?", target.bot, True),
				  ("Top role", target.top_role.mention, True),
				  ("Status", str(target.status), True),
				  ("Activity", f"{target.activity.name if target.activity else ''}", True),
				  ("Created at", target.created_at.strftime("%d/%m/%Y %H:%M:%S"), True),
				  ("Joined at", target.joined_at.strftime("%d/%m/%Y %H:%M:%S"), True),
				  ("Boosted", bool(target.premium_since), True)]

		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)

		await ctx.respond(embed=embed)

	@slash_command(description="Check the server's info")
	async def server_info(self, ctx):
		embed = Embed(title=f'<:verified:884020441373605958> "{ctx.guild.name}" Server information',
					  timestamp=datetime.utcnow())

		embed.set_thumbnail(url=ctx.guild.icon.url)

		statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
					len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]
		created_at = ctx.guild.created_at.strftime('%d/%m/%Y %H:%M:%S')
		joined_at = ctx.author.joined_at.strftime("%d/%m/%Y %H:%M:%S")
		channels =0
		text=0
		voice=0
		announcement=0
		for x in ctx.guild.channels:
			channels = channels+1
		
		for x in ctx.guild.text_channels:
			if x.is_news():
				announcement += 1
			else:
				text += 1
		for x in ctx.guild.voice_channels:
			voice = voice+1
		fields=[("<:notepad:884023914701922334> Description : ",ctx.guild.description,False),
				("<:hyphen:884022484595253248> Miscellaneous : ",f"Server name: **{ctx.guild.name}**\n Server ID: **{ctx.guild.id}**\n Server Icon: [Click Here]({ctx.guild.icon.url} 'Server Logo') \n Server Banner: [Click Here]({ctx.guild.banner.url} 'Server Banner')  \n Server Owner: **{ctx.guild.owner} (`{ctx.guild.owner_id}`)** \n Server Boosts: **{ctx.guild.premium_subscription_count} Boosts** \n Verification Level:**{ctx.guild.verification_level}** ",False),
				("<:remind:884031965320331275> Dates : ",f"Created At: **{created_at}** \n Joined At: **{joined_at}**",False),
				("<:folder:884021905043095583> Channels : ",f"Total Channels: **{channels}** \n <:channel:884022113013481502> **{text}** <:voice:884022216512110612> **{voice}** <:announcement:884022180927668234> **{announcement}**",True),
				("<:member:884023021373882418> Members : ",f"Total Members: **{ctx.guild.member_count}** \n <:online:884034069967556618>**{statuses[0]}** <:idle:884034313119748106> **{statuses[1]}** <:dnd:884034275777847346> **{statuses[2]}** <:offline:884034380048257074> **{statuses[3]}**",True)]

		for name, value, inline in fields:
			embed.add_field(name=name, value=value, inline=inline)

		await ctx.respond(embed=embed)



def setup(bot):
	bot.add_cog(Info(bot))