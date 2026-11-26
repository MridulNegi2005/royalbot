from googlesearch import search as search2
from discord.ext import commands,tasks
import asyncio
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

    @slash_command(description="Search google!")
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def search(self,ctx,query:Option(str,"The query you want to search.")):
        await ctx.defer()

        # googlesearch scrapes synchronously, so this has to stay off the event loop.
        def run_search():
            return list(search2(query,stop=10,pause=0.5))

        try:
            result = await asyncio.to_thread(run_search)
        except Exception as e:
            await ctx.send_followup(f"Search failed: {e}")
            return
        if not result:
            await ctx.send_followup("No results found.")
            return
        view = self.paginator(ctx,result)
        await ctx.send_followup(result[0],view=view)
def setup(bot):
    bot.add_cog(Gsearch(bot))