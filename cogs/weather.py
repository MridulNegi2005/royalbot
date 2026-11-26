import discord
from discord.ext import commands
import aiohttp
import os
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

base_url = "https://api.openweathermap.org/data/2.5/weather"
ICON = "https://i.ibb.co/CMrsxdX/weather.png"


class WeatherView(discord.ui.DesignerView):
  def __init__(self,name,description,main,requester,color):
    super().__init__(timeout=None)
    container = discord.ui.Container(color=color)
    container.add_section(
      discord.ui.TextDisplay(f"### Weather in {name}\n{description.capitalize()}"),
      accessory=discord.ui.Thumbnail(ICON))
    container.add_separator(divider=True)
    container.add_text(
      f"**Temperature** · {round(main['temp'])}°C\n"
      f"**Humidity** · {main['humidity']}%\n"
      f"**Pressure** · {main['pressure']} hPa")
    container.add_separator(divider=False)
    container.add_text(f"-# Requested by {requester}")
    self.add_item(container)


class Weather(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @slash_command(description="Check weather of a particular City/State/Country")
  async def weather(self,ctx, city:Option(str,"Region Name")):
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
      await ctx.respond("The weather API key is not configured.",ephemeral=True)
      return

    await ctx.defer()
    params = {"appid": api_key, "q": city, "units": "metric"}
    try:
      async with aiohttp.ClientSession() as session:
        async with session.get(base_url,params=params,timeout=aiohttp.ClientTimeout(total=10)) as r:
          x = await r.json()
    except Exception as e:
      await ctx.send_followup(f"Could not reach the weather service: {e}")
      return

    if str(x.get("cod")) != "200":
      await ctx.send_followup(f"Could not find weather for **{city}**.")
      return

    await ctx.send_followup(view=WeatherView(
      x.get("name",city), x["weather"][0]["description"], x["main"], ctx.author.name,
      ctx.guild.me.top_role.color if ctx.guild else discord.Color.blue()))


def setup(bot):
  bot.add_cog(Weather(bot))
