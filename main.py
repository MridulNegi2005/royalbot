from re import M
import discord
from discord.ext import commands
from discord.commands import permissions,Option
import os
import json
import asyncio
import requests
import random
import time
import datetime
import psycopg2
import sqlite3
import socket
import heroku3
import platform
from dotenv import load_dotenv
load_dotenv()

if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

#KEY=os.getenv('HEROKU_API_KEY')
#cloud = heroku3.from_key(KEY)
#app = cloud.apps()['royal-disc-bot']
#web = app.process_formation()['web']
temp_role='hello'
whitelist=[767591735295213580]
def get_connection():
    try:
        return psycopg2.connect(
            database=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
			sslmode="require"
        )
    except:
        return False
con = get_connection()
query = con.cursor()
conn = sqlite3.connect('help.db')
cur = conn.cursor()
child = True
sent_users = []
playing=[]
intents = discord.Intents().all()
intents.members = True
intents.message_content=True
intents.presences = True
prefix = '*'
bot = commands.Bot(command_prefix=prefix,intents=intents,activity=discord.Activity(type=discord.ActivityType.listening, name=f"COSMIC'S UNIVERSE | /help"),status=discord.Status.dnd)
bot.remove_command("help")
@bot.check
def check_commands(ctx):
	if isinstance(ctx, discord.ApplicationContext):
		return True
	elif ctx.command.name == "akinator":
		return True
	elif ctx.command.name == "lfg":
		return ctx.channel.id == 767591735559716910 or ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540
	elif ctx.command.cog_name == "Music2":
		return True
	else : 
		return ctx.channel.id in whitelist or ctx.guild.get_role(767591734850879495) in ctx.author.roles or ctx.guild.get_role(816681109001207808) in ctx.author.roles or ctx.guild.id != 767591734841835540

t = "Cosmic Bot"

def get_quote():
	response = requests.get("https://zenquotes.io/api/random")
	json_data = json.loads(response.text)
	quote = json_data[0]['q'] + " -" + json_data[0]['a']
	return (quote)
 
class invite2(discord.ui.View):
	def __init__(self):
		super().__init__()
	@discord.ui.button(label="⠀⠀⠀⠀⠀Invite⠀⠀⠀⠀⠀", style=discord.ButtonStyle.green)
	async def callback(self,button,interaction):
		await interaction.response.send_message("https://tenor.com/view/rickroll-roll-rick-never-gonna-give-you-up-never-gonna-gif-22954713",ephemeral=True)
	async def on_timeout(self,interaction):
		await interaction.response.send_message("WTF")

class Dropdown(discord.ui.Select):
	def __init__(self,help):
		self.help=help
		options = [
			discord.SelectOption(
                label="Main Menu", description="View main page", emoji="<:warn:918879085789331456>"
            ),
            discord.SelectOption(
                label="General", description="General common commands", emoji="<:settings:918878102900310016>"
            ),
            discord.SelectOption(
                label="Server Config", description="Commands related to server config.", emoji="<:configuration:918878174190907464>"
            ),
			discord.SelectOption(
                label="Moderation", description="Help to moderatate the server. Mods must see it!", emoji="<:moderation:918877676478021642>"
            ),
			discord.SelectOption(
                label="Music", description="Listen to the music and enjoy! :)", emoji="<:music:918875299326877696>"
            ),
        ]
		super().__init__(
            placeholder="Choose module",
            min_values=1,
            max_values=1,
            options=options,
        )
	async def callback(self, interaction: discord.Interaction):
		query = self.values[0]
		view = Help(self.help)
		if query == "Main Menu":
			await interaction.response.send_message(embed=self.help[0],ephemeral=True)
		elif query.lower() == 'general':
			await interaction.response.send_message(embed=self.help[1],ephemeral=True)
		elif query.lower() == 'server config':
			await interaction.response.send_message(embed=self.help[2],ephemeral=True)
		elif query.lower() == 'moderation' or query.lower()=="mod":
			await interaction.response.send_message(embed=self.help[3],ephemeral=True)
		elif query.lower() == 'music':
			await interaction.response.send_message(embed=self.help[4],ephemeral=True)
class Help(discord.ui.View):
    def __init__(self,help):
        super().__init__()
        self.add_item(Dropdown(help))
@bot.event
async def on_ready():
	bot.load_extension("cogs.sub")
	print('We have logged in as {0.user}'.format(bot))
import sys
def try_load_extension(name):
	try:
		bot.load_extension(name)
		print(f'[main.py] Loaded {name} successfully.', file=sys.stderr, flush=True)
	except Exception as e:
		print(f'[main.py] Failed to load {name}: {e}', file=sys.stderr, flush=True)
		import traceback
		traceback.print_exc()

try_load_extension("cogs.info")
try_load_extension("cogs.codeshock")
#try_load_extension("cogs.wikipedia")
try_load_extension("cogs.weather")
try_load_extension("cogs.eval")
try_load_extension("cogs.fake")
try_load_extension("cogs.highlight")
try_load_extension("cogs.music")
try_load_extension("cogs.perm")
try_load_extension("cogs.welcome")
try_load_extension("cogs.buttonrole")
try_load_extension("cogs.levelling")
#try_load_extension("cogs.christmas")
try_load_extension("cogs.moderation")
try_load_extension("cogs.afk")
try_load_extension("cogs.casino")
try_load_extension("cogs.role")
try_load_extension("cogs.gsearch")
try_load_extension("cogs.starboard")
try_load_extension("cogs.import")
try_load_extension("cogs.giveaway")
try_load_extension("cogs.vc_levelling")
print('All cogs loaded!')
@bot.slash_command(guild_ids=[767591734841835540],description="Check out the response time!")
async def ping(ctx):
    latency = bot.latency
    pong = discord.Embed(title="Cosmic Bot",description="Bot latency is : " +str((round(latency, 5))*1000) + " milliseconds!",color=discord.Color.blue())
    await ctx.respond(embed=pong)
@bot.slash_command(guild_ids=[767591734841835540],description="Love this bot? Invite right now!!")
async def invite(ctx):
    await ctx.respond("Thanks for using this bot! You can invite it from link below!",view=invite2())
    
def get_all_cog_names():
	"""Get all cog file names from the cogs/ directory."""
	cog_names = []
	cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")
	for f in os.listdir(cogs_dir):
		if f.endswith(".py") and not f.startswith("_"):
			cog_names.append(f[:-3])  # strip .py
	cog_names.sort()
	return cog_names

def is_cog_loaded(cog_name):
	"""Check if a cog is currently loaded."""
	return f"cogs.{cog_name}" in bot.extensions

class CogActionView(discord.ui.View):
	"""Buttons to Load / Unload / Reload a selected cog."""
	def __init__(self, cog_name):
		super().__init__(timeout=60)
		self.cog_name = cog_name

	@discord.ui.button(label="Load", style=discord.ButtonStyle.green, emoji="📥")
	async def load_button(self, button, interaction):
		ext = f"cogs.{self.cog_name}"
		if ext in bot.extensions:
			await interaction.response.send_message(f"⚠️ `{self.cog_name}` is already loaded.", ephemeral=True)
			return
		try:
			bot.load_extension(ext)
			await interaction.response.send_message(f"✅ Loaded `{self.cog_name}` successfully!", ephemeral=True)
		except Exception as e:
			await interaction.response.send_message(f"❌ Failed to load `{self.cog_name}`:\n```{e}```", ephemeral=True)

	@discord.ui.button(label="Unload", style=discord.ButtonStyle.red, emoji="📤")
	async def unload_button(self, button, interaction):
		ext = f"cogs.{self.cog_name}"
		if ext not in bot.extensions:
			await interaction.response.send_message(f"⚠️ `{self.cog_name}` is not loaded.", ephemeral=True)
			return
		try:
			bot.unload_extension(ext)
			await interaction.response.send_message(f"✅ Unloaded `{self.cog_name}` successfully!", ephemeral=True)
		except Exception as e:
			await interaction.response.send_message(f"❌ Failed to unload `{self.cog_name}`:\n```{e}```", ephemeral=True)

	@discord.ui.button(label="Reload", style=discord.ButtonStyle.blurple, emoji="🔄")
	async def reload_button(self, button, interaction):
		ext = f"cogs.{self.cog_name}"
		try:
			if ext in bot.extensions:
				bot.unload_extension(ext)
			bot.load_extension(ext)
			await interaction.response.send_message(f"✅ Reloaded `{self.cog_name}` successfully!", ephemeral=True)
		except Exception as e:
			await interaction.response.send_message(f"❌ Failed to reload `{self.cog_name}`:\n```{e}```", ephemeral=True)

class CogSelect(discord.ui.Select):
	"""Dropdown that lists all available cogs with their load status."""
	def __init__(self):
		cog_names = get_all_cog_names()
		options = []
		for name in cog_names[:25]:  # Discord limit: 25 options
			status = "✅ Loaded" if is_cog_loaded(name) else "❌ Not loaded"
			options.append(discord.SelectOption(label=name, description=status, emoji="🔧"))
		super().__init__(placeholder="Select a cog to manage...", min_values=1, max_values=1, options=options)

	async def callback(self, interaction: discord.Interaction):
		selected_cog = self.values[0]
		status = "✅ **Loaded**" if is_cog_loaded(selected_cog) else "❌ **Not loaded**"
		embed = discord.Embed(
			title=f"🔧 Manage Cog: `{selected_cog}`",
			description=f"Current status: {status}\n\nChoose an action below:",
			color=discord.Color.blurple()
		)
		await interaction.response.send_message(embed=embed, view=CogActionView(selected_cog), ephemeral=True)

class CogManageView(discord.ui.View):
	"""View containing the cog selection dropdown."""
	def __init__(self):
		super().__init__(timeout=120)
		self.add_item(CogSelect())

@bot.slash_command(guild_ids=[767591734841835540], description="Manage bot extensions (load/unload/reload)", default_permission=False)
@discord.default_permissions(administrator=True)
async def cogs(ctx):
	cog_names = get_all_cog_names()
	loaded = [n for n in cog_names if is_cog_loaded(n)]
	embed = discord.Embed(
		title="⚙️ Cog Manager",
		description=f"**{len(loaded)}** / **{len(cog_names)}** cogs loaded.\n\nSelect a cog from the dropdown below to manage it.",
		color=discord.Color.blurple()
	)
	await ctx.respond(embed=embed, view=CogManageView(), ephemeral=True)

@bot.slash_command(guild_ids=[767591734841835540],description="Restart Bot",default_permission=False)
@discord.default_permissions(administrator=True,)
async def restart(ctx):
    await ctx.respond("Restarting bot")
    #app.restart()
'''	
@bot.slash_command(guild_ids=[767591734841835540])
async def enlarge(ctx, emoji:discord.PartialEmoji):
	try:
		if not emoji:
			await ctx.respond("You need to provide an emoji!")
		else:
			await ctx.respond(emoji.url)
	except:
		await ctx.respond(f"Couldn't convert {emoji} to emoji")
'''
@bot.slash_command(description="Shows yours or another user's avatar!")
async def avatar(ctx,user:Option(discord.User,"User whose avatar you want to enlarge",required=False,default=None),guild_avatar:Option(str,"Choose if to display guild specific avatar (only works in servers)",choices=["True","False"],default=False,required=False)):
	if user==None:user=ctx.author
	if guild_avatar =="True" and ctx.guild:
		try:
			# Try to get the member object for guild avatar
			member = ctx.guild.get_member(user.id)
			if member and member.guild_avatar:
				avatar = member.guild_avatar.url
			else:
				avatar = user.display_avatar.url
		except:
			avatar = user.display_avatar.url
	else:
		avatar = user.display_avatar.url
	await ctx.respond(avatar)
@bot.command()
@commands.has_role('LFG')
@commands.cooldown(1, 900, commands.BucketType.guild)
async def lfg(ctx,*, msg="Somebody wants to play?"):
	if ctx.channel.id == 767591735559716910 :
		user = ctx.author.name
		await ctx.send(f"<@&877427025508450344> **{user}** : *{msg}*")
	else : 
		msg = await ctx.send("You can use this command only in <#767591735559716910>")


@bot.slash_command(description="Get inspired!")
async def quote(ctx):
	msg = get_quote()
	embed = discord.Embed(title="QUOTE", description=msg, color=0x6a23a1)
	await ctx.respond(embed=embed)


@bot.slash_command(guild_ids=[767591734841835540],description="Get list of roles",default_permission=False)
@discord.default_permissions(administrator=True,)
async def roles(ctx):
	desc = ""
	guild = ctx.guild
	for role in guild.roles:
		desc = desc + f"{role.mention}\n"

	chan = discord.Embed(title="All roles", description=desc,color=0xbbff87)
	await ctx.send(embed=chan)


@bot.slash_command(guild_ids=[767591734841835540],description="Get list of all channels",default_permission=False)
@discord.default_permissions(administrator=True,)
async def channels(ctx):
	guild = ctx.guild
	counter = 0
	chan = discord.Embed(title="All Channels",color=0xbbff87)
	for x in guild.text_channels:
		counter = counter +1
		if counter == 26 or counter == 51 or counter == 76:
			await ctx.send(embed=chan)
			chan = discord.Embed(title="\u200b",color=0xbbff87)
		chan.add_field(name=x, value="\u200b", inline=False)
	await ctx.send(embed=chan)

@bot.slash_command(description="Get help related this bot.")
async def help(ctx,query:Option(str,"Help regarding particular module/command",required=False,default=None)):
	dev = bot.get_user(745884061066592266) or await bot.fetch_user(745884061066592266)

	
	help1 = discord.Embed(
	    title=
	    "<:help:928002911823343616> Cosmic Bot Help <:help:928002911823343616>",
	    description="\u200b",
	    color=0x5d27a1)
	help1.set_footer(text=f"Developed by {dev.name}#{dev.discriminator}")
	help1.add_field(name="<:warn:918879085789331456> Help",
	                value="View This Page",
	                inline=False)
	help1.add_field(name="<:settings:918878102900310016> General",
	                value="General common codes",
	                inline=False)
	help1.add_field(name="<:configuration:918878174190907464> Server config",
	                value="Commands related to server config.",
	                inline=False)
	help1.add_field(name="<:moderation:918877676478021642> Moderation",
	                value="Help to moderatate the server. Mods must see it!",
	                inline=False)
	help1.add_field(name="<:music:918875299326877696> Music",
	                value="Listen to the music and enjoy! :)",
	                inline=False)
	help2 = discord.Embed(
	    title=
	    "<:settings:918878102900310016> General Commands <:settings:918878102900310016>",
	    description="\u200b",
	    color=0x5d27a1)
	help2.set_footer(text=f"Developed by {dev.name}#{dev.discriminator}")
	help3 = discord.Embed(
	    title=
	    "<:configuration:918878174190907464> Server Config. <:configuration:918878174190907464>",
	    description="\u200b",
	    color=0x5d27a1)
	help3.set_footer(text=f"Developed by {dev.name}#{dev.discriminator}")
	help4 = discord.Embed(
	    title=
	    "<:moderation:918877676478021642>  Moderation Commands <:moderation:918877676478021642>",
	    description="\u200b",
	    color=0x5d27a1)
	help4.set_footer(text=f"Developed by {dev.name}#{dev.discriminator}")
	help5 = discord.Embed(
	    title=
	    "<:music:918875299326877696> Music <:music:918875299326877696>",
	    description="\u200b",
	    color=0x5d27a1)
	help5.set_footer(text=f"Developed by {dev.name}#{dev.discriminator}")
	
	cur.execute("SELECT * FROM command")
	rows = cur.fetchall()
	for row in rows:
		if row[0].lower()=='general':
			help2.add_field(name=row[1],value=row[2])
		elif row[0].lower()=='server config':
			help3.add_field(name=row[1],value=row[2])
		elif row[0].lower()=='moderation':
			help4.add_field(name=row[1],value=row[2])
		elif row[0].lower()=='music':
			help5.add_field(name=row[1],value=row[2])
	help = (help1,help2,help3,help4,help5)
	view = Help(help)
	if query==None or query.lower() in ('general','server','moderation','mod','music'):
		if query ==None:
			message = await ctx.respond(embed=help1,view=view)
		elif query.lower() == 'general':
			message = await ctx.respond(embed=help2,view=view)
		elif query.lower() == 'server':
			message = await ctx.respond(embed=help3,view=view)
		elif query.lower() == 'moderation' or query.lower()=="mod":
			message = await ctx.respond(embed=help4,view=view)
		elif query.lower() == 'music':
			message = await ctx.respond(embed=help5,view=view)
		
	else:
		cur.execute(f"SELECT * FROM command WHERE name like '{query}'")
		hint = cur.fetchone()
		help = discord.Embed(title=f"{prefix}{hint[1]}",description="*Values in () are optional and Values in [] are required*",color=0xe02626)
		help.add_field(name="Description:",value=hint[2])
		help.add_field(name="Syntax:",value=f"`{prefix}{hint[3]}`")
		help.add_field(name="Example:",value=hint[4].format(prefix))
		await ctx.respond(embed=help)


#-----------------AKINATOR------------------------
'''
@bot.command(name="akinator", aliases=["aki"])
async def akinator_game(ctx):
	guild = bot.get_guild(884886495301885952)
	thonk = guild.emojis
	if ctx.channel.id != 843860718268448778 :
		message = await ctx.reply("You can use this command only in <#843860718268448778>")
		return
	elif ctx.author.id in playing:
		message = await ctx.reply("Complete your ongoing game! Or \n React with <:BS_Cross:881610413874225292> to quit")
		await message.add_reaction("<:BS_Cross:881610413874225292>")
		def check(reaction, user):
			return user == ctx.author and str(reaction.emoji) in [
			"<:BS_Cross:881610413874225292>"
			]
		try:
			reaction, user = await bot.wait_for('reaction_add', check=check, timeout=60)
			if str(reaction.emoji) == "<:BS_Cross:881610413874225292>":
				playing.remove(ctx.author.id)
				await ctx.send("Game Ended")
				return
		except : 
			await message.delete()
		return
	else:
		
		right = 0
		playing.append(ctx.author.id)
		option = discord.Embed(title="Akinator",color=0xFFFF05)
		option.add_field(name="Choose Game mode",value="👫 Character\n 🐼 Animal\n<:BS_Cross:881610413874225292> Quit")
		message = await ctx.send(embed=option)
		# getting the message object for editing and reacting

		await message.add_reaction(
			"👫")
		await message.add_reaction("🐼")
		await message.add_reaction("<:BS_Cross:881610413874225292>")

		def check(reaction, user):
			return user == ctx.author and str(reaction.emoji) in [
				"👫",
				"🐼",
				"⚽",
				"<:BS_Cross:881610413874225292>"
			]
			# This makes sure nobody except the command sender can interact with the "menu"

		try:
			reaction, user = await bot.wait_for("reaction_add",
													timeout=60,
													check=check)
				# waiting for a reaction to be added - times out after 60 seconds
				
			if str(reaction.emoji) == "👫":
				lang = 'en'
			elif str(reaction.emoji) == "🐼":
				lang='en_animals'
			elif str(reaction.emoji) == "⚽":
				lang='en_objects'
			elif str(reaction.emoji) == "<:BS_Cross:881610413874225292>":
				await message.delete()
				playing.remove(ctx.author.id)
				return
			else:
				await message.remove_reaction(reaction, user)
					# removes reactions if the user tries to go forward on the last page or
					# backwards on the first page
			
			aki = Akinator()
			first = await ctx.send("Starting Akinator Game! Hold On!")
			q = await aki.start_game(language=lang,child_mode=True)
			game_embed = discord.Embed(title=f"Question : {aki.step + 1}", color=0xFFFFE0)
			game_embed.add_field(name=q,value="[Yes(**y**) \ No(**n**)\ I dont know(**idk**)] \n [Probably(**p**)\ Probably Not(**pn**)\ Back(**b**)\ Quit(**q**)]")
			game_embed.set_footer(text=f"You have 45 sec to answer!")

			
			def check(msg):   #a check function which takes the user's response
				return msg
			def option_check(reaction, user):   #a check function which takes the user's response
				return user==ctx.author and str(reaction.emoji) in ['<:BS_Tick:881610301152305202>', '<:BS_Cross:881610413874225292>']
			n=80
			while aki.step<79:
				while True:    #Keeps running code until it guessed right. Or until its last question!
					if aki.step == 0:
						try:
							await first.delete()
							game_message = await ctx.send(embed=game_embed)
						except:
							pass
					while True :
						msg = await bot.wait_for('message',check=check,timeout=45)#Waits for the user to answer the question within 45 sec
						if msg.channel.id != 843860718268448778:
							return
						if msg.author == ctx.author:
							if msg.content.lower() in ['y','n','p','pn','idk','b','q','yes','no','i','probably']:
								ans = msg.content.lower()
								break
						
					if msg.content.lower() == 'q':      
						playing.remove(ctx.author.id)
						right = 1 #Just a variable to know wether loop has to be breaked.
						await aki.close()
						return await msg.reply("Game ended.")
					async with ctx.channel.typing():
						if msg.content.lower() == 'b' :   #to go back to previous question
							try:
								q = await aki.back()
							except:   #excepting trying-to-go-beyond-first-question error
								pass 
							#editing embed for next question
							game_embed = discord.Embed(title=f"Question : {aki.step +1}",color=0xFFFFE0)
							game_embed.add_field(name=q,value="[Yes(**y**) \ No(**n**)\ I dont know(**idk**)] \n [Probably(**p**)\ Probably Not(**pn**)\ Back(**b**)\ Quit(**q**)]")
							game_embed.set_footer(text=f"You have 45 sec to answer!")
							game_message = await msg.reply(embed=game_embed)
							continue
						else:
							
							if aki.progression >= n :#Checks the progression before asking question
								await ctx.send(random.choice(thonk))
								await aki.win()
								result_embed = discord.Embed(title="Is this your character?", colour=discord.Color.blue())
								result_embed.add_field(name=f"**{aki.first_guess['name']}**", value=f"{aki.first_guess['description']}\nRanking as **#{aki.first_guess['ranking']}**", inline=False)
								result_embed.add_field(name="\u200b",value="\u200b")
								result_embed.add_field(name="Am I right?",value="Add the reaction accordingly.")
								result_embed.set_image(url=aki.first_guess['absolute_picture_path'])
								result_message = await ctx.send(embed=result_embed)
								await result_message.add_reaction('<:BS_Tick:881610301152305202>')
								await result_message.add_reaction("<:BS_Cross:881610413874225292>")
								option, user = await bot.wait_for('reaction_add', check=option_check, timeout=45)
								if str(option.emoji) ==  '<:BS_Tick:881610301152305202>' :
									playing.remove(ctx.author.id)
									final_embed = discord.Embed(title="Akinator",description="It was nice playing with you! Hope to meet you again!", color=discord.Color.green())
									final_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843860718268448778/884907894603149342/PicsArt_09-03-09.20.28.png")
									await ctx.send(embed=final_embed)
									guess = 1 #Just a variable to know wether loop has to be breaked.
									await aki.close()
									break
								elif str(option.emoji) == '<:BS_Cross:881610413874225292>':
									guess = 0
									n = n+7
									if aki.step>=79:
										right =0
										break
									q = await aki.answer(ans)
									#editing embed for next question
									game_embed = discord.Embed(title=f"Question : {aki.step +1}", color=0xFFFFE0)
									game_embed.add_field(name=q,value="[Yes(**y**) \ No(**n**)\ I dont know(**idk**)] \n [Probably(**p**)\ Probably Not(**pn**)\ Back(**b**)\ Quit(**q**)]")
									game_embed.set_footer(text=f"You have 45 sec to answer!")
									game_message = await msg.reply(embed=game_embed)
									continue
							else:
								if aki.step>=79:
									right =0
									break
								q = await aki.answer(ans)
										#editing embed for next question
								game_embed = discord.Embed(title=f"Question : {aki.step +1}", color=0xFFFFE0)
								game_embed.add_field(name=q,value="[Yes(**y**) \ No(**n**)\ I dont know(**idk**)] \n [Probably(**p**)\ Probably Not(**pn**)\ Back(**b**)\ Quit(**q**)]")
								game_embed.set_footer(text=f"You have 45 sec to answer!")
								game_message = await msg.reply(embed=game_embed)
								continue
				if guess == 1: # Guess right! So loops break
					right = 1 # Just a avriable to know whether thats last question
					break
				else:
					right = 0 # Guessed wrong but last question
					break
			if right == 0: # GUessed wrong but will make last guess As its last question
				await ctx.send(random.choice(thonk))
				await aki.win()
				result_embed = discord.Embed(title="Akinator", colour=discord.Color.blue())
				result_embed.add_field(name=f"**{aki.first_guess['name']}**", value=f"{aki.first_guess['description']}\nRanking as **#{aki.first_guess['ranking']}**", inline=False)
				result_embed.add_field(name="\u200b",value="\u200b")
				result_embed.add_field(name="Am I right?",value="Add the reaction accordingly.")
				result_embed.set_image(url=aki.first_guess['absolute_picture_path'])
				result_message = await ctx.send(embed=result_embed)
				await result_message.add_reaction('<:BS_Tick:881610301152305202>')
				await result_message.add_reaction("<:BS_Cross:881610413874225292>")
				option, user = await bot.wait_for('reaction_add', check=option_check, timeout=15)
				if str(option.emoji) ==  '<:BS_Tick:881610301152305202>':
					playing.remove(ctx.author.id)
					final_embed = discord.Embed(title="Akinator",description="It was nice playing with you! Hope to meet you again!", color=discord.Color.green())
					final_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843860718268448778/884907894603149342/PicsArt_09-03-09.20.28.png")
					await ctx.send(embed=final_embed)
					await aki.close()
					
				elif str(option.emoji) == '<:BS_Cross:881610413874225292>':
					playing.remove(ctx.author.id)
					final_embed = discord.Embed(title="Akinator",description="I lost this time. Hope to meet you again!", color=discord.Color.red())
					final_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/843860718268448778/884907894603149342/PicsArt_09-03-09.20.28.png")
					await ctx.send(embed=final_embed)
					await aki.close()

		except asyncio.TimeoutError:
			playing.remove(ctx.author.id)
			await ctx.send("Didn't answered in time!")

@akinator_game.error
async def akinator_game_error(ctx,error):
	try:
		playing.remove(ctx.author.id)
	except :
		pass
	print(error)
'''
#------------------------------------------------------------
@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, commands.CommandNotFound):
		pass
	elif 'Forbidden' in str(error):
		await ctx.send("The bot lacks permissions to do that task")
	elif isinstance(error, commands.MissingPermissions):
		await ctx.send("You dont have permission to use that command")
	elif isinstance(error, commands.CommandOnCooldown):
		time = error.retry_after
		time = convert(time)
		embed = discord.Embed(title="Command on Cooldown!",description=f"The command was used recently! Try again in **{time}**")
		await ctx.send(embed=embed)
	elif isinstance(error,commands.MissingRequiredArgument):
		cur.execute(f"SELECT * FROM command WHERE name like '{ctx.command.name}'")
		hint = cur.fetchone()
		help = discord.Embed(title=f"{prefix}{hint[1]}",description="Values in () are optional\nValues in [] are required",color=0xe02626)
		help.add_field(name="Description:",value=hint[2])
		help.add_field(name="Syntax:",value=f"`{prefix}{hint[3]}`")
		help.add_field(name="Example:",value=hint[4].format(prefix))
		await ctx.send(embed=help)


	else:
		raise error

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
      
    return "%02d min %02d sec" % (minutes, seconds)

#https://discord.com/oauth2/authorize?client_id=823112553051193357&scope=bot&permissions=4278190079
bot.run(os.getenv('DISCORD_BOT_TOKEN'))