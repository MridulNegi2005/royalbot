from distutils.log import error
import discord
from discord.ext import commands
from discord.interactions import InteractionResponse
import os
from dotenv import load_dotenv
load_dotenv()
import json
import asyncio
sent_users=[]
intents = discord.Intents().all()
# we need members intent too
intents.members = True
intents.message_content=True
bot = commands.Bot(command_prefix="=",intents=intents)
bot.remove_command("help")



@bot.event
async def on_ready():
	print('We have logged in as {0.user}'.format(bot))
	await bot.change_presence(status=discord.Status.dnd ,activity=discord.Activity(type=discord.ActivityType.listening, name="COSMIC'S UNIVERSE | DM for help!"))
class invite2(discord.ui.View):
	def __init__(self):
		super().__init__()
	@discord.ui.button(label="⠀⠀⠀⠀⠀⠀Invite⠀⠀⠀⠀⠀⠀⠀", style=discord.ButtonStyle.green)
	async def callback(self,button,interaction):
		await interaction.response.send_message("https://tenor.com/view/rickroll-roll-rick-never-gonna-give-you-up-never-gonna-gif-22954713",ephemeral=True)

class delete(discord.ui.Button):
	def __init__(self,id,channel):
		self.channel=channel
		super().__init__(
			emoji="<:trashbin:943145548674916363>",
            style=discord.enums.ButtonStyle.red,
            custom_id=id
        )
	async def callback(self,interaction: discord.Interaction):
		message = await self.channel.fetch_message(int(self.custom_id))
		await message.delete()
		await interaction.response.send_message(f"Message deleted!")
class Confirm(discord.ui.View):
	def __init__(self,message):
		self.message=message
		super().__init__()
	@discord.ui.button(emoji ="<:BS_Tick:881610301152305202>", style=discord.ButtonStyle.green)
	async def tick(self,button,interaction):
		embed = discord.Embed(color=0x00FFFF)
		embed.set_author(name=f"Cosmic Shock Support", icon_url="https://cdn.discordapp.com/attachments/823112885877735435/1013500182765252639/a_4bef9ab663e08abc11d6e7b28a386729.gif")
		embed.add_field(name='Your ticket has been initiated', value="You may now describe your issue below. Staff will contact you shortly!")
		embed.set_footer(text="Cosmic Shock | Help & Support ")
					
		await interaction.response.send_message(embed=embed)

		guild = bot.get_guild(767591734841835540)
		categ = discord.utils.get(guild.categories, name = "Modmail tickets")
		mod = discord.utils.get(guild.roles, name = "TΞAM COSMIC")
		if not categ:
			overwrites = {
				guild.default_role : discord.PermissionOverwrite(read_messages = False),
				guild.me : discord.PermissionOverwrite(read_messages = True),
				mod : discord.PermissionOverwrite(read_messages = True)
			}
			categ = await guild.create_category(name = "Modmail tickets", overwrites = overwrites)

		channel = bot.get_channel(853590083739582474)
		thread = discord.utils.get(channel.threads, name = f"{str(interaction.user.name)}{interaction.user.discriminator}",archived=False)
		if not thread:
			new = discord.Embed(title="New ticket",color=0xFFED89,description="Type a Message in this channel to reply. Messages starting with the server prefix '=' are ignored, and can be used for staff discussion.The messages sent by the bots are ignored too. Use the command =close [reason] to close this ticket.")
			new.add_field(name="User",value=f"{interaction.user.mention}\n ({interaction.user.id})")
			new.set_footer(text=interaction.user,icon_url = interaction.user.display_avatar.url)
			logs = bot.get_channel(853590083739582474)
			log_new = discord.Embed(title="New Ticket",color=discord.Color.green())
			log_new.set_footer(icon_url = interaction.user.display_avatar.url,text=str(interaction.user)+f" ({interaction.user.id})")
			first =await logs.send(embed=log_new)
			thread = await first.create_thread(name = f"{str(interaction.user.name)}{interaction.user.discriminator}")
			message = await thread.send(f"{interaction.user.id}",embed=new)
			await message.pin(reason="Modmail Ticket")
			#await thread.send("<@&816681109001207808><@&767591734850879497>",allowed_mentions=discord.AllowedMentions(roles=False))
			guild = bot.get_guild(767591734841835540)
			mod = discord.utils.get(guild.roles,id=816681109001207808)
			admin = discord.utils.get(guild.roles,id=767591734850879495)
			staff=[]
			
			for x in guild.members:
				if mod in x.roles or admin in x.roles:
					print(x)
					staff.append(x)
					await thread.add_user(x)
			
			categ = discord.utils.get(guild.categories, name = "Modmail tickets")
						
		file=[]
		for x in self.message.attachments:
			file.append(await x.to_file())
		embed = discord.Embed(description = self.message.content, colour = 0xb734eb)
		embed.set_author(name = "Message Received")
		embed.set_footer(text=interaction.user,icon_url = interaction.user.display_avatar.url)
		await thread.send(embed = embed,files=file)
	@discord.ui.button(emoji ="<:BS_Cross:881610413874225292>", style=discord.ButtonStyle.red)
	async def cross(self,button,interaction):
		embed = discord.Embed(color=0x00FFFF)
		embed.set_author(name=f"Cosmic Shock Support", icon_url="https://cdn.discordapp.com/attachments/823112885877735435/1013500182765252639/a_4bef9ab663e08abc11d6e7b28a386729.gif")
		embed.add_field(name='Your ticket request has been cancelled', value="\u200b")
		embed.set_footer(text="Cosmic Shock | Help & Suport ")
		await interaction.response.send_message(embed=embed)
		sent_users.remove(interaction.user.id)

@bot.command()
async def invite(ctx):
    await ctx.message.reply("Thanks for using this bot! You can invite it from link below",view=invite2())
@bot.command()
async def close(ctx,*,message="No reason was provided"):
	thread = ctx.channel
	msg = message
	parent = thread.parent_id
	if parent == 853590083739582474:
		messages = await thread.pins()
		member = ctx.guild.get_member(int(messages[0].content))
		if member : 
			embed = discord.Embed(title="Ticket Closed!",description=msg,color=0xe80000)
			embed.set_author(name = ctx.author, icon_url = ctx.author.display_avatar.url)
			if member:
				await member.send(embed=embed)
			await thread.edit(archived=True)
			guild = bot.get_guild(767591734841835540)
			categ = discord.utils.get(guild.categories, name = "Modmail tickets")
			logs = bot.get_channel(853590083739582474)
			log_close = discord.Embed(title="Ticket closed",description=msg,color=discord.Color.red())
			log_close.set_author(icon_url=member.display_avatar.url,name=f"{member} ({member.id})")
			log_close.set_footer(icon_url = ctx.author.display_avatar.url,text=ctx.author)
			await logs.send(embed=log_close)
			sent_users.remove(member.id)
	

@bot.listen("on_message")
async def support(message):
	view=Confirm(message)
	try:
		guild = bot.get_guild(767591734841835540)
		categ = discord.utils.get(guild.categories, name = "Modmail tickets")
		channel = bot.get_channel(853590083739582474)
		thread = discord.utils.get(channel.threads, name = f"{str(message.author.name)}{message.author.discriminator}",archived=False)
		if not thread:
			try:
				sent_users.remove(message.author.id)
			except:
				pass
	except : 
		pass
	if message.author == bot.user:
		return
	if str(message.channel.type) == "private":
		guild = bot.get_guild(767591734841835540)
		if guild.get_member(message.author.id) is not None:
			pass
		else:
			await message.author.send("You are not a member of Cosmic's Universe! Join the server for any help or support needed!")
			await message.author.send("https://discord.gg/9peGjQZpbF")
			return
		if message.author.id in sent_users: # Ensure the intial message hasn't been sent before
			guild = bot.get_guild(767591734841835540)
			categ = discord.utils.get(guild.categories, name = "Modmail tickets")
			channel = bot.get_channel(853590083739582474)
			thread = discord.utils.get(channel.threads, name = f"{str(message.author.name)}{message.author.discriminator}",archived=False)
			if thread:
				attachment = message.attachments
				embed = discord.Embed(description = message.content, colour = 0xb734eb)
				embed.set_author(name = "Message Received")
				embed.set_footer(text=message.author,icon_url = message.author.display_avatar.url)
				file=[]
				for x in attachment:
					file.append(await x.to_file())
				await thread.send(embed = embed,files=file)
				msg = message
				await msg.add_reaction("<:BS_Tick:881610301152305202>")
			
		else:
			if guild.get_member(message.author.id) is not None:
				pass
			else:
				await message.author.send("You are not a member of Cosmic's Universe! Join the server for any help or support needed!")
				await message.author.send("discord.gg/sFj5b45ZY4")
				return
			modmail_channel = bot.get_channel(848872549315641345)

			embed = discord.Embed(color=0x00FFFF)
			embed.set_author(name=f"Cosmic Shock Modmail System", icon_url="https://cdn.discordapp.com/attachments/823112885877735435/1013500182765252639/a_4bef9ab663e08abc11d6e7b28a386729.gif")
			embed.add_field(name='Do you really want to get support from our staffs?', value=f"React below to confirm")
			embed.set_footer(text="Cosmic's Universe | Modmail")
			msg = await message.author.send(embed=embed,view=view)
			sent_users.append(message.author.id) # add this user to the list of sent users

	elif isinstance(message.channel, discord.Thread):
		thread = message.channel
		parent = thread.parent_id
		if parent == 853590083739582474:
			try:
				messages = await thread.pins()
				print(messages[0].content)
				member =await message.guild.fetch_member(int(messages[0].content))
				print(member)
				print(member.dm_channel)
				for x in dir(member):
					print(x,"= ",getattr(member,x))
				if member:
					if message.content.startswith('='):
						return
					if message.author.bot == True:
						await message.add_reaction("<:BS_Cross:881610413874225292>")
						return
					embed1 = discord.Embed(description = message.content, colour = 0x61eb34)
					embed1.set_author(name = "Message Received")
					embed1.set_footer(text=message.author,icon_url = message.author.display_avatar.url)
					attachment = message.attachments
					file=[]
					for x in attachment:
						file.append(await x.to_file())
					message2 = await member.send(embed = embed1,files=file)
					view=discord.ui.View(timeout=None)
					if member.dm_channel is None:
						await member.create_dm()
					print(member.dm_channel)
					print(message2.id)
					print(message2.channel)
					print(await member.create_dm())
					view.add_item(delete(str(message2.id),member.dm_channel))                                              
					embed = discord.Embed(description = message.content, colour = 0x61eb34)
					embed.set_author(name = "Message Sent")
					embed.set_footer(text=message.author,icon_url = message.author.display_avatar.url)
					attachment = message.attachments
					await message.delete()
					file=[]
					for x in attachment:
						file.append(await x.to_file())
					await message.channel.send(embed=embed,view=view,files=file)
				else:
					await message.channel.send("The user left the server. You may now close ticket with `=close [reason]` command")
					return
			except Exception as e:
				print(e)
				

#https://discord.com/api/oauth2/authorize?client_id=847160870000656425&permissions=0&scope=bot
bot.run(os.getenv('DISCORD_MODMAIL_TOKEN'))