import discord
from discord.ext import commands
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

class fake(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Send message as a particular user!")
    @discord.default_permissions(manage_messages=True)
    async def fake(self,ctx,user:Option(discord.Member,"User you want to disguise."),message:Option(str,"Message to send!"),channel:Option(discord.TextChannel,"Channel to send message to",required=False,default=None)):
        chan = channel or ctx.channel
        try:
            hooks = await chan.webhooks()
        except discord.Forbidden:
            await ctx.respond("I need the Manage Webhooks permission in that channel.",ephemeral=True)
            return

        webhook = discord.utils.find(lambda w: w.user == ctx.me, hooks)
        if webhook is None:
            webhook = await chan.create_webhook(name="Cosmic Bot")

        await webhook.send(str(message), username=user.display_name,
                           avatar_url=user.display_avatar.url)
        await ctx.respond("Message sent!",ephemeral=True)


def setup(bot):
  bot.add_cog(fake(bot))
