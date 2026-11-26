import discord
from discord.ext import commands
import aiohttp
import os
from discord.commands import slash_command,SlashCommandGroup,permissions,Option

base_url = "https://api.openweathermap.org/data/2.5/weather"

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

    y = x["main"]
    weather_description = x["weather"][0]["description"]
    color = ctx.guild.me.top_role.color if ctx.guild else discord.Color.blue()
    embed = discord.Embed(title=f"Weather in {x.get('name',city)}", color=color)
    embed.add_field(name="Descripition", value=f"**{weather_description}**", inline=False)
    embed.add_field(name="Temperature(C)", value=f"**{round(y['temp'])}°C**", inline=False)
    embed.add_field(name="Humidity(%)", value=f"**{y['humidity']}%**", inline=False)
    embed.add_field(name="Atmospheric Pressure(hPa)", value=f"**{y['pressure']}hPa**", inline=False)
    embed.set_thumbnail(url="https://i.ibb.co/CMrsxdX/weather.png")
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    await ctx.send_followup(embed=embed)


def setup(bot):
  bot.add_cog(Weather(bot))
