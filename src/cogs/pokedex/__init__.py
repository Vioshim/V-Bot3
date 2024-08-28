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


from itertools import groupby
from random import choice, random
from re import IGNORECASE
from re import compile as re_compile
from typing import Callable, Literal, Optional

from discord import Embed, Guild, TextChannel, app_commands
from discord.ext import commands
from discord.utils import get
from yarl import URL

from src.cogs.pokedex.search import (
    AbilityArg,
    DefaultSpeciesArg,
    FindFlags,
    GroupBy,
    MoveArg,
    MovepoolFlags,
)
from src.cogs.submission.oc_submission import ModCharactersView
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mon_typing import TypingEnum
from src.structures.move import Category
from src.structures.movepool import Movepool
from src.structures.species import Fusion, Species
from src.utils.etc import WHITE_BAR, MapElements
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

    @commands.hybrid_group(aliases=["pokedex"])
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    @app_commands.allowed_installs(guilds=True, users=False)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def dex(self, ctx: commands.Context[CustomBot]):
        pass

    @dex.command()
    async def movepool(self, ctx: commands.Context[CustomBot], *, flags: MovepoolFlags):
        """Check for Movepool information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        """
        await ctx.defer(ephemeral=True)
        embed = Embed(
            title="See Movepool",
            description="To use this command, provide Species and/or Move.",
            color=ctx.author.color,
            timestamp=ctx.message.created_at,
        )

        if mons := {flags.species, flags.fused1, flags.fused2} - {None}:
            mon = Fusion(*mons)
            species = mon
            movepool = mon.total_movepool
        elif species := flags.fakemon:
            movepool = flags.fakemon.movepool
            embed.title = f"See {species.name}'s movepool"
        else:
            movepool = Movepool()

        if flags.size:
            scale = species.age.scale if isinstance(species, Character) else 1
            embed.add_field(name="Height", value=flags.size.label_for(scale))

        view = None
        if flags.move_id is None:
            view = MovepoolView(member=ctx.author, movepool=movepool, target=ctx)

        if species:
            if flags.move_id is None:
                embed.title = f"{species.name}'s movepool"
            elif description := "\n".join(f"> • **{x.title()}**" for x in movepool.methods_for(flags.move_id)):
                embed.title = f"{species.name} learns {flags.move_id.name} by"
                embed.description = description
            else:
                embed.title = f"{species.name} can not learn {flags.move_id.name}."

            if possible_types := "\n".join(f"• {'/'.join(i.name for i in x)}" for x in species.possible_types):
                embed.add_field(name="Possible Types", value=possible_types, inline=False)

        elif flags.move_id:
            mons = {x for x in Species.all() if flags.move_id in x.movepool}
            db = ctx.bot.mongo_db("Characters")
            key = {"server": ctx.guild.id}
            if role := get(ctx.guild.roles, name="Roleplayer"):
                key["author"] = {"$in": [x.id for x in role.members]}
            ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
            view = SpeciesComplex(member=ctx.author, target=ctx, mon_total=mons, keep_working=True, ocs=ocs)
            embed = view.embed
            embed.description = (
                f"The following {len(mons):02d} species and its fusions/variants can usually learn the move."
            )
            embed.title = flags.move_id.name
            embed.color = flags.move_id.type.color
            embed.set_thumbnail(url=flags.move_id.emoji.url)

        self.bot.logger.info(
            "%s is reading %s's movepool",
            str(ctx.author),
            getattr(species or flags.move_id, "name", "None"),
        )

        if view is None:
            await ctx.reply(embed=embed, ephemeral=True)
        else:
            await view.simple_send(embed=embed, ephemeral=True)

    @dex.command()
    async def species(self, ctx: commands.Context[CustomBot], *, species: DefaultSpeciesArg):
        """Command to check Species Information
        
        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        species : DefaultSpeciesArg
            Species to check
        """
        embed = Embed(title=species.name, color=ctx.author.color)
        for k, v in species.dex.items():
            embed.add_field(name=k, value=v, inline=False)
        await ctx.reply(embed=embed, ephemeral=True)

    @dex.command()
    async def move(self, ctx: commands.Context[CustomBot], move: MoveArg, *, category: Optional[Category] = None,):
        """Command to check Move Information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        move : MoveArg
            Move to check
        category : Optional[Category]
            Category to check
        """ 
        embed = Embed(title=move.name, color=ctx.author.color)
        category = category or move.category
        embed.set_footer(text=category.name, icon_url=category.emoji.url)
        for k, v in move.dex_category(category).items():
            embed.add_field(name=k, value=v, inline=False)
        await ctx.reply(embed=embed, ephemeral=True)

    @dex.command()
    async def chart(
        self,
        ctx: commands.Context[CustomBot],
        type1: TypingEnum,
        type2: Optional[TypingEnum],
        type3: Optional[TypingEnum],
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
        type3 : Optional[TypingArg]
            Type 3
        mode : str
            Method to calculate
        inverse : bool
            Used for inverse battles. Defaults to False
        """
        if type2:
            type1 += type2

        if type3:
            type1 += type3

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

        items = [x for x in TypingEnum if x not in (TypingEnum.Shadow, TypingEnum.Typeless)]
        items.sort(key=method, reverse=True)
        for k, v in groupby(items, key=method):
            if item := "\n".join(f"{x.emoji} {x.name}" for x in sorted(v, key=lambda x: x.name)):
                embed.add_field(name=f"Damage {k}x", value=item)

        await ctx.reply(embed=embed, ephemeral=True)

    @dex.command()
    async def type(self, ctx: commands.Context[CustomBot], type: TypingEnum):
        """Command to check Type Information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        type : TypingEnum
            Type to check
        """
        embed = Embed(title=type.name, color=type.color)
        embed.set_thumbnail(url=type.emoji.url)
        for k, v in type.dex.items():
            embed.add_field(name=k, value=v, inline=False)
        await ctx.reply(embed=embed, ephemeral=True)

    @dex.command()
    async def ability(self, ctx: commands.Context[CustomBot], *, ability: AbilityArg):
        """Command to check Ability Information

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        ability : AbilityArg
            Ability to check
        """
        embed = Embed(title=ability.name, color=ctx.author.color)
        for k, v in ability.dex.items():
            embed.add_field(name=k, value=v, inline=False)
        await ctx.reply(embed=embed, ephemeral=True)

    @dex.command()
    async def fusion(
        self,
        ctx: commands.Context[CustomBot],
        species1: DefaultSpeciesArg,
        species2: DefaultSpeciesArg,
        species3: Optional[DefaultSpeciesArg],
    ):
        """Command to check Fusion Information

        Parameters
        ----------
        ctx : Context[CustomBot]
            Context[CustomBot]
        species1 : DefaultSpeciesArg
            First Species
        species2 : DefaultSpeciesArg
            Second Species
        species3 : Optional[DefaultSpeciesArg]
            Third Species
        """
        items = {species1, species2, species3} - {None}
        mon = Fusion(*items)
        embed = Embed(title=mon.name, color=ctx.author.color)

        if mon.banned:
            embed.title = f"{embed.title} - Banned Fusion"

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

        await ctx.reply(embed=embed, ephemeral=True)

    @commands.hybrid_command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def find(self, ctx: commands.Context[CustomBot], *, flags: FindFlags):
        """Command to obtain Pokemon entries and its ocs

        Parameters
        ----------
        ctx : Context[CustomBot]
            Context[CustomBot]
        """
        await ctx.defer(ephemeral=True)
        text: str = ""
        guild: Guild = ctx.guild
        embed = Embed(title="Select the Character", url=PLACEHOLDER, color=ctx.author.color)
        embed.set_image(url=WHITE_BAR)
        embeds = [embed]
        db = self.bot.mongo_db("Characters")
        total = [Character.from_mongo_dict(x) async for x in db.find({"server": guild.id})]
        filters: list[Callable[[Character], bool]] = []
        ocs = [flags.species] if isinstance(flags.species, Character) else total
        if flags.name:
            name_pattern = re_compile(flags.name, IGNORECASE)
            filters.append(lambda oc: name_pattern.search(oc.name))
        if flags.age:
            filters.append(lambda oc: oc.age == flags.age)

        if member_id := getattr(flags.member, "id", flags.member):
            filters.append(lambda oc: oc.author == member_id)
        else:
            filters.append(lambda x: guild.get_member(x.author))

        items = {flags.species, flags.fused1, flags.fused2} - {None}
        mon = Fusion(*items)

        if mon.bases:
            filters.append(
                lambda oc: (
                    mon.bases.issubset(oc.species.bases)
                    if isinstance(oc.species, Fusion)
                    else getattr(oc.species, "base", oc.species) == mon
                )
            )
            embed.title = mon.name
            if mon.banned:
                embed.title += " - Banned Species"
            mon_types = "\n".join(f"• {'/'.join(i.name for i in item)}" for item in mon.possible_types)
            embed.set_footer(text=f"Possible Types:\n{mon_types}")

            if ab_text := "\n".join(f"• {ab.name}" for ab in mon.abilities):
                embed.add_field(name=f"Abilities (Max {min(len(mon.abilities), 2)})", value=ab_text)

        if flags.pronoun:
            filters.append(lambda oc: flags.pronoun in oc.pronoun)
        if flags.backstory:
            backstory_pattern = re_compile(flags.backstory, IGNORECASE)
            filters.append(lambda oc: oc.backstory and backstory_pattern.search(oc.backstory))
        if flags.personality:
            personality_pattern = re_compile(flags.personality, IGNORECASE)
            filters.append(lambda oc: oc.personality and personality_pattern.search(oc.personality))
        if flags.extra:
            extra_pattern = re_compile(flags.extra, IGNORECASE)
            filters.append(lambda oc: oc.extra and extra_pattern.search(oc.extra))
        if flags.unique_trait:
            sp_ability_pattern = re_compile(flags.unique_trait, IGNORECASE)
            filters.append(lambda oc: oc.sp_ability and any(map(sp_ability_pattern.search, oc.sp_ability.params)))
        if flags.type:
            filters.append(lambda oc: flags.type in oc.types)
            if embed.color == ctx.author.color:
                embed.color = flags.type.color
            embed.set_thumbnail(url=flags.type.emoji.url)

        if flags.move:
            filters.append(lambda oc: flags.move in oc.moveset)
            title = repr(flags.move)
            if flags.move.banned:
                title += " - Banned Move"
            description = flags.move.description
            if embed.color == ctx.author.color:
                embed.color = flags.move.color
            embed.set_thumbnail(url=flags.move.type.emoji.url)

            if embed.description:
                embed.add_field(name=title, value=description[:1024], inline=False)
            else:
                embed.title = title
                embed.description = description
        if flags.kind:
            filters.append(lambda oc: oc.kind == flags.kind)
        if flags.weight:
            filters.append(lambda oc: oc.weight == flags.weight)

        ocs = [mon for mon in ocs if all(i(mon) for i in filters)]

        if flags.group_by:
            group_by = GroupBy[flags.group_by.name]
            view = group_by.generate(ctx=ctx, ocs=ocs, flags=flags)
            embed.title = f"{embed.title} - Group by {group_by.name}"
        else:
            ocs.sort(key=lambda x: x.name)
            view = ModCharactersView(member=ctx.author, ocs=ocs, target=ctx, keep_working=True)

        async with view.send(ephemeral=True, embeds=embeds, content=text):
            namespace = " ".join(f"{k}={v}" for k, v in flags if v is not None)
            self.bot.logger.info("%s is reading /find %s", str(ctx.author), namespace)

    @commands.hybrid_group(fallback="location", aliases=["location"])
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def random(self, ctx: commands.Context[CustomBot], *, category: Optional[MapElements] = None):
        """Command to get Random RP Channel

        Parameters
        ----------
        ctx : Interaction[CustomBot]
            Interaction[CustomBot]
        category : Optional[MapElements]
            Category to choose from
        """
        item = category or choice(list(MapElements))
        cat_id = item.value.category
        if not (cat := ctx.guild.get_channel(cat_id)):
            cat = await ctx.guild.fetch_channel(cat_id)

        channels = [x for x in cat.channels if isinstance(x, TextChannel)]
        channel = choice(channels)

        embed = Embed(
            title=f"Category: {item.name}",
            description=channel.mention,
            color=ctx.author.color,
        )

        await ctx.reply(embed=embed, ephemeral=True)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Pokedex(bot))
