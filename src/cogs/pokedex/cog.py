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
from dataclasses import astuple
from re import IGNORECASE, compile
from typing import Literal, Optional

from discord import (
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Thread,
    User,
    app_commands,
)
from discord.ext import commands
from discord.utils import utcnow

from src.cogs.pokedex.search import (
    AbilityArg,
    DefaultSpeciesArg,
    FakemonArg,
    MoveArg,
    SpeciesArg,
    TypingArg,
)
from src.structures.bot import CustomBot
from src.structures.character import Character, FusionCharacter
from src.structures.movepool import Movepool
from src.structures.species import Fusion, Species, Variant
from src.utils.etc import WHITE_BAR
from src.utils.functions import fix
from src.views import CharactersView, MovepoolViewSelector

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088"
KINDS = Literal[
    "Legendary",
    "Mythical",
    "Ultra Beast",
    "Pokemon",
    "Fakemon",
    "Variant",
    "Fusion",
    "Custom Mega",
    "Mega",
]
REF_KINDS = [
    "LEGENDARY",
    "MYTHICAL",
    "ULTRABEAST",
    "POKEMON",
    "FAKEMON",
    "VARIANT",
    "FUSION",
    "CUSTOMMEGA",
    "MEGA",
]

OPERATORS = {
    "<=": lambda x, y: x <= y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    ">": lambda x, y: x > y,
}


def foo(x: str) -> Optional[int]:
    x = x.strip()
    if x.isdigit():
        return int(x)


def age_parser(text: str, oc: Character):
    """Filter through range

    Parameters
    ----------
    text : str
        Range

    Returns
    -------
    bool
        valid
    """
    age: int = oc.age or 0
    for item in map(
        lambda x: x.strip(), text.replace(",", ";").replace("|", ";").split(";")
    ):
        op = sorted(o for x in item.split("-") if isinstance(o := foo(x), int))
        if (len(op) == 2 and op[0] <= age <= op[1]) or age in op:
            return True

        for key, operator in filter(lambda x: x[0] in item, OPERATORS.items()):
            op1, op2 = map(foo, item.split(key))
            op1 = op1 if isinstance(op1, int) else op2
            if isinstance(op1, int) and operator(op1, age):
                return True

    return False


class Pokedex(commands.Cog):
    """This is a standard Pokedex Cog"""

    def __init__(self, bot: CustomBot):
        """Default init Method

        Parameters
        ----------
        bot : CustomBot
            Bot instance
        """
        self.bot = bot

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.describe(
        species="Species to look up info about",
        fused="To check when fused",
        fakemon="Search fakemon species",
        move_id="Move to lookup",
    )
    async def movepool(
        self,
        ctx: Interaction,
        species: Optional[DefaultSpeciesArg],
        fused: Optional[DefaultSpeciesArg],
        fakemon: Optional[FakemonArg],
        move_id: Optional[MoveArg],
    ):
        """Check for Movepool information

        Parameters
        ----------
        ctx : Interaction
            Interaction
        species : Optional[DefaultSpeciesArg]
            Species to look up info about
        fused : Optional[DefaultSpeciesArg]
            To check when fused
        fakemon : Optional[FakemonArg]
            Search fakemon species
        move_id : Optional[MoveArg]
            Move to lookup
        """
        resp: InteractionResponse = ctx.response
        embed = Embed(
            title="See Movepool",
            color=ctx.user.color,
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        await resp.defer(ephemeral=True)
        if not species:
            species = fused

        if species:
            if fused and species != fused:
                mon = Fusion(species, fused)
                mon_types = mon.possible_types
            else:
                mon = species
                mon_types = [species.types]

            embed.title = f"See {mon.name}'s movepool"
            movepool = mon.total_movepool
            if info := "\n".join(f"• {'/'.join(i.name for i in x)}" for x in mon_types):
                embed.add_field(name="Possible Types", value=info)
        elif fakemon:
            movepool = fakemon.movepool
            embed.title = f"See {fakemon.species.name}'s movepool"
        else:
            movepool = Movepool()

        if move_id:
            if methods := "\n".join(
                f"> • **{x.title()}**" for x in movepool.methods_for(move_id)
            ):
                await ctx.followup.send(
                    f"The pokemon can learn {move_id.name} through:\n{methods}.",
                    ephemeral=True,
                )
            else:
                await ctx.followup.send(
                    f"The pokemon can not learn {move_id.name}.",
                    ephemeral=True,
                )
        else:
            view = MovepoolViewSelector(bot=self.bot, movepool=movepool)
            await ctx.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.describe(
        name="Any name that matches(regex works).",
        kind="Filter by kind",
        _type="Type to filter",
        ability="Ability to filter",
        move="Move to filter",
        species="Species to look up info about.",
        fused="Search Fusions that contain the species",
        member="Member to filter",
        location="Location to filter",
        backstory="Any words to look for in backstories",
        extra="Any words to look for in the extra info",
        sp_ability="Any words to look for in Sp Abilities",
        pronoun="Pronoun to Look for",
        age="OC's age. e.g. 18-24, 13, >20",
    )
    async def find(
        self,
        ctx: Interaction,
        name: Optional[str],
        kind: Optional[KINDS],
        _type: Optional[TypingArg],
        ability: Optional[AbilityArg],
        move: Optional[MoveArg],
        species: Optional[SpeciesArg],
        fused: Optional[DefaultSpeciesArg],
        member: Optional[Member],
        location: Optional[TextChannel],
        backstory: Optional[str],
        extra: Optional[str],
        sp_ability: Optional[str],
        pronoun: Optional[Literal["He", "She", "Them"]],
        age: Optional[str],
    ):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : Interaction
            Context
        name : Optional[str]
            Any name that matches(regex works).
        kind : Optional[KINDS]
            Filter by kind
        _type : Optional[TypingArg]
            Type to filter
        ability : Optional[AbilityArg]
            Ability to filter
        move : Optional[MoveArg]
            Move to filter
        species : Optional[SpeciesArg]
            Species to look up info about.
        fused : Optional[DefaultSpeciesArg]
            Search Fusions that contain the species
        member : Optional[Member]
            Member to filter
        location : Optional[TextChannel  |  Thread]
            Location to filter
        backstory : Optional[str]
            Any words to look for in backstories
        extra : Optional[str]
            Any words to look for in the extra info
        sp_ability : Optional[str]
            Any words to look for in Sp Abilities
        pronoun : Optional[Literal['He', 'She', 'Them']]
            Pronoun to Look for
        age : Optional[str]
            OC's age. e.g. 18-24, 13, >20
        """
        resp: InteractionResponse = ctx.response
        text: str = ""
        guild: Guild = ctx.guild
        cog = ctx.client.get_cog("Submission")
        await resp.defer(ephemeral=True)
        embed = Embed(
            title="Select the Character",
            url=PLACEHOLDER,
            color=ctx.user.color,
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embeds = [embed]
        total: list[Character] = [
            oc for oc in cog.ocs.values() if guild.get_member(oc.author)
        ]
        if isinstance(species, Character):
            ocs = [species]
        else:
            ocs = total

        if name:
            pattern = compile(name, IGNORECASE)
            ocs = [oc for oc in ocs if pattern.search(oc.name)]

        if age:
            ocs = [oc for oc in ocs if age_parser(age, oc)]

        if isinstance(location, Thread):
            location = location.parent
        if isinstance(location, TextChannel):
            ocs = [
                oc
                for oc in ocs
                if (ch := guild.get_channel_or_thread(oc.location))
                and (ch.parent if isinstance(ch, Thread) else ch) == location
            ]

        if isinstance(member, (User, Member)):
            ocs = [oc for oc in ocs if oc.author == member.id]
        elif member:
            ocs = [oc for oc in ocs if oc.author == member]

        mon = None
        if isinstance(species, Species):
            mon = species
            if fused and species != fused and not isinstance(fused, Fusion):
                mon = Fusion(species, fused)
            if kind == "Variant":
                ocs = [
                    oc
                    for oc in ocs
                    if isinstance(oc.species, Variant) and oc.species.base == mon
                ]
            else:
                ocs = [oc for oc in ocs if oc.species == mon]
        elif fused and not isinstance(fused, Fusion):
            mon = fused
            ocs = [
                oc
                for oc in ocs
                if isinstance(oc, FusionCharacter) and species in oc.species.bases
            ]

        if isinstance(mon, Species):
            if mon.banned:
                embed.title = f"{mon.name} - Banned Species"
            else:
                embed.title = mon.name

            if mon_types := ", ".join(i.name for i in mon.types):
                embed.set_footer(text=f"Types: {mon_types}")
            elif isinstance(mon, Fusion) and (
                mon_types := ", ".join(
                    "/".join(i.name for i in item) for item in mon.possible_types
                )
            ):
                embed.set_footer(text=f"Possible Types: {mon_types}")

            if ab_text := "\n".join(f"• {ab.name}" for ab in mon.abilities):
                embed.add_field(
                    name=f"Abilities (Max {mon.max_amount_abilities})",
                    value=ab_text,
                )

            if isinstance(mon, Fusion):
                if pronoun == "She":
                    image1, image2 = (
                        mon.mon1.female_image,
                        mon.mon2.female_image,
                    )
                else:
                    image1, image2 = mon.mon1.base_image, mon.mon2.base_image
            elif pronoun == "She":
                image1, image2 = mon.female_image, mon.female_image_shiny
            else:
                image1, image2 = mon.base_image, mon.base_image_shiny

            embeds = [
                embed.set_image(url=image1),
                Embed(url=PLACEHOLDER).set_image(url=image2),
            ]
        if pronoun:
            ocs = [oc for oc in ocs if oc.pronoun.name == pronoun.title()]
        if backstory:
            ocs = [
                oc
                for oc in ocs
                if oc.backstory and backstory.lower() in oc.backstory.lower()
            ]
        if extra:
            ocs = [oc for oc in ocs if oc.extra and extra.lower() in oc.extra.lower()]
        if sp_ability:
            ocs = [
                oc
                for oc in ocs
                if (item := oc.sp_ability)
                and any(sp_ability.lower() in x.lower() for x in astuple(item))
            ]
        if _type:
            ocs = [oc for oc in ocs if _type in oc.types]
            if embed.color == ctx.user.color:
                embed.color = _type.color
            embed.set_thumbnail(url=_type.emoji.url)
        if ability:
            ocs = [oc for oc in ocs if ability in oc.abilities]
            if embed.description:
                embed.add_field(
                    name=f"Ability - {ability.name}",
                    value=ability.description,
                    inline=False,
                )
            else:
                embed.title = ability.name
                embed.description = ability.description
            if battle := ability.battle:
                embed.add_field(
                    name="Battle effect",
                    value=battle,
                    inline=False,
                )
            if outside := ability.outside:
                embed.add_field(
                    name="Usage",
                    value=outside,
                    inline=False,
                )
            if random_fact := ability.random_fact:
                embed.add_field(
                    name="Random Fact",
                    value=random_fact,
                    inline=False,
                )
        if move:
            ocs = [oc for oc in ocs if move in oc.moveset]
            title = repr(move)
            if move.banned:
                title += " - Banned Move"
            description = move.desc or move.shortDesc
            if embed.color == ctx.user.color:
                embed.color = move.color
            embed.set_thumbnail(url=move.type.emoji.url)
            embed.set_image(url=move.image)
            power = move.base or "-"
            acc = move.accuracy or "-"
            pp = move.pp or "-"

            if embed.description:
                embed.add_field(
                    name=f"{title} - Power:{power}|Acc:{acc}|PP:{pp}",
                    value=description,
                    inline=False,
                )
            else:
                embed.title = title
                embed.description = description
                embed.add_field(name="Power", value=power)
                embed.add_field(name="Accuracy", value=acc)
                embed.add_field(name="PP", value=pp)
            for e in embeds:
                e.url = move.url
        if kind:
            ocs = [
                oc
                for oc in ocs
                if fix(oc.kind) == (fix(kind) if fix(kind) != "POKEMON" else "COMMON")
            ]

        view = CharactersView(
            bot=self.bot,
            member=ctx.user,
            ocs=ocs,
            target=ctx,
            keep_working=True,
        )

        await ctx.followup.send(
            content=text,
            embeds=embeds,
            view=view,
            ephemeral=True,
        )


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Pokedex(bot))
