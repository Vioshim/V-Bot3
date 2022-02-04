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

from discord import Embed, Option, OptionChoice
from discord.commands import SlashCommandGroup
from discord.ext.commands import Cog

from src.cogs.pokedex.search import default_species_autocomplete
from src.context import ApplicationContext
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.species import Species, Variant
from src.views import CharactersView

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088"


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

    find = SlashCommandGroup(
        "find",
        "Useful pokedex info.",
        guild_ids=[719343092963999804],
    )

    @find.command(name="species")
    async def find_species(
        self,
        ctx: ApplicationContext,
        kind: Option(
            str,
            description="Filter by kind",
            choices=[
                OptionChoice(name="Legendary", value="LEGENDARY"),
                OptionChoice(name="Mythical", value="MYTHICAL"),
                OptionChoice(name="Ultra Beast", value="ULTRABEAST"),
                OptionChoice(name="Pokemon", value="POKEMON"),
                OptionChoice(name="Any", value="ANY"),
            ],
            required=False,
        ),
        species: Option(
            str,
            description="Species to look up info about.",
            autocomplete=default_species_autocomplete,
            required=False,
        ),
        variant: Option(
            bool, description="wanna see Variant OCs?", required=False
        ),
    ):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : ApplicationContext
            Context
        species : str, optional
            Species, by default None
        kind : str, optional
            Kind, by default None
        variant : bool, optional
            Variant, by default None
        """
        cog = ctx.bot.get_cog("Submission")
        if mon := Species.from_ID(species):
            self.bot.logger.info(
                "%s is reading /find species %s", str(ctx.user), mon.name
            )
            ocs = []
            for oc in cog.ocs.values():
                if (
                    variant
                    and isinstance(species := oc.species, Variant)
                    and species.base == mon
                ) or oc.species == mon:
                    ocs.append(oc)

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

            embed.title = (
                mon.name if not mon.banned else f"{mon.name} - Banned Species"
            )
            embed.color = mon.color
            embed.url = PLACEHOLDER
            embed.description = f"```yaml\n{text}\n```"

            mon_types = ", ".join(i.name for i in mon.types)
            embed.set_footer(text=f"Types: {mon_types}")
            for index, ability in enumerate(mon.abilities, start=1):
                embed.add_field(
                    name=f"Ability {index} - {ability.name}",
                    value=f"> {ability.description}",
                    inline=False,
                )
            embeds = [
                embed.set_image(url=mon.base_image),
                Embed(url=PLACEHOLDER).set_image(url=mon.base_image_shiny),
            ]
            if mon.base_image != mon.female_image:
                embeds += [
                    Embed(url=PLACEHOLDER).set_image(url=mon.female_image),
                    Embed(url=PLACEHOLDER).set_image(
                        url=mon.female_image_shiny
                    ),
                ]

            await ctx.send_response(
                embeds=embeds,
                view=view,
                ephemeral=True,
            )
        elif species:
            await ctx.send_response(
                content=f"Unable to identify the species: {species}",
                ephemeral=True,
            )
        else:
            ocs = []
            amounts: dict[str, set[Character]] = {}
            items: list[Character] = cog.ocs.values()
            for oc in items:
                amounts.setdefault(oc.kind, set())
                amounts[oc.kind].add(oc)

            await ctx.send_response(
                content="\n".join(
                    sorted(
                        amounts.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ),
                ephemeral=True,
            )


def setup(bot: CustomBot):
    """Default Cog Loader

    :param bot: Bot
    :return:
    """
    bot.add_cog(Pokedex(bot))
