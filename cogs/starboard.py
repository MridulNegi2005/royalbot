from discord.ext import commands,tasks
import re
import discord
from discord.ext.commands.cog import Cog
import psycopg2,datetime
from main import query,con
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
class starboard(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.con = con
        self.query = query
    @Cog.listener("on_raw_reaction_add")
    async def on_reaction_add(self,payload: discord.RawReactionActionEvent):
        guild_id = payload.guild_id
        if guild_id is None:
            return
        if guild_id!=767591734841835540:
            return
        
        if payload.channel_id == 899903267868389386:
            return
        emoji = payload.emoji
        if emoji.name != '⭐':
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if payload.user_id==message.author.id:
            return
        sql = 'SELECT * FROM "starboard" where "message" =%s'
        val=(payload.message_id,)
        self.query.execute(sql,val)
        x = self.query.fetchall()
        if len(x)>0:
            star = x[0][1] + 1
            posted = x[0][2]
            if star == 3:
                embed = discord.Embed(description=f"{message.content}\n⠀\n⠀\n**[➜ Click to jump to this message]({message.jump_url})**",color=0x2f3136,timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"{message.author.name}",icon_url=message.author.display_avatar.url)
                embed.set_footer(text=f"Cosmic's Universe",icon_url="https://cdn.discordapp.com/icons/767591734841835540/a_059eba705bfaa741a3483a9c8cb68b58.gif?size=4096")
                starchan = self.bot.get_channel(899903267868389386)
                files=[]
                for attachment in message.attachments:
                    files.append(await attachment.to_file())
                starmessage = await starchan.send(f"**{star}** ⭐ **|**<#{message.channel.id}>",embed=embed,files=files)
                sql = 'UPDATE "starboard" SET "star" = %s , "starmessage" = %s WHERE "message" = %s'
                val=(star,starmessage.id,payload.message_id)
                self.query.execute(sql,val)
            else:
                sql = 'UPDATE "starboard" SET "star" = %s WHERE "message" = %s'
                val=(star,payload.message_id)
                self.query.execute(sql,val)
                if star>3 and posted:
                    id = message.channel.id
                    posted_message = await self.bot.get_channel(899903267868389386).fetch_message(posted)
                    await posted_message.edit(f"**{star}** ⭐ **|**<#{id}>")
        else:
            star = 1
            sql = 'INSERT INTO "starboard" ("message","star") values (%s,%s)'
            val=(payload.message_id,star)
            self.query.execute(sql,val)
            self.con.commit()
    @Cog.listener("on_raw_reaction_remove")
    async def on_reaction_remove(self,payload: discord.RawReactionActionEvent):
        guild_id = payload.guild_id
        if guild_id is None:
            return
        if guild_id!=767591734841835540:
            return
        if payload.channel_id == 899903267868389386:
            return
        emoji = payload.emoji
        if emoji.name != '⭐':
            return
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
        if payload.user_id==message.author.id:
            return
        sql = 'SELECT * FROM "starboard" where "message" =%s'
        val=(payload.message_id,)
        self.query.execute(sql,val)
        x = self.query.fetchall()
        if not x:
            return
        star = x[0][1] - 1
        starmessage = x[0][2]
        if star>=3:
            sql = 'UPDATE "starboard" SET "star" = %s where "message"=%s'
            val=(star,payload.message_id)
            self.query.execute(sql,val)
            if starmessage:
                id = message.channel.id
                message = await self.bot.get_channel(899903267868389386).fetch_message(starmessage)
                await message.edit(f"**{star}** ⭐ **|**<#{id}>")
        elif star==2:
            sql = 'DELETE from "starboard" where "message"=%s'
            val=(payload.message_id,)
            self.query.execute(sql,val)
            if starmessage:
                message = await self.bot.get_channel(899903267868389386).fetch_message(starmessage)
                await message.delete()
        else:
            sql = 'UPDATE "starboard" SET "star" = %s where "message"=%s'
            self.query.execute(sql,(max(star,0),payload.message_id))
def setup(bot):
    bot.add_cog(starboard(bot))