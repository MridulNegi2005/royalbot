import discord
import mysql.connector
from discord.ext import commands
import mysql.connector
from discord.utils import get
import os
title = "Cosmic Bot"

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
mydb =  mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"))
query = mydb.cursor()
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
achievements = {
    'TeamPlayer',
    'Pro TeamPlayer',
    'Solo Player', 
    'Duo Player',
    'Undefeated Champion',
    'Extreme Player',
    'Overpowered Player',
    'Addicted Player',
    'Casual Player',
    'Long-Time Player',
    'No-Lifer',

    'Gem Carrier',
    'Sneaky Snake',
    'Lucky Balls',
    'Quick Ball',
    'Bounty Boss',
    'Perfect Bounty',
    'Perfect Heist',
    'Lucky Heist',
    'Siege Monster',
    'Pure Winner',
    'Skilled Solo',
    'Close Call',
    'Like a Boss',
    'Marconian'}
Profile ={'TeamPlayer',
    'Pro TeamPlayer',
    'Solo Player', 
    'Duo Player',
    'Undefeated Champion',
    'Extreme Player',
    'Overpowered Player',
    'Addicted Player'
}
Levels = {
    'Casual Player',
    'Long-Time Player',
    'No-Lifer'
}
gem={
    'Gem Carrier',
    'Sneaky Snake'
}
ball={
    'Lucky Balls',
    'Quick Ball'
}
bounty={
     'Bounty Boss',
    'Perfect Bounty'
}
heist ={
    'Perfect Heist',
    'Lucky Heist'
}
siege={'Siege Monster'}
showdown={
    'Pure Winner',
    'Skilled Solo',
    'Close Call'
}
weekend={'Like a Boss'}
club={'Marconian'}
mode = "Others"

ach2 = discord.Embed(color=0xe83535)
class achievement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def add(self,ctx,user: discord.Member=None,*,ach):
        
        if user==None:
            await ctx.send("Mention a user/id!")
            return
        temp =[]
        ach = str(ach)
        for x in achievements:
            if ach.lower() in x.lower():
                temp.append(x)
        if temp[0] in Profile:
            mode = "Profile"
        if temp[0] in Levels:
            mode = "Levels"
        if temp[0] in gem:
            mode = "Gem Grab"
        if temp[0] in ball:
            mode = "Brawl Ball"
        if temp[0] in bounty:
            mode = "Bounty"
        if temp[0] in heist:
            mode = "Heist"
        if temp[0] in showdown:
            mode = "Showdown"
        if temp[0] in siege:
            mode = "Seige"
        if temp[0] in weekend:
            mode = "Events"
        if temp[0] in club:
                mode = "Club"
        await ctx.send(mode)
        sql = "INSERT INTO achievements (user,achievement,mode) VALUES ( %s,%s,%s)"
        val = (user.id,temp[0],mode)
        query.execute(sql, val)
        mydb.commit()
        achieve = discord.Embed(title="Achievement",description=f"{user.mention} has been awarded  : {temp[0]}",color=user.color )
        await ctx.send(embed=achieve)

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def remove(self,ctx, user: discord.Member=None,*,name):
        if user==None:
            await ctx.send("Mention a user/id!")
        count =0
        sql = "SELECT * FROM achievements WHERE user LIKE "+str(user.id)
        query.execute(sql)
        
        myresult = query.fetchall()

        for x in myresult:
            count = count + 1
        if count > 0:
            if name == "all" :
                sql = "DELETE FROM achievements WHERE user = %s"
                user1 = (user.id,)
                query.execute(sql,user1)
                mydb.commit()
                await ctx.send("Successfully Cleared all achievements from "+user.name)
            else:
                sql = "SELECT achievement FROM achievements"
                query.execute(sql)
                temp =[]
                temp = query.fetchall()
                a = str(temp)
                a = a.replace('(','')
                a = a.replace('[','')
                a = a.replace(']','')
                a = a.replace("'",'')
                a = a.replace(')','')
                y = a.split(',')
                for x in y:
                    if name.lower() in x.lower():
                        try :
                            print(x)
                            sql1 = "DELETE FROM achievements WHERE user = %s and achievement like %s"
                            id = (user.id,x)
                            query.execute(sql1,id)
                            mydb.commit()
                            await ctx.send(f"Successfully removed a {x} from "+user.name)
                        except :
                            await ctx.send("Can't find any achievement with that name")
        else:
             await ctx.send(user.name+" has no achievements!")

    @commands.command(aliases=['achieve'])
    @commands.has_permissions(kick_members=True)
    async def achievements(self,ctx,user:discord.Member=None):
        if user == None:
            user = ctx.author
        pfp = user.avatar_url
        count =0
        sql = "SELECT * FROM achievements WHERE user LIKE "+str(user.id)
        query.execute(sql)

        myresult = query.fetchall()

        for x in myresult:
            count = count + 1
        if count == 0:
            await ctx.send("You have no achievements! Grab some!")    
        else :  
            
            ach2.set_author(name=f"> {count} Achievements for {user.name} ({user.id})",icon_url = pfp)
            ach2.set_thumbnail(url="https://cdn.discordapp.com/attachments/746718123406917654/842979300709761024/medal.png")
            for x in myresult:
                a = str(x)
                a = a.replace('(','')
                a = a.replace(')','')
                y = a.split(',')
                

def setup(bot):
  bot.add_cog(achievement(bot))  