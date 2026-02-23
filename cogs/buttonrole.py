import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
import asyncio
import time
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from main import query,con

pronoun=[802048051286900736, 802048082844975154, 884056974818439209]
ping=[802048418834546719, 802048451318775818, 899942347859697675, 802048596689420298, 802048627656622120, 811609004093734962, 899912455088648202, 877427025508450344,1257040770515468289,1257040695399677982]
region=[802048113442947073, 802048172922765361, 802048204400754708, 802048286512513044, 802048242212667393]
emoji={802048051286900736 : '<:he_him:957523777414131743>',802048082844975154 : '<:she_her:957523839133319188>', 884056974818439209 : '<:they_them:957526116392906762>',802048418834546719:'<:chat_healer:957526941093752882> ', 802048451318775818:'<:notification_squad:957526970663571466>', 899942347859697675:'<:update:957526987390455838>', 802048596689420298:'<:poll:957532618348457995>', 802048627656622120:'<:giveaway:957527039483740180>', 811609004093734962:'<:event:957527063387045928>', 899912455088648202:'<:mini_event:957527076892737616>', 877427025508450344:'<:lfg:957527086791295046>',802048113442947073:'<:asia:957526225633566760>', 802048172922765361:'<:africa:957526279639420938>', 802048204400754708:'<:australia:957526532467867729>', 802048286512513044:'<:europe:957526560561311754>', 802048242212667393:'<:america:957526581532823613>',1257040770515468289:'<:views:918875283526942790>',1257040695399677982:'<:warn:918879085789331456>'}

class ClearButton(discord.ui.Button):
    def __init__(self,cat):
        self.cat=cat
        super().__init__(
            label="Clear",
            emoji='<:trashbin:943145548674916363>',
            style=discord.enums.ButtonStyle.red,
            custom_id="Clear"
        )
    async def callback(self,interaction: discord.Interaction):
        for x in self.view.children:
            x.style=discord.ButtonStyle.gray
        self.style=discord.ButtonStyle.red
        await interaction.response.edit_message(view=self.view)
        for x in self.cat:
            role2 = interaction.guild.get_role(x)
            await interaction.user.remove_roles(role2)

class RoleButton(discord.ui.Button):
    def __init__(self, role: discord.Role,style):
        super().__init__(
            emoji=emoji.get(role.id),
            style=style,
            custom_id=str(role.id),
        )

    async def callback(self,interaction: discord.Interaction):
        
        user = interaction.user
        role = interaction.guild.get_role(int(self.custom_id))

        if role is None:
            return

        if role not in user.roles:
            if role.id in pronoun:
                for x in pronoun:
                    role2 = interaction.guild.get_role(x)
                    await user.remove_roles(role2)
                for x in self.view.children:
                    if x.custom_id=="Clear":
                        continue
                    x.style = discord.ButtonStyle.gray
            if role.id in region:
                for x in region:
                    role2 = interaction.guild.get_role(x)
                    await user.remove_roles(role2)
                for x in self.view.children:
                    if x.custom_id=="Clear":
                        continue
                    x.style = discord.ButtonStyle.gray
            self.style = discord.ButtonStyle.blurple
            await user.add_roles(role)
            await interaction.response.edit_message(view=self.view)
        else:
            await user.remove_roles(role)
            self.style=discord.ButtonStyle.gray
            await interaction.response.edit_message(view=self.view)

class Role_cat(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label=f"Pronouns", style=discord.ButtonStyle.grey,custom_id="Pronoun")
    async def pronoun(self, button,interaction):
        view = discord.ui.View(timeout=300)
        for role_id in pronoun:
            role = interaction.guild.get_role(role_id)
            if role in interaction.user.roles:
                style = discord.enums.ButtonStyle.blurple
            else:  
                style = discord.enums.ButtonStyle.grey
            view.add_item(RoleButton(role,style))
        view.add_item(ClearButton(pronoun))
        await interaction.response.send_message("""**__Pronoun Roles__** <a:nyaaCall:942016595495112735>
> Click <:he_him:957523777414131743> if you want **He/Him** pronouns
> 
> Click <:she_her:957523839133319188> if you want **She/Her** pronouns
> 
> Click <:they_them:957526116392906762> if you want **They/Them** pronouns""",view=view,ephemeral=True)

    @discord.ui.button(label=f"Region", style=discord.ButtonStyle.grey,custom_id="Region")
    async def region(self, button,interaction):
        view = discord.ui.View(timeout=120)
        for role_id in region:
            role = interaction.guild.get_role(role_id)
            if role in interaction.user.roles:
                style = discord.enums.ButtonStyle.blurple
            else:
                style = discord.enums.ButtonStyle.grey
            view.add_item(RoleButton(role,style))
        view.add_item(ClearButton(region))
        await interaction.response.send_message("""**__Region Roles__** <:earth:892650878744555521> 
> Click <:asia:957526225633566760> if you belong to Asia
> 
> Click <:africa:957526279639420938> if you belong to Africa 
> 
> Click <:australia:957526532467867729> if you belong to Australia
> 
> Click <:europe:957526560561311754> if you belong to Europe
> 
> Click <:america:957526581532823613> if you belong to North/South America""",view=view,ephemeral=True)

    @discord.ui.button(label=f"Ping", style=discord.ButtonStyle.grey,custom_id="Ping")
    async def ping(self, button,interaction):
        view = discord.ui.View(timeout=120)
        for role_id in ping:
            role = interaction.guild.get_role(role_id)
            if role in interaction.user.roles:
                style = discord.enums.ButtonStyle.blurple
            else:
                style = discord.enums.ButtonStyle.grey
            view.add_item(RoleButton(role,style))
        view.add_item(ClearButton(ping))
        await interaction.response.send_message("""**__Ping Roles__** <:blobpinghammer:942041834228695060> 
> Click <:chat_healer:957526941093752882> if you want to get pinged for reviving the chat.
> `We ping this role when Cosmic Shock comes in the chat. (Not always)`
> 
> Click <:notification_squad:957526970663571466> to get pinged whenever Cosmic Shock uploads a video
> 
> Click <:update:957526987390455838>  to get pinged whenever there's a server update in #◯│server-updates
> 
> Click <:poll:957532618348457995> to get pinged whenever we post a poll
> 
> Click <:giveaway:957527039483740180> to get pinged whenever we host a Giveaway or Lucky Draw
>
> Click <:views:918875283526942790> to get pinged whenever cosmic needs help to make story videos (English)
>
> Click <:warn:918879085789331456> to get pinged whenever cosmic needs help to make story videos (Hindi)
>                                                                             
> Click <:event:957527063387045928>  to get pinged whenever we start a new event.
> `Hosted once in a month`
> 
> Click <:mini_event:957527076892737616> to get pinged whenever we host mini events.
>  `Hosted very frequently`
> 
> Click <:lfg:957527086791295046>  to add the LFG role to yourself. This role can be tagged in #★╰looking-for-group by others looking to find teammates. Use command `*lfg <Text message>`""",view=view,ephemeral=True)

class buttonrole1(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(default_permission=False)
    @discord.default_permissions(administrator=True,)
    async def publish(self,ctx):
        view = Role_cat()
        await ctx.respond("OK!",ephemeral=True)
        await ctx.send("https://cdn.discordapp.com/attachments/861608400243654676/957327286867202078/self_roles.png")
        await ctx.send("<a:redloading:943117026375905280> Click on the buttons below to access the button roles for the particular category.\n<:tick:957332344493178891> In order to get a role, all you have to do is click the button below the message until you see it highlight blue. All the roles you currently have will be shown in blue.\n<:icons_Wrong:957332414957506590> You can remove a role by clicking on the button that is highlighted blue. If the role is removed, button will turn back to grey.",view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(Role_cat())

def setup(bot):
    bot.add_cog(buttonrole1(bot))
