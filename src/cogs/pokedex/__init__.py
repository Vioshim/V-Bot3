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


from datetime import timedelta
from itertools import groupby
from random import random
from re import IGNORECASE
from re import compile as re_compile
from typing import Callable, Literal, Optional

from bs4 import BeautifulSoup
from discord import (
    Embed,
    ForumChannel,
    Guild,
    Interaction,
    Member,
    Thread,
    User,
    app_commands,
)
from discord.ext import commands
from discord.utils import get, time_snowflake
from yarl import URL

from src.cogs.pokedex.search import (
    AbilityArg,
    DefaultSpeciesArg,
    FakemonArg,
    GroupByArg,
    MoveArg,
)
from src.cogs.submission.oc_submission import ModCharactersView
from src.structures.bot import CustomBot
from src.structures.character import AgeGroup, Character, Kind, Size
from src.structures.mon_typing import TypingEnum
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import Fakemon, Fusion, Species
from src.utils.etc import WHITE_BAR
from src.views.move_view import MovepoolView
from src.views.species_view import SpeciesComplex

__all__ = ("Pokedex", "setup")

PLACEHOLDER = "https://discord.com/channels/719343092963999804/860590339327918100/1023703599538257940"
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
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def random_oc(self, ctx: Interaction[CustomBot]):
        """Generate a Random OC

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
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
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def movepool(
        self,
        ctx: Interaction[CustomBot],
        species: Optional[DefaultSpeciesArg],
        fused: Optional[DefaultSpeciesArg],
        fakemon: Optional[FakemonArg],
        move_id: Optional[MoveArg],
        level: int = 0,
        ivs: int = 0,
        evs: int = 0,
    ):
        """Check for Movepool information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        species : Optional[DefaultSpeciesArg]
            Species to look up info about
        fused : Optional[DefaultSpeciesArg]
            To check when fused
        fakemon : Optional[FakemonArg]
            Search fakemon species
        move_id : Optional[MoveArg]
            Move to lookup
        level : int
            Level to calculate stats for
        ivs : int
            IVs to calculate stats for
        evs : int
            EVs to calculate stats for
        """
        embed = Embed(
            title="See Movepool",
            description="To use this command, provide Species and/or Move.",
            color=ctx.user.color,
            timestamp=ctx.created_at,
        )
        await ctx.response.defer(ephemeral=True, thinking=True)

        mons: set[Optional[Species]] = {species, fused}
        if aux := {x for x in mons if x is not None}:
            mon = Fusion(*aux, ratio=0.5) if len(aux) == 2 else aux.pop()
            species = mon
            movepool = mon.total_movepool
        elif fakemon:
            species = fakemon
            movepool = fakemon.movepool
            embed.title = f"See {fakemon.species.name}'s movepool"
        else:
            movepool = None

        view = None
        if isinstance(movepool, Movepool):
            if move_id is None:
                view = MovepoolView(member=ctx.user, movepool=movepool, target=ctx)
            if species:
                if move_id is None:
                    embed.title = f"{species.name}'s movepool"
                elif description := "\n".join(f"> • **{x.title()}**" for x in movepool.methods_for(move_id)):
                    embed.title = f"{species.name} learns {move_id.name} by"
                    embed.description = description
                else:
                    embed.title = f"{species.name} can not learn {move_id.name}."

                if possible_types := "\n".join(f"• {'/'.join(i.name for i in x)}" for x in species.possible_types):
                    embed.add_field(name="Possible Types", value=possible_types, inline=False)

                if isinstance(species, Character):
                    base = species.species
                    data1, data2 = species.size, species.weight
                    height, val1 = (data1, 0.0) if isinstance(data1, Size) else (Size.M, data1)
                    weight, val2 = (data2, 0.0) if isinstance(data2, Size) else (Size.M, data2)
                else:
                    base = species
                    height, weight, val1, val2 = Size.M, Size.M, species.height, species.weight

                if isinstance(base, Fakemon):
                    embed.add_field(name="Height", value=height.height_info(val1), inline=False)
                    embed.add_field(name="Weight", value=weight.weight_info(val2), inline=False)
                else:
                    if isinstance(base, Fusion) and len(base.bases) >= 2:
                        h1, *_, h2 = sorted(base.bases, key=lambda x: x.height)
                        w1, *_, w2 = sorted(base.bases, key=lambda x: x.weight)
                        h1, h2, h3 = h1.height, val1, h2.height
                        w1, w2, w3 = w1.weight, val2, w2.weight
                    else:
                        h1, h2, h3 = val1, val1, val1
                        w1, w2, w3 = val2, val2, val2

                    embed.add_field(name="Height (Min)", value=Size.XXXS.height_info(h1))
                    embed.add_field(name="Height (Avg)", value=height.height_info(h2))
                    embed.add_field(name="Height (Max)", value=Size.XXXL.height_info(h3))

                    embed.add_field(name="Weight (Min)", value=Size.XXXS.weight_info(w1))
                    embed.add_field(name="Weight (Avg)", value=weight.weight_info(w2))
                    embed.add_field(name="Weight (Max)", value=Size.XXXL.weight_info(w3))

                if isinstance(species, Species):
                    if evs or ivs:
                        level = level or 100

                    if level:
                        evs = evs or 252
                        ivs = ivs or 31

                        HP, ATK, DEF, SPA, SPD, SPE = (
                            species.HP,
                            species.ATK,
                            species.DEF,
                            species.SPA,
                            species.SPD,
                            species.SPE,
                        )
                        cHP = 1
                        cATK, cDEF, cSPA, cSPD, cSPE = (
                            int((ivs + 2 * ATK + (evs // 4)) * level / 100) + 5,
                            int((ivs + 2 * DEF + (evs // 4)) * level / 100) + 5,
                            int((ivs + 2 * SPA + (evs // 4)) * level / 100) + 5,
                            int((ivs + 2 * SPD + (evs // 4)) * level / 100) + 5,
                            int((ivs + 2 * SPE + (evs // 4)) * level / 100) + 5,
                        )

                        if ab := get(species.abilities, name="Wonder Guard"):
                            hp_value = ab.name
                        else:
                            cHP = int((ivs + 2 * HP + (evs // 4)) * level / 100) + 10 + level
                            hp_value = f"{0.9*cHP:.0f} - {1.1*cHP:.0f}"
                        embed.add_field(name=f"{HP=}, {cHP=}", value=hp_value)
                        embed.add_field(name=f"{ATK:}, {cATK=}", value=f"{0.9*cATK:.0f} - {1.1*cATK:.0f}")
                        embed.add_field(name=f"{DEF=}, {cDEF=}", value=f"{0.9*cDEF:.0f} - {1.1*cDEF:.0f}")
                        embed.add_field(name=f"{SPA=}, {cSPA=}", value=f"{0.9*cSPA:.0f} - {1.1*cSPA:.0f}")
                        embed.add_field(name=f"{SPD=}, {cSPD=}", value=f"{0.9*cSPD:.0f} - {1.1*cSPD:.0f}")
                        embed.add_field(name=f"{SPE=}, {cSPE=}", value=f"{0.9*cSPE:.0f} - {1.1*cSPE:.0f}")

        elif move_id:
            mons = {x for x in Species.all() if move_id in x.movepool}
            db = ctx.client.mongo_db("Characters")
            date_value = time_snowflake(ctx.created_at - timedelta(days=14))
            key = {
                "server": ctx.guild_id,
                "$or": [
                    {"id": {"$gte": date_value}},
                    {"location": {"$gte": date_value}},
                    {"last_used": {"$gte": date_value}},
                ],
            }
            if role := get(ctx.guild.roles, name="Registered"):
                key["author"] = {"$in": [x.id for x in role.members]}
            ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
            view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mons, keep_working=True, ocs=ocs)
            embed = view.embed
            embed.description = (
                f"The following {len(mons):02d} species and its fusions/variants can usually learn the move."
            )
            embed.title = move_id.name
            embed.color = move_id.type.color
            embed.set_thumbnail(url=move_id.emoji.url)

        self.bot.logger.info(
            "%s is reading %s's movepool",
            str(ctx.user),
            getattr(species or move_id, "name", "None"),
        )

        if view is None:
            await ctx.followup.send(embed=embed, ephemeral=True)
        else:
            await view.simple_send(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def fusion(
        self,
        ctx: Interaction[CustomBot],
        species1: DefaultSpeciesArg,
        species2: DefaultSpeciesArg,
        ratio: Literal[10, 20, 30, 40, 50, 60, 70, 80, 90] = 50,
    ):
        """Command to check Fusion Information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        species1 : DefaultSpeciesArg
            First Species
        species2 : DefaultSpeciesArg
            Second Species
        ratio : int
            Ratio of Fusion, defaults to 50%
        """
        await ctx.response.defer(ephemeral=True, thinking=True)
        mon = Fusion(species1, species2, ratio=ratio / 100)

        ratio_a, ratio_b = ratio / 100, 1 - ratio / 100

        embed = Embed(
            title=f"{ratio_a:.1%} {species1.name} + {ratio_b:.1%} {species2.name}",
            color=ctx.user.color,
        )

        if mon.banned or not mon.egg_groups:
            embed.title += " - Banned Fusion"

        if mon_types := ", ".join(i.name for i in mon.types):
            embed.set_footer(text=f"Types: {mon_types}")

        elif possible_types := "\n".join(f"• {'/'.join(i.name for i in x)}" for x in mon.possible_types):
            embed.set_footer(text=f"Possible Types:\n{possible_types}")

        if ab_text := "\n".join(f"• {ab.name}" for ab in mon.abilities):
            amount = min(len(mon.abilities), 2)
            embed.add_field(name=f"Abilities (Max {amount})", value=ab_text)

        if mon.abilities:
            embed.add_field(
                name="Abilities",
                value="\n".join(f"• {ab.name}" for ab in mon.abilities),
                inline=False,
            )

        await ctx.followup.send(embed=embed)

    @app_commands.command()
    @app_commands.rename(_type="type", sp_ability="unique_trait")
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def find(
        self,
        ctx: Interaction[CustomBot],
        name: Optional[str],
        kind: Optional[Kind],
        _type: Optional[TypingEnum],
        ability: Optional[AbilityArg],
        move: Optional[MoveArg],
        species: Optional[DefaultSpeciesArg],
        fused: Optional[DefaultSpeciesArg],
        member: Optional[Member | User],
        location: Optional[ForumChannel | Thread],
        backstory: Optional[str],
        personality: Optional[str],
        extra: Optional[str],
        sp_ability: Optional[str],
        pronoun: Optional[Pronoun],
        age: Optional[AgeGroup],
        group_by: Optional[GroupByArg],
        amount: Optional[str],
        active: bool = True,
    ):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : Interaction[CustomBot]
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
        species : Optional[DefaultSpeciesArg]
            Species to look up info about.
        fused : Optional[DefaultSpeciesArg]
            Search Fusions that contain the species
        member : Optional[Member]
            Member to filter
        location : Optional[ForumChannel | Thread]
            Location to filter
        backstory : Optional[str]
            Any words to look for in backstories
        personality : Optional[str]
            Any words to look for in the personality info
        extra : Optional[str]
            Any words to look for in the extra info
        sp_ability : Optional[str]
            Any words to look for in Sp Abilities
        pronoun : Optional[Pronoun]
            Pronoun to Look for
        age : Optional[AgeGroup]
            OC's Age group.
        group_by : Optional[GroupByArg]
            Group by method
        amount : amount
            Groupby limit search
        active : bool
            modified/used since last 2 weeks. True by default
        """
        text: str = ""
        guild: Guild = ctx.guild
        await ctx.response.defer(ephemeral=True, thinking=True)
        embed = Embed(title="Select the Character", url=PLACEHOLDER, color=ctx.user.color, timestamp=ctx.created_at)
        embed.set_image(url=WHITE_BAR)
        embeds = [embed]
        db = self.bot.mongo_db("Characters")
        total = [Character.from_mongo_dict(x) async for x in db.find({"server": ctx.guild_id})]
        filters: list[Callable[[Character], bool]] = []
        ocs = [species] if isinstance(species, Character) else total
        if name:
            name_pattern = re_compile(name, IGNORECASE)
            filters.append(lambda oc: name_pattern.search(oc.name))
        if age:
            filters.append(lambda oc: oc.age == age)
        if isinstance(location, ForumChannel):
            filters.append(
                lambda oc: (ch := guild.get_channel_or_thread(oc.location))
                and (ch.parent if isinstance(ch, Thread) else ch) == location
            )
        if isinstance(location, Thread):
            filters.append(lambda oc: oc.location == location.id)
        if member_id := getattr(member, "id", member):
            filters.append(lambda oc: oc.author == member_id)
        else:
            filters.append(lambda x: guild.get_member(x.author))

        if isinstance(mon := species, Species):
            if fused and mon != fused and not isinstance(fused, Fusion) and not isinstance(mon, Fusion):
                mon = Fusion(mon, fused, ratio=0.5)
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
                amount = min(len(mon.abilities), 2)
                embed.add_field(name=f"Abilities (Max {amount})", value=ab_text)

            if isinstance(mon, Fusion):
                image1, image2 = mon.mon1.image(gender=pronoun), mon.mon2.image(gender=pronoun)
            else:
                image1, image2 = mon.image(gender=pronoun), mon.image(gender=pronoun, shiny=True)

            embeds = [embed.set_image(url=image1), Embed(url=PLACEHOLDER).set_image(url=image2)]
        if pronoun:
            filters.append(lambda oc: pronoun in oc.pronoun)
        if backstory:
            backstory_pattern = re_compile(backstory, IGNORECASE)
            filters.append(lambda oc: oc.backstory and backstory_pattern.search(oc.backstory))
        if personality:
            personality_pattern = re_compile(personality, IGNORECASE)
            filters.append(lambda oc: oc.personality and personality_pattern.search(oc.personality))
        if extra:
            extra_pattern = re_compile(extra, IGNORECASE)
            filters.append(lambda oc: oc.extra and extra_pattern.search(oc.extra))
        if sp_ability:
            sp_ability_pattern = re_compile(sp_ability, IGNORECASE)
            filters.append(lambda oc: oc.sp_ability and any(map(sp_ability_pattern.search, oc.sp_ability.params)))
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
            description = move.description
            if embed.color == ctx.user.color:
                embed.color = move.color
            embed.set_thumbnail(url=move.type.emoji.url)

            if embed.description:
                embed.add_field(name=title, value=description[:1024], inline=False)
            else:
                embed.title = title
                embed.description = description
        if kind:
            filters.append(lambda oc: oc.kind == kind)

        date = ctx.created_at - timedelta(days=14)
        if active:
            filters.append(lambda x: x.last_used_at >= date)
        else:
            filters.append(lambda x: x.last_used_at < date)

        ocs = [mon for mon in ocs if all(i(mon) for i in filters)]

        if group_by:
            view = group_by.generate(ctx=ctx, ocs=ocs, amount=amount)
            embed.title = f"{embed.title} - Group by {group_by.name}"
        else:
            ocs.sort(key=lambda x: x.name)
            view = ModCharactersView(member=ctx.user, ocs=ocs, target=ctx, keep_working=True)

        async with view.send(ephemeral=True, embeds=embeds, content=text):
            namespace = " ".join(f"{k}={v}" for k, v in ctx.namespace)
            self.bot.logger.info("%s is reading /find %s", str(ctx.user), namespace)

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def chart(
        self,
        ctx: Interaction[CustomBot],
        type1: TypingEnum,
        type2: Optional[TypingEnum],
        mode: Literal["Attacking", "Defending"] = "Defending",
        inverse: bool = False,
    ):
        """Command for getting Type Chart

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
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

        if mode == "Attacking":

            def method(x: TypingEnum) -> float:
                return type1.when_attacking(x, inverse=inverse)

        else:

            def method(x: TypingEnum) -> float:
                return type1.when_attacked_by(x, inverse=inverse)

        for k, v in groupby(sorted(TypingEnum, key=method, reverse=True), key=method):
            if item := "\n".join(f"{x.emoji} {x.name}" for x in sorted(v, key=lambda x: x.name)):
                embed.add_field(name=f"Damage {k}x", value=item)

        await ctx.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Pokedex(bot))
