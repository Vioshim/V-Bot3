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


from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from itertools import groupby
from typing import Any, Callable, Generic, Iterable, Optional, TypeVar

from discord import ForumChannel, Guild, Interaction, Member, TextChannel, Thread, User
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ext import commands
from discord.ui import Select, select
from rapidfuzz import process

from src.cogs.submission.oc_submission import ModCharactersView
from src.pagination.complex import Complex
from src.structures.ability import Ability, UTraitKind
from src.structures.bot import CustomBot
from src.structures.character import AgeGroup, Character, Kind, Nature, Size
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.pokeball import Pokeball
from src.structures.pronouns import Pronoun
from src.structures.species import (
    CustomMega,
    CustomParadox,
    CustomUltraBeast,
    Fakemon,
    Fusion,
    Species,
    Variant,
)

STANDARD = [
    Kind.Common,
    Kind.Mythical,
    Kind.Legendary,
    Kind.UltraBeast,
    Kind.Mega,
    Kind.Paradox,
]

OPERATORS = {
    "<=": lambda x, y: x <= y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    ">": lambda x, y: x > y,
}


def item_name(mon: Character | Species) -> str:
    if isinstance(mon, Character) and mon.species:
        mon = mon.species
    return getattr(mon, "name", mon)


def item_value(mon: Character | Species):
    if isinstance(mon, Character) and mon.kind in STANDARD and mon.species:
        mon = mon.species
    return str(mon.id)


def foo(x: str) -> Optional[int]:
    x = x.strip()
    if x.isdigit():
        return int(x)


def amount_parser(text: Optional[str], ocs: Iterable[Character]):
    ocs = frozenset(ocs)
    if not text:
        return bool(ocs)

    amount = len(ocs)

    text = text.replace(",", ";").replace("|", ";")
    for item in map(lambda x: x.strip(), text.split(";")):
        if item.isdigit() and int(item) == amount:
            return True

        op = [val for x in item.split("-") if isinstance(val := foo(x), int)]
        if len(op) == 2 and op[0] <= amount <= op[1]:
            return True

        for key, operator in filter(lambda x: x[0] in text, OPERATORS.items()):
            op = [foo(x) or 0 for x in item.split(key)]
            if operator(op[0], amount) if op[0] else operator(amount, op[1]):
                return True

    return False


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
    if not text:
        return True

    age = oc.age or 0

    text = text.replace(",", ";").replace("|", ";")
    for item in map(lambda x: x.strip(), text.split(";")):
        if item.isdigit() and int(item) == age:
            return True

        op = [val for x in item.split("-") if isinstance(val := foo(x), int)]
        if len(op) == 2 and op[0] <= age <= op[1]:
            return age != 0

        for key, operator in filter(lambda x: x[0] in text, OPERATORS.items()):
            op = [foo(x) or 0 for x in item.split(key)]
            if operator(op[0], age) if op[0] else operator(age, op[1]):
                return age != 0

    return False


class MoveTransformer(commands.Converter[str], Transformer):
    async def transform(self, _: Interaction[CustomBot], value: str, /):
        if move := Move.deduce(value):
            return move

        raise ValueError(f"Move {value!r} Not found.")

    async def autocomplete(self, _: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        items = list(Move.all())
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in set(options)]

    async def convert(self, _: commands.Context[CustomBot], argument: str, /):
        if move := Move.deduce(argument):
            return move

        raise ValueError(f"Move {argument!r} Not found.")


MoveArg = Transform[Move, MoveTransformer]


class SpeciesTransformer(commands.Converter[str], Transformer):
    async def transform(self, itx: Interaction[CustomBot], value: Optional[str], /):
        db = itx.client.mongo_db("Characters")
        value = value or ""
        if value.isdigit() and (item := await db.find_one({"id": int(value), "server": itx.guild_id})):
            return Character.from_mongo_dict(item)
        if oc := Species.single_deduce(value):
            return oc
        raise ValueError(f"Species {value!r} not found")

    async def convert(self, ctx: commands.Context[CustomBot], argument: str, /):
        db = ctx.bot.mongo_db("Characters")
        argument = argument or ""
        if argument.isdigit() and (item := await db.find_one({"id": int(argument), "server": ctx.guild.id})):
            return Character.from_mongo_dict(item)
        if oc := Species.single_deduce(argument):
            return oc
        raise ValueError(f"Species {argument!r} not found")

    async def autocomplete(self, ctx: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        db = ctx.client.mongo_db("Characters")
        guild: Guild = ctx.guild
        key = {"server": ctx.guild_id}
        pk_filters: list[Callable[[Species], bool]] = []
        oc_filters: list[Callable[[Character], bool]] = []

        if member := ctx.namespace.member:
            key["author"] = member.id
        else:
            oc_filters.append(lambda x: bool(guild.get_member(x.author)))

        if (ability := ctx.namespace.ability) and (ability := Ability.from_ID(ability)):
            key["abilities"] = {"$in": [ability.id]}
            pk_filters.append(lambda x: ability in x.abilities)

        if (mon_type := ctx.namespace.type) and (mon_type := TypingEnum.deduce(mon_type)):
            key["types"] = {"$in": [str(mon_type)]}
            pk_filters.append(lambda x: mon_type in x.types)

        if (move := ctx.namespace.move) and (move := Move.from_ID(move)):
            key["moveset"] = {"$in": [move.id]}
            pk_filters.append(lambda x: move in x.total_movepool)

        if fused := Species.from_ID(ctx.namespace.fused):
            key["species.fusion.species"] = {"$in": fused.id.split("/")}
            pk_filters.append(lambda x: fused == x)
        elif kind := Kind.associated(ctx.namespace.kind):
            oc_filters.append(lambda x: x.kind == kind)
            pk_filters.append(lambda x: isinstance(x, kind.value))

        if location := ctx.namespace.location:

            def foo2(oc: Character) -> bool:
                ref = ch.parent_id if (ch := guild.get_thread(oc.location)) else oc.location
                return oc.species and ref == location.id

            oc_filters.append(foo2)

        if not (
            ocs := {
                o async for x in db.find(key) if (o := Character.from_mongo_dict(x)) and all(i(o) for i in oc_filters)
            }
        ):
            ocs = [x for x in Species.all() if all(i(x) for i in pk_filters)]

        if data := process.extract(value, choices=ocs, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in data]
        elif not value:
            options = list(ocs)[:25]

        entries = {item_name(x): item_value(x) for x in options}
        return [Choice(name=k, value=v) for k, v in entries.items()]


class DefaultSpeciesTransformer(commands.Converter[str], Transformer):
    cache: dict = {}

    async def convert(self, _: commands.Context[CustomBot], argument: str, /):
        if item := Species.single_deduce(argument):
            return item

        raise ValueError(f"Species {argument!r} not found")

    async def transform(self, _: Interaction[CustomBot], value: Optional[str], /):
        if item := Species.single_deduce(value):
            return item

        raise ValueError(f"Species {value!r} not found")

    async def autocomplete(self, ctx: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        if ctx.command and ctx.command.name == "find" and (fused := Species.from_ID(ctx.namespace.species)):
            db = ctx.client.mongo_db("Characters")
            items = [
                base
                async for x in db.find(
                    {
                        "$or": [
                            {"species.chimera": {"$in": fused.id.split("/")}},
                            {"species.fusion.species": {"$in": fused.id.split("/")}},
                        ],
                        "server": ctx.guild_id,
                    }
                )
                if (oc := Character.from_mongo_dict(x))
                and isinstance(oc.species, Fusion)
                and ctx.guild.get_member(oc.author)
                for base in oc.species.bases
                if base != fused
            ]
        else:
            items = [*Species.all()]
        if options := process.extract(value or "", choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in options]


SpeciesArg = Transform[Species, SpeciesTransformer]
DefaultSpeciesArg = Transform[Species, DefaultSpeciesTransformer]


class AbilityTransformer(commands.Converter[str], Transformer):
    async def convert(self, _: commands.Context[CustomBot], argument: str, /):
        if item := Ability.from_ID(argument):
            return item

        raise ValueError(f"Ability {argument!r} not found")

    async def transform(self, _: Interaction[CustomBot], value: Optional[str], /):
        if item := Ability.from_ID(value):
            return item

        raise ValueError(f"Ability {value!r} not found")

    async def autocomplete(self, _: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        items = list(Ability.all())
        if options := process.extract(value or "", choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in options]


AbilityArg = Transform[Ability, AbilityTransformer]


class FakemonTransformer(commands.Converter[str], Transformer):
    async def process(self, bot: CustomBot, value: str, guild_id: int):
        db = bot.mongo_db("Characters")
        oc: Optional[Character] = None
        if value.isdigit() and (item := await db.find_one({"id": int(value), "server": guild_id})):
            oc = Character.from_mongo_dict(item)
        elif ocs := process.extractOne(
            value or "",
            choices=[
                Character.from_mongo_dict(x)
                async for x in db.find(
                    {
                        "species.evolves_from": {"$exists": 1},
                        "species.base": {"$exists": 0},
                        "server": guild_id,
                    }
                )
            ],
            processor=item_name,
            score_cutoff=60,
        ):
            oc = ocs[0]
        if not oc:
            raise ValueError(f"Fakemon {value!r} not found.")
        return oc

    async def transform(self, itx: Interaction[CustomBot], value: Optional[str], /):
        await self.process(itx.client, value, itx.guild_id)

    async def convert(self, ctx: commands.Context[CustomBot], argument: str, /):
        await self.process(ctx.bot, argument, ctx.guild and ctx.guild.id)

    async def autocomplete(self, ctx: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        guild: Guild = ctx.guild
        db = ctx.client.mongo_db("Characters")
        mons = [
            Character.from_mongo_dict(x)
            async for x in db.find(
                {
                    "species.evolves_from": {"$exists": 1},
                    "species.base": {"$exists": 0},
                    "server": ctx.guild_id,
                }
            )
            if guild.get_member(x["author"])
        ]
        if options := process.extract(value or "", choices=mons, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = mons[:25]
        return [Choice(name=x.species.name, value=str(x.id)) for x in set(options)]


FakemonArg = Transform[Character, FakemonTransformer]


class GroupByComplex(Complex[tuple[str, list[Character]]]):
    def __init__(
        self,
        member: Member,
        target: Interaction[CustomBot],
        data: dict[str, list[Character]],
        inner_parser: Callable[[Any, list[Character]], tuple[str, str]],
    ):
        self.data = data
        super(GroupByComplex, self).__init__(
            member=member,
            target=target,
            parser=lambda x: inner_parser(x, data.get(x, [])),
            values=list(data),
            keep_working=True,
            auto_text_component=True,
        )

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction[CustomBot], sct: Select) -> None:
        key = self.current_choice
        ocs = self.data.get(key, [])
        view = ModCharactersView(member=interaction.user, target=interaction, ocs=ocs, keep_working=True)
        async with view.send(ephemeral=True):
            await super(GroupByComplex, self).select_choice(interaction, sct)


D = TypeVar("D")


class MovepoolFlags(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix=":"):
    species: Optional[DefaultSpeciesArg] = commands.flag(
        positional=True,
        default=None,
        description="Species to look up info about",
    )
    fused1: Optional[DefaultSpeciesArg] = commands.flag(default=None, description="To check when fused")
    fused2: Optional[DefaultSpeciesArg] = commands.flag(default=None, description="To check when fused")
    fakemon: Optional[FakemonArg] = commands.flag(default=None, description="Search fakemon species")
    move_id: Optional[MoveArg] = commands.flag(default=None, description="Move to lookup")
    level: int = commands.flag(default=0, description="Level to calculate stats for")
    ivs: int = commands.flag(default=0, description="IVs to calculate stats for")
    evs: int = commands.flag(default=0, description="EVs to calculate stats for")


class GroupByArg(StrEnum):
    Kind = auto()
    Shape = auto()
    Age = auto()
    Species = auto()
    EvoLine = auto()
    Type = auto()
    Pronoun = auto()
    Move = auto()
    Ability = auto()
    Location = auto()
    Member = auto()
    HiddenPower = auto()
    Nature = auto()
    UniqueTrait = auto()
    Pokeball = auto()
    Height = auto()
    Weight = auto()


class FindFlags(commands.FlagConverter, case_insensitive=True, delimiter=" ", prefix=":"):
    name: Optional[str] = commands.flag(default=None, description="Name to look for", positional=True)
    kind: Optional[Kind] = commands.flag(default=None, description="Kind to look for")
    type: Optional[TypingEnum] = commands.flag(default=None, description="Type to look for")
    ability: Optional[AbilityArg] = commands.flag(default=None, description="Ability to look for")
    move: Optional[MoveArg] = commands.flag(default=None, description="Move to look for")
    species: Optional[DefaultSpeciesArg] = commands.flag(default=None, description="Species to look for")
    fused1: Optional[DefaultSpeciesArg] = commands.flag(default=None, description="Fusion to look for")
    fused2: Optional[DefaultSpeciesArg] = commands.flag(default=None, description="Fusion to look for")
    member: Optional[Member | User] = commands.flag(default=None, description="Member to look for")
    location: Optional[TextChannel | ForumChannel | Thread] = commands.flag(
        default=None, description="Location to look for"
    )
    backstory: Optional[str] = commands.flag(default=None, description="Backstory to look for")
    personality: Optional[str] = commands.flag(default=None, description="Personality to look for")
    extra: Optional[str] = commands.flag(default=None, description="Extra to look for")
    unique_trait: Optional[str] = commands.flag(default=None, description="Unique Trait to look for")
    pronoun: Optional[Pronoun] = commands.flag(default=None, description="Pronoun to look for")
    age: Optional[AgeGroup] = commands.flag(default=None, description="Age group to look for")
    group_by: Optional[GroupByArg] = commands.flag(default=None, description="Group by method")
    amount: Optional[str] = commands.flag(default=None, description="Amount to group by")


class OCGroupBy(Generic[D], ABC):
    @classmethod
    @abstractmethod
    def method(
        cls,
        ctx: commands.Context[CustomBot],
        ocs: Iterable[Character],
        flags: FindFlags,
    ) -> dict[D, frozenset[Character]]:
        """Abstract method for grouping

        Parameters
        ----------
        ctx : commands.Context[CustomBot]
            Context
        ocs : Iterable[Character]
            Characters to process
        flags : FindFlags
            Flags

        Returns
        -------
        dict[str, frozenset[Character]]
            Characters per category
        """

    @staticmethod
    def inner_parser(group: D, elements: list[Character]):
        return getattr(group, "name", str(group)), f"Group has {len(elements):02d} OCs."

    @staticmethod
    def sort_key(item: tuple[D, list[Character]]) -> Any:
        ref, items = item
        return -len(items), str(getattr(ref, "name", ref))

    @classmethod
    def sort_by(cls, items: list[tuple[D, list[Character]]]) -> list[tuple[D, list[Character]]]:
        return sorted(items, key=cls.sort_key)

    @classmethod
    def generate(
        cls,
        ctx: commands.Context[CustomBot],
        ocs: Iterable[Character],
        flags: FindFlags,
    ):
        if flags.member:
            ocs = [x for x in ocs if x.author == flags.member.id]
        else:
            ocs = [x for x in ocs if ctx.guild.get_member(x.author)]

        items = [(x, sorted(y, key=lambda o: o.name)) for x, y in cls.method(ctx, ocs, flags).items()]
        data = {k: v for k, v in cls.sort_by(items) if amount_parser(flags.amount, v)}
        return GroupByComplex(member=ctx.author, target=ctx, data=data, inner_parser=cls.inner_parser)


class OCGroupByKind(OCGroupBy[Kind]):
    @staticmethod
    def inner_parser(group: Kind, elements: list[Character]):
        return group.title, f"Kind has {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.kind)}


class OCGroupByShape(OCGroupBy[str]):
    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[str, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, Fusion):
                for mon in species.bases:
                    data.setdefault(mon.shape, set())
                    data[mon.shape].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant, CustomParadox, CustomUltraBeast)):
                    shape = species.base.shape
                elif isinstance(species, Fakemon):
                    if mon := species.species_evolves_from:
                        shape = mon.shape
                    else:
                        continue
                else:
                    shape = mon.shape

                if shape:
                    data.setdefault(shape, set())
                    data[shape].add(oc)

        return data


class OCGroupByAge(OCGroupBy[AgeGroup]):
    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.age.name)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.age)}


class OCGroupBySpecies(OCGroupBy[Kind | Species]):
    @staticmethod
    def inner_parser(group: Kind | Species, elements: list[Character]):
        if isinstance(group, Kind):
            return group.title, f"Kind has {len(elements):02d} OCs."
        return group.name, f"Species has {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        data = {}
        for k, v in groupby(ocs, lambda x: x.kind):
            if k not in STANDARD:
                data[k] = frozenset(v)
            elif items := sorted(v, key=lambda x: getattr(x.species, "base", x.species).id):
                data |= {
                    i: frozenset(j) for i, j in groupby(items, key=lambda x: getattr(x.species, "base", x.species))
                }
        return data


class OCGroupByEvoLine(OCGroupBy[Species]):
    @staticmethod
    def inner_parser(group: Species, elements: list[Character]):
        return group.name, f"Evo line has {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[Species, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, Fusion):
                for mon in species.bases:
                    mon = mon.first_evo
                    data.setdefault(mon, set())
                    data[mon].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant, CustomParadox, CustomUltraBeast)) and species.base:
                    mon = species.base.first_evo
                elif isinstance(species, Fakemon):
                    mon = species.species_evolves_from
                else:
                    mon = mon.first_evo

                if mon:
                    data.setdefault(mon, set())
                    data[mon].add(oc)

        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByType(OCGroupBy[TypingEnum]):
    @staticmethod
    def inner_parser(group: TypingEnum, elements: list[Character]):
        return group.name, f"Included in {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[TypingEnum, set[Character]] = {}

        for oc in ocs:
            for x in oc.types:
                data.setdefault(x, set())
                data[x].add(oc)

        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByPronoun(OCGroupBy[Pronoun]):
    @staticmethod
    def inner_parser(group: Pronoun, elements: list[Character]):
        return group.name, f"Used by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[Pronoun, set[Character]] = {}
        for oc in ocs:
            for x in oc.pronoun:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByMove(OCGroupBy[Move]):
    @staticmethod
    def inner_parser(group: Move, elements: list[Character]):
        return group.name, f"Learned by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[Move, set[Character]] = {}
        for oc in ocs:
            for x in oc.moveset:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByAbility(OCGroupBy[Ability]):
    @staticmethod
    def inner_parser(group: Ability, elements: list[Character]):
        return group.name, f"Carried by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        data: dict[Ability, set[Character]] = {}
        for oc in ocs:
            for x in oc.abilities:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByLocation(OCGroupBy[ForumChannel | None]):
    @staticmethod
    def inner_parser(group: ForumChannel | None, elements: list[Character]):
        if group is None:
            return "Unknown", f"Total unassigned: {len(elements):02d} OCs."
        return group.name, f"Explored by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        guild: Guild = ctx.guild

        def foo(oc: Character):
            if ch := guild.get_channel_or_thread(oc.location):
                if isinstance(ch, Thread):
                    ch = ch.parent
                if isinstance(ch, ForumChannel):
                    return ch

        ocs = sorted(ocs, key=lambda x: o.id if (o := foo(x)) else 0)

        return {k: frozenset(v) for k, v in groupby(ocs, key=foo)}


class OCGroupByMember(OCGroupBy[Member]):
    @staticmethod
    def inner_parser(group: Member, elements: list[Character]):
        return group.display_name, f"Has {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.author)
        guild: Guild = ctx.guild
        return {m: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.author) if (m := guild.get_member(k))}


class OCGroupByHiddenPower(OCGroupBy[TypingEnum | None]):
    @staticmethod
    def inner_parser(group: TypingEnum | None, elements: list[Character]):
        if group is None:
            return "Unknown", f"Unknown to {len(elements):02d} OCs."
        return group.name, f"Granted to {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: getattr(x.hidden_power, "name", "Unknown"))
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.hidden_power)}


class OCGroupByUniqueTrait(OCGroupBy[UTraitKind | None]):
    @staticmethod
    def inner_parser(group: UTraitKind | None, elements: list[Character]):
        if group is None:
            return "Unknown", f"Unknown to {len(elements):02d} OCs."
        return group.name, f"Used by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.sp_ability.kind.name if x.sp_ability else "Unknown")
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.sp_ability.kind if x.sp_ability else None)}


class OCGroupByPokeball(OCGroupBy[Pokeball | None]):
    @staticmethod
    def inner_parser(group: Pokeball | None, elements: list[Character]):
        if group is None:
            return "None", f"Total without: {len(elements):02d} OCs."
        return group.label, f"Obtained by {len(elements):02d} OCs."

    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.pokeball.name if x.pokeball else "None")
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.pokeball)}


class OCGroupByNature(OCGroupBy[Nature | None]):
    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.nature.name if x.nature else "None")
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.nature)}


class OCGroupByHeight(OCGroupBy[float]):
    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.height_value, reverse=True)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.height_value) if k}

    @staticmethod
    def inner_parser(group: float, elements: list[Character]):
        key = Size.M.height_info(group)
        return key, f"Group has {len(elements):02d} OCs."

    @staticmethod
    def sort_key(item: tuple[float, list[Character]]):
        ref, items = item
        return ref, -len(items)


class OCGroupByWeight(OCGroupBy[float]):
    @classmethod
    def method(cls, ctx: commands.Context[CustomBot], ocs: Iterable[Character], flags: FindFlags):
        ocs = sorted(ocs, key=lambda x: x.weight_value, reverse=True)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.weight_value) if k}

    @staticmethod
    def inner_parser(group: float, elements: list[Character]):
        key = Size.M.weight_info(group)
        return key, f"Group has {len(elements):02d} OCs."

    @staticmethod
    def sort_key(item: tuple[float, list[Character]]):
        ref, items = item
        return ref, -len(items)


class GroupBy(Enum):
    Kind = OCGroupByKind
    Shape = OCGroupByShape
    Age = OCGroupByAge
    Species = OCGroupBySpecies
    EvoLine = OCGroupByEvoLine
    Type = OCGroupByType
    Pronoun = OCGroupByPronoun
    Move = OCGroupByMove
    Ability = OCGroupByAbility
    Location = OCGroupByLocation
    Member = OCGroupByMember
    HiddenPower = OCGroupByHiddenPower
    Nature = OCGroupByNature
    UniqueTrait = OCGroupByUniqueTrait
    Pokeball = OCGroupByPokeball
    Height = OCGroupByHeight
    Weight = OCGroupByWeight

    def generate(
        self,
        ctx: commands.Context[CustomBot],
        ocs: Iterable[Character],
        flags: FindFlags,
    ):
        """Short cut generate

        Parameters
        ----------
        ctx : commands.Context
            Context
        ocs : Iterable[Character]
            Characters
        amount : Optional[str], optional
            Amount, by default None

        Returns
        -------
        GroupByComplex
            Information complex paginator groups.
        """
        value: OCGroupBy = self.value
        return value.generate(ctx=ctx, ocs=ocs, flags=flags)
