from discord.ext import commands,tasks
import re
import discord
from discord.ext.commands.cog import Cog
import psycopg2
from main import query,con
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

STARBOARD_CHANNEL = 899903267868389386
TEXT_BUDGET = 3600


def image_names(message):
    return [a.filename for a in message.attachments
            if (a.content_type or "").startswith("image/")]


async def attachment_copies(message):
    """Copies of the attachments, so the card keeps them after the source message
    is deleted. The gallery refers to them by attachment:// name."""
    files = []
    for attachment in message.attachments:
        try:
            files.append(await attachment.to_file())
        except discord.HTTPException:
            pass
    return files


def star_card(message, star, names=()):
    body = message.content
    # Stickers are not attachments, so a sticker-only message used to reach the
    # starboard as an empty card.
    for sticker in message.stickers:
        body += f"\n[sticker: {sticker.name}]({sticker.url})"

    view = discord.ui.DesignerView(timeout=None)
    container = discord.ui.Container(color=0x2f3136)
    container.add_section(
        discord.ui.TextDisplay(
            f"**{star}** ⭐ **|** <#{message.channel.id}>\n**{message.author.name}**"),
        accessory=discord.ui.Thumbnail(message.author.display_avatar.url))
    if body.strip():
        container.add_separator(divider=True)
        container.add_text(body[:TEXT_BUDGET])
    if names:
        container.add_gallery(
            *[discord.MediaGalleryItem(f"attachment://{n}") for n in names[:10]])
    container.add_separator(divider=True)
    container.add_text(
        f"**[➜ Click to jump to this message]({message.jump_url})**\n"
        f"-# Cosmic's Universe")
    view.add_item(container)
    return view


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
        
        if payload.channel_id == STARBOARD_CHANNEL:
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
                starchan = self.bot.get_channel(STARBOARD_CHANNEL)
                files = await attachment_copies(message)
                starmessage = await starchan.send(
                    view=star_card(message,star,image_names(message)),files=files)
                sql = 'UPDATE "starboard" SET "star" = %s , "starmessage" = %s WHERE "message" = %s'
                val=(star,starmessage.id,payload.message_id)
                self.query.execute(sql,val)
            else:
                sql = 'UPDATE "starboard" SET "star" = %s WHERE "message" = %s'
                val=(star,payload.message_id)
                self.query.execute(sql,val)
                if star>3 and posted:
                    posted_message = await self.bot.get_channel(STARBOARD_CHANNEL).fetch_message(posted)
                    # content and embeds are cleared because a V2 message carries
                    # neither, and cards posted before this change still have both.
                    await posted_message.edit(content=None,embeds=[],
                                              view=star_card(message,star,image_names(message)))
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
        if payload.channel_id == STARBOARD_CHANNEL:
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
                posted_message = await self.bot.get_channel(STARBOARD_CHANNEL).fetch_message(starmessage)
                await posted_message.edit(content=None,embeds=[],
                                          view=star_card(message,star,image_names(message)))
        elif star==2:
            sql = 'DELETE from "starboard" where "message"=%s'
            val=(payload.message_id,)
            self.query.execute(sql,val)
            if starmessage:
                message = await self.bot.get_channel(STARBOARD_CHANNEL).fetch_message(starmessage)
                await message.delete()
        else:
            sql = 'UPDATE "starboard" SET "star" = %s where "message"=%s'
            self.query.execute(sql,(max(star,0),payload.message_id))
def setup(bot):
    bot.add_cog(starboard(bot))