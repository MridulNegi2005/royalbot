from datetime import datetime, timezone
from typing import Optional
import asyncio
import discord
import speedtest
from discord import Member
from discord.ext import commands
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

# Components V2 has no embed fields, so both cards are hand-laid text.

def user_info_card(target):
	view = discord.ui.DesignerView(timeout=None)
	container = discord.ui.Container(color=target.colour)
	container.add_section(
		discord.ui.TextDisplay(f"### {target}\n`{target.id}`"),
		accessory=discord.ui.Thumbnail(target.display_avatar.url))
	container.add_separator(divider=True)
	container.add_text(
		f"**Top role** · {target.top_role.mention}\n"
		f"**Status** · {target.status}\n"
		f"**Activity** · {target.activity.name if target.activity else 'None'}\n"
		f"**Bot** · {'Yes' if target.bot else 'No'}\n"
		f"**Boosted** · {'Yes' if target.premium_since else 'No'}")
	container.add_separator(divider=False)
	container.add_text(
		f"**Created at** · {target.created_at.strftime('%d/%m/%Y %H:%M:%S')}\n"
		f"**Joined at** · "
		f"{target.joined_at.strftime('%d/%m/%Y %H:%M:%S') if target.joined_at else 'Unknown'}")
	container.add_separator(divider=False)
	container.add_text(f"-# [Avatar]({target.display_avatar.url})")
	view.add_item(container)
	return view


def server_info_card(guild, viewer):
	statuses = {"online": 0, "idle": 0, "dnd": 0, "offline": 0}
	for member in guild.members:
		state = str(member.status)
		if state in statuses:
			statuses[state] += 1

	text = voice = announcement = 0
	for channel in guild.text_channels:
		if channel.is_news():
			announcement += 1
		else:
			text += 1
	for channel in guild.voice_channels:
		voice += 1

	icon_link = f"[Click Here]({guild.icon.url})" if guild.icon else "None"
	banner_link = f"[Click Here]({guild.banner.url})" if guild.banner else "None"

	view = discord.ui.DesignerView(timeout=None)
	container = discord.ui.Container()
	head = discord.ui.TextDisplay(
		f"### <:verified:884020441373605958> {guild.name}\nServer information")
	if guild.icon:
		container.add_section(head, accessory=discord.ui.Thumbnail(guild.icon.url))
	else:
		container.add_item(head)

	if guild.description:
		container.add_separator(divider=True)
		container.add_text(
			f"<:notepad:884023914701922334> **Description**\n{guild.description}")

	container.add_separator(divider=True)
	container.add_text(
		f"<:hyphen:884022484595253248> **Miscellaneous**\n"
		f"Server ID: **{guild.id}**\n"
		f"Server Icon: {icon_link}\n"
		f"Server Banner: {banner_link}\n"
		f"Server Owner: **{guild.owner} (`{guild.owner_id}`)**\n"
		f"Server Boosts: **{guild.premium_subscription_count} Boosts**\n"
		f"Verification Level: **{guild.verification_level}**")

	container.add_separator(divider=True)
	container.add_text(
		f"<:remind:884031965320331275> **Dates**\n"
		f"Created At: **{guild.created_at.strftime('%d/%m/%Y %H:%M:%S')}**\n"
		f"Joined At: **{viewer.joined_at.strftime('%d/%m/%Y %H:%M:%S') if viewer.joined_at else 'Unknown'}**")

	container.add_separator(divider=True)
	container.add_text(
		f"<:folder:884021905043095583> **Channels**\n"
		f"Total Channels: **{len(guild.channels)}**\n"
		f"<:channel:884022113013481502> **{text}** "
		f"<:voice:884022216512110612> **{voice}** "
		f"<:announcement:884022180927668234> **{announcement}**")

	container.add_separator(divider=False)
	container.add_text(
		f"<:member:884023021373882418> **Members**\n"
		f"Total Members: **{guild.member_count}**\n"
		f"<:online:884034069967556618> **{statuses['online']}** "
		f"<:idle:884034313119748106> **{statuses['idle']}** "
		f"<:dnd:884034275777847346> **{statuses['dnd']}** "
		f"<:offline:884034380048257074> **{statuses['offline']}**")
	view.add_item(container)
	return view


class Info(Cog):
	def __init__(self, bot):
		self.bot = bot

	@slash_command(description="Test the bot's internet speed!")
	@commands.cooldown(1, 120, commands.BucketType.guild)
	async def speedtest(self,ctx):
		await ctx.respond("Calculating <a:loading:886509142934683678>")

		def run_test():
			s = speedtest.Speedtest()
			return (s.download()//10000)/100, (s.upload()//10000)/100

		# speedtest-cli blocks for 10-30 seconds. Run on the event loop it stops
		# every command, event and voice heartbeat in the bot for that long.
		try:
			download, upload = await asyncio.to_thread(run_test)
		except Exception as e:
			await ctx.send(f"Speed test failed: {e}")
			return
		await ctx.send(f"Downloading Speed: {download} Mbps\nUploading Speed: {upload} Mbps")

	@slash_command(description="Check information regarding a user")
	async def user_info(self, ctx, target:Option(discord.Member,"Member whose info you wanted to check",required=False)):
		if target==None:target=ctx.author
		await ctx.respond(view=user_info_card(target))

	@slash_command(description="Check the server's info")
	async def server_info(self, ctx):
		await ctx.respond(view=server_info_card(ctx.guild, ctx.author))


def setup(bot):
	bot.add_cog(Info(bot))
