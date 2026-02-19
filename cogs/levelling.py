import schedule
import discord
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
from discord.ext import commands
from discord.ext.commands.cog import Cog
import asyncio
import time
import aiopg
import datetime
import ast
import random
import math
from PIL import Image, ImageFont, ImageDraw, ImageFilter,ImageOps
import numpy as np
import io,requests
from easy_pil import Editor, Canvas, load_image_async, Font,Text

# ─── DATABASE CONFIG ─────────────────────────────────────────
DSN = "dbname=postgres user=postgres password=CEBYsadMjKqaCJJjGbUYY2gf5UxF2fGxAhDrGcDD host=35.223.191.80 port=5432 sslmode=require"
"""
625 : Trophy Road Brawler
2500 : Rare Brawler
5625 : Super Rare Brawler
10000 : Epic Brawler
22500 : Mythic Brawler
40000 : Legendary Brawler
62500 : Chromatic Brawler"""

class Themes(discord.ui.Button):
    def __init__(self,user,name,id,cog):
        self.user=user
        self.cog=cog
        super().__init__(
            label=name,
            style=discord.enums.ButtonStyle.blurple,
            custom_id=id
        )
    async def callback(self,interaction: discord.Interaction):
        try:
            await self.cog._db_execute(
                'UPDATE "levelling" SET "theme" = %s where "user"=%s',
                (int(self.custom_id), self.user.id)
            )
            await interaction.response.send_message(f"Changed your theme to {self.label}!",ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error updating theme: {e}",ephemeral=True)

class levelling(commands.Cog):
    @slash_command(guild_ids=[767591734841835540], description="Set your theme for level card!")
    async def theme(self, ctx):
        """
        Combined theme command for testing: shows rank cards, current level, and theme/overlay buttons.
        Only available to admins for testing.
        """
        # Send the rank cards image (ephemeral)
        await ctx.respond(file=discord.File('cogs/assests/Rank_Cards.png'), ephemeral=False)

        # Fetch user XP and theme info
        try:
            myresult = await self._db_fetchall('SELECT * FROM levelling')
        except Exception as e:
            await ctx.send_followup(f"Database error: {e}")
            return
        lb1 = {}
        theme = 1
        overlay = "True"
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            lb1[y[0]] = int(y[1])
            if y[0] == ctx.author.id:
                theme = y[2]
                overlay = y[3]
        xp = int(lb1.get(ctx.author.id, 0))
        level = int(0.2 * (math.sqrt(xp)))

        # Compose level message
        msg = f"Your current level: **{level}** | XP: **{xp}**\nSelect a theme or toggle overlay below."

        # Theme requirements
        theme_defs = [
            (1, "Tech", 0),
            (2, "Mint", 5),
            (3, "Cosmos", 10),
            (4, "Red Metal", 15),
            (5, "City", 20),
        ]

        class ThemeTestView(discord.ui.View):
            def __init__(self, user_id, current_theme, current_overlay, user_level, user_xp, ctx, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.user_id = user_id
                self.current_theme = current_theme
                self.current_overlay = current_overlay
                self.user_level = user_level
                self.user_xp = user_xp
                self.ctx = ctx
                # Add theme buttons
                for tid, tname, treq in theme_defs:
                    if user_level >= treq:
                        style = discord.ButtonStyle.success if current_theme == tid else discord.ButtonStyle.danger
                        disabled = False
                    else:
                        style = discord.ButtonStyle.secondary
                        disabled = True
                    self.add_item(self.ThemeButton(tid, tname, style, disabled, self))
                # Overlay toggle button
                overlay_style = discord.ButtonStyle.success if current_overlay == "True" else discord.ButtonStyle.danger
                self.add_item(self.OverlayButton(current_overlay, overlay_style, self))

            class ThemeButton(discord.ui.Button):
                def __init__(self, theme_id, theme_name, style, disabled, parent_view):
                    super().__init__(
                        label=theme_name,
                        style=style,
                        custom_id=f"theme_{theme_id}",
                        disabled=disabled
                    )
                    self.theme_id = theme_id
                    self.parent_view = parent_view
                async def callback(self, interaction: discord.Interaction):
                    if interaction.user.id != self.parent_view.user_id:
                        await interaction.response.send_message("You can't use this!", ephemeral=True)
                        return
                    # Update theme in DB
                    try:
                        await self.parent_view.ctx.cog._db_execute(
                            'UPDATE "levelling" SET "theme" = %s WHERE "user"=%s',
                            (self.theme_id, interaction.user.id)
                        )
                    except Exception as e:
                        await interaction.response.send_message(f"DB error: {e}", ephemeral=True)
                        return
                    # Update view state
                    self.parent_view.current_theme = self.theme_id
                    # Regenerate level card image
                    file = await generate_level_card(
                        interaction.user,
                        self.parent_view.user_xp,
                        self.parent_view.user_level,
                        self.theme_id,
                        self.parent_view.current_overlay
                    )
                    # Rebuild view
                    new_view = ThemeTestView(
                        self.parent_view.user_id,
                        self.theme_id,
                        self.parent_view.current_overlay,
                        self.parent_view.user_level,
                        self.parent_view.user_xp,
                        self.parent_view.ctx
                    )
                    # Send new message as a reply to the previous message, then delete old
                    await interaction.channel.send(
                        content=f"Theme changed to **{self.label}**!\nYour current level: **{self.parent_view.user_level}** | XP: **{self.parent_view.user_xp}**",
                        view=new_view,
                        file=file,
                        reference=interaction.message
                    )
                    try:
                        await interaction.message.delete()
                    except Exception:
                        pass

            class OverlayButton(discord.ui.Button):
                def __init__(self, overlay_state, style, parent_view):
                    label = "Overlay: ON" if overlay_state == "True" else "Overlay: OFF"
                    super().__init__(
                        label=label,
                        style=style,
                        custom_id="overlay_toggle"
                    )
                    self.parent_view = parent_view
                async def callback(self, interaction: discord.Interaction):
                    if interaction.user.id != self.parent_view.user_id:
                        await interaction.response.send_message("You can't use this!", ephemeral=True)
                        return
                    # Toggle overlay in DB
                    new_state = "False" if self.parent_view.current_overlay == "True" else "True"
                    try:
                        await self.parent_view.ctx.cog._db_execute(
                            'UPDATE "levelling" SET "overlay" = %s WHERE "user"=%s',
                            (new_state, interaction.user.id)
                        )
                    except Exception as e:
                        await interaction.response.send_message(f"DB error: {e}", ephemeral=True)
                        return
                    # Update view state
                    self.parent_view.current_overlay = new_state
                    # Regenerate level card image
                    file = await generate_level_card(
                        interaction.user,
                        self.parent_view.user_xp,
                        self.parent_view.user_level,
                        self.parent_view.current_theme,
                        new_state
                    )
                    # Rebuild view
                    overlay_style = discord.ButtonStyle.success if new_state == "True" else discord.ButtonStyle.danger
                    new_view = ThemeTestView(
                        self.parent_view.user_id,
                        self.parent_view.current_theme,
                        new_state,
                        self.parent_view.user_level,
                        self.parent_view.user_xp,
                        self.parent_view.ctx
                    )
                    # Send new message as a reply to the previous message, then delete old
                    await interaction.channel.send(
                        content=f"Overlay toggled to **{'ON' if new_state == 'True' else 'OFF'}**.\nYour current level: **{self.parent_view.user_level}** | XP: **{self.parent_view.user_xp}**",
                        view=new_view,
                        file=file,
                        reference=interaction.message
                    )
                    try:
                        await interaction.message.delete()
                    except Exception:
                        pass

        # Helper to generate the level card image (like /level)
        async def generate_level_card(user, xp, level, theme, overlay_option):
            # This logic is adapted from the level command
            from easy_pil import Editor, Canvas, load_image_async
            from PIL import Image, ImageFont, ImageDraw
            import io
            # Theme backgrounds/colors
            backgrounds = {
                1: ("cogs/assests/background1.png", '#17F3F6', "cogs/assests/overlay1.png", '#ffffff'),
                2: ("cogs/assests/background2.png", '#ff1f97', "cogs/assests/overlay1.png", '#11ebf2'),
                3: ("cogs/assests/background3.png", '#ff1f97', "cogs/assests/overlay1.png", '#11ebf2'),
                4: ("cogs/assests/background4.png", '#ff5145', "cogs/assests/overlay1.png", '#11ebf2'),
                5: ("cogs/assests/background5.png", '#ff1f97', "cogs/assests/overlay2.png", '#11ebf2'),
            }
            bg_path, bcolor, overlay_path, name_color = backgrounds.get(theme, backgrounds[1])
            background = Editor(bg_path)
            overlay = Editor(overlay_path)
            avatar = await load_image_async(str(user.display_avatar.url))
            avatar = Editor(avatar).resize((177, 177)).circle_image()
            overlay = Editor(overlay).resize((230, 230))
            square = Canvas((500, 500), "#06FFBF")
            square = Editor(square)
            square.rotate(30, expand=True)
            background.paste(square.image, (600, -250))
            background.paste(avatar.image, (38, 40))
            if overlay_option == "True":
                background.paste(overlay.image, (10, 15))
            background.rectangle((265, 210), width=710, height=30, fill="white", radius=20)
            # Progress bar
            if level == 0:
                interval_1 = 0
                interval_2 = (int((level + 1) * 5) ** 2)
                percentage = (xp / 75) * 100
            else:
                interval_1 = (int((level) * 5) ** 2)
                interval_2 = (int((level + 1) / 0.2) ** 2)
                xp_diff = (int((level + 1) * 5) ** 2) - (int((level) / 0.2) ** 2)
                percentage = ((xp - interval_1) / xp_diff) * 100
            background.bar((265, 210), max_width=710, height=30, percentage=percentage, fill="#FF4242", radius=20)
            background.rectangle((240, 20), width=5, height=211, fill=bcolor)
            background = Image.open(background.image_bytes)
            draw = ImageDraw.Draw(background)
            big_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 60)
            xp_font = ImageFont.FreeTypeFont("cogs/assests/LemonMilk.ttf", 25)
            small_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 30)
            name_font = ImageFont.FreeTypeFont("cogs/assests/seguiemj.ttf", 35)
            # Level, rank, XP text
            text_bbox = draw.textbbox((0, 0), str(level), font=big_font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
            offset_x = 1000 - 15 - text_size[0]
            offset_y = 10
            draw.text((offset_x, offset_y), str(level), font=big_font, fill="#11ebf2")
            text_bbox = draw.textbbox((0, 0), "LEVEL", font=small_font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
            offset_x -= text_size[0] + 5
            draw.text((offset_x, offset_y + 27), "LEVEL", font=small_font, fill="#11ebf2")
            text_bbox = draw.textbbox((0, 0), f"/ {human_format(interval_2)} XP", font=small_font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
            offset_x = 980 - text_size[0]
            offset_y = 210 - text_size[1] - 10
            draw.text((offset_x, offset_y), f"/ {human_format(interval_2)} XP", font=xp_font, fill="#727175")
            text_bbox = draw.textbbox((0, 0), f"{human_format(xp)}", font=xp_font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
            offset_x -= text_size[0] + 8
            draw.text((offset_x, offset_y), f"{human_format(xp)}", font=xp_font, fill="#fff")
            text_bbox = draw.textbbox((0, 0), user.name, font=name_font)
            text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
            offset_x = 265
            offset_y = 210 - text_size[1] - 5
            draw.text((offset_x, offset_y), user.name, font=name_font, fill='#FF4242', stroke_width=1, stroke_fill='#FF4242')
            with io.BytesIO() as image_binary:
                background.save(image_binary, 'PNG')
                image_binary.seek(0)
                return discord.File(fp=image_binary, filename='Level.png')

        # Attach context to view for DB access
        view = ThemeTestView(ctx.author.id, theme, overlay, level, xp, ctx)
        # Generate initial level card image
        file = await generate_level_card(ctx.author, xp, level, theme, overlay)
        await ctx.send_followup(content=msg, view=view, file=file, ephemeral=False)
    def __init__(self, bot):
        self.cooldown=[]
        self.bot = bot
        self.pool = None  # aiopg connection pool, created in _ensure_pool
        self.background=None
        self.bcolor = ''
        self.overlay = None
        self.name_color = ''
        self.overlay_option="False"
        self.lb1={}
        self.level=0
        self.interval_1=0
        self.interval_2=0
        self.percentage=0
        self.blacklist=[767591735295213580,871803124376043520,832169387150671912,793866893097828353,783352677253644299,767591735693410370,888410427896242194,767591735559716907,767591735559716910,861608400243654676,861608481157283860,767644851750699008,899183274717511690,785822879836274688,768467599562113085,843859706022723584,843860718268448778]
        self.autorole= {625 : 821049550801207326,
                        2500 : 767945159525531649,
                        5625 : 767945807109816341,
                        10000 : 772357207592796170,
                        22500 : 772357373771382794,
                        40000 : 772665309021995018,
                        62500 : 805778791586070538}

    # ─── DATABASE HELPERS (aiopg) ────────────────────────────

    async def _ensure_pool(self):
        """Create the connection pool if it doesn't exist or is closed."""
        if self.pool is None or self.pool.closed:
            self.pool = await aiopg.create_pool(DSN, minsize=1, maxsize=5)
            print("[levelling] DB connection pool created.")

    async def _db_execute(self, sql, params=None):
        """Execute a query (INSERT/UPDATE/DELETE). Crash-proof."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)

    async def _db_fetchone(self, sql, params=None):
        """Execute a query and return one row. Crash-proof."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchone()

    async def _db_fetchall(self, sql, params=None):
        """Execute a query and return all rows. Crash-proof."""
        await self._ensure_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, params)
                return await cur.fetchall()

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        if self.pool and not self.pool.closed:
            self.pool.close()
            print("[levelling] DB connection pool closed.")

    @Cog.listener("on_ready")
    async def on_ready(self):
        """Create pool when bot is ready."""
        await self._ensure_pool()
    #theme = SlashCommandGroup("theme", "Themes related commands")
    class paginator(discord.ui.View):
        def __init__(self,ctx):
            self.counter=0
            self.lb=[]
            self.ctx=ctx
            
            super().__init__()
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
            await interaction.response.edit_message(embed=self.lb[0],view=self)
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
                await interaction.response.edit_message(embed=self.lb[self.counter],view=self)
                
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
                await interaction.response.edit_message(embed=self.lb[self.counter],view=self)
        @discord.ui.button(emoji="<:fast_forward:918872194099077191>", style=discord.ButtonStyle.gray)
        async def last(self,button,interaction):
            if interaction.user.id != self.ctx.author.id:
                await interaction.response.send_message("You can't use this!",ephemeral=True)
                return
            self.back.disabled=False
            self.first.disabled=False
            button.disabled=True
            self.next.disabled=True
            self.counter=len(self.lb)-1
            await interaction.response.edit_message(embed=self.lb[-1],view=self)

    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def add_xp(self,ctx,user:Option(discord.Member,"User to give xp to"),xp:Option(int,"Amount of xp to be added")):
        try:
            x = await self._db_fetchall(
                'SELECT "xp" FROM "levelling" where "user" =%s',
                (user.id,)
            )
            xp_gain = xp
            if len(x)>0:
                xp = x[0][0]
                xp=xp+xp_gain
                await self._db_execute(
                    'UPDATE "levelling" SET "xp" = %s,"theme" = %s,"overlay"=%s where "user"=%s',
                    (xp,1,"True",user.id)
                )
            else:
                xp= xp_gain
                await self._db_execute(
                    'INSERT INTO "levelling" ("user","xp","theme","overlay") values (%s,%s,%s,%s)',
                    (user.id,xp,1,"True")
                )
            await ctx.respond(f"Successfully added {xp_gain} xp to {user.mention}. He/She now has {xp} xp!")
        except Exception as e:
            await ctx.respond(f"Database error: {e}")

    @slash_command(guild_ids=[767591734841835540],default_permission=False)
    @discord.default_permissions(ban_members=True,)
    async def remove_xp(self,ctx,user:Option(discord.Member,"User to remove xp from"),xp:Option(int,"Amount of xp to be subtracted")):
        try:
            x = await self._db_fetchall(
                'SELECT "xp" FROM "levelling" where "user" =%s',
                (user.id,)
            )
            xp_loss = xp
            if len(x)>0:
                xp = x[0][0]
                if xp>xp_loss:
                    xp=xp-xp_loss
                else:
                    xp_loss=xp
                    xp=0
                await self._db_execute(
                    'UPDATE "levelling" SET "xp" = %s,"theme" = %s,"overlay"=%s where "user"=%s',
                    (xp,1,"True",user.id)
                )
                await ctx.respond(f"Successfully removed {xp_loss} xp from {user.mention}. He/She now has {xp} xp!")
            else:
                await ctx.respond(f"{user.mention} has no xp!")
        except Exception as e:
            await ctx.respond(f"Database error: {e}")

    '''@theme.command(description="List all the themes with their requirements.")
    async def list(self,ctx):
        await ctx.respond(file=discord.File('cogs/assests/Rank_Cards.png'),ephemeral=True)

    @theme.command(description="Set a theme unlocked for you!")
    async def set(self,ctx):
        sql = 'SELECT * FROM levelling'
        self.query.execute(sql)
        myresult = self.query.fetchall()
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            self.lb1[y[0]]=int(y[1])
        self.lb1 = {k: v for k, v in sorted(self.lb1.items(), key=lambda item: item[1],reverse=True)}
        xp = int(self.lb1.get(ctx.author.id))
        themes={}
        level=int(0.2*(math.sqrt(xp)))
        for x in ctx.user.roles:
            if x.id == 767591734850879495:
                level = 50
                break
        if level >= 20:
            themes[5] = "City"
        if level >= 15:
            themes[4] = "Red Metal"
        if level >= 10:
            themes[3] = "Cosmos"
        if level >= 5:
            themes[2] = "Mint"
        if level > 0:
            themes[1] = "Tech"
        view = discord.ui.View()
        for x in themes.keys():
            view.add_item(Themes(ctx.user,themes[x],str(x),self.query,self.con))
        await ctx.respond("Select your theme below :",view=view)

    @theme.command(description="Toggle pfp overlay in rank card")
    async def overlay(self,ctx,value:Option(str,"Choose respectively!",choices=["Enable","Disable"])):
        await ctx.respond(f"Overlay {value}d!")
        if value=="Enable":value="True"
        else:value="False"
        sql = 'UPDATE "levelling" SET "overlay" = %s where "user"=%s'
        val=(value,ctx.author.id)
        self.query.execute(sql,val)
        self.con.commit()'''
    @slash_command(guild_ids=[767591734841835540],description="Check your level")
    async def level(self,ctx,user:Option(discord.Member,"Member whose rank you wanted to see",required=False,default=None)):
        await ctx.defer()
        if user==None:user=ctx.author
        try:
            myresult = await self._db_fetchall('SELECT * FROM levelling')
        except Exception as e:
            await ctx.send_followup(f"Database error: {e}")
            return
        theme = 0
        self.overlay_option="False"
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            if y[0] == user.id:
                theme=y[2]
                self.overlay_option=y[3]
            self.lb1[y[0]]=int(y[1])
        self.lb1 = {k: v for k, v in sorted(self.lb1.items(), key=lambda item: item[1],reverse=True)}
        rank=0
        
        self.interval_1=0
        self.interval_2=0
        self.percentage = 0
        xp = int(self.lb1.get(user.id))
        self.level = int(0.2*(math.sqrt(xp)))

        if self.level == 0:
            self.percentage = (xp/75)*100
            self.interval_1=0
            self.interval_2=(int((self.level +1)*5)**2)
        else:
            xp_diff = (int((self.level +1)*5)**2)-(int((self.level)/ 0.2)**2)
            self.interval_1= (int((self.level)*5)**2)
            self.interval_2 = (int((self.level +1)/ 0.2)**2)
            self.percentage = ((xp-self.interval_1)/xp_diff)*100

        for x in self.lb1:
            rank+=1
            if x == user.id:break
        if theme ==1 :
            self.background = Editor("cogs/assests/background1.png")
            self.bcolor = '#17F3F6'
            self.overlay = Editor("cogs/assests/overlay1.png")
            self.name_color = '#ffffff'
        if theme ==2 :
            self.background = Editor("cogs/assests/background2.png")
            self.bcolor = '#ff1f97'
            self.overlay = Editor("cogs/assests/overlay1.png")
            self.name_color = '#11ebf2'
        if theme ==3 :
            self.background = Editor("cogs/assests/background3.png")
            self.bcolor = '#ff1f97'
            self.overlay = Editor("cogs/assests/overlay1.png")
            self.name_color = '#11ebf2'
        if theme ==4 :
            self.background = Editor("cogs/assests/background4.png")
            self.bcolor = '#ff5145'
            self.overlay = Editor("cogs/assests/overlay1.png")
            self.name_color = '#11ebf2'
        if theme ==5 :
            self.background = Editor("cogs/assests/background5.png")
            self.bcolor = '#ff1f97'
            self.overlay = Editor("cogs/assests/overlay2.png")
            self.name_color = '#11ebf2'

        avatar = await load_image_async(str(user.display_avatar.url))
        avatar = Editor(avatar).resize((177, 177)).circle_image()
        self.overlay =Editor(self.overlay).resize((230, 230))

        square = Canvas((500, 500), "#06FFBF")
        square = Editor(square)
        square.rotate(30, expand=True)

        self.background.paste(square.image, (600, -250))

        self.background.paste(avatar.image, (38, 40))
        if self.overlay_option == "True":
            self.background.paste(self.overlay.image, (10, 15))

        self.background.rectangle((265, 210), width=710, height=30, fill="white", radius=20)
        self.background.bar(
            (265, 210),
            max_width=710,
            height=30,
            percentage=self.percentage,
            fill="#FF4242",
            radius=20,)

        self.background.rectangle((240, 20), width=5, height=211, fill=self.bcolor)

        #Progress bar positions
        bar_offset_x = 265
        bar_offset_y = 210
        bar_offset_x_1 = 970
        bar_offset_y_1 = 240

        self.background = Image.open(self.background.image_bytes)
        draw = ImageDraw.Draw(self.background)
        # Working with Fonts
        big_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 60)
        xp_font = ImageFont.FreeTypeFont("cogs/assests/LemonMilk.ttf", 25)
        small_font = ImageFont.FreeTypeFont("cogs/assests/ABeeZee-Regular.otf", 30)
        name = ImageFont.FreeTypeFont("cogs/assests/seguiemj.ttf", 35)

        # Placing Right Upper Part
        text_bbox = draw.textbbox((0, 0), str(self.level), font=big_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x = 1000 - 15 - text_size[0]
        offset_y = 10
        draw.text((offset_x, offset_y), str(self.level), font=big_font, fill="#11ebf2")

        text_bbox = draw.textbbox((0, 0), "LEVEL", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 5
        draw.text((offset_x, offset_y + 27), "LEVEL", font=small_font, fill="#11ebf2")

        text_bbox = draw.textbbox((0, 0), f"#{rank}", font=big_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 15
        draw.text((offset_x, offset_y), f"#{rank}", font=big_font, fill="#fff")

        text_bbox = draw.textbbox((0, 0), "RANK", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 5
        draw.text((offset_x, offset_y + 27), "RANK", font=small_font, fill="#fff")

        text_bbox = draw.textbbox((0, 0), f"/ {human_format(self.interval_2)} XP", font=small_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])

        offset_x = 980 - text_size[0]
        offset_y = bar_offset_y - text_size[1] - 10

        draw.text((offset_x, offset_y), f"/ {human_format(self.interval_2)} XP", font=xp_font, fill="#727175")

        text_bbox = draw.textbbox((0, 0), f"{human_format(xp)}", font=xp_font)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
        offset_x -= text_size[0] + 8
        draw.text((offset_x, offset_y), f"{human_format(xp)}", font=xp_font, fill="#fff")


        # Name
        text_bbox = draw.textbbox((0, 0), user.name, font=name)
        text_size = (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])

        offset_x = bar_offset_x
        offset_y = bar_offset_y - text_size[1] - 5
        draw.text((offset_x, offset_y),user.name, font=name, fill='#FF4242',stroke_width=1, stroke_fill='#FF4242')


        with io.BytesIO() as image_binary:
            self.background.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send_followup(file=discord.File(fp=image_binary, filename='Level.png'))

    @slash_command(guild_ids=[767591734841835540])
    async def leaderboard(self,ctx):
        await ctx.defer()
        try:
            myresult = await self._db_fetchall('SELECT * FROM levelling')
        except Exception as e:
            await ctx.send_followup(f"Database error: {e}")
            return
        for x in myresult:
            a = str(x)
            y = ast.literal_eval(a)
            self.lb1[y[0]]=int(y[1])
        self.lb1 = {k: v for k, v in sorted(self.lb1.items(), key=lambda item: item[1],reverse=True)}
        desc=[""]
        first=0
        count=0
        rank=0
        view=self.paginator(ctx)
        for x in self.lb1:
            rank+=1
            if x == ctx.author.id:break
        for i in self.lb1.keys():
            try:
                user = ctx.guild.get_member(i)
                name = f"**{user.display_name}**"
            except:name=f"**User not in the server**({i})"
            if count>=10:
                desc.append("")
                count = 0
            desc[int(first/10)]+=f"❯`{int(first+1)}` {name}\n　└─{self.lb1[i]}\n"
            count+=1
            first+=1
        counter=0
        for i in desc:
            counter+=1
            embed = discord.Embed(title="Leaderboard",description=i,timestamp=datetime.datetime.utcnow())
            embed.set_footer(text=f"{counter}/{len(desc)} • Your rank : {rank}",icon_url=ctx.author.avatar.url)
            view.lb.append(embed)
        await ctx.send_followup(embed=view.lb[0],view=view)

    @Cog.listener("on_message")
    async def on_message(self,message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.guild.id != 767591734841835540:
            return
        if message.channel.id in self.blacklist:
            return
        if message.author.id not in self.cooldown:
            xp_gain = random.randint(4,8)
            try:
                x = await self._db_fetchall(
                    'SELECT "xp" FROM "levelling" where "user" =%s',
                    (message.author.id,)
                )
                if len(x)>0:
                    xp = x[0][0]
                    level_before= int(0.2*(math.sqrt(xp)))
                    xp=xp+xp_gain
                    level_after= int(0.2*(math.sqrt(xp)))
                    await self._db_execute(
                        'UPDATE "levelling" SET "xp" = %s where "user"=%s',
                        (xp,message.author.id)
                    )
                    if level_after>level_before:
                        await message.channel.send(f"Congratulations {message.author.mention},you just reached level {level_after} in this dead server! <:CS_zMilkSip:853199496674279455>")
                else:
                    xp= xp_gain
                    await self._db_execute(
                        'INSERT INTO "levelling" ("user","xp","theme","overlay") values (%s,%s,%s,%s)',
                        (message.author.id,xp,1,"True")
                    )
                for x in self.autorole.keys():
                    if xp > x:
                        role = message.guild.get_role(self.autorole[x])
                        roles=""
                        counter=0
                        if role not in message.author.roles:
                            counter+=1
                            await message.author.add_roles(role,reason="Level Up!")
                            roles+=f"{role.name} "
                        theme_unlock_msg = ""
                        # Check for theme unlocks at new level thresholds
                        new_level = int(0.2*(math.sqrt(xp)))
                        theme_unlocks = []
                        if new_level >= 20:
                            theme_unlocks.append("City")
                        elif new_level >= 15:
                            theme_unlocks.append("Red Metal")
                        elif new_level >= 10:
                            theme_unlocks.append("Cosmos")
                        elif new_level >= 5:
                            theme_unlocks.append("Mint")
                        elif new_level > 0:
                            theme_unlocks.append("Tech")
                        if theme_unlocks:
                            theme_unlock_msg = f"You also unlocked the theme: {theme_unlocks[-1]}! Use /theme to select your new theme."
                        if counter == 1:
                            await message.channel.send(f"Congratulations dear {message.author.mention}, you achieved the role {roles}!\n{theme_unlock_msg}")
                        elif counter > 1:
                            await message.channel.send(f"Congratulations dear {message.author.mention}, you achieved the roles {roles}!{theme_unlock_msg}")
            except Exception as e:
                print(f"[levelling] DB error in on_message: {e}")
            self.cooldown.append(message.author.id)
            await asyncio.sleep(60)
            self.cooldown.remove(message.author.id)

def human_format(num):
    num = float('{:.4g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    return '{}{}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', ' K', ' M', ' B', ' T'][magnitude])
def setup(bot):
    bot.add_cog(levelling(bot))