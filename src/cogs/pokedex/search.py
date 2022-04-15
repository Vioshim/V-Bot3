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

from typing import Optional

from discord import Guild, Interaction, Thread
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer

from src.cogs.submission.cog import Submission
from src.structures.ability import Ability
from src.structures.character import Character, FakemonCharacter
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.species import (
    Legendary,
    Mega,
    Mythical,
    Pokemon,
    Species,
    UltraBeast,
)
from src.utils.functions import fix


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
