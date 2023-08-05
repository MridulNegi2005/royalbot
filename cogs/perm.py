import schedule
import discord
from discord.commands import slash_command
from discord.ext import commands
import asyncio
import time
import psycopg2
import datetime
	
class perm(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def perm(self,ctx):
        print(self.bot.pending_application_commands)
        await ctx.send("hello")
"""
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def perm(self,ctx):
        perm1 = discord.Embed(title="Permission handler",description="Mention channels whose permission you want to change seperated by commas or 'all' to apply for all channel \n `<channel_1>,<channel_2> \t or all` ",color=0xbe6ae6)
        perm2 = discord.Embed(title="Permission handler",description="Mention roles whose permission you want to change seperated by commas or 'all' to apply for all roles \n `<role_id_1>,<role_id_2> \t or \t all` ",color=0xbe6ae6)
        perm3 = discord.Embed(title="Permission handler",description="Select Permssion to update",color=0xbe6ae6)
        perm4 = discord.Embed(title="Permission handler",description="Select Value for permission",color=0xbe6ae6)
        await ctx.send(embed=perm1)
        n=1
        while n<4:
            channels = await self.bot.wait_for('message',timeout=45)
            if channels.author.id == ctx.author.id :
                await ctx.send(str(channel))
                channels = str(channels.content).replace(' ','')
                channels = str(channels.content).replace('#','')
                channels = str(channels).replace('<','')
                channels = str(channels).replace('>','')
                channels = channels.split(',')
                print("hey")

                for x in channels :
                    print(x.channel)
                    chan = self.bot.get_channel(x.channel)
                    if x =='all':
                        break
                    elif not chan:
                        await ctx.send(f"Improper argument \n {3-n} tries left!")
                        n+=1
        await ctx.send(embed=perm2)			
        n=1
        while n<4:
            roles = await self.bot.wait_for('message',timeout=45)
            if roles.author.id == ctx.author.id :
                roles = str(roles).replace(' ','')
                roles = roles.split(',')
                for x in roles :
                    if x == 'all':
                        break
                    chan = self.bot.get_role(x)
                    if not chan:
                        await ctx.send(f"Improper argument \n {3-n} tries left!")
        embed = discord.Embed(title=f"Updating {role.name} permissions for all Channels!",description="__*Kindly Wait*__",color=discord.Color.red())
        msg = await ctx.send(embed=embed)
        start = round(time.time(),3)
        print(start)
        guild = ctx.guild
        for x in guild.text_channels:
            y = x.overwrites_for(role)
            y.update(read_messages= True)
            await x.set_permissions(role,overwrite=y)
        end = round(time.time())
        duration = str(end-start)+"s"
        t = converttime(duration)
        embed = discord.Embed(title=f"Updated {role.name} permissions",description= f"Operation took {t} seconds!",color=discord.Color.green())
        await msg.edit(embed=embed)"""
		
		
def setup(bot):
    bot.add_cog(perm(bot))