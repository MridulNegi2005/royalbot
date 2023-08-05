from googlesearch import search as search2
from discord.ext import commands,tasks
import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

class Gsearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    class paginator(discord.ui.View):
        def __init__(self,ctx,result):
            self.counter=0
            self.lb=result
            self.ctx=ctx
            super().__init__(timeout=120)
        async def on_timeout(self,button,interaction):
            button.disabled = True
            await interaction.response.edit_message(view=None)
        @discord.ui.button(emoji='<:fast_backward:918877900109914122>', style=discord.ButtonStyle.grey,disabled=True)
        async def first(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.next.disabled=False
            self.last.disabled=False
            self.counter=0
            button.disabled=True
            self.back.disabled=True
            await interaction.response.edit_message(content=self.lb[0],view=self) #This is better this way
        @discord.ui.button(emoji='<:backward:918872031796277320>', style=discord.ButtonStyle.gray,disabled=True)
        async def back(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.next.disabled=False
            self.last.disabled=False
            if self.counter>0:
                self.counter-=1
                if self.counter==0:
                    button.disabled=True
                    self.first.disabled=True
                await interaction.response.edit_message(content=self.lb[self.counter],view=self)
                
        @discord.ui.button(emoji='<:forward:918871999596617790>', style=discord.ButtonStyle.grey)
        async def next(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.back.disabled=False
            self.first.disabled=False
            if self.counter<len(self.lb)-1:
                self.counter+=1
                if self.counter==len(self.lb)-1:
                    button.disabled=True
                    self.last.disabled=True
                await interaction.response.edit_message(content=self.lb[self.counter],view=self)
        @discord.ui.button(emoji="<:fast_forward:918872194099077191>", style=discord.ButtonStyle.gray)
        async def last(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.back.disabled=False
            self.first.disabled=False
            button.disabled=True
            self.next.disabled=True
            await interaction.response.edit_message(content=self.lb[-1],view=self)

    @slash_command(guild_ids=[767591734841835540],description="Search google!")
    async def search(self,ctx,query:Option(str,"The query you want to search.")):
        results = search2(query,stop=10)
        result=[]
        for x in results:
            result.append(x)
        print(result)
        view = self.paginator(ctx,result)
        await ctx.send(result[0],view=view)
def setup(bot):
    bot.add_cog(Gsearch(bot))