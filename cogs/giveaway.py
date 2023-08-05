import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
from main import query,con
import time
from discord.ext import tasks
import requests
import random
import base64,json
import heroku3

KEY='f69844b0-e62b-4448-83d5-914184c2905b'
cloud = heroku3.from_key(KEY)
app = cloud.apps()['royal-disc-bot']
web = app.process_formation()['web']
class Next(discord.ui.Button):
    def __init__(self,item,winners,picture,query,con,ctx):
        self.ctx=ctx
        self.item = item
        self.winners = winners
        self.picture = picture
        self.query = query
        
        self.con = con
        super().__init__(
            label="Next",
            style=discord.enums.ButtonStyle.green,
            custom_id="Next"
        )
    async def callback(self,interaction:discord.Interaction):
        if self.ctx.author.id!=interaction.user.id:
            await interaction.response.send_message(f"You can't setup this giveaway. Command was called by <@{self.ctx.author.id}>",ephemeral=True)
            return
        for x in self.view.children:
            if x.custom_id == '7':
                if x.placeholder != 'Select days':
                    day = x.placeholder
                else:day='0'
            if x.custom_id == '24':
                if x.placeholder != 'Select hours':
                    hour = x.placeholder
                else:hour='0'
            if x.custom_id == '60':
                if x.placeholder != 'Select minutes':
                    min = x.placeholder
                else:min='0'
        time2 = converttime(day+'d '+hour+'h '+min+'m')
        if time2==0:
            await interaction.response.send_message(f'Select duration!',ephemeral=True)
        else:
            channel = interaction.guild.get_channel(783973682137530388)
            embed = discord.Embed(title=self.item.capitalize(),color=0xFF4242)
            embed.add_field(name='Giveaway ends in',value=f'<t:{int(time.time()+time2)}:R> [<t:{int(time.time()+time2)}>]')
            embed.add_field(name='Hosted by',value=f'{interaction.user.mention}',inline=True)
            embed.set_footer(text=f'Winners: {self.winners}')
            if self.picture!=None:
                embed.set_image(url=self.picture.url)
            message = await channel.send(embed=embed,view=enter(self.query,self.con))
            sql = 'INSERT INTO "gconfig" values (%s,%s,%s)'
            val=(int(time.time())+time2,message.id,self.winners)
            self.query.execute(sql,val)
            self.con.commit()
            sql = 'DELETE FROM "giveaway"'
            self.query.execute(sql)
            self.con.commit()
        await interaction.response.edit_message(content="Giveaway successfully created in <#783973682137530388>.\n*Do not create any other giveaway while this is running. Else the current giveaway will stop!*",view=None)
        web.scale(1)
class Dropdown(discord.ui.Select):
    def __init__(self,x,ctx):
        options=[]
        self.ctx=ctx
        if x<25:
            for i in range(x):
                options.append(discord.SelectOption(label=f"{i}"))
        else:
            for i in range(0,x,5):
                options.append(discord.SelectOption(label=f"{i}"))
        if x==7:placeholder='Select days'
        if x==24:placeholder='Select hours'
        if x==60:placeholder='Select minutes'
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options,
            custom_id=str(x)
        )
    async def callback(self,interaction: discord.Interaction):
        if self.ctx.author.id!=interaction.user.id:
            await interaction.response.send_message(f"You can't setup this giveaway. Command was called by <@{self.ctx.author.id}>",ephemeral=True)
            return
        self.placeholder=str(self.values[0])
        await interaction.response.edit_message(view=self.view)

class remove(discord.ui.View):
    def __init__(self,query,con):
        self.query = query
        self.con = con
        super().__init__()
    @discord.ui.button(emoji='<:BS_Tick:881610301152305202>', style=discord.ButtonStyle.green)
    async def yes(self,button,interaction):
        sql = 'DELETE FROM "giveaway" WHERE "user"= %s'
        val=(interaction.user.id,)
        self.query.execute(sql,val)
        self.con.commit()
        await interaction.response.edit_message(content="Your entry has been removed :(",view=None)
    @discord.ui.button(emoji='<:BS_Cross:881610413874225292>', style=discord.ButtonStyle.red)
    async def no(self,button,interaction:discord.Interaction):
        await interaction.response.edit_message(content="Your entry has not been removed :D",view=None)

class Continue(discord.ui.View):
    def __init__(self,player,query,con,ref,ctx):
        self.query = query
        self.con=con
        self.player = player
        self.ref=ref
        self.ctx=ctx
        super().__init__()
    @discord.ui.button(emoji='<:BS_Tick:881610301152305202>', style=discord.ButtonStyle.green)
    async def yes(self,button,interaction:discord.Interaction):
        if self.ref == 'enter':
            sql = 'INSERT INTO "giveaway" ("user","tag") values (%s,%s)'
            val=(interaction.user.id,self.player)
            self.query.execute(sql,val)
            self.con.commit()
            await interaction.response.edit_message(content="Giveaway entry confirmed!",view=None)
        elif self.ref=='end':
            await end2(self.ctx)
            await interaction.response.edit_message(content="Giveaway ended!",view=None)
    @discord.ui.button(emoji='<:BS_Cross:881610413874225292>', style=discord.ButtonStyle.red)
    async def no(self,button,interaction:discord.Interaction):
        if self.ref=='enter':
            await interaction.response.edit_message(content="Giveaway entry failed.Try again",view=None)
        elif self.ref=='end':
            await interaction.response.edit_message(content="Your giveaway is safely running!",view=None)

class tag(discord.ui.Modal):
    def __init__(self,query,con,*args, **kwargs):
        self.query=query
        self.con = con
        super().__init__(
            discord.ui.InputText(
                label="Brawl Stars tag",
                
            ),*args, **kwargs
        )
    async def callback(self, interaction: discord.Interaction):
        try:
            headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjAxM2I2ODNjLTAwN2UtNGI3Yy05ZjI0LWRjYjBiN2QzMGZiMiIsImlhdCI6MTY4NDI5MTY3NCwic3ViIjoiZGV2ZWxvcGVyL2Q5MmEzMjJlLTAzNDQtNWYzMS1jODQ5LWE0YjU0YzQ1MWUxNSIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiNDUuNzkuMjE4Ljc5Il0sInR5cGUiOiJjbGllbnQifV19.IpzvftdcLePP8wVd4D5kgSY-3PNXtvigd584IS42-hCEBi1IAfcup9KC0FcU9_kzQ6n5n9WlgeBc02ZUcJ20Gg"}
            bstag = self.children[0].value
            bstag = bstag.replace('#','')
            response = requests.get(f'https://bsproxy.royaleapi.dev/v1/players/%23{bstag}', headers=headers)
            view = Continue(bstag,self.query,self.con,'enter',self)
            await interaction.response.send_message(f"Are you **{response.json()['name']}**? Click Yes to enter giveaway\n*You can't change your player tag later. You will receive skin on this account only.*",ephemeral=True,view=view)
        except : 
            if response.json()['reason']=='notFound':
                await interaction.response.send_message(f"Incorrect Brawl Stars Tag! Try again",ephemeral=True)
            else:
                await interaction.response.send_message(f"Error. Contact <@745884061066592266> for more guidance!\n Send this screenshot of this error code : {response.json()['reason']}",ephemeral=True)
class enter(discord.ui.View):
    def __init__(self,query,con):
        self.query=query
        self.con=con
        super().__init__(timeout=None)

    @discord.ui.button(label=f"Enter giveaway", style=discord.ButtonStyle.green,custom_id="Enter")
    async def enter2(self, button,interaction:discord.Interaction):
        view = discord.ui.View(timeout=300)
        
        sql = 'SELECT "tag" FROM "giveaway" where "user" =%s'
        val=(interaction.user.id,)
        self.query.execute(sql,val)
        x = self.query.fetchall()
        if len(x)>0:
            await interaction.response.send_message("You have already entered the giveaway!\nWant to remove your entry?",ephemeral=True,view=remove(self.query,self.con))
        else:
            await interaction.response.send_modal(tag(self.query,self.con,title="Enter your Brawl Stars Tag!"))
    @discord.ui.button(emoji='<:info:1110747166928015461>',style=discord.ButtonStyle.blurple,custom_id="Info")
    async def info(self,button,interaction:discord.Interaction):
        sql='SELECT * FROM giveaway'
        query.execute(sql)
        myresult = query.fetchall()
        await interaction.response.send_message(f"**Participants** : {len(myresult)}\nClick [here](https://royal-disc-bot.herokuapp.com/) for timer",ephemeral=True)
class giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.query = query
        self.con = con
    giveaway = SlashCommandGroup("giveaway", "iveaways related commands")

    @giveaway.command(guild_ids=[767591734841835540],default_permission=False,description="Start the giveaway")
    @discord.default_permissions(administrator=True,)
    async def start(self,ctx,item:Option(str,"Item you want to giveaway [Eg. Banana Colt Skin]"),winners:Option(int,'Number of winners for this giveaway.',choices=[1,2,3,4,5]),picture:Option(discord.Attachment,'Add a picture or gif of what you are giveawaying. Adds to the appeal!',required=False,default=None)):
        view = discord.ui.View(timeout=300)
        view.add_item(Dropdown(7,ctx))
        view.add_item(Dropdown(24,ctx))
        view.add_item(Dropdown(60,ctx))
        view.add_item(Next(item,winners,picture,self.query,self.con,ctx))
        await ctx.respond("Enter duration",view=view)
    @giveaway.command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(administrator=True,)
    async def end(self,ctx):
        view = Continue('',self.query,self.con,'end',self)
        await ctx.respond("Do you really want to **end** giveaway?",ephemeral=True,view=view)

    @giveaway.command(guild_ids=[767591734841835540],default_permission=False,description="Get another winner")
    @discord.default_permissions(administrator=True,)
    async def reroll(self,ctx,winner:Option(int,'Number of winners to reroll.',choices=[1,2,3,4,5])):
        entries={}
        sql='SELECT * FROM giveaway'
        query.execute(sql)
        myresult = query.fetchall()
        for x in myresult:
            entries[x[0]]=x[1]
        winners=[]
        print(winner)
        print(len(list(entries.keys())))
        if int(winner)>len(list(entries.keys())):
            winner = len(list(entries.keys()))
        winners= random.sample(list(entries.keys()), int(winner))
        print(winners)
        if len(winners)>1: 
            winner_text="# Rerolled winners:\n"
        else:winner_text="# Rerolled winner:\n"
        counter=0
        winner_text2=''
        for x in winners:
            if counter!=0:
                winner_text+='\n'
                winner_text2+=','
            winner_text2+=f'<@{x}>'
            headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjAxM2I2ODNjLTAwN2UtNGI3Yy05ZjI0LWRjYjBiN2QzMGZiMiIsImlhdCI6MTY4NDI5MTY3NCwic3ViIjoiZGV2ZWxvcGVyL2Q5MmEzMjJlLTAzNDQtNWYzMS1jODQ5LWE0YjU0YzQ1MWUxNSIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiNDUuNzkuMjE4Ljc5Il0sInR5cGUiOiJjbGllbnQifV19.IpzvftdcLePP8wVd4D5kgSY-3PNXtvigd584IS42-hCEBi1IAfcup9KC0FcU9_kzQ6n5n9WlgeBc02ZUcJ20Gg"}
        
            response = requests.get(f'https://bsproxy.royaleapi.dev/v1/players/%23{entries[x]}', headers=headers)
            winner_text+=f'- <@{x}>\n  - Ingame name : {response.json()["name"]}\n  - Brawl Stars Tag : #{entries[x]}'
            counter+=1
        message:discord.Message
        ctx:discord.ApplicationContext
        await ctx.respond(winner_text)
    @commands.command(guild_ids=[767591734841835540],default_permission=False,description="Restart Bot")
    @discord.default_permissions(administrator=True,)
    async def restart(self,ctx):
        await ctx.respond("Restarting bot")
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(enter(self.query,self.con))
async def end2(self):
    sql='SELECT * FROM gconfig'
    query.execute(sql)
    myresult = query.fetchall()
    lines = myresult[-1]
    print(int(lines[1]))
    message = await self.bot.get_channel(783973682137530388).fetch_message(int(lines[1]))
    winner=lines[2]
    embed = message.embeds[0]
    embed:discord.Embed
    embed.set_field_at(index=0,name='Giveaway ended:',value=embed.fields[0].value)
    entries={}
    sql='SELECT * FROM giveaway'
    query.execute(sql)
    myresult = query.fetchall()
    for x in myresult:
        entries[x[0]]=x[1]
    winners=[]
    if int(winner)>len(list(entries.keys())):
        winner = len(list(entries.keys()))
    winners= random.sample(list(entries.keys()), int(winner))
    if len(winners)>1: 
        winner_text="# Congratulations to the winners:\n"
    else:winner_text="# Congratulations to the winner:\n"
    counter=0
    winner_text2=''
    for x in winners:
        if counter!=0:
            winner_text+='\n'
            winner_text2+=','
        winner_text2+=f'<@{x}>'
        headers = {"Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjAxM2I2ODNjLTAwN2UtNGI3Yy05ZjI0LWRjYjBiN2QzMGZiMiIsImlhdCI6MTY4NDI5MTY3NCwic3ViIjoiZGV2ZWxvcGVyL2Q5MmEzMjJlLTAzNDQtNWYzMS1jODQ5LWE0YjU0YzQ1MWUxNSIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiNDUuNzkuMjE4Ljc5Il0sInR5cGUiOiJjbGllbnQifV19.IpzvftdcLePP8wVd4D5kgSY-3PNXtvigd584IS42-hCEBi1IAfcup9KC0FcU9_kzQ6n5n9WlgeBc02ZUcJ20Gg"}
        
        response = requests.get(f'https://bsproxy.royaleapi.dev/v1/players/%23{entries[x]}', headers=headers)
        winner_text+=f'- <@{x}>\n  - Ingame name : {response.json()["name"]}\n  - Brawl Stars Tag : #{entries[x]}'
        counter+=1
    embed.add_field(name="Winners",value=winner_text2)
    await message.edit(embed=embed,view=None)
    message:discord.Message
    await message.reply(winner_text)
    sql = 'DELETE FROM "gconfig"'
    self.query.execute(sql)
    self.con.commit()
    web.scale(0)
def converttime(time):
    ftime=0
    time = time.split()
    units = ["s", "h", "m", "d"]
    for x in time:
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
def setup(bot):
    bot.add_cog(giveaway(bot))