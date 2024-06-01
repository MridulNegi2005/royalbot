import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext.commands.cog import Cog
from discord.ext import commands
import time
from discord.ext import tasks
import psycopg2
def get_connection():
    try:
        return psycopg2.connect(
            database="postgres",
            user="postgres",
            password="cosmicbot",
            host="35.225.24.72",
            port=5432,
        )
    except:
        return False
con = get_connection()
query = con.cursor()

class codeshock(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.query = query
        self.con = con

    supporter = SlashCommandGroup("supporter", "Themes related commands")
    @supporter.command(guild_ids=[767591734841835540],description="Give Code Shock role")
    async def give(self,ctx,user:Option(discord.Member,"Member you wanted to give code shock role"),duration:Option(str,"Enter Duration for code shock role. Seperate each time values with a space. Eg :1d 12h")):
        duration=converttime(duration)
        if duration=="error":
            await ctx.respond("The time unit is not valid",ephemeral=True)
            return
        sql = 'SELECT * FROM "temprole" WHERE "user"=%s AND "role"=%s'
        val = (user.id,1191376926263230526)
        query.execute(sql, val)
        myresult = query.fetchall()
        if len(myresult)!=0:
            time2=myresult[0][2]
            duration=duration+time2
            sql = 'UPDATE "temprole" SET "time"=%s WHERE "user"=%s AND "role"=%s'
            val = (time2,user.id,1191376926263230526)
            try:
                query.execute(sql, val)
                con.commit()
                await ctx.respond(f"Successfully extended <@{user.id}>'s role duration>!",allowed_mentions=discord.AllowedMentions.none())
            except Exception as e:
                await ctx.respond(f"An error occured while adding time to <@{user.id}>!\nError : {e}",ephemeral=True)
            return
        sql = 'INSERT INTO temprole ("user","role","time") VALUES ( %s,%s,%s)'
        role=ctx.guild.get_role(1191376926263230526)
        await user.add_roles(role)
        try:
            val = (user.id,1191376926263230526,int(time.time()+duration))
            query.execute(sql, val)
            con.commit()
            await ctx.respond(f"Successfully added <@&1191376926263230526> role to <@{user.id}>!",allowed_mentions=discord.AllowedMentions(roles=False))
        except Exception as e:
            await user.remove_roles(role)
            await ctx.respond(f"An error occured while adding <@&1191376926263230526> role to <@{user.id}>!\nError : {e}",ephemeral=True)
    @supporter.command(guild_ids=[767591734841835540],description="Remove Code Shock role")
    async def remove(self,ctx,user:Option(discord.Member,"Member you wanted to remove code shock role from"),duration:Option(str,"Enter Duration for code shock role to remove. Seperate each time values with a space. Eg :1d 12h")):
        duration=converttime(duration)
        if duration=="error":
            await ctx.respond("The time unit is not valid",ephemeral=True)
            return
        sql = 'SELECT * FROM "temprole" WHERE "user"=%s AND "role"=%s'
        val = (user.id,1191376926263230526)
        query.execute(sql, val)
        myresult = query.fetchall()
        if len(myresult)!=0:
            time2=myresult[0][2]
            print(time2)
            time2-=duration
            print(duration)
            sql = 'UPDATE "temprole" SET "time"=%s WHERE "user"=%s AND "role"=%s'
            val = (time2,user.id,1191376926263230526)
            try:
                query.execute(sql, val)
                con.commit()
                await ctx.respond(f"Successfully decreased <@{user.id}>'s role duration!")
            except Exception as e:
                await ctx.respond(f"An error occured while adding time to <@{user.id}>!\nError : {e}",ephemeral=True)
            return
        else:
            await ctx.respond(f"<@{user.id}> doesn't have <@&1191376926263230526> role!",ephemeral=True)
    @supporter.command(guild_ids=[767591734841835540],description="Know duration of code shock role")
    async def duration(self,ctx,user:Option(discord.Member,"Member you wanted to know the duration of code shock role")):
        sql = 'SELECT * FROM "temprole" WHERE "user"=%s AND "role"=%s'
        val = (user.id,1191376926263230526)
        query.execute(sql, val)
        myresult = query.fetchall()
        if len(myresult)==0:
            await ctx.respond(f"<@{user.id}> doesn't have <@&1191376926263230526> role!",ephemeral=True)
        else:
            time2=myresult[0][2]-int(time.time())
            await ctx.respond(f"<@{user.id}> has <@&1191376926263230526> role for {convert(time2)}")

def converttime(duration):
    ftime=0
    duration = str(duration).split()
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
    day = seconds // (24 * 3600)
    seconds %= (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600  
    minutes = seconds // 60
    seconds %= 60
    if day ==0:
        if hour == 0:
            if minutes !=0: 
                return "%02d min and %02d sec" % (minutes,seconds)
            else : 
                return "%02d sec" % (seconds,)
        else:return "%02d hr, %02d min and %02d sec" % (hour,minutes,seconds)
    else:return "%02d days %02d hr, %02d min and %02d sec" % (day,hour,minutes,seconds)

def setup(bot):
    bot.add_cog(codeshock(bot))