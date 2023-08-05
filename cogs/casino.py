import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
from discord.ext.commands.cog import Cog
import asyncio
import time
import psycopg2
import datetime
from main import query,con
import ast
class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    casino = SlashCommandGroup("casino", "Casino related commands")

    roles = casino.create_subgroup("role", "Configure roles from casino")


    @roles.command(description="Add role you own in casino.")
    async def add(self, ctx,role:Option(str,"Select role to add",choices=['Casino Red','Casino Blue','Casino Coral','Casino Gold','Casino Crimson','Casino Pink','Casino Green',])):
        roles=[]
        sql='SELECT "role" FROM "temprole" WHERE "user" = %s'
        val=(ctx.author.id,)
        query.execute(sql,val)
        myresult = query.fetchall()
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            roles.append(y[0])
        
        if role=="Casino Red":
            role=ctx.guild.get_role(783038419147161650)
        elif role=="Casino Blue":
            role=ctx.guild.get_role(783308376339513345)
        elif role=="Casino Coral":
            role=ctx.guild.get_role(783314459019313152)
        elif role=="Casino Gold":
            role=ctx.guild.get_role(783317796317691946)
        elif role =="Casino Crimson":
            role=ctx.guild.get_role(783318887939833886)
        elif role=="Casino Pink":
            role=ctx.guild.get_role(897401951816417310)
        elif role =="Casino Green":
            role=ctx.guild.get_role(897402749321379852)

        
        if role.id in roles:
            await ctx.author.add_roles(role)
            await ctx.respond(f"Successfully added {role.name} role!")
        else:
            await ctx.respond("You dont own that role!")
    @roles.command(description="Remove role you own in casino.")
    async def remove(self, ctx,role:Option(str,"Select role to remove",choices=['Casino Red','Casino Blue','Casino Coral','Casino Gold','Casino Crimson','Casino Pink','Casino Green',])):
        if role=="Casino Red":
            role=ctx.guild.get_role(783038419147161650)
        elif role=="Casino Blue":
            role=ctx.guild.get_role(783308376339513345)
        elif role=="Casino Coral":
            role=ctx.guild.get_role(783314459019313152)
        elif role=="Casino Gold":
            role=ctx.guild.get_role(783317796317691946)
        elif role =="Casino Crimson":
            role=ctx.guild.get_role(783318887939833886)
        elif role=="Casino Pink":
            role=ctx.guild.get_role(897401951816417310)
        elif role =="Casino Green":
            role=ctx.guild.get_role(897402749321379852)

        if role in ctx.author.roles:
            await ctx.author.remove_roles(role)
            await ctx.respond(f"Role {role.name} removed! You can add that role anytime using '/casino role add' command!")
        else:
            await ctx.respond("You dont own that role!")
def setup(bot):
    bot.add_cog(Casino(bot))