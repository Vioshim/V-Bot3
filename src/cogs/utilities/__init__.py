# Copyright 2022 Vioshim
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os import path
from re import IGNORECASE, compile, escape
from typing import Optional
from unicodedata import name as u_name

from d20 import roll
from d20.utils import simplify_expr
from discord import Color, Embed, Interaction, InteractionResponse, Thread, app_commands
from discord.ext import commands
from discord.utils import utcnow

from src.cogs.utilities.sphinx_reader import SphinxObjectFileReader
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import WHITE_BAR, RTFMPages


def to_string(c: str) -> str:
    """To String Method

    Parameters
    ----------
    c : str
        Character

    Returns
    -------
    str
        Parameters
    """
    digit = f"{ord(c):x}"
    name = u_name(c, "Name not found.")
    return f"[`\\U{digit:>08}`: {name} - {c}](<http://www.fileformat.info/info/unicode/char/{digit}>)"


class Utilities(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self._rtfm_cache: dict[str, dict[str, str]] = {}

    def finder(self, text, collection, *, key=None, lazy=True):
        suggestions = []
        text = str(text)
        pat = ".*?".join(map(escape, text))
        regex = compile(pat, flags=IGNORECASE)
        for item in collection:
            to_search = key(item) if key else item
            r = regex.search(to_search)
            if r:
                suggestions.append((len(r.group()), r.start(), item))

        def sort_key(tup):
            if key:
                return tup[0], tup[1], key(tup[2])
            return tup

        if lazy:
            return (z for _, _, z in sorted(suggestions, key=sort_key))
        return [z for _, _, z in sorted(suggestions, key=sort_key)]

    def parse_object_inv(self, stream: SphinxObjectFileReader, url: str):

        result: dict[str, str] = {}

        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        stream.readline().rstrip()[11:]
        stream.readline().rstrip()[11:]

        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        entry_regex = compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, prio, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:

                continue

            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            result[f"{prefix}{key}"] = path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self):
        cache = {}
        for item in RTFMPages:
            async with self.bot.session.get(f"{item.value}/objects.inv") as resp:
                if resp.status != 200:
                    raise RuntimeError("Cannot build rtfm lookup table, try again later.")

                stream = SphinxObjectFileReader(await resp.read())
                cache[item.name] = self.parse_object_inv(stream, item.value)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: Interaction, key: RTFMPages, obj: Optional[str]):

        if obj is None:
            return await ctx.followup.send(key.value)

        if not self._rtfm_cache:
            await self.build_rtfm_lookup_table()

        cache = list(self._rtfm_cache[key].items())

        matches = self.finder(obj, cache, key=lambda t: t[0], lazy=False)
        if text := "\n".join(f"[`{key}`]({url})" for key, url in matches[:8]):
            await ctx.followup.send(text, ephemeral=True)
        else:
            await ctx.followup.send("Could not find anything. Sorry.", ephemeral=True)

    @commands.command()
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """
        embed = Embed(
            title="Character Information",
            description="\n".join(map(to_string, characters)),
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        if len(embed.description) > 4096:
            embed.description = "Output too long to display."
            embed.color = Color.red()

        await ctx.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def rtfm(self, ctx: Interaction, key: Optional[RTFMPages], query: Optional[str]):
        """Executes a manual query

        Parameters
        ----------
        ctx : Interaction
            Interaction
        key : Optional[RTFMPages]
            Website
        query : Optional[str]
            Query to look for
        """
        resp: InteractionResponse = ctx.response
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        await self.do_rtfm(ctx, key or RTFMPages.Discord, query)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def metronome(self, ctx: Interaction):
        """Allows to use metronome

        Parameters
        ----------
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        item = Move.getMetronome()
        await resp.send_message(embed=item.embed)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def roll(self, ctx: Interaction, expression: str, hidden: bool = False):
        """Allows to roll dice based on 20

        Parameters
        ----------
        ctx : Interaction
            Interaction
        expression : str
            Expression (Example: d20)
        hidden : bool, optional
            If it's shown, by default visible
        """
        resp: InteractionResponse = ctx.response
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=hidden, thinking=True)
        try:
            value = roll(expr=expression, allow_comments=True)
            if len(value.result) > 4096:
                simplify_expr(value.expr)

            embed = Embed(
                title=f"Rolling: {expression}",
                description=value.result,
                color=Color.blurple(),
                timestamp=utcnow(),
            )
            if len(embed.title) > 256:
                embed.title = "Rolling Expression"

            embed.set_image(url=WHITE_BAR)
            embed.set_thumbnail(url=f"https://dummyimage.com/512x512/FFFFFF/000000&text={value.total}")

            if guild := ctx.guild:
                embed.set_footer(text=guild.name, icon_url=guild.icon)

            await ctx.followup.send(embed=embed, ephemeral=hidden)
        except Exception as e:
            self.bot.logger.exception("Error while rolling dice.", exc_info=e)
            await ctx.followup.send("Invalid expression", ephemeral=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Utilities(bot))
