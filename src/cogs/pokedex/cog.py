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

from discord import (
    Embed,
    Guild,
    Member,
    Option,
    OptionChoice,
    TextChannel,
    Thread,
)
from discord.commands import slash_command
from discord.ext.commands import Cog
from discord.utils import utcnow

from src.cogs.pokedex.search import (
    ability_autocomplete,
    default_species_autocomplete,
    move_autocomplete,
    species_autocomplete,
    type_autocomplete,
)
from src.context import ApplicationContext
from src.structures.ability import Ability
from src.structures.bot import CustomBot
from src.structures.character import Character, FusionCharacter
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.species import Fusion, Species, Variant
from src.utils.etc import WHITE_BAR
from src.utils.functions import fix
from src.views import CharactersView

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088"
KINDS = [
    "Legendary",
    "Mythical",
    "Ultra Beast",
    "Pokemon",
    "Fakemon",
    "Variant",
    "Fusion",
]
REF_KINDS = [fix(i) for i in KINDS]


class Pokedex(Cog):
    """This is a standard Pokedex Cog"""

    def __init__(self, bot: CustomBot):
        """Default init Method

        Parameters
        ----------
        bot : CustomBot
            Bot instance
        """
        self.bot = bot

    @slash_command(guild_ids=[719343092963999804])
    async def find(
        self,
        ctx: ApplicationContext,
        kind: Option(
            str,
            description="Filter by kind",
            choices=[
                OptionChoice(
                    name=item,
                    value=item.replace(" ", "").upper(),
                )
                for item in KINDS
            ],
            required=False,
        ),
        type_id: Option(
            str,
            name="type",
            description="Type to filter",
            autocomplete=type_autocomplete,
            required=False,
        ),
        ability_id: Option(
            str,
            name="ability",
            description="Ability to filter",
            autocomplete=ability_autocomplete,
            required=False,
        ),
        move_id: Option(
            str,
            name="move",
            description="Move to filter",
            autocomplete=move_autocomplete,
            required=False,
        ),
        species: Option(
            str,
            description="Species to look up info about.",
            autocomplete=species_autocomplete,
            required=False,
        ),
        fused: Option(
            str,
            description="Search Fusions that contain the species",
            autocomplete=default_species_autocomplete,
            required=False,
        ),
        member: Option(
            Member,
            description="Member to filter",
            required=False,
        ),
        location: Option(
            TextChannel,
            description="OCs at a location to filter",
            required=False,
        ),
    ):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : ApplicationContext
            Context
        kind : str, optional
            Kind, by default None
        type_id : str, optional
            Typing, by default None
        ability_id : str, optional
            Ability, by default None
        move_id : str, optional
            Move, by default None
        species : str, optional
            Species, by default None
        fused : str, optional
            Fusion, by default None
        member : Member, optional
            Member, by default None
        location : TextChannel, optional
            Channel, by default None
        """
        species: str = species or ""
        fused: str = fused or ""
        ability_id: str = ability_id or ""
        move_id: str = move_id or ""
        type_id: str = type_id or ""
        text: str = ""
        cog = ctx.bot.get_cog("Submission")
        await ctx.defer(ephemeral=True)
        embed = Embed(
            title="Select the Character",
            url=PLACEHOLDER,
            color=ctx.author.color,
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embeds = [embed]
        total: list[Character] = list(cog.ocs.values())
        if species.isdigit() and (oc := cog.ocs.get(int(species))):
            ocs = [oc]
        else:
            ocs = total
        guild: Guild = ctx.guild
        if isinstance(location, Thread):
            location = location.parent
        if isinstance(location, TextChannel):
            ocs = [
                oc
                for oc in ocs
                if (ch := guild.get_channel_or_thread(oc.location))
                and (ch.parent if isinstance(ch, Thread) else ch) == location
            ]
        if member_id := getattr(member, "id", member):
            ocs = [oc for oc in ocs if oc.author == int(member_id)]
        fuse_mon = Species.from_ID(fused)
        mon = Species.from_ID(species.removesuffix("+"))
        if mon or fuse_mon:
            if mon:
                if fuse_mon and not isinstance(mon, Fusion):
                    mon = Fusion(mon, fuse_mon)
                ocs = [
                    oc
                    for oc in ocs
                    if (
                        species.endswith("+")
                        and isinstance(oc.species, Variant)
                        and oc.species.base == mon
                    )
                    or oc.species == mon
                ]
            else:
                mon = fuse_mon
                ocs = [
                    oc
                    for oc in ocs
                    if isinstance(oc, FusionCharacter)
                    and fuse_mon in oc.species.bases
                ]

            movepool = mon.movepool
            data = dict(
                Level=movepool.level_moves,
                Egg=movepool.egg,
                Event=movepool.event,
                TM=movepool.tm,
                Tutor=movepool.tutor,
                LevelUp=movepool.levelup,
                Other=movepool.other,
            )

            if (
                len(
                    moves_description := "\n".join(
                        f"{key} Moves: \n> {info}"
                        for key, moves in data.items()
                        if (info := ", ".join(m.name for m in moves))
                    )
                )
                <= 2000
            ):
                embed.description = moves_description
            else:
                embed.description = "\n".join(
                    f"{key} Moves: {len(moves)}"
                    for key, moves in data.items()
                    if moves
                )

            embed.color = mon.color

            if mon.banned:
                embed.title = f"{mon.name} - Banned Species"
            else:
                embed.title = mon.name

            if mon_types := ", ".join(i.name for i in mon.types):
                embed.set_footer(text=f"Types: {mon_types}")
            elif isinstance(mon, Fusion) and (
                mon_types := ", ".join(
                    "/".join(i.name for i in item)
                    for item in mon.possible_types
                )
            ):
                embed.set_footer(text=f"Possible Types: {mon_types}")

            if ab_text := "\n".join(f"• {ab.name}" for ab in mon.abilities):
                embed.add_field(
                    name=f"Abilities (Max {mon.max_amount_abilities})",
                    value=ab_text,
                )

            if isinstance(mon, Fusion):
                embeds = [
                    embed.set_image(url=mon.mon1.base_image),
                    Embed(url=PLACEHOLDER).set_image(url=mon.mon2.base_image),
                ]
            else:
                embeds = [
                    embed.set_image(url=mon.base_image),
                    Embed(url=PLACEHOLDER).set_image(url=mon.base_image_shiny),
                ]
        elif species and not fuse_mon:
            embed.title = f"Unable to identify the species: {species}.\nShowing all Instead"
        if type_id and (item := Typing.from_ID(type_id)):
            ocs = [oc for oc in ocs if item in oc.types]
            if embed.color == ctx.author.color:
                embed.color = item.color
            embed.set_thumbnail(url=item.emoji.url)
        if ability_id and (item := Ability.from_ID(ability_id)):
            ocs = [oc for oc in ocs if item in oc.abilities]
            if embed.description:
                embed.add_field(
                    name=f"Ability - {item.name}",
                    value=item.description,
                    inline=False,
                )
            else:
                embed.title = item.name
                embed.description = item.description
            if battle := item.battle:
                embed.add_field(
                    name="Battle effect",
                    value=battle,
                    inline=False,
                )
            if outside := item.outside:
                embed.add_field(
                    name="Usage",
                    value=outside,
                    inline=False,
                )
            if random_fact := item.random_fact:
                embed.add_field(
                    name="Random Fact",
                    value=random_fact,
                    inline=False,
                )
        if move_id and (item := Move.from_ID(move_id)):
            ocs = [oc for oc in ocs if item in oc.moveset]
            title = repr(item)
            if item.banned:
                title += " - Banned Move"
            description = item.desc or item.shortDesc
            if embed.color == ctx.author.color:
                embed.color = item.color
            embed.set_thumbnail(url=item.type.emoji.url)
            embed.set_image(url=item.image)
            power = item.base or "-"
            acc = item.accuracy or "-"
            pp = item.pp or "-"

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
                e.url = item.url
        if (kind := fix(kind)) in REF_KINDS:
            ocs = [
                oc
                for oc in ocs
                if fix(oc.kind) == kind.replace("POKEMON", "COMMON")
            ]

        view = CharactersView(
            bot=self.bot,
            member=ctx.author,
            ocs=ocs,
            target=ctx.interaction,
            keep_working=True,
        )

        if not ocs or total == ocs:

            amounts: dict[str, set[Character]] = {}
            for oc in cog.ocs.values():
                amounts.setdefault(oc.kind, set())
                amounts[oc.kind].add(oc)

            info = [(k, len(v)) for k, v in amounts.items()]
            info.sort(key=lambda x: x[1], reverse=True)

            data = "\n".join(f"{k}: {v}" for k, v in info).title()
            data = f"```yaml\n{data}\n```"
            if embed.description:
                text = f"**__Total OCs in Server__**\n{data}"
            else:
                embed.description = data

        await ctx.respond(
            content=text,
            embeds=embeds,
            view=view,
            ephemeral=True,
        )


def setup(bot: CustomBot):
    """Default Cog Loader

    :param bot: Bot
    :return:
    """
    bot.add_cog(Pokedex(bot))
