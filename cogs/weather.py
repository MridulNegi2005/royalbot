import discord
from discord.ext import commands
import requests
from discord.commands import slash_command,SlashCommandGroup,permissions,Option
api_key = "9ccb707ce80672014364dd1b8d6d7e44"
base_url = "http://api.openweathermap.org/data/2.5/weather?"

class Weather(commands.Cog):
  def __init__(self,bot):
    self.bot = bot

  @slash_command(description="Check weather of a particular City/State/Country")
  async def weather(self,ctx, city:Option(str,"Region Name")):
    city_name = city
    complete_url = base_url + "appid=" + api_key + "&q=" + city_name
    response = requests.get(complete_url)
    x = response.json()
    if x["cod"] != "404":
      y = x["main"]
      current_temperature = y["temp"]
      current_temperature_celsiuis = str(round(current_temperature - 273.15))
      current_pressure = y["pressure"]
      current_humidity = y["humidity"]
      z = x["weather"]
      weather_description = z[0]["description"]
      # Use bot's role color in server, fallback to blue in DMs
      color = ctx.guild.me.top_role.color if ctx.guild else discord.Color.blue()
      embed = discord.Embed(title=f"Weather in {city_name}",
                            color=color,)
      embed.add_field(name="Descripition", value=f"**{weather_description}**", inline=False)
      embed.add_field(name="Temperature(C)", value=f"**{current_temperature_celsiuis}°C**", inline=False)
      embed.add_field(name="Humidity(%)", value=f"**{current_humidity}%**", inline=False)
      embed.add_field(name="Atmospheric Pressure(hPa)", value=f"**{current_pressure}hPa**", inline=False)
      embed.set_thumbnail(url="https://i.ibb.co/CMrsxdX/weather.png")
      embed.set_footer(text=f"Requested by {ctx.author.name}")
      await ctx.respond(embed=embed)


def setup(bot):
  bot.add_cog(Weather(bot))