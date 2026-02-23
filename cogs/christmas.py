import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
from discord.ext.commands.cog import Cog
import asyncio
import time
import psycopg2
import os
import datetime
import ast
import random
from PIL import Image, ImageFont, ImageDraw, ImageFilter,ImageOps
import numpy as np
from easy_pil import Editor, Canvas, load_image_async, Font
class christmas(commands.Cog):
    def __init__(self, bot):
        self.cooldown=[]
        self.bot = bot
        self.con = psycopg2.connect(os.getenv('HEROKU_POSTGRES_URI'), sslmode='require')
        self.query = self.con.cursor()
        self.lb1={}
        self.status=True
        self.interval_1=0
        self.interval_2=0
        self.percentage=0
    event = SlashCommandGroup("event", "Event related commands")
    class paginator(discord.ui.View):
        def __init__(self,ctx):
            self.counter=0
            self.lb=[]
            self.ctx=ctx
            
            super().__init__(timeout=120)
        async def on_timeout(self,button,interaction):
            button.disabled = True
            await interaction.response.edit_message(view=button)
        @discord.ui.button(label=f"Back", style=discord.ButtonStyle.red,disabled=True)
        async def back(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.next.style = discord.ButtonStyle.green
            self.next.disabled=False
            if self.counter>0:
                self.counter-=1
                if self.counter==0:
                    button.style = discord.ButtonStyle.red
                    button.disabled=True
                await interaction.response.edit_message(embed=self.lb[self.counter],view=self)
                
        @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
        async def next(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.back.style = discord.ButtonStyle.green
            self.back.disabled=False
            if self.counter<len(self.lb)-1:
                self.counter+=1
                if self.counter==len(self.lb)-1:
                    button.style = discord.ButtonStyle.red
                    button.disabled=True
                await interaction.response.edit_message(embed=self.lb[self.counter],view=self)
    """@slash_command(default_permission=False)
    @permissions.has_role(767591734850879495)
    async def event(self,ctx,value:Option(str,"Start/End Event",choices=["Start","End"])):
        if value=="Start":
            self.status=True
            await ctx.respond("Event started and commands enabled!",ephemeral=True)
        if value=="End":
            self.status=False
            await ctx.respond("Event ended and commands disabled!!",ephemeral=True)
    @slash_command(default_permission=False)
    @permissions.has_role(767591734850879495)
    async def reset(self,ctx,user:Option(discord.Member,"User whose xp you want to reset.",required=False,Default=None)):
        if user == None:
            sql = 'SELECT * FROM christmas'
            self.query.execute(sql)
            myresult = self.query.fetchall()
            users=[]
            for x in myresult:
                a = str(x)
                y = ast.literal_eval(a)
                users.append(y[0])
            for x in users:
                sql = 'DELETE FROM christmas WHERE "user" = %s'
                val=(x,)
                self.query.execute(sql,val)
                self.con.commit()
                await ctx.respond("Resetted xp for whole server!")
        else:
            sql ='DELETE FROM christmas WHERE "user" = %s'
            val=(user.id,)
            self.query.execute(sql,val)
            self.con.commit()
            await ctx.respond(f"Resetted xp for {user.display_name}!")
    @slash_command(description="Check your level for christmas event")
    @permissions.has_role(767591734850879495)
    async def level(self,ctx,user:Option(discord.Member,"Member whose rank you wanted to see",required=False,default=None)):
        if user==None:user=ctx.author
        if self.status==False:
            await ctx.respond("You saw a secret command!",ephemeral=True)
            return
        sql = 'SELECT * FROM christmas'
        self.query.execute(sql)
        myresult = self.query.fetchall()
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            self.lb1[y[0]]=int(y[1])
        self.lb1 = {k: v for k, v in sorted(self.lb1.items(), key=lambda item: item[1],reverse=True)}
        rank=0
        self.interval_1=0
        self.interval_2=0
        self.percentage = 0
        xp = int(self.lb1.get(user.id))
        if xp < 1000:
            self.percentage = (xp/1000)*100
            self.interval_1=0
            self.interval_2=1000
        else:
            self.interval_1= (xp//1000)*1000
            self.interval_2 = self.interval_1+1000
            self.percentage = ((xp-self.interval_1)/1000)*100
        for x in self.lb1:
            rank+=1
            if x == user.id:break

        background = Editor("cogs/assests/c.jpg")
        avatar = await load_image_async(str(user.avatar.url))
        avatar = Editor(avatar).resize((177, 177)).circle_image()
        overlay = Editor("cogs/assests/overlay.png")
        overlay = Editor(overlay).resize((230, 230))
        poppins = Font(path="cogs/assests/FredokaOne-Regular.ttf",size=50)
        poppins_small = Font(path="cogs/assests/LemonMilk.ttf",size=30)

        square = Canvas((500, 500), "#06FFBF")
        square = Editor(square)
        square.rotate(30, expand=True)

        background.paste(square.image, (600, -250))
        background.paste(avatar.image, (35, 45))
        background.paste(overlay.image, (10, 15))

        background.rectangle((220, 200), width=720, height=40, fill="white", radius=20)
        background.bar(
            (220, 200),
            max_width=720,
            height=40,
            percentage=self.percentage,
            fill="#FF4242",
            radius=20,
        )
        background.text((250, 40), str(user), font=poppins, color="white")

        background.rectangle((230, 100), width=700, height=2, fill="#17F3F6")
        background.text(
            (250, 120),
            f" XP : {xp}",
            font=poppins_small,
            color="white",
        )
        background.text(
            (800, 120),
            f"Rank : {rank}",
            font=poppins_small,
            color="white",
        )
        background.text(
            (230, 165),
            f" {self.interval_1}",
            font=poppins_small,
            color="white",
        )
        background.text(
            (850, 165),
            f" {self.interval_2}",
            font=poppins_small,
            color="white",
        )

        file = discord.File(fp=background.image_bytes,filename="Level.png")
        await ctx.respond(file=file)"""

    @event.command()
    @permissions.has_role(767591734850879495)
    async def leaderboard(self,ctx):
        if self.status==False:
            await ctx.respond("You saw a secret command!",ephemeral=True)
            return
        sql = 'SELECT * FROM christmas'
        self.query.execute(sql)
        myresult = self.query.fetchall()
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            self.lb1[y[0]]=int(y[1])
        self.lb1 = {k: v for k, v in sorted(self.lb1.items(), key=lambda item: item[1],reverse=True)}
        desc=[""]
        first=0
        count=0
        rank=0
        view=self.paginator(ctx)
        for x in self.lb1:
            rank+=1
            if x == ctx.author.id:break
        for i in self.lb1.keys():
            try:
                user = ctx.guild.get_member(i)
                name = f"**{user.display_name}**"
            except:name=f"**User not in the server**({i})"
            if count>=10:
                desc.append("")
                count = 0
            desc[int(first/10)]+=f"❯`{int(first+1)}` {name}\n　└─{self.lb1[i]}\n"
            count+=1
            first+=1
        for i in desc:
            embed = discord.Embed(title="Leaderboard",description=i,timestamp=datetime.datetime.utcnow())
            embed.set_footer(text=f"Your position : {rank}",icon_url=ctx.author.avatar.url)
            view.lb.append(embed)
        await ctx.send(embed=view.lb[0],view=view)

    @Cog.listener("on_message")
    async def on_message(self,message):
        if self.status==False:
            return
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.guild.id != 767591734841835540:
            return
        if message.channel.id != 814016728950112317 and message.channel.id != 883563221947125770:
            return
        if message.author.id not in self.cooldown:
            xp_gain = random.randint(6,12)
            sql = 'SELECT "xp" FROM "christmas" where "user" =%s'
            val=(message.author.id,)
            self.query.execute(sql,val)
            x = self.query.fetchall()
            if len(x)>0:
                xp = x[0][0]
                xp=xp+xp_gain
                sql = 'UPDATE "christmas" SET "xp" = %s where "user"=%s'
                val=(xp,message.author.id)
                self.query.execute(sql,val)
                self.con.commit()
            else:
                xp= xp_gain
                sql = 'INSERT INTO "christmas" ("user","xp") values (%s,%s)'
                val=(message.author.id,xp)
                self.query.execute(sql,val)
                self.con.commit()
            self.cooldown.append(message.author.id)
            await asyncio.sleep(60)
            self.cooldown.remove(message.author.id)
def setup(bot):
    bot.add_cog(christmas(bot))