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

from d20 import MarkdownStringifier, RollSyntaxError, roll
from d20.utils import simplify_expr
from discord import Embed, HTTPException, Option
from discord.commands import slash_command
from discord.ext.commands import Cog
from discord.utils import utcnow

from src.context import ApplicationContext
from src.enums.moves import Moves
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import WHITE_BAR


class Utilities(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot

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
        embed.set_footer(text=move.category.title())
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
