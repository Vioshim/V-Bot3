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

from abc import ABC, abstractclassmethod
from itertools import groupby
from typing import Iterable, Optional

from discord import (
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Thread,
)
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ui import Select, select

from pagination.complex import Complex
from src.cogs.submission.cog import Submission
from src.structures.ability import Ability
from src.structures.character import Character, FakemonCharacter
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.species import (
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Pokemon,
    Species,
    UltraBeast,
)
from src.utils.functions import fix
from views import CharactersView

OPERATORS = {
    "<=": lambda x, y: x <= y,
    "<": lambda x, y: x < y,
    ">=": lambda x, y: x >= y,
    ">": lambda x, y: x > y,
}


def foo(x: str) -> Optional[int]:
    x = x.strip()
    if x.isdigit():
        return int(x)


def amount_parser(text: Optional[str], ocs: Iterable[Character]):
    ocs = frozenset(ocs)
    if not text:
        return True

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
    @classmethod
    async def transform(cls, _: Interaction, value: Optional[str]):
        move = Move.from_ID(value)
        if not move:
            raise ValueError(f"Move {value!r} Not found.")
        return move

    @classmethod
    async def autocomplete(cls, _: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        return [Choice(name=i.name, value=i.id) for i in Move.all() if text in i.id or i.id in text][:25]


MoveArg = Transform[Move, MoveTransformer]


class SpeciesTransformer(Transformer):
    @classmethod
    async def transform(cls, ctx: Interaction, value: Optional[str]):
        value = value or ""
        cog: Submission = ctx.client.get_cog("Submission")
        if value.isdigit() and (oc := cog.ocs.get(int(value))):
            return oc
        mon = Species.from_ID(value.removesuffix("+"))
        if not mon:
            raise ValueError(f"Species {value!r} not found")
        return mon

    @classmethod
    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        cog: Submission = ctx.client.get_cog("Submission")
        guild: Guild = ctx.guild

        match fix(ctx.namespace.kind):
            case "LEGENDARY":
                mons = Legendary.all()
            case "MYTHICAL":
                mons = Mythical.all()
            case "UTRABEAST":
                mons = UltraBeast.all()
            case "POKEMON":
                mons = Pokemon.all()
            case "MEGA":
                mons = Mega.all()
            case "CUSTOMMEGA":
                mons = [oc for oc in cog.ocs.values() if oc.kind == "CUSTOM MEGA" and guild.get_member(oc.author)]
            case "FAKEMON":
                mons = [oc for oc in cog.ocs.values() if oc.kind == "FAKEMON" and guild.get_member(oc.author)]
            case "VARIANT":
                mons = [oc for oc in cog.ocs.values() if oc.kind == "VARIANT" and guild.get_member(oc.author)]
            case "FUSION":
                mons = [oc for oc in cog.ocs.values() if oc.kind == "FUSION" and guild.get_member(oc.author)]
            case _:
                mons = Species.all()

        mons: list[Character | Species] = list(mons)
        filters = []

        if member := ctx.namespace.member:
            ocs1 = {x.species for x in cog.rpers.get(member.id, {}).values()}
            filters.append(lambda x: x.author == member.id if isinstance(x, Character) else x in ocs1)
        if location := ctx.namespace.location:

            def foo2(oc: Character):
                ch = guild.get_channel_or_thread(oc.location)
                if isinstance(ch, Thread):
                    return ch.parent_id == location.id
                return oc.location == location.id

            ocs2 = {x.species for x in cog.ocs.values() if foo2(x)}
            filters.append(lambda x: foo2(x) if isinstance(x, Character) else x in ocs2)
        if (mon_type := ctx.namespace.types) and (mon_type := Typing.from_ID(mon_type)):
            filters.append(lambda x: mon_type in x.types)
        if (abilities := ctx.namespace.abilities) and (ability := Ability.from_ID(abilities)):
            filters.append(lambda x: ability in x.abilities)
        if (moves := ctx.namespace.moves) and (move := Move.from_ID(moves)):
            filters.append(lambda x: move in x.movepool)

        options = {
            item_name(mon): item_value(mon)
            for mon in sorted(
                filter(lambda x: all(i(x) for i in filters), mons),
                key=item_name,
            )
        }

        return [Choice(name=k, value=v) for k, v in options.items() if v in text or text in v][:25]


class DefaultSpeciesTransformer(Transformer):
    @classmethod
    async def transform(cls, _: Interaction, value: Optional[str]):
        item = Species.single_deduce(value)
        if not item:
            raise ValueError(f"Species {value!r} not found")
        return item

    @classmethod
    async def autocomplete(cls, _: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        return [Choice(name=i.name, value=i.id) for i in Species.all() if text in i.id or i.id in text][:25]


SpeciesArg = Transform[Species, SpeciesTransformer]
DefaultSpeciesArg = Transform[Species, DefaultSpeciesTransformer]


class AbilityTransformer(Transformer):
    @classmethod
    async def transform(cls, _: Interaction, value: Optional[str]):
        item = Ability.deduce(value)
        if not item:
            raise ValueError(f"Ability {item!r} not found")
        return item

    @classmethod
    async def autocomplete(cls, _: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        return [Choice(name=i.name, value=i.id) for i in Ability.all() if text in i.id or i.id in text][:25]


AbilityArg = Transform[Ability, AbilityTransformer]


class TypingTransformer(Transformer):
    @classmethod
    async def transform(cls, _: Interaction, value: Optional[str]):
        item = Typing.deduce(value)
        if not item:
            raise ValueError(f"Typing {item!r} not found")
        return item

    @classmethod
    async def autocomplete(cls, _: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        return [Choice(name=i.name, value=i.id) for i in Typing.all() if text in str(i) or str(i) in text][:25]


TypingArg = Transform[Typing, TypingTransformer]


def item_name(mon: Character | Species):
    if isinstance(mon, Species):
        return mon.name
    return mon.species.name


def item_value(mon: Character | Species):
    if isinstance(mon, Species):
        return str(mon.id)
    return str(mon.species.id)


class FakemonTransformer(Transformer):
    @classmethod
    async def transform(cls, ctx: Interaction, value: Optional[str]):
        cog: Submission = ctx.client.get_cog("Submission")
        oc = cog.ocs.get(value)
        if not oc:
            raise ValueError(f"Fakemon {value!r} not found.")
        return oc

    @classmethod
    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        text: str = fix(value or "")
        guild: Guild = ctx.guild
        cog: Submission = ctx.client.get_cog("Submission")
        mons = [oc for oc in cog.ocs.values() if oc.kind == "FAKEMON" and guild.get_member(oc.author)]

        options = {
            mon.species.name: item_value(mon)
            for mon in sorted(mons, key=lambda x: x.species.name)
            if mon.species.name.lower() in text or text in mon.species.name.lower()
        }

        return [Choice(name=k, value=v) for k, v in options.items()][:25]


FakemonArg = Transform[FakemonCharacter, FakemonTransformer]


class GroupByComplex(Complex):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        data: dict[str, list[Character]],
    ):
        super(GroupByComplex, self).__init__(
            member=member,
            target=target,
            values=data.keys(),
            keep_working=True,
        )
        self.data = data

    @select(
        row=1,
        placeholder="Select the elements",
        custom_id="selector",
    )
    async def select_choice(
        self,
        interaction: Interaction,
        sct: Select,
    ) -> None:
        resp: InteractionResponse = interaction.response
        key = self.current_choice
        ocs = self.data.get(key, [])
        view = CharactersView(
            member=interaction.user,
            target=interaction,
            values=ocs,
            keep_working=True,
        )
        await resp.send_message(embed=view.embed, view=view, ephemeral=True)
        await super(GroupByComplex, self).select_choice(interaction, sct)


class OCGroupBy(ABC):
    @abstractclassmethod
    def method(
        cls,
        ctx: Interaction,
        ocs: Iterable[Character],
    ) -> dict[str, frozenset[Character]]:
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

    def generate(
        cls,
        ctx: Interaction,
        ocs: Iterable[Character],
        amount: Optional[str] = None,
    ):
        items = {
            k: sorted(v, key=lambda x: x.name)
            for k, v in sorted(
                cls.method(ctx, ocs).items(),
                reverse=True,
                key=lambda x: (len(x[1]), x[0]),
            )
            if amount_parser(amount, v)
        }
        return GroupByComplex(member=ctx.user, target=ctx, data=items)


class OCGroupByKind(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.kind)}


class OCGroupByAge(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {str(k or "Unknown"): frozenset(v) for k, v in groupby(ocs, key=lambda x: x.age)}


class OCGroupBySpecies(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        items = {
            k.title(): frozenset(v)
            for k, v in groupby(ocs, key=lambda x: x.kind)
            if k
            not in [
                "COMMON",
                "MYTHICAL",
                "LEGENDARY",
                "ULTRA BEAST",
            ]
        }
        items.update(
            (
                item.name,
                frozenset(
                    {
                        oc
                        for oc in ocs
                        if (
                            item in oc.species.bases
                            if isinstance(oc.species, Fusion)
                            else getattr(oc.species, "base", oc.species) == item
                        )
                    }
                ),
            )
            for item in Species.all()
        )
        return items


class OCGroupByType(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {item.name: frozenset({oc for oc in ocs if item in oc.types}) for item in Typing.all()}


class OCGroupByPronoun(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        return {k: frozenset(v) for k, v in groupby(ocs, key=lambda x: x.pronoun.name)}


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

        return {k.name.split("〛")[-1].replace("-", " ").title(): frozenset(v) for k, v in aux.items()}


class OCGroupByMember(OCGroupBy):
    @classmethod
    def method(cls, ctx: Interaction, ocs: Iterable[Character]):
        guild: Guild = ctx.guild
        return {
            m.display_name[:100]: frozenset(v)
            for k, v in groupby(ocs, key=lambda x: x.author)
            if (m := guild.get_member(k))
        }


GROUP_BY_METHODS: dict[str, OCGroupBy] = {
    "Kind": OCGroupByKind,
    "Age": OCGroupByAge,
    "Species": OCGroupBySpecies,
    "Type": OCGroupByType,
    "Pronoun": OCGroupByPronoun,
    "Move": OCGroupByMove,
    "Ability": OCGroupByAbility,
    "Location": OCGroupByLocation,
    "Member": OCGroupByMember,
}


class GroupTransformer(Transformer):
    @classmethod
    async def transform(cls, ctx: Interaction, value: Optional[str]):
        return GROUP_BY_METHODS[value]

    @classmethod
    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        value = (value or "").lower()
        return [Choice(name=x, value=x) for x in GROUP_BY_METHODS if value in x.lower()]


GroupByArg = Transform[OCGroupBy, GroupTransformer]
