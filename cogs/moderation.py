from email.policy import default
import discord
from discord.ext import commands
from discord.ext.commands.cog import Cog
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
import datetime,asyncio
import time
from main import query,con

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def slowmode(self, ctx, seconds:Option(int,"Slowmode time in seconds. '0' for none")):
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.respond(
            f"Slowmode in this channel has been set to {seconds} seconds")
    
    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def say(self, ctx,message:Option(str,"Add Text Message"),channel:Option(discord.TextChannel,"Channel to send message to",required=False,default=None)):
        if channel == None:
            channel = ctx.channel
        await channel.send(message)
        await ctx.respond("Message sent!",ephemeral=True)
		
    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def nick(self, ctx, member:Option(discord.Member,"User whose nickname you want to change."),nick:Option(str,"Enter the new nickname.")):
        if ctx.author.top_role > member.top_role:
            await member.edit(nick=nick)
            await ctx.respond(f'Nickname was changed for {member.mention} ')
        else :
            await ctx.respond("Don't try to change nickame of your peers!",ephemeral=True)
        

    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def kick(self,ctx, member: Option(discord.Member,"Member who you want to kick!"), reason:Option(str,"Reason")):
        if ctx.author.top_role > member.top_role:
            await self.guild.kick(member)
            await ctx.respond(f'User {member} has been kick. Reason : '+reason)
        else :
            await ctx.respond("Don't try to kick your peers!",ephemeral=True)
        

    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def mute(self,ctx, member: Option(discord.Member,"Member who you want to mute!"),duration:Option(str,"Enter Duration.Seperate each time values with a space. Eg : 1d 12h"),reason:Option(str,"Reason")):
        if ctx.author.top_role > member.top_role:
            duration = converttime(str(duration))
            duration2 = datetime.timedelta(seconds=duration)
            mute = discord.Embed(title="User Muted",description=f"{member.mention} has been muted  muted for {convert(duration)}.\nReason : {reason}",color=0xff4242)
            
            await member.timeout_for(duration2)
            await ctx.respond(f'User {member} has been muted for {convert(duration)}. Reason : {reason}')# I already did this work 
            
        else :
            await ctx.respond(embed=mute)


    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def unmute(self,ctx, member: Option(discord.Member,"Member who you want to unmute!"), reason:Option(str,"Reason",default="Not specified")):
        await member.remove_timeout(reason=reason)

        await ctx.respond(f"{member.mention} has been unmuted.\nReason : {reason}")


    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def ban(self,ctx, member: Option(discord.Member,"Member who you want to ban!"), reason:Option(str,"Reason")):
        if ctx.author.top_role > member.top_role:
            dm = await member.create_dm()
            try:
                await dm.send("You were banned from the server! \nFor ban appeal join : https://discord.gg/ctsN7T9Adv")
                await member.ban(reason=reason)
                await ctx.respond(f'User {member} has been banned for Reason :{reason}')
            except:
                await member.ban(reason=reason)
                await ctx.respond(f'User {member} has been banned for Reason :{reason}')
        else : 
            await ctx.respond("Don't try to ban your peers!",ephemeral=True)


           
    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def warn(self,ctx, member: Option(discord.Member,"Member who you want to warn!"), reason:Option(str,"Reason")):
        user=member
        if user==None:
            await ctx.send("Mention a user/id!")
            return
        x = datetime.datetime.now()
        date1 = x.strftime("%d") +" "+x.strftime("%b") +" "+x.strftime("%Y")
        sql = 'INSERT INTO warns ("user","reason","moderator","date") VALUES ( %s,%s,%s,%s)'
        val = (user.id,reason,ctx.author.id,date1)
        query.execute(sql, val)
        con.commit()
        warn = discord.Embed(description=f"{user.mention} has been warned by {ctx.author.mention} for Reason : {reason}",color=user.color )
        await ctx.respond(embed=warn)

    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def clear_warn(self,ctx, member: Option(discord.Member,"Member whose warn you want to clear!"),warn_id:Option(str,"ID of warn you want to clear. Write 'all' to clear all"),reason:Option(str,"Reason")):
        user=member
        num = warn_id
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
                await ctx.respond("Successfully Cleared all warnings from "+user.name)
            else:
                num = int(num)
                sql = 'DELETE FROM "warns" WHERE "id" = %s'
                id = (num,)
                query.execute(sql,id)
                con.commit()
                await ctx.send("Successfully Cleared a warn from "+user.name)
        else:
             await ctx.send(user.name+" has no warnings!")
    
    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    async def warnings(self,ctx, member: Option(discord.Member,"Member whose warn you want to check",required=False,deafult=None)):
        user = member
        staff = False
        if user == None:
            user = ctx.author
        else:
            for x in ctx.author.roles:
                if x.id == 767591734850879495:
                    staff=True
                    break
                if x.id == 767591734850879494:
                    staff=True
                    break
            if staff==False:
                ctx.respond("You can only check yours warnings!")
        pfp = user.avatar.url
        count =0
        sql = 'SELECT * FROM warns WHERE "user" = %s'
        query.execute(sql,(user.id,))
        myresult = query.fetchall()
        for x in myresult:
            count = count + 1
                
        warns = discord.Embed(color=0xe83535)
        warns.set_author(name=f"{count} Warnings for {user.name} ({user.id})",icon_url = pfp)
        for x in myresult.reverse():
            a = str(x)
            a = a.replace('(','')
            a = a.replace(')','')
            a = a.replace("'",'')
            y = a.split(',')
            u = y[2].replace(' ','')
            user1 = self.bot.get_user(u) or await self.bot.fetch_user(u)
            warns.add_field(name=f"Warn ID : {y[3]}  || Moderator : {user1.name}", value=f"Reason : {y[1]} \t ```{y[4]}``` ", inline=False)
        await ctx.send(embed=warns)


    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def purge(self,ctx,limit:Option(int,"No. of messages u want to purge!")):
            await ctx.channel.purge(limit=limit)
            await ctx.respond(f"Purged {limit} messages!")
def converttime(duration):
    ftime=0
    duration = duration.split()
    units = ["s", "h", "m", "d"]
    for x in duration:
        unit = x[-1]
        if unit not in units:
            return "error"
        t = int(x[:-1])
        if unit == "s":
            ftime=ftime+t
        elif unit == "h":
            ftime=ftime+( 60 * 60 * t)
        elif unit == "m":
            ftime=ftime+(60 * t)
        elif unit == 'd':
            ftime=ftime+(24*60*60*t)
    return ftime
def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600  
    minutes = seconds // 60
    seconds %= 60
    if hour == 0:
        if minutes !=0: 
            return "%02d min and %02d sec" % (minutes,seconds)
        else : 
            return "%02d sec" % (seconds,)
    else:return "%02d hr, %02d min and %02d sec" % (hour,minutes,seconds)
def setup(bot):
    bot.add_cog(Moderation(bot))