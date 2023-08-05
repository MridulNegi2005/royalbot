import schedule
import discord
from discord.ext import commands
import typing
import asyncio
import time
import psycopg2
import datetime
title = "Cosmic Bot"
#-------------------------------------------------------------------------

con = psycopg2.connect('postgres://balxuonbzytruy:2be081d80c21d0869d500f997e19ff385ad5278d020402608fc23ac1f8d71bc6@ec2-52-73-184-24.compute-1.amazonaws.com:5432/des0u9rjq76pq', sslmode='require')
query = con.cursor()
print(con)

#-------------------------------------------------------------------------


class mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    
    @commands.command(aliases=['sm'])
    @commands.has_permissions(kick_members=True)
    async def slowmode(self, ctx, seconds: int):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(
            f"Slowmode in this channel has been set to {seconds} seconds")
        await ctx.message.delete()
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def say(self, ctx,channel:typing.Optional[discord.TextChannel], *, message):
        if not channel:
            channel = ctx.channel
        await channel.send(message)
        await ctx.message.delete()
		
    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def nick(self, ctx, member: discord.Member, *, nick):
        if ctx.author.top_role > member.top_role:
            await member.edit(nick=nick)
            await ctx.send(f'Nickname was changed for {member.mention} ')
        else :
            await ctx.send("Don't try to change nickame of your peers!")
        

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self,ctx, member: discord.Member, *, reason=None):
        if ctx.author.top_role > member.top_role:
            await self.guild.kick(member)
            await ctx.send(f'User {member} has been kick. Reason : '+reason)
        else :
            await ctx.send("Don't try to kick your peers!")
        

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def mute(self, ctx,member: discord.Member,*,reason="Not provided"):
        if ctx.author.top_role > member.top_role:
            await member.add_roles(discord.utils.get(ctx.guild.roles, name="Muted"))
            mute = discord.Embed(title="User Muted",description=f"{member.mention} has been muted for Reason : {reason}",color=0xff00f6)
            await ctx.send(embed=mute)
        else :
            await ctx.send("Don't try to mute your peers!")
        

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def tempmute(self, ctx,member: discord.Member,duration,*,reason="Not provided"):
        t = converttime(duration)
        if t == "error":
            await ctx.send("The time unit is not valid")
            return
        await member.add_roles(discord.utils.get(ctx.guild.roles, name="Muted"))
        await ctx.send(
            f"{member.mention} has been muted for {duration}. Reason : {reason}")
        await asyncio.sleep(int(t))
        await member.remove_roles(discord.utils.get(ctx.guild.roles, name="Muted"))

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def unmute(self, ctx, user: discord.Member, *, reason="Not provided"):
        muterole = discord.utils.get(ctx.guild.roles, name="Muted")
        if muterole not in user.roles:
            await ctx.send("Member is not muted")
            return
        await user.remove_roles(discord.utils.get(ctx.guild.roles, name="Muted"))

        await ctx.send(f"{user.mention} has been unmuted. Reason : {reason}")

    @commands.command(aliases=['fban'])
    @commands.has_permissions(ban_members=True)
    async def forceban(self, ctx, userID:int):
        if userID in ctx.guild.members:
            embed = discord.Embed(description=" "+f"Unsuccessful, the user is in this guild. Ban him using *ban", color=discord.Color.orange())
            await ctx.reply(embed=embed, mention_author=False)

        else:
            await ctx.guild.ban(discord.Object(id=userID))
            embed = discord.Embed(title=f"Successfully force banned {userID}", color=discord.Color.orange())
            await ctx.reply(embed=embed, mention_author=False)
    
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        if ctx.author.top_role > member.top_role:
            dm = await member.create_dm()
            await dm.send("You were banned from the server! \nFor ban appeal join : https://discord.gg/ctsN7T9Adv")
            await member.ban(reason=reason)
            await ctx.send(f'User {member} has been banned for Reason :{reason}')
        else :
            await ctx.send("Don't try to ban your peers!")


           
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def warn(self,ctx, user: discord.Member=None,*, reason="Not Provided"):
        if user==None:
            await ctx.send("Mention a user/id!")
            return
        x = datetime.datetime.now()
        date1 = x.strftime("%d") +" "+x.strftime("%b") +" "+x.strftime("%Y")
        sql = 'INSERT INTO warns ("user","reason","moderator","date") VALUES ( %s,%s,%s,%s)'
        val = (user.id,reason,ctx.author.id,date1)
        query.execute(sql, val)
        con.commit()
        warn = discord.Embed(title=title,description=f"{user.mention} has been warned by {ctx.author.mention} for Reason : {reason}",color=user.color )
        await ctx.send(embed=warn)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def clearwarn(self,ctx, user: discord.Member=None,*,num):
        if user==None:
            await ctx.send("Mention a user/id!")
        count =0
        sql = 'SELECT * FROM "warns" WHERE "user" = '+str(user.id)
        query.execute(sql)

        myresult = query.fetchall()

        for x in myresult:
            count = count + 1
        if count > 0:
            if num == "all" :
                sql = "DELETE FROM 'warns' WHERE 'user' = %s"
                user1 = (user.id,)
                query.execute(sql,user1)
                con.commit()
                await ctx.send("Successfully Cleared all warnings from "+user.name)
            else:
                num = int(num)
                sql = 'DELETE FROM "warns" WHERE "id" = %s'
                id = (num,)
                query.execute(sql,id)
                con.commit()
                await ctx.send("Successfully Cleared a warn from "+user.name)
        else:
             await ctx.send(user.name+" has no warnings!")
    @commands.command(aliases=['warns'])
    @commands.has_permissions(kick_members=True)
    async def warnings(self,ctx,user:discord.Member=None):
        if user == None:
            user = ctx.author
        pfp = user.avatar.url
        count =0
        sql = 'SELECT * FROM warns WHERE "user" = %s'
        query.execute(sql,(user.id,))
        myresult = query.fetchall()
        for x in myresult:
            count = count + 1
                
        warns = discord.Embed(color=0xe83535)
        warns.set_author(name=f"{count} Warnings for {user.name} ({user.id})",icon_url = pfp)
        for x in myresult:
            a = str(x)
            a = a.replace('(','')
            a = a.replace(')','')
            a = a.replace("'",'')
            y = a.split(',')
            u = y[2].replace(' ','')
            user1 = self.bot.get_user(u) or await self.bot.fetch_user(u)
            warns.add_field(name=f"Warn ID : {y[3]}  || Moderator : {user1.name}", value=f"Reason : {y[1]} \t -```{y[4]}``` ", inline=False)
        await ctx.send(embed=warns)

    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def whitechan(self,ctx, chan: discord.TextChannel=None,*, reason="Not Provided"):
        if chan ==None:
            await ctx.send("Mention a channel/id!")
            return
        sql = 'INSERT INTO config("whitechan",) VALUES ( %s,)'
        val = (chan.id,)
        query.execute(sql, val)
        con.commit()
        await ctx.send("Channel Whitelisted")


'''
    @commands.command(pass_context=True)
    @commands.has_permissions(kick_members=True)
    async def purge(self,ctx, limit: int):
            await ctx.channel.purge(limit=limit)
            message = await ctx.send(f"Purged {limit} messages!")
            await asyncio.sleep(5)
            await message.delete()
'''
def converttime(time):
    units = ["s", "h", "m","d"]
    unit = time[-1]
    if unit not in units:
        return "error"
    t = time[:-1]
    if unit == "s":
        return 1 * t
    elif unit == "h":
        return 60 * 60 * t
    elif unit == "m":
        return 60 * t
    elif unit == 'd':
        return 24*60*60*t    
def setup(bot):
    bot.add_cog(mod(bot))
