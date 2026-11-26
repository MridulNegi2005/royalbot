import os
import aiohttp
import discord
from discord.ext import commands
from discord.commands import slash_command, Option

ENDPOINT = "https://www.googleapis.com/customsearch/v1"
PER_PAGE = 5


async def run_search(query, limit=10):
    """Google Programmable Search JSON API.

    The old cog scraped google.com through the unmaintained 'google' package.
    Measured from the VM it returns zero results: Google blocks datacentre
    addresses, and DuckDuckGo answers the same address with its anomaly page.
    A key is the only thing that works from a server."""
    key = os.getenv("GOOGLE_SEARCH_API_KEY")
    cx = os.getenv("GOOGLE_SEARCH_CX")
    if not key or not cx:
        raise RuntimeError("missing key")

    params = {"key": key, "cx": cx, "q": query, "num": min(limit, 10), "safe": "active"}
    async with aiohttp.ClientSession() as session:
        async with session.get(ENDPOINT, params=params,
                               timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()

    if "error" in data:
        raise RuntimeError(data["error"].get("message", "search failed"))
    return [
        (item.get("title", "Untitled"),
         item.get("link", ""),
         item.get("snippet", "").replace("\n", " "))
        for item in data.get("items", [])
    ]


def page_count(results):
    return max(1, -(-len(results) // PER_PAGE))


class SearchControls(discord.ui.ActionRow):
    def __init__(self, result_set, page):
        super().__init__()
        self.result_set = result_set
        self.page = page
        self.previous.disabled = page == 0
        self.next.disabled = page >= page_count(result_set.results) - 1

    async def _turn(self, interaction, page):
        if interaction.user.id != self.result_set.owner:
            await interaction.response.send_message(
                "Run the command yourself to page through it.", ephemeral=True)
            return
        await interaction.response.edit_message(view=SearchView(self.result_set, page))

    @discord.ui.button(emoji="◀", style=discord.ButtonStyle.secondary)
    async def previous(self, button, interaction):
        await self._turn(interaction, self.page - 1)

    @discord.ui.button(emoji="▶", style=discord.ButtonStyle.secondary)
    async def next(self, button, interaction):
        await self._turn(interaction, self.page + 1)


class ResultSet:
    def __init__(self, query, results, owner):
        self.query = query
        self.results = results
        self.owner = owner


class SearchView(discord.ui.DesignerView):
    """Components V2: a container carries the whole reply, so nothing is sent as
    content or as an embed. The two cannot be mixed in one message."""

    def __init__(self, result_set, page=0):
        super().__init__(timeout=300, disable_on_timeout=True)
        pages = page_count(result_set.results)
        page = max(0, min(page, pages - 1))
        chunk = result_set.results[page * PER_PAGE:(page + 1) * PER_PAGE]

        container = discord.ui.Container()
        container.add_text(f"### Results for `{result_set.query[:80]}`")
        container.add_separator(divider=True)
        for offset, (title, link, snippet) in enumerate(chunk, start=page * PER_PAGE + 1):
            container.add_text(f"**{offset}. [{title[:120]}]({link})**\n-# {snippet[:220]}")
        container.add_separator(divider=True)
        container.add_text(f"-# Page {page + 1} of {pages} · {len(result_set.results)} result(s)")
        container.add_item(SearchControls(result_set, page))
        self.add_item(container)


class Gsearch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Search the web!")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def search(self, ctx, query: Option(str, "The query you want to search.")):
        await ctx.defer()
        try:
            results = await run_search(query)
        except RuntimeError as e:
            if str(e) == "missing key":
                await ctx.send_followup(
                    "Search is not configured. Set `GOOGLE_SEARCH_API_KEY` and "
                    "`GOOGLE_SEARCH_CX` in `.env`.", ephemeral=True)
            else:
                await ctx.send_followup(f"Search failed: {e}", ephemeral=True)
            return
        except Exception as e:
            await ctx.send_followup(f"Could not reach the search API: {e}", ephemeral=True)
            return

        if not results:
            await ctx.send_followup(f"No results for **{query}**.")
            return

        await ctx.send_followup(view=SearchView(ResultSet(query, results, ctx.author.id)))


def setup(bot):
    bot.add_cog(Gsearch(bot))
