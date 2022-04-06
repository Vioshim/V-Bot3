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
from discord import Interaction, InteractionResponse, app_commands
from discord.ext import commands

from src.cogs.utilities.sphinx_reader import SphinxObjectFileReader
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import RTFMPages


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
    # noinspection HttpUrlsUsage
    return (
        f"`\\U{digit:>08}`: {name} - {c}"
        " \N{EM DASH} "
        f"<http://www.fileformat.info/info/unicode/char/{digit}>"
    )


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
        else:
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
                    raise RuntimeError(
                        "Cannot build rtfm lookup table, try again later."
                    )

                stream = SphinxObjectFileReader(await resp.read())
                cache[item.name] = self.parse_object_inv(stream, item.value)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: Interaction, key: RTFMPages, obj: str):

        if obj is None:
            return await ctx.followup.send(key.value)

        if not self._rtfm_cache:
            await self.build_rtfm_lookup_table()

        cache = list(self._rtfm_cache[key].items())

        matches = self.finder(obj, cache, key=lambda t: t[0], lazy=False)
        self.matches = matches[:8]

        if text := "\n".join(f"[`{key}`]({url})" for key, url in self.matches):
            await ctx.followup.send(text)
        else:
            await ctx.followup.send("Could not find anything. Sorry.")

    @commands.command()
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send("Output too long to display.")
        await ctx.send(msg)

    @app_commands.command(description="Executes a manual query")
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def rtfm(
        self,
        ctx: Interaction,
        key: Optional[RTFMPages],
        query: Optional[str],
    ):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        if not key:
            key = RTFMPages.Discord
        await self.do_rtfm(ctx, key, query)

    @app_commands.command(description="Allows to use metronome",)
    @app_commands.guilds(719343092963999804)
    async def metronome(
        self,
        ctx: Interaction,
    ):
        resp: InteractionResponse = ctx.response
        item = Move.getMetronome()
        await resp.send_message(embed=item.embed)

    @app_commands.command(description="Allows to roll dice based on d20")
    @app_commands.guilds(719343092963999804)
    @app_commands.describe(expression="Expression (Example: d20)")
    async def roll(
        self,
        ctx: Interaction,
        expression: str,
        hidden: bool = False,
    ):
        resp: InteractionResponse = ctx.response
        try:
            value = roll(
                expr=expression,
                allow_comments=True,
            )
            if len(result := value.result) >= 2000:
                simplify_expr(value.expr)
            if len(result := value.result) <= 2000:
                return await resp.send_message(result, ephemeral=hidden)
            await resp.send_message(
                f"Expression is too long, result is: {value.total}",
                ephemeral=hidden,
            )
        except Exception:
            await resp.send_message("Invalid expression", ephemeral=True)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Utilities(bot))
