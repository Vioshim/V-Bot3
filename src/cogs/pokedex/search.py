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
from rapidfuzz import process

from src.pagination.complex import Complex
from src.structures.ability import Ability
from src.structures.character import Character, Kind
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.species import CustomMega, Fakemon, Fusion, Species, Variant
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
    if isinstance(mon, Character):
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


class SpeciesTransformer(Transformer):
    async def transform(self, ctx: Interaction, value: Optional[str]):
        value = value or ""
        cog = ctx.client.get_cog("Submission")
        if value.isdigit() and (oc := cog.ocs.get(int(value))):
            return oc
        mon = Species.from_ID(value)
        if not mon:
            raise ValueError(f"Species {value!r} not found")
        return mon

    async def autocomplete(self, ctx: Interaction, value: str) -> list[Choice[str]]:
        cog = ctx.client.get_cog("Submission")
        guild: Guild = ctx.guild
        mons = cog.ocs.values()
        filters: list[Callable[[Character | Species], bool]] = [
            lambda x: bool(guild.get_member(x.author)) if isinstance(x, Character) else True
        ]
        if fused := Species.from_ID(ctx.namespace.fused):
            mons = {
                (set(x.species.bases) - {fused}).pop()
                for x in mons
                if isinstance(x.species, Fusion) and fused in x.species.bases
            }
        elif kind := Kind.associated(ctx.namespace.kind):
            filters.append(lambda x: x.kind == kind if isinstance(x, Character) else isinstance(x, kind.value))
            mons = kind.all() or mons
        if member := ctx.namespace.member:
            ocs1 = {x.species for x in cog.ocs.values() if x.author == member.id}
            filters.append(lambda x: x.author == member.id if isinstance(x, Character) else x in ocs1)
        if location := ctx.namespace.location:

            def foo2(oc: Character) -> bool:
                ref = ch.parent_id if (ch := guild.get_thread(oc.location)) else oc.location
                return oc.species and ref == location.id

            ocs2 = {x.species for x in filter(foo2, cog.ocs.values())}
            filters.append(lambda x: foo2(x) if isinstance(x, Character) else x in ocs2)
        if (mon_type := ctx.namespace.types) and (mon_type := Typing.from_ID(mon_type)):
            filters.append(lambda x: mon_type in x.types)
        if (abilities := ctx.namespace.abilities) and (ability := Ability.from_ID(abilities)):
            filters.append(lambda x: ability in x.abilities)
        if (moves := ctx.namespace.moves) and (move := Move.from_ID(moves)):
            filters.append(lambda x: move in x.movepool)

        values = {mon for mon in mons if all(i(mon) for i in filters)}
        if options := process.extract(value, choices=values, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = list(values)[:25]
        entries = {item_name(x): item_value(x) for x in options}
        return [Choice(name=k, value=v) for k, v in entries.items()]


class DefaultSpeciesTransformer(Transformer):
    async def transform(self, _: Interaction, value: Optional[str]):
        item = Species.single_deduce(value)
        if not item:
            raise ValueError(f"Species {value!r} not found")
        return item

    async def autocomplete(self, ctx: Interaction, value: str) -> list[Choice[str]]:
        items = list(Species.all())
        if ctx.command and ctx.command.name == "find" and (fused := Species.from_ID(ctx.namespace.species)):
            cog = ctx.client.get_cog("Submission")
            items = list(
                {
                    (set(x.species.bases) - {fused}).pop()
                    for x in cog.ocs.values()
                    if isinstance(x.species, Fusion) and fused in x.species.bases
                }
            )
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
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
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.id) for x in set(options)]


AbilityArg = Transform[Ability, AbilityTransformer]


class TypingTransformer(Transformer):
    async def transform(self, _: Interaction, value: Optional[str]):
        item = Typing.deduce(value)
        if not item:
            raise ValueError(f"Typing {item!r} not found")
        return item

    async def autocomplete(self, _: Interaction, value: str) -> list[Choice[str]]:
        items = list(Typing.all())
        if options := process.extract(value, choices=items, limit=25, processor=item_name, score_cutoff=60):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=str(x)) for x in set(options)]


TypingArg = Transform[Typing, TypingTransformer]


class FakemonTransformer(Transformer):
    async def transform(cls, ctx: Interaction, value: Optional[str]):
        cog = ctx.client.get_cog("Submission")
        oc: Optional[Character] = None
        if value.isdigit():
            oc = cog.ocs.get(int(value))
        elif ocs := process.extractOne(value, choices=cog.ocs.values(), processor=item_name, score_cutoff=60):
            oc = ocs[0]
        if not oc:
            raise ValueError(f"Fakemon {value!r} not found.")
        return oc

    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        guild: Guild = ctx.guild
        cog = ctx.client.get_cog("Submission")
        mons = [oc for oc in cog.ocs.values() if oc.kind == Kind.Fakemon and guild.get_member(oc.author)]
        if options := process.extract(value, choices=mons, limit=25, processor=item_name, score_cutoff=60):
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

        super(GroupByComplex, self).__init__(
            member=member,
            target=target,
            parser=inner_parser,
            values=list(data.keys()),
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
        items = {
            k: sorted(v, key=lambda x: x.name)
            for k, v in sorted(cls.method(ctx, ocs).items(), key=lambda x: (-len(x[1]), x[0]))
            if amount_parser(amount, v)
        }
        return GroupByComplex(member=ctx.user, target=ctx, data=items)


class OCGroupByKind(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        return {k.name: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.kind)}


class OCGroupByAge(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.age or 0)
        return {str(k or "Unknown"): frozenset(v) for k, v in groupby(ocs, key=lambda x: x.age)}


class OCGroupBySpecies(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.kind.name)
        items = {k.name.title(): set(v) for k, v in groupby(ocs, key=lambda x: x.kind) if k not in STANDARD}
        ocs = sorted(ocs, key=lambda x: getattr(x.species, "base", x.species).name)
        items |= {
            k.name.title(): set(v)
            for k, v in groupby(ocs, key=lambda x: getattr(x.species, "base", x.species))
            if any(x.from_class(k) for x in STANDARD)
        }
        return items


class OCGroupByEvoLine(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        data: dict[str, set[Character]] = {}
        for oc in ocs:
            if isinstance(species := oc.species, Fusion):
                mon1, mon2 = species.mon1.first_evo, species.mon2.first_evo
                data.setdefault(mon1.name, set())
                data.setdefault(mon2.name, set())
                data[mon1.name].add(oc)
                data[mon2.name].add(oc)
            elif species:
                mon = species
                if isinstance(species, (CustomMega, Variant)):
                    mon = species.base.first_evo
                elif isinstance(species, Fakemon):
                    if mon := species.species_evolves_from:
                        mon = mon.first_evo
                    else:
                        continue
                data.setdefault(mon.name, set())
                data[mon.name].add(ocs)

        return data


class OCGroupByType(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {item.name: frozenset({oc for oc in ocs if item in oc.types}) for item in Typing.all()}


class OCGroupByPronoun(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.pronoun.name)
        return {k.name: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.pronoun)}


class OCGroupByMove(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {item.name: {oc for oc in ocs if item in oc.moveset} for item in Move.all()}


class OCGroupByAbility(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {item.name: {oc for oc in ocs if item in oc.abilities} for item in Ability.all()}


class OCGroupByLocation(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        guild: Guild = ctx.guild
        aux: dict[TextChannel, set[Character]] = {}
        for oc in ocs:
            if ch := guild.get_channel_or_thread(oc.location):
                if isinstance(ch, Thread):
                    ch = ch.parent
                aux.setdefault(ch, set())
                aux[ch].add(oc)

        return {k.name.replace("-", " ").title(): frozenset(v) for k, v in aux.items()}


class OCGroupByMember(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        ocs = sorted(ocs, key=lambda x: x.author)
        guild: Guild = ctx.guild
        return {
            m.display_name[:100]: frozenset(v)
            for k, v in groupby(ocs, key=lambda x: x.author)
            if (m := guild.get_member(k))
        }


class GroupByArg(Enum):
    Kind = OCGroupByKind
    Age = OCGroupByAge
    Species = OCGroupBySpecies
    EvoLine = OCGroupByEvoLine
    Type = OCGroupByType
    Pronoun = OCGroupByPronoun
    Move = OCGroupByMove
    Ability = OCGroupByAbility
    Location = OCGroupByLocation
    Member = OCGroupByMember

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
