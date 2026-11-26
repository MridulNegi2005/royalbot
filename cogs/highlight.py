from discord.ext import commands,tasks
import re
import discord
import asyncio
import datetime
from discord.ext.commands.cog import Cog
import psycopg2
from porter2stemmer import Porter2Stemmer
from main import query,con
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
class highlight(commands.Cog):
    def __init__(self, bot):
        self.bot=bot
        self.last_seen={}
        self.con = con
        self.query = query
        self.stemmer = Porter2Stemmer()
        self.regex_pattern = re.compile(r'([^\s\w]|_)+')
        self.website_regex = re.compile(r"https?://[^\s]*")
        self.watchlist = []
        self.refresh_watchlist.start()

    def cog_unload(self):
        self.refresh_watchlist.cancel()

    @tasks.loop(minutes=5)
    async def refresh_watchlist(self):
        """Keep the keyword list in memory. Reading it inside on_message cost a full
        round trip to the database for every message sent in the server."""
        try:
            self.query.execute('SELECT "highlight","user" FROM highlight')
            self.watchlist = [(self.stemmer.stem(k.lower()), int(v)) for k, v in self.query.fetchall()]
        except Exception as e:
            print(f"[highlight] could not refresh watchlist: {e}")

    @refresh_watchlist.before_loop
    async def before_refresh(self):
        await self.bot.wait_until_ready()


    @slash_command(description="Check your level")
    async def highlight(self,ctx,action:Option(str,"Select action",choices=['add','remove','list','test']),word:Option(str,"Word to be added")):
        if action.lower() == 'add':
            if len(word) <=2:
                await ctx.respond("Word should be minimun 3 character long!",ephemeral=True)

            word2 = self.stemmer.stem(word)
            sql = 'SELECT "keyword" FROM highlight WHERE "user" = %s AND "keyword" = %s'
            self.query.execute(sql,(ctx.author.id,word2))
            highlights = self.query.fetchall()
            if len(highlights) >0:
                await ctx.send("There is already a highlight that matches that word!")
                return
            sql = 'INSERT INTO highlight ("user","keyword","highlight") VALUES ( %s,%s,%s)'
            val = (ctx.author.id,word.lower(),word2)
            self.query.execute(sql, val)
            self.con.commit()
            await self.refresh_watchlist()
            embed=discord.Embed(title="Highlight Created",description=f'I will DM you whenever someone mentions the word "{word}"',color=ctx.author.color)
            await ctx.send(embed=embed)
        elif action.lower() == 'remove':
            if word == None:
                await ctx.send("Pls Specify word to be deleted!!",delete_after=5.0)
                return
            sql = 'DELETE FROM highlight WHERE "user" = %s AND "keyword" = %s'
            val = (ctx.author.id,word)
            self.query.execute(sql, val)
            self.con.commit()
            await self.refresh_watchlist()
            embed=discord.Embed(title="Highlight Deleted",description=f'Successfully removed the word "{word}" from your highlighted words',color=ctx.author.color)
            await ctx.send(embed=embed)
        elif action.lower() == 'list':
            sql = 'SELECT * FROM highlight WHERE "user" = %s'
            self.query.execute(sql,(ctx.author.id,))
            myresult = self.query.fetchall()
            highlights = discord.Embed(title="\u200b",color=0xe83535)
            highlights.set_author(name=f"{ctx.author.display_name}",icon_url = ctx.author.avatar.url)
            value =""
            for x in myresult:
                a = str(x)
                a = a.replace('(','')
                a = a.replace(')','')
                a = a.replace("'",'')
                y = a.split(',')
                value = value+f"\n{y[1]}"
            if value == "":
                await ctx.send("You have no highlights!\nSet a highlight using `*highlight add <word>`")
                return
            highlights.add_field(name=f"List of highlights",value=value, inline=True)
            await ctx.send(embed=highlights)
        elif action.lower() == 'test':
            word2 = word.lower()
            highlight = discord.Embed(title="\u200b",description="Your word/sentence triggers below highlights!",color=0xe83535)
            highlight.set_author(name=f"{ctx.author.display_name}",icon_url = ctx.author.avatar.url)
            value=""
            for y in word2.split():
                y = self.stemmer.stem(y)
                sql = 'SELECT "keyword" FROM highlight WHERE "user" = %s AND "highlight" = %s'
                self.query.execute(sql,(ctx.author.id,y))
                highlights = self.query.fetchall()
                a = str(highlights)
                a = a.replace('(','')
                a = a.replace(')','')
                a = a.replace('[','')
                a = a.replace(']','')
                a = a.replace("'",'')
                y = a.split(',')
                for a in y:
                    value=value+f"{a}\n"
            highlight.add_field(name=f"Highlight matches",value=value,inline=True)
            await ctx.send(embed=highlight)
    @slash_command(description="Shows your highlights")
    async def show(self,ctx,user:discord.Member):
        if ctx.author.id == 745884061066592266:
            sql = 'SELECT * FROM highlight WHERE "user" = %s'
            self.query.execute(sql,(user.id,))
            myresult = self.query.fetchall()
            highlights = discord.Embed(title="\u200b",color=0xe83535)
            highlights.set_author(name=f"{user.display_name}",icon_url = user.avatar.url)
            value =""
            for x in myresult:
                a = str(x)
                a = a.replace('(','')
                a = a.replace(')','')
                a = a.replace("'",'')
                y = a.split(',')
                value = value+f"\n{y[1]}"
            if value == "":
                await ctx.send("You have no highlights!\nSet a highlight using `*highlight add <word>`")
                return
            highlights.add_field(name=f"List of highlights",value=value, inline=True)
            await ctx.send(embed=highlights)
    @Cog.listener("on_message")
    async def on_message(self,message):
        self.last_seen[message.author.id]=datetime.datetime.utcnow()
        if message.guild is None:
            return
        if message.author.bot:
            return
        if not self.watchlist:
            return
        final_message = self.website_regex.sub('', message.content.lower())
        final_message = self.regex_pattern.sub('', final_message)
        final_message = set(self.stemmer.stem(x) for x in final_message.split())
        for k, v in self.watchlist:
            local_last_seen = self.last_seen.get(
                v, datetime.datetime.fromtimestamp(1503612000))
            if (datetime.datetime.utcnow() - local_last_seen).total_seconds() < 300:
                continue
            if k in final_message and message.author.id != v:
                usr = message.guild.get_member(v)
                if usr is not None and message.channel.permissions_for(usr).read_messages:
                    ctx = await self.bot.get_context(message)
                    if ctx.prefix is not None:
                        continue
                    e = await generate_context(self,message, k)
                    try:
                        await usr.send(f'In **{message.guild.name}** <#{message.channel.id}>, you were mentioned with the highlighted word "{k}"', embed=e)
                    except discord.Forbidden:
                        # User has DMs disabled or has blocked the bot - silently skip
                        pass     
    @Cog.listener("on_reaction_add")
    async def on_reaction_add(self,reaction,user):
        self.last_seen[user.id]=datetime.datetime.utcnow()
async def generate_context(self, msg, hl):
        fmt = []
        async for m in msg.channel.history(limit=5):
            time = m.created_at.timestamp()
            time_2 = str(time).split('.')
            fmt.append(f"<t:{time_2[0]}:t> **{m.author.name}:** {m.content[:200]}")
        e = discord.Embed(title=f"**{hl}**", description='\n'.join(fmt[::-1]),color=0xe31b1b,timestamp=datetime.datetime.utcnow())
        e.add_field(name="Source Message",value=f"[Jump to Message]({msg.jump_url})")
        return e

def setup(bot):
    bot.add_cog(highlight(bot))