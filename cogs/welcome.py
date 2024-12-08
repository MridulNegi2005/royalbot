from discord.ext import commands
from discord.ext.commands.cog import Cog
import discord
from multicolorcaptcha import CaptchaGenerator
import io
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
import random
import re
import datetime,time,asyncio
class PreVerify(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:White_Tick:1017507109568516147>",label=f"Verify Here", style=discord.ButtonStyle.blurple,custom_id="Preverify")
    async def preverify(self, button,interaction:discord.Interaction):
        number = random.randint(10000,99999)
        embed = discord.Embed(description=f"Please enter the number {number} below and confirm.")
        embed.set_author(name=interaction.message.author.name,icon_url=interaction.message.author.avatar.url)
        embed.add_field(name="Input",value='``` ```')
        await interaction.response.send_message(embed=embed,view=Verify(number),ephemeral=True)
    @discord.ui.button(label=f"Help Me", style=discord.ButtonStyle.red,custom_id="Verify_Help")
    async def verifyhelp(self, button,interaction:discord.Interaction):
        await interaction.response.send_message("Follow the simple,quick guide if you have trouble verifying",file=discord.File(r"./cogs/assests/Verify Help.mp4"),ephemeral=True)
        
class Verify(discord.ui.View):
    def __init__(self,otp):
        super().__init__(timeout=300)
        self.otp = otp
    @discord.ui.button(label=f"1", style=discord.ButtonStyle.blurple,row=0)
    async def one(self, button,interaction:discord.Interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='1'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"2", style=discord.ButtonStyle.blurple,row=0)
    async def two(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='2'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"3", style=discord.ButtonStyle.blurple,row=0)
    async def three(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='3'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"4", style=discord.ButtonStyle.blurple,row=1)
    async def four(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='4'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"5", style=discord.ButtonStyle.blurple,row=1)
    async def five(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='5'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"6", style=discord.ButtonStyle.blurple,row=1)
    async def six(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='6'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"7", style=discord.ButtonStyle.blurple,row=2)
    async def seven(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='7'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"8", style=discord.ButtonStyle.blurple,row=2)
    async def eight(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='8'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"9", style=discord.ButtonStyle.blurple,row=2)
    async def nine(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='9'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"Clear", style=discord.ButtonStyle.red,row=3)
    async def clear(self, button,interaction):
        embed=interaction.message.embeds[0]
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n ```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(label=f"0", style=discord.ButtonStyle.blurple,row=3)
    async def zero(self, button,interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        input+='0'
        embed.clear_fields()
        embed.add_field(name='Input',value=f"```py\n{input}```")
        await interaction.response.edit_message(embed=embed)
    @discord.ui.button(emoji="<:WhiteTick:1006961527737286726>", style=discord.ButtonStyle.green,row=3)
    async def verify(self, button,interaction:discord.Interaction):
        embed=interaction.message.embeds[0]
        input = embed.fields[0].value
        input = re.sub('\D', '', input)
        if self.otp==int(input):
            channel = interaction.guild.get_channel(819183528402223157)
            await interaction.user.add_roles(interaction.guild.get_role(804028250997260308))
            await interaction.response.send_message("You are now verified! Have Fun",ephemeral=True)
            x = datetime.datetime.now(datetime.timezone.utc)
            time_gap = x-interaction.user.joined_at
            time_gap = convert(time_gap.total_seconds())
            embed = discord.Embed(title=f"{interaction.user.name}#{interaction.user.discriminator}'s Verification Result:",description=f"The user successfully verified after {time_gap} later!",color=0xff4242)
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await channel.send(embed=embed)
            channel = interaction.guild.get_channel(814016728950112317)
            await channel.send(content=f"Heya {interaction.user.mention} <a:nyaaCall:942016595495112735> ,\n**Welcome to Cosmic's Universe**! \nCome let's chat here and make some awesome friends <a:CS_BlueHearts:886856930516168705>",delete_after=120)
        else :
            self.one.disabled=True
            self.two.disabled=True
            self.three.disabled=True
            self.four.disabled=True
            self.five.disabled=True
            self.six.disabled=True
            self.seven.disabled=True
            self.eight.disabled=True
            self.nine.disabled=True
            self.zero.disabled=True
            self.clear.disabled=True
            self.verify.disabled=True

            input='Try again!'
            embed.clear_fields()
            embed.add_field(name='Input',value=f"```py\n{input}```")
            await interaction.response.edit_message(embed=embed,view=self)
            
        
class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @slash_command(guild_ids=[767591734841835540],description="Initiate Verification Process here",default_permission=False)
    @discord.default_permissions(administrator=True,)
    async def verify(self,ctx):
        embed=discord.Embed(title="<:verify:1006910059101560873> Verification Required!",description="To prevent server raids and spam accounts, We require you to pass this short verification test.",color=0xff4242)
        await ctx.respond("Alright!",ephemeral=True)
        await ctx.send(embed=embed,view=PreVerify())

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PreVerify())
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
    bot.add_cog(Welcome(bot))