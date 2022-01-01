# Copyright 2021 Vioshim
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
from unicodedata import name as u_name

from d20 import MarkdownStringifier, RollSyntaxError, roll
from d20.utils import simplify_expr
from discord import Embed, HTTPException, Option, OptionChoice
from discord.commands import slash_command
from discord.commands.permissions import is_owner
from discord.ext.commands import Cog, command
from discord.utils import utcnow

from src.cogs.utilities.sphinx_reader import SphinxObjectFileReader
from src.context import ApplicationContext, Context
from src.enums.moves import Moves
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import WHITE_BAR

PAGE_TYPES: dict[str, str] = {
    "discord": "https://pycord.readthedocs.io/en/master/",
    "python": "https://docs.python.org/3",
    "apscheduler": "https://apscheduler.readthedocs.io/en/3.x/",
    "bs4": "https://www.crummy.com/software/BeautifulSoup/bs4/doc/",
    "dateparser": "https://dateparser.readthedocs.io/en/latest/",
    "asyncpg": "https://magicstack.github.io/asyncpg/current/",
    "black": "https://black.readthedocs.io/en/stable/",
    "uvloop": "https://uvloop.readthedocs.io/",
    "d20": "https://d20.readthedocs.io/en/latest/",
    "aiohttp": "https://docs.aiohttp.org/en/stable/",
}


class Utilities(Cog):
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
            raise RuntimeError(
                "Invalid objects.inv file, not z-lib compatible."
            )

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

    async def build_rtfm_lookup_table(self, page_types: dict[str, str]):
        cache = {}
        for key, page in page_types.items():
            async with self.bot.session.get(page + "/objects.inv") as resp:
                if resp.status != 200:
                    raise RuntimeError(
                        "Cannot build rtfm lookup table, try again later."
                    )

                stream = SphinxObjectFileReader(await resp.read())
                cache[key] = self.parse_object_inv(stream, page)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: ApplicationContext, key: str, obj: str):

        if obj is None:
            return await ctx.send_followup(PAGE_TYPES[key])

        if not self._rtfm_cache:
            await ctx.trigger_typing()
            await self.build_rtfm_lookup_table(PAGE_TYPES)

        cache = list(self._rtfm_cache[key].items())

        self.matches = self.finder(obj, cache, key=lambda t: t[0], lazy=False)[
            :8
        ]

        e = Embed(colour=0x05FFF0)
        e.set_image(url=WHITE_BAR)
        if len(self.matches) == 0:
            return await ctx.send_followup("Could not find anything. Sorry.")

        e.description = "\n".join(
            f"[`{key}`]({url})" for key, url in self.matches
        )
        await ctx.send_followup(embed=e)

    @command()
    async def charinfo(self, ctx: Context, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """

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

        msg = "\n".join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send("Output too long to display.")
        await ctx.send(msg)

    @slash_command(
        guild_ids=[719343092963999804],
        description="Executes a manual query",
    )
    @is_owner()
    async def rtfm(
        self,
        ctx: ApplicationContext,
        key: Option(
            str,
            description="Site",
            required=False,
            choices=[
                OptionChoice(
                    name=item.title(),
                    value=item,
                )
                for item in PAGE_TYPES
            ],
        ),
        query: str = None,
    ):
        await ctx.defer()
        if not key or key.lower() not in PAGE_TYPES:
            query = query or ""
            key = key or ""
            query = key + query
            key = "discord"

        await self.do_rtfm(ctx, key, query)

    @slash_command(
        guild_ids=[719343092963999804],
        description="Allows to use metronome",
    )
    async def metronome(
        self,
        ctx: ApplicationContext,
    ):
        item = Moves.metronome_fetch()
        move: Move = item.value
        description = move.desc or move.shortDesc
        embed = Embed(
            title=move.name,
            description=description,
            color=move.type.color,
            timestamp=utcnow(),
        )
        embed.add_field(name="Power", value=f"{move.base}")
        embed.add_field(name="Accuracy", value=f"{move.accuracy}")
        embed.set_footer(text=move.category.name.title())
        embed.add_field(name="PP", value=f"{move.pp}")
        embed.set_thumbnail(url=move.type.emoji.url)
        embed.set_image(url=WHITE_BAR)
        await ctx.respond(embed=embed)

    @slash_command(
        guild_ids=[719343092963999804],
        description="Allows to roll dice based on d20",
    )
    async def roll(
        self,
        ctx: ApplicationContext,
        expression: Option(
            str,
            description="Expression (Example: d20)",
        ),
    ):
        value = roll(expr=expression, stringifier=MarkdownStringifier())
        try:
            await ctx.respond(value.result)
        except RollSyntaxError:
            await ctx.respond("Invalid expression", ephemeral=True)
        except HTTPException:
            expr = value.expr
            simplify_expr(expr)
            await ctx.respond(value.result)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Utilities(bot))
