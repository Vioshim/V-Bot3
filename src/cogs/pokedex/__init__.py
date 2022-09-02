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
from itertools import groupby
from random import random
from re import IGNORECASE
from re import compile as re_compile
from typing import Callable, Literal, Optional

from bs4 import BeautifulSoup
from discord import (
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Thread,
    app_commands,
)
from discord.ext import commands
from discord.utils import utcnow
from yarl import URL

from src.cogs.pokedex.search import (
    AbilityArg,
    DefaultSpeciesArg,
    FakemonArg,
    GroupByArg,
    MoveArg,
    SpeciesArg,
    age_parser,
)
from src.structures.bot import CustomBot
from src.structures.character import Character, Kind
from src.structures.mon_typing import TypingEnum
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import Fusion, Species
from src.utils.etc import WHITE_BAR
from src.views.characters_view import CharactersView
from src.views.movepool_view import MovepoolViewSelector
from src.views.species_view import SpeciesComplex

__all__ = ("Pokedex", "setup")

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088"
API = URL("https://ash-pinto-frog.glitch.me/api")


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
    async def random_oc(self, ctx: Interaction):
        """Generate a Random OC

        Parameters
        ----------
        ctx : Interaction
            Interaction
        """
        await ctx.response.defer(thinking=True)
        embed = Embed(title="Pokémon Mystery Dungeon OC Generator", color=ctx.user.color)
        embed.set_author(
            name="perchance",
            icon_url="https://cdn.discordapp.com/emojis/952524707146637342.webp",
            url="https://perchance.org/3dm3a5la78",
        )
        embed.set_image(url=WHITE_BAR)
        url = API.with_query(generator="3dm3a5la78", list="output", __cacheBust=random())
        async with self.bot.session.get(url) as data:
            if data.status == 200:
                content = await data.text()
                soup = BeautifulSoup(content, "html.parser")
                items = soup.find_all("p")
                for item in items:
                    if item.img:
                        embed.set_thumbnail(url=item.img.src)
                embed.description = "\n\n".join({x.text for x in items if x.text})
        await ctx.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
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
        embed = Embed(title="See Movepool", color=ctx.user.color, timestamp=utcnow())
        embed.set_image(url=WHITE_BAR)
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
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
            species = fakemon
            movepool = fakemon.movepool
            embed.title = f"See {fakemon.species.name}'s movepool"
        else:
            movepool = Movepool()

        if not move_id:
            view = MovepoolViewSelector(movepool=movepool, member=ctx.user, target=ctx)
        elif species:
            if methods := "\n".join(f"> • **{x.title()}**" for x in movepool.methods_for(move_id)):
                await ctx.followup.send(f"{species.name} can learn {move_id.name} through:\n{methods}.", ephemeral=True)
            else:
                await ctx.followup.send(f"{species.name} can not learn {move_id.name}.", ephemeral=True)
            return
        else:
            mons = {x for x in Species.all() if move_id in x.movepool}
            view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mons)
            view.silent_mode = True
            view.keep_working = True
            embed = view.embed
            embed.description = (
                f"The following {len(mons):02d} species and its fusions/variants can usually learn the move."
            )
            embed.title = move_id.name
            embed.color = move_id.type.color
            embed.set_image(url=move_id.image or WHITE_BAR)
            embed.set_thumbnail(url=move_id.emoji.url)

        async with view.send(embed=embed, ephemeral=True):
            self.bot.logger.info(
                "%s is reading %s's movepool",
                str(ctx.user),
                getattr(species or move_id, "name", "None"),
            )

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.rename(_type="type")
    async def find(
        self,
        ctx: Interaction,
        name: Optional[str],
        kind: Optional[Kind],
        _type: Optional[TypingEnum],
        ability: Optional[AbilityArg],
        move: Optional[MoveArg],
        species: Optional[SpeciesArg],
        fused: Optional[DefaultSpeciesArg],
        member: Optional[Member],
        location: Optional[TextChannel],
        backstory: Optional[str],
        extra: Optional[str],
        sp_ability: Optional[str],
        pronoun: Optional[Pronoun],
        age: Optional[str],
        group_by: Optional[GroupByArg],
        amount: Optional[str],
    ):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : Interaction
            Context
        name : Optional[str]
            Any name that matches(regex works).
        kind : Optional[Kind]
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
        pronoun : Optional[Pronoun]
            Pronoun to Look for
        age : Optional[str]
            OC's age. e.g. 18-24, 13, >20
        group_by : Optional[GroupByArg]
            Group by method
        amount : amount
            Groupby limit search
        """
        resp: InteractionResponse = ctx.response
        text: str = ""
        guild: Guild = ctx.guild
        cog = ctx.client.get_cog("Submission")
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        embed = Embed(title="Select the Character", url=PLACEHOLDER, color=ctx.user.color, timestamp=utcnow())
        embed.set_image(url=WHITE_BAR)
        embeds = [embed]
        total: list[Character] = list(cog.ocs.values())
        filters: list[Callable[[Character], bool]] = [lambda x: guild.get_member(x.author)]
        ocs = [species] if isinstance(species, Character) else total
        if name:
            name_pattern = re_compile(name, IGNORECASE)
            filters.append(lambda oc: name_pattern.search(oc.name))
        if age:
            filters.append(lambda oc: age_parser(age, oc))
        if isinstance(location, Thread):
            location = location.parent
        if isinstance(location, TextChannel):
            filters.append(
                lambda oc: (ch := guild.get_channel_or_thread(oc.location))
                and (ch.parent if isinstance(ch, Thread) else ch) == location
            )
        if member_id := getattr(member, "id", member):
            filters.append(lambda oc: oc.author == member_id)

        if isinstance(mon := species, Species):
            if fused and mon != fused and not isinstance(fused, Fusion) and not isinstance(mon, Fusion):
                mon = Fusion(mon, fused)
            filters.append(lambda oc: getattr(oc.species, "base", oc.species) == mon)
        elif fused and not isinstance(fused, Fusion):
            filters.append(lambda oc: isinstance(oc.species, Fusion) and fused in oc.species.bases)
            mon = fused

        if isinstance(mon, Species):
            embed.title = mon.name
            if mon.banned:
                embed.title += " - Banned Species"
            if mon_types := ", ".join(i.name for i in mon.types):
                embed.set_footer(text=f"Types: {mon_types}")
            elif isinstance(species, Fusion):
                mon_types = "\n".join(f"• {'/'.join(i.name for i in item)}" for item in mon.possible_types)
                embed.set_footer(text=f"Possible Types:\n{mon_types}")

            if ab_text := "\n".join(f"• {ab.name}" for ab in mon.abilities):
                embed.add_field(name=f"Abilities (Max {mon.max_amount_abilities})", value=ab_text)

            if isinstance(mon, Fusion):
                image1, image2 = mon.mon1.image(gender=pronoun), mon.mon2.image(gender=pronoun)
            else:
                image1, image2 = mon.image(gender=pronoun), mon.image(gender=pronoun, shiny=True)

            embeds = [embed.set_image(url=image1), Embed(url=PLACEHOLDER).set_image(url=image2)]
        if pronoun:
            filters.append(lambda oc: oc.pronoun == pronoun)
        if backstory:
            backstory_pattern = re_compile(backstory, IGNORECASE)
            filters.append(lambda oc: oc.backstory and backstory_pattern.search(oc.backstory))
        if extra:
            extra_pattern = re_compile(extra, IGNORECASE)
            filters.append(lambda oc: oc.extra and extra_pattern.search(oc.extra))
        if sp_ability:
            sp_ability_pattern = re_compile(sp_ability, IGNORECASE)
            filters.append(
                lambda oc: oc.sp_ability
                and any(sp_ability_pattern.search(sp_ability) for y in astuple(oc.sp_ability) if y)
            )
        if _type:
            filters.append(lambda oc: _type in oc.types)
            if embed.color == ctx.user.color:
                embed.color = _type.color
            embed.set_thumbnail(url=_type.emoji.url)
        if ability:
            filters.append(lambda oc: ability in oc.abilities)
            if embed.description:
                embed.add_field(name=f"Ability - {ability.name}", value=ability.description, inline=False)
            else:
                embed.title = ability.name
                embed.description = ability.description
            if battle := ability.battle:
                embed.add_field(name="Battle effect", value=battle, inline=False)
            if outside := ability.outside:
                embed.add_field(name="Usage", value=outside, inline=False)
            if random_fact := ability.random_fact:
                embed.add_field(name="Random Fact", value=random_fact, inline=False)
        if move:
            filters.append(lambda oc: move in oc.moveset)
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
                embed.add_field(name=f"{title} - Power:{power}|Acc:{acc}|PP:{pp}", value=description, inline=False)
            else:
                embed.title = title
                embed.description = description
                embed.add_field(name="Power", value=power)
                embed.add_field(name="Accuracy", value=acc)
                embed.add_field(name="PP", value=pp)
            for e in embeds:
                e.url = move.url
        if kind:
            filters.append(lambda oc: oc.kind == kind)
        ocs = [mon for mon in ocs if all(i(mon) for i in filters)]
        if group_by:
            view = group_by.generate(ctx=ctx, ocs=ocs, amount=amount)
            embed.title = f"{embed.title} - Group by {group_by.name}"
        else:
            ocs.sort(key=lambda x: x.name)
            view = CharactersView(member=ctx.user, ocs=ocs, target=ctx, keep_working=True)

        async with view.send(ephemeral=True, embeds=embeds, content=text):
            self.bot.logger.info("%s is reading /find %s", str(ctx.user), repr(ctx.namespace))

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def chart(
        self,
        ctx: Interaction,
        type1: TypingEnum,
        type2: Optional[TypingEnum],
        mode: Literal["Attacking", "Defending"] = "Defending",
        inverse: bool = False,
    ):
        """Command for getting Type Chart

        Parameters
        ----------
        ctx : Interaction
            Interaction
        type1 : Optional[TypingArg]
            Type 1
        type2 : Optional[TypingArg]
            Type 2
        mode : str
            Method to calculate
        inverse : bool
            Used for inverse battles. Defaults to False
        """
        if type2:
            type1 += type2

        embed = Embed(title=f"{type1.name} when {mode}", color=type1.color)
        if inverse:
            embed.title += "(Inverse)"
        embed.set_image(url=WHITE_BAR)

        def method(x: TypingEnum) -> float:
            if mode == "Attacking":
                return type1.when_attacking(x, inverse=inverse)
            return type1.when_attacked_by(x, inverse=inverse)

        for k, v in groupby(sorted(TypingEnum, key=method, reverse=True), key=method):
            if item := "\n".join(f"{x.emoji} {x.name}" for x in sorted(v, key=lambda x: x.name)):
                embed.add_field(name=f"Damage {k}x", value=item)

        await ctx.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Pokedex(bot))
