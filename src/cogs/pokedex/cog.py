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

from discord import Embed, InteractionResponse, Option, OptionChoice
from discord.commands import slash_command
from discord.ext.commands import Cog

from src.cogs.pokedex.search import (
    ability_autocomplete,
    default_species_autocomplete,
    move_autocomplete,
    type_autocomplete,
)
from src.context import ApplicationContext
from src.structures.ability import Ability
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.species import Fusion, Species, Variant
from src.utils.etc import WHITE_BAR
from src.views import CharactersView, PingView

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088"
KINDS = [
    "Legendary",
    "Mythical",
    "Ultra Beast",
    "Pokemon",
    "Fakemon",
    "Variant",
    "Fusion",
    "Any",
]


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
            autocomplete=default_species_autocomplete,
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
        """
        species: str = species or ""
        ability_id: str = ability_id or ""
        move_id: str = move_id or ""
        type_id: str = type_id or ""
        cog = ctx.bot.get_cog("Submission")

        resp: InteractionResponse = ctx.respose
        await resp.defer(ephemeral=True)

        if species.isdigit() and (oc := cog.ocs.get(int(species))):
            view = PingView(oc, oc.author == ctx.user.id)
            await ctx.send_followup(
                embeds=oc.embed,
                view=view,
                ephemeral=True,
            )
        elif mon := Species.from_ID(species.removesuffix("+")):
            self.bot.logger.info(
                "%s is reading /find species %s", str(ctx.user), mon.name
            )
            ocs = [
                oc
                for oc in cog.ocs.values()
                if (
                    species.endswith("+")
                    and isinstance(oc.species, Variant)
                    and oc.species.base == mon
                )
                or oc.species == mon
            ]

            view = CharactersView(
                bot=self.bot,
                member=ctx.author,
                ocs=ocs,
                target=ctx.interaction,
                keep_working=True,
            )
            embed = view.embed
            stats = dict(
                HP=mon.HP,
                ATK=mon.ATK,
                DEF=mon.DEF,
                SPA=mon.SPA,
                SPD=mon.SPD,
                SPE=mon.SPE,
            )
            text = "\n".join(f"{k}: {v:03d}" for k, v in stats.items())

            if mon.banned:
                embed.title = f"{mon.name} - Banned Species"
            else:
                embed.title = mon.name

            embed.color = mon.color
            embed.url = PLACEHOLDER
            embed.description = f"```yaml\n{text}\n```"

            if mon_types := ", ".join(i.name for i in mon.types):
                embed.set_footer(text=f"Types: {mon_types}")

            if isinstance(mon, Fusion):
                mon_types = ", ".join(
                    "/".join(i.name for i in item)
                    for item in mon.possible_types
                )
                embeds = [
                    embed.set_image(url=mon.mon1.base_image),
                    Embed(url=PLACEHOLDER).set_image(url=mon.mon2.base_image),
                ]
                embed.set_footer(text=f"Possible Types: {mon_types}")
            else:
                embeds = [
                    embed.set_image(url=mon.base_image),
                    Embed(url=PLACEHOLDER).set_image(url=mon.base_image_shiny),
                ]
                if mon.base_image != mon.female_image:
                    embeds += [
                        Embed(url=PLACEHOLDER).set_image(
                            url=mon.female_image,
                        ),
                        Embed(url=PLACEHOLDER).set_image(
                            url=mon.female_image_shiny,
                        ),
                    ]

            for index, ability in enumerate(mon.abilities, start=1):
                embed.add_field(
                    name=f"Ability {index} - {ability.name}",
                    value=f"> {ability.description}",
                    inline=False,
                )

            await ctx.send_followup(
                embeds=embeds,
                view=view,
                ephemeral=True,
            )
        elif species:
            await ctx.send_followup(
                content=f"Unable to identify the species: {species}",
                ephemeral=True,
            )
        elif (
            (type_id and (item := Typing.from_ID(type_id)))
            or (ability_id and (item := Ability.from_ID(ability_id)))
            or (move_id and (item := Move.from_ID(move_id)))
        ):
            if isinstance(item, Ability):
                ocs = [oc for oc in cog.ocs.values() if item in oc.abilities]
            elif isinstance(item, Typing):
                ocs = [oc for oc in cog.ocs.values() if item in oc.types]
            else:
                ocs = [oc for oc in cog.ocs.values() if item in oc.moveset]
            view = CharactersView(
                bot=self.bot,
                member=ctx.author,
                ocs=ocs,
                target=ctx.interaction,
                keep_working=True,
            )
            embed = view.embed
            embed.title = item.name
            embed.set_image(url=WHITE_BAR)
            if isinstance(item, Ability):
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
            elif isinstance(item, Typing):
                embed.color = item.color
                embed.set_thumbnail(url=item.emoji.url)
            else:
                embed = item.embed
                embed.url = item.url

            await ctx.send_followup(
                embed=embed,
                view=view,
                ephemeral=True,
            )
        else:
            amounts: dict[str, set[Character]] = {}
            items: list[Character] = cog.ocs.values()
            for oc in items:
                amounts.setdefault(oc.kind, set())
                amounts[oc.kind].add(oc)

            info = [(k, len(v)) for k, v in amounts.items()]
            info.sort(key=lambda x: x[1], reverse=True)

            text = "\n".join(f"{k}: {v}" for k, v in info)
            text = f"```yaml\n{text}\n```".title()

            await ctx.send_followup(
                content=text,
                ephemeral=True,
            )


def setup(bot: CustomBot):
    """Default Cog Loader

    :param bot: Bot
    :return:
    """
    bot.add_cog(Pokedex(bot))
