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
        self.con = con#psycopg2.connect('postgres://balxuonbzytruy:2be081d80c21d0869d500f997e19ff385ad5278d020402608fc23ac1f8d71bc6@ec2-52-73-184-24.compute-1.amazonaws.com:5432/des0u9rjq76pq', sslmode='require')
        self.query = query#self.con.cursor()
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
        print(x)
        if len(x)>0:
            star = x[0][1]
            sql = 'UPDATE "starboard" SET "star" = %s where "message"=%s'
            val=(star,payload.message_id)
            self.query.execute(sql,val)
            self.con.commit()
            
            if message.author.id == payload.user_id:
                return
            star +=1
            if star == 3:
                embed = discord.Embed(description=f"{message.content}\n⠀\n⠀\n**[➜ Click to jump to this message]({message.jump_url})**",color=0x2f3136,timestamp=datetime.datetime.utcnow())
                embed.set_author(name=f"{message.author.name}#{message.author.discriminator}",icon_url=message.author.avatar.url)
                embed.set_footer(text=f"Cosmic's Universe",icon_url="https://cdn.discordapp.com/icons/767591734841835540/a_059eba705bfaa741a3483a9c8cb68b58.gif?size=4096")
                starchan = self.bot.get_channel(899903267868389386)
                files=[]
                for x in message.attachments:
                    temp = await x.to_file()
                    files.append(temp)
                starmessage = await starchan.send(f"**{star}** ⭐ **|**<#{message.channel.id}>",embed=embed,files=files)
                sql = 'UPDATE "starboard" SET "star" = %s , "starmessage" = %s WHERE "message" = %s'
                val=(star,starmessage.id,payload.message_id)
                self.query.execute(sql,val)
                self.con.commit()
            elif star>3 :
                id = message.channel.id
                message = await self.bot.get_channel(899903267868389386).fetch_message(x[0][2])
                await message.edit(f"**{star}** ⭐ **|**<#{id}>")
                sql = 'UPDATE "starboard" SET "star" = %s WHERE "message" = %s'
                val=(star,payload.message_id)
                self.query.execute(sql,val)
                self.con.commit()
            else:
                sql = 'UPDATE "starboard" SET "star" = %s WHERE "message" = %s'
                val=(star,payload.message_id)
                self.query.execute(sql,val)
                self.con.commit()
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
        star = x[0][1]
        star -=1
        if star>=3:
            sql = 'UPDATE "starboard" SET "star" = %s where "message"=%s'
            val=(star,payload.message_id)
            self.query.execute(sql,val)
            self.con.commit()
            id = message.channel.id
            message = await self.bot.get_channel(899903267868389386).fetch_message(x[0][2])
            await message.edit(f"**{star}** ⭐ **|**<#{id}>")
        elif star==2:
            sql = 'DELETE from "starboard" where "message"=%s'
            val=(payload.message_id,)
            self.query.execute(sql,val)
            self.con.commit()
            message = await self.bot.get_channel(899903267868389386).fetch_message(x[0][2])
            await message.delete()
def setup(bot):
    bot.add_cog(starboard(bot))