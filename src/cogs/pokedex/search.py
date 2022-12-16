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


from abc import ABC, abstractmethod
from enum import Enum
from itertools import groupby
from typing import Any, Callable, Iterable, Optional

from discord import Guild, Interaction, Member, Thread
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ui import Select, select
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.cogs.submission.oc_submission import ModCharactersView
from src.pagination.complex import Complex
from src.structures.ability import Ability
from src.structures.character import Character, Kind
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.species import (
    Chimera,
    CustomMega,
    CustomParadox,
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
    if isinstance(mon, Character):
        mon = mon.species
    return getattr(mon, "name", mon)


def item_value(mon: Character | Species):
    if isinstance(mon, Character) and mon.kind in STANDARD:
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


class MoveTransformer(Transformer):
    async def transform(self, _: Interaction, value: Optional[str], /):
        move = Move.deduce(value)
        if not move:
            raise ValueError(f"Move {value!r} Not found.")
        return move

    async def autocomplete(self, _: Interaction, value: str, /) -> list[Choice[str]]:
        items = list(Move.all())
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in set(options)]


MoveArg = Transform[Move, MoveTransformer]


class ABCTransformer(Transformer):
    async def on_submit(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        return []

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        items = await self.on_submit(ctx, value)
        if options := process.extract(
            value or "",
            choices=items,
            limit=25,
            processor=lambda x: x.name,
            score_cutoff=60,
        ):
            return [x[0] for x in options]
        return items[:25]


class SpeciesTransformer(Transformer):
    async def transform(self, ctx: Interaction, value: Optional[str], /):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        value = value or ""
        if value.isdigit() and (item := await db.find_one({"id": int(value)})):
            return Character.from_mongo_dict(item)
        elif oc := Species.single_deduce(value):
            return oc
        raise ValueError(f"Species {value!r} not found")

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
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


class DefaultSpeciesTransformer(Transformer):
    cache: dict = {}

    async def transform(self, _: Interaction, value: Optional[str], /):
        if not (item := Species.single_deduce(value)):
            raise ValueError(f"Species {value!r} not found")
        return item

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        if ctx.command and ctx.command.name == "find" and (fused := Species.from_ID(ctx.namespace.species)):
            db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
            items = [
                base
                async for x in db.find(
                    {
                        "$or": [
                            {"species.chimera": {"$in": fused.id.split("/")}},
                            {"species.fusion.species": {"$in": fused.id.split("/")}},
                        ]
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


class AbilityTransformer(Transformer):
    async def transform(self, _: Interaction, value: Optional[str], /):
        item = Ability.from_ID(value)
        if not item:
            raise ValueError(f"Ability {item!r} not found")
        return item

    async def autocomplete(self, _: Interaction, value: str, /) -> list[Choice[str]]:
        items = list(Ability.all())
        if options := process.extract(value or "", choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in options]


AbilityArg = Transform[Ability, AbilityTransformer]


class FakemonTransformer(Transformer):
    async def transform(self, ctx: Interaction, value: Optional[str], /):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        oc: Optional[Character] = None
        if value.isdigit() and (item := await db.find_one({"id": int(value)})):
            oc = Character.from_mongo_dict(item)
        elif ocs := process.extractOne(
            value or "",
            choices=[
                Character.from_mongo_dict(x)
                async for x in db.find({"species.evolves_from": {"$exists": 1}, "species.base": {"$exists": 0}})
            ],
            processor=item_name,
            score_cutoff=60,
        ):
            oc = ocs[0]
        if not oc:
            raise ValueError(f"Fakemon {value!r} not found.")
        return oc

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        guild: Guild = ctx.guild
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        mons = [
            Character.from_mongo_dict(x)
            async for x in db.find({"species.evolves_from": {"$exists": 1}, "species.base": {"$exists": 0}})
            if guild.get_member(x["author"])
        ]
        if options := process.extract(value or "", choices=mons, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = mons[:25]
        return [Choice(name=x.species.name, value=str(x.id)) for x in set(options)]


FakemonArg = Transform[Character, FakemonTransformer]


class GroupByComplex(Complex[str]):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        data: dict[str, list[Character]],
    ):
        self.data = data

        def inner_parser(item: str):
            elements = self.data.get(item, [])
            return getattr(item, "name", str(item)), f"Group has {len(elements):02d} OCs."

        super(GroupByComplex, self).__init__(
            member=member,
            target=target,
            parser=inner_parser,
            values=data.keys(),
            keep_working=True,
            sort_key=lambda x: (-len(data.get(x, [])), getattr(x, "name", str(x))),
        )

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        key = self.current_choice
        ocs = self.data.get(key, [])
        view = ModCharactersView(member=interaction.user, target=interaction, ocs=ocs, keep_working=True)
        async with view.send(ephemeral=True):
            await super(GroupByComplex, self).select_choice(interaction, sct)


class OCGroupBy(ABC):
    @classmethod
    @abstractmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]) -> dict[str, frozenset[Character]]:
        """Abstract method for grouping

        Parameters
        ----------
        ctx : Interaction
            Interaction
        ocs : Iterable[Character]
            Characters to process

        Returns
        -------
        dict[str, frozenset[Character]]
            Characters per category
        """

    @staticmethod
    def sort_by(items: list[tuple[Any, list[Character]]]):
        try:
            return sorted(items, key=lambda x: (-len(x[1]), x[0]))
        except TypeError:
            return sorted(items, key=lambda x: (-len(x[1]), getattr(x[0], "name", str(x[0]))))

    @classmethod
    def generate(
        cls,
        ctx: Interaction,
        ocs: Iterable[Character],
        amount: Optional[str] = None,
    ):
        if member := ctx.namespace.member:
            ocs = [x for x in ocs if x.author == member.id]
        else:
            ocs = [x for x in ocs if ctx.guild.get_member(x.author)]

        items = [(x, sorted(y, key=lambda o: o.name)) for x, y in cls.method(ctx, ocs).items()]
        data = {k: v for k, v in cls.sort_by(items) if amount_parser(amount, v)}
        return GroupByComplex(member=ctx.user, target=ctx, data=data)


class OCGroupByKind(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.kind)}


class OCGroupByShape(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        data: dict[str, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, (Fusion, Chimera)):
                for mon in species.bases:
                    data.setdefault(mon.shape, set())
                    data[mon.shape].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant, CustomParadox)):
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


class OCGroupByAge(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.age.name)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.age)}


class OCGroupBySpecies(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        data = {}
        for k, v in groupby(ocs, lambda x: x.kind):
            if k not in STANDARD:
                data[k] = frozenset(v)
            elif items := sorted(v, key=lambda x: getattr(x.species, "base", x.species).id):
                data.update(
                    {i: frozenset(j) for i, j in groupby(items, key=lambda x: getattr(x.species, "base", x.species))}
                )
        return data


class OCGroupByEvoLine(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        data: dict[Species, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, (Fusion, Chimera)):
                for mon in species.bases:
                    mon = mon.first_evo
                    data.setdefault(mon, set())
                    data[mon].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant, CustomParadox)):
                    mon = species.base.first_evo
                elif isinstance(species, Fakemon):
                    mon = species.species_evolves_from
                else:
                    mon = mon.first_evo

                if mon:
                    data.setdefault(mon, set())
                    data[mon].add(oc)

        return data


class OCGroupByType(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        data: dict[TypingEnum, set[Character]] = {}
        for oc in ocs:
            for x in oc.types:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByPronoun(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.pronoun.name)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.pronoun)}


class OCGroupByMove(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        data: dict[Move, set[Character]] = {}
        for oc in ocs:
            for x in oc.moveset:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByAbility(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        data: dict[Ability, set[Character]] = {}
        for oc in ocs:
            for x in oc.abilities:
                data.setdefault(x, set())
                data[x].add(oc)
        return {k: frozenset(v) for k, v in data.items()}


class OCGroupByLocation(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        guild: Guild = ctx.guild

        def foo(oc: Character):
            if ch := guild.get_channel_or_thread(oc.location):
                if isinstance(ch, Thread):
                    ch = ch.parent
                return ch

        ocs = sorted(ocs, key=lambda x: o.id if (o := foo(x)) else 0)

        return {k: frozenset(v) for k, v in groupby(ocs, key=foo)}

    @staticmethod
    def sort_by(items: list[tuple[Thread, list[Character]]]):
        return sorted(items, key=lambda x: x[0].name if x[0] else "None")


class OCGroupByMember(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.author)
        guild: Guild = ctx.guild
        return {m: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.author) if (m := guild.get_member(k))}

    @staticmethod
    def sort_by(items: list[tuple[Member, list[Character]]]):
        return sorted(items, key=lambda x: x[0].name)


class OCGroupByHiddenPower(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: getattr(x.hidden_power, "name", "Unknown"))
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.hidden_power or "Unknown")}


class OCGroupByUniqueTrait(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.sp_ability.kind.name if x.sp_ability else "Unknown")
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: getattr(x.sp_ability, "kind", "Unknown"))}


class OCGroupByPokeball(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: getattr(x.pokeball, "name", "None"))
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.pokeball or "None")}


class OCGroupByHeight(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.size.height_value(x.species.height), reverse=True)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.size.height_info(x.species.height)) if k}

    @staticmethod
    def sort_by(items: list[tuple[str, list[Character]]]):
        return sorted(items, key=lambda x: float(x[0].split(" m ")[0]), reverse=True)


class OCGroupByWeight(OCGroupBy):
    @classmethod
    def method(cls, _: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.weight.weight_value(x.species.weight), reverse=True)
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.weight.weight_info(x.species.weight)) if k}

    @staticmethod
    def sort_by(items: list[tuple[str, list[Character]]]):
        return sorted(items, key=lambda x: float(x[0].split(" kg ")[0]), reverse=True)


class GroupByArg(Enum):
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
    UniqueTrait = OCGroupByUniqueTrait
    Pokeball = OCGroupByPokeball
    Height = OCGroupByHeight
    Weight = OCGroupByWeight

    def generate(
        self,
        ctx: Interaction,
        ocs: Iterable[Character],
        amount: Optional[str] = None,
    ):
        """Short cut generate

        Parameters
        ----------
        ctx : Interaction
            Interaction
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
        return value.generate(ctx=ctx, ocs=ocs, amount=amount)
