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

from discord import AutocompleteContext, OptionChoice

from src.cogs.submission.cog import Submission
from src.structures.ability import Ability
from src.structures.character import Character
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


def move_autocomplete(ctx: AutocompleteContext) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=i.id)
        for i in Move.all()
        if text in i.id or i.id in text
    ]


def default_species_autocomplete(
    ctx: AutocompleteContext,
) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=i.id)
        for i in Species.all()
        if text in i.id or i.id in text
    ]


def ability_autocomplete(ctx: AutocompleteContext) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=i.id)
        for i in Ability.all()
        if text in i.id or i.id in text
    ]


def type_autocomplete(ctx: AutocompleteContext):
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=str(i))
        for i in Typing.all()
        if text in str(i) or str(i) in text
    ]


def species_autocomplete(
    ctx: AutocompleteContext,
) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
    cog: Submission = ctx.bot.get_cog("Submission")
    match fix(ctx.options.get("kind", "")):
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
        case "FAKEMON":
            mons = [oc for oc in cog.ocs.values() if oc.kind == "FAKEMON"]
        case "VARIANT":
            mons = [oc for oc in cog.ocs.values() if oc.kind == "VARIANT"]
        case "FUSION":
            mons = [oc for oc in cog.ocs.values() if oc.kind == "FUSION"]
        case _:
            mons = Species.all()

    mons: list[Character | Species] = list(mons)

    if member_id := ctx.options.get("member"):
        mons = [i for i in mons if i.author == int(member_id)]

    if location_id := ctx.options.get("location"):
        mons = [i for i in mons if i.location == int(location_id)]

    mon_type_id = ctx.options.get("types")
    if mon_type_id and (mon_type := Typing.from_ID(mon_type_id)):
        mons = [i for i in mons if mon_type in i.types]

    ability_id = ctx.options.get("abilities")
    if ability_id and (ability := Ability.from_ID(ability_id)):
        mons = [i for i in mons if ability in i.abilities]

    move_id = ctx.options.get("moves")
    if move_id and (move := Move.from_ID(move_id)):
        mons = [i for i in mons if move in i.movepool]

    def name(mon: Character | Species):
        if isinstance(mon, Species):
            return mon.name
        return mon.species.name

    def value(mon: Character | Species):
        if isinstance(mon, Species):
            return str(mon.id)
        return str(mon.species.id)

    options = {name(mon): value(mon) for mon in sorted(mons, key=name)}

    return [
        OptionChoice(name=k, value=v)
        for k, v in options.items()
        if v in text or text in v
    ]
