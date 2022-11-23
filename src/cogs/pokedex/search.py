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
from typing import Callable, Iterable, Optional

from discord import Guild, Interaction, Member, TextChannel, Thread
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ui import Select, select
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.pagination.complex import Complex
from src.structures.ability import Ability
from src.structures.character import AgeGroup, Character, Kind
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.pronouns import Pronoun
from src.structures.species import (
    Chimera,
    CustomMega,
    Fakemon,
    Fusion,
    Species,
    Variant,
)
from src.views.characters_view import CharactersView

STANDARD = [
    Kind.Common,
    Kind.Mythical,
    Kind.Legendary,
    Kind.UltraBeast,
    Kind.Mega,
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
    async def transform(cls, _: Interaction, value: Optional[str]):
        move = Move.deduce(value)
        if not move:
            raise ValueError(f"Move {value!r} Not found.")
        return move

    async def autocomplete(cls, _: Interaction, value: str) -> list[Choice[str]]:
        items = list(Move.all())
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in set(options)]


MoveArg = Transform[Move, MoveTransformer]


class ABCTransformer(Transformer):
    async def on_submit(self, ctx: Interaction, value: str) -> list[Choice[str]]:
        return []

    async def autocomplete(self, ctx: Interaction, value: str) -> list[Choice[str]]:
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
    async def transform(self, ctx: Interaction, value: Optional[str]):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        value = value or ""
        if value.isdigit() and (item := await db.find_one({"id": int(value)})):
            return Character.from_mongo_dict(item)
        elif oc := Species.single_deduce(value):
            return oc
        raise ValueError(f"Species {value!r} not found")

    async def autocomplete(self, ctx: Interaction, value: str) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"server": ctx.guild_id})]
        guild: Guild = ctx.guild
        mons: set[Character | Species] = {x for x in ocs if x.species} | set(Species.all())
        filters: list[Callable[[Character | Species], bool]] = []
        if fused := Species.from_ID(ctx.namespace.fused):
            mons = {
                (set(x.species.bases) - {fused}).pop()
                for x in mons
                if isinstance(x, Character) and isinstance(x.species, (Fusion, Chimera)) and fused in x.species.bases
            }
        elif kind := Kind.associated(ctx.namespace.kind):
            filters.append(lambda x: x.kind == kind if isinstance(x, Character) else isinstance(x, kind.value))
            mons = kind.all() or mons

        if member := ctx.namespace.member:
            ocs1 = {x.species for x in ocs if x.author == member.id}
            filters.append(lambda x: x.author == member.id if isinstance(x, Character) else x in ocs1)
        else:
            filters.append(lambda x: bool(guild.get_member(x.author)) if isinstance(x, Character) else True)

        if location := ctx.namespace.location:

            def foo2(oc: Character) -> bool:
                ref = ch.parent_id if (ch := guild.get_thread(oc.location)) else oc.location
                return oc.species and ref == location.id

            ocs2 = {x.species for x in filter(foo2, ocs)}
            filters.append(lambda x: foo2(x) if isinstance(x, Character) else x in ocs2)

        if (mon_type := ctx.namespace.type) and (mon_type := TypingEnum.deduce(mon_type)):
            filters.append(lambda x: mon_type in x.types)

        if (ability := ctx.namespace.ability) and (ability := Ability.from_ID(ability)):
            filters.append(lambda x: ability in x.abilities)

        if (move := ctx.namespace.move) and (move := Move.from_ID(move)):
            filters.append(lambda x: move in x.moveset if isinstance(x, Character) else True)

        values = {mon for mon in mons if all(i(mon) for i in filters)}
        if data := process.extract(value or "", choices=values, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in data]
        elif not value:
            options = list(values)[:25]

        entries = {item_name(x): item_value(x) for x in options}

        return [Choice(name=k, value=v) for k, v in entries.items()]


class DefaultSpeciesTransformer(Transformer):
    cache: dict = {}

    async def transform(self, _: Interaction, value: Optional[str]):
        if not (item := Species.single_deduce(value)):
            raise ValueError(f"Species {value!r} not found")
        return item

    async def autocomplete(self, ctx: Interaction, value: str) -> list[Choice[str]]:
        if ctx.command and ctx.command.name == "find" and (fused := Species.from_ID(ctx.namespace.species)):
            db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
            items = list(
                {
                    (set(oc.species.bases) - {fused}).pop()
                    async for x in db.find(
                        {"$or": [{"species.chimera": {"$exists": 1}}, {"species.fusion": {"$exists": 1}}]}
                    )
                    if (oc := Character.from_mongo_dict(x))
                    and fused in oc.species.bases
                    and ctx.guild.get_member(oc.author)
                }
            )
        else:
            items = list(Species.all())
        if options := process.extract(value or "", choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items
        return [Choice(name=x.name, value=x.id) for x in set(options[:25])]


SpeciesArg = Transform[Species, SpeciesTransformer]
DefaultSpeciesArg = Transform[Species, DefaultSpeciesTransformer]


class AbilityTransformer(Transformer):
    async def transform(self, _: Interaction, value: Optional[str]):
        item = Ability.from_ID(value)
        if not item:
            raise ValueError(f"Ability {item!r} not found")
        return item

    async def autocomplete(self, _: Interaction, value: str) -> list[Choice[str]]:
        items = list(Ability.all())
        if options := process.extract(value or "", choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in set(options)]


AbilityArg = Transform[Ability, AbilityTransformer]


class FakemonTransformer(Transformer):
    async def transform(cls, ctx: Interaction, value: Optional[str]):
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

    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
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
    def __init__(self, member: Member, target: Interaction, data: dict[str, list[Character]]):
        self.data = data

        def inner_parser(item: str):
            elements = self.data.get(item, [])
            return item, f"Group has {len(elements):02d} OCs."

        values = list(data.keys())
        values.sort(key=lambda x: (-len(data.get(x, [])), x))

        super(GroupByComplex, self).__init__(
            member=member,
            target=target,
            parser=inner_parser,
            values=values,
            keep_working=True,
        )

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        key = self.current_choice
        ocs = self.data.get(key, [])
        view = CharactersView(member=interaction.user, target=interaction, ocs=ocs, keep_working=True)
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

    @classmethod
    def generate(cls, ctx: Interaction, ocs: Iterable[Character], amount: Optional[str] = None):
        if member := ctx.namespace.member:
            ocs = [x for x in ocs if x.author == member.id]
        else:
            ocs = [x for x in ocs if ctx.guild.get_member(x.author)]
        values = sorted(cls.method(ctx, ocs).items(), key=lambda x: (-len(x[1]), x[0]))
        items = {k: sorted(v, key=lambda x: x.name) for k, v in values if amount_parser(amount, v)}
        return GroupByComplex(member=ctx.user, target=ctx, data=items)


class OCGroupByKind(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {k.name: frozenset({x for x in ocs if x.kind == k}) for k in Kind}


class OCGroupByShape(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        data: dict[str, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, (Fusion, Chimera)):
                for mon in species.bases:
                    data.setdefault(mon.shape, set())
                    data[mon.shape].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant)):
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
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {k.name: frozenset({x for x in ocs if x.age == k}) for k in AgeGroup}


class OCGroupBySpecies(OCGroupBy):
    @classmethod
    def total_data(cls, ctx: Interaction) -> list[Species]:
        filters: list[Callable[[Species], bool]] = []

        if item_type := TypingEnum.deduce(ctx.namespace.type):
            filters.append(lambda x: item_type in x.types)
        if item_ability := Ability.deduce(ctx.namespace.ability):
            filters.append(lambda x: item_ability in x.abilities)
        if item_move := Move.deduce(ctx.namespace.move):
            filters.append(lambda x: item_move in x.total_movepool)
        if (item_kind := Kind.associated(ctx.namespace.kind)) and item_kind not in [Kind.Fusion, Kind.Chimera]:
            filters.append(lambda x: isinstance(x, item_kind.value))

        return [x for x in Species.all() if all(i(x) for i in filters)]

    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        data = {k.name: frozenset(o) for k in Kind if k not in STANDARD and (o := {x for x in ocs if x.kind == k})}
        total = cls.total_data(ctx)
        data |= {k.name: frozenset({x for x in ocs if getattr(x.species, "base", x.species) == k}) for k in total}
        return data


class OCGroupByEvoLine(OCGroupBy):
    @classmethod
    def total_data(cls, ctx: Interaction) -> list[Species]:
        filters: list[Callable[[Species], bool]] = []

        if item_type := TypingEnum.deduce(ctx.namespace.type):
            filters.append(lambda x: item_type in x.types)
        if item_ability := Ability.deduce(ctx.namespace.ability):
            filters.append(lambda x: item_ability in x.abilities)
        if item_move := Move.deduce(ctx.namespace.move):
            filters.append(lambda x: item_move in x.total_movepool)
        if (item_kind := Kind.associated(ctx.namespace.kind)) and item_kind not in [Kind.Fusion, Kind.Chimera]:
            filters.append(lambda x: isinstance(x, item_kind.value))

        return [x for x in Species.all() if x.evolves_from is None and all(i(x) for i in filters)]

    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        data = {x.name: set() for x in cls.total_data(ctx)}
        for oc in ocs:
            if isinstance(species := oc.species, (Fusion, Chimera)):
                for mon in species.bases:
                    mon = mon.first_evo
                    data.setdefault(mon.name, set())
                    data[mon.name].add(oc)
            elif mon := species:
                if isinstance(species, (CustomMega, Variant)):
                    mon = species.base.first_evo
                elif isinstance(species, Fakemon):
                    mon = species.species_evolves_from
                else:
                    mon = mon.first_evo

                if mon:
                    data.setdefault(mon.name, set())
                    data[mon.name].add(oc)

        return data


class OCGroupByType(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {x.name: frozenset({oc for oc in ocs if x in oc.types}) for x in TypingEnum}


class OCGroupByPronoun(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {k.name: frozenset({x for x in ocs if x.pronoun == k}) for k in Pronoun}


class OCGroupByMove(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {x.name: frozenset({oc for oc in ocs if x in oc.moveset}) for x in Move.all()}


class OCGroupByAbility(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {item.name: frozenset({oc for oc in ocs if item in oc.abilities}) for item in Ability.all()}


class OCGroupByLocation(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        guild: Guild = ctx.guild
        aux: dict[TextChannel, set[Character]] = {}
        unknown = set()
        for oc in ocs:
            if ch := guild.get_channel_or_thread(oc.location):
                if isinstance(ch, Thread):
                    ch = ch.parent
                aux.setdefault(ch, set())
                aux[ch].add(oc)
            else:
                unknown.add(oc)
        data = {k.name.replace("-", " ").title(): frozenset(v) for k, v in aux.items()}
        data["Unknown"] = unknown
        return data


class OCGroupByMember(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.author)
        guild: Guild = ctx.guild
        return {
            m.display_name: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.author) if (m := guild.get_member(k))
        }


class OCGroupByHiddenPower(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        data = {k.name: frozenset({x for x in ocs if x.hidden_power == k}) for k in TypingEnum}
        data["Unknown"] = frozenset({x for x in ocs if x.hidden_power is None})
        return data


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

    def generate(self, ctx: Interaction, ocs: Iterable[Character], amount: Optional[str] = None):
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
