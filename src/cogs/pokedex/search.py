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

# /find-species name: str, fusion: str = None, kind: str = None, variants: bool = False
# /find-species name: str, fusion: str = None, kind: str = None
# /find-species name: str, fusion: str = None, kind: str = None
# /find-species name: str, fusion: str = None, kind: str = None


def move_autocomplete(ctx: AutocompleteContext) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=i.id)
        for i in Move.all()
        if text in i.id or i.id in text
    ]


def type_autocomplete(ctx: AutocompleteContext):
    text: str = fix(ctx.value or "")
    return [
        OptionChoice(name=i.name, value=str(i))
        for i in Typing.all()
        if text in str(i) or str(i) in text
    ]


def default_species_autocomplete(
    ctx: AutocompleteContext,
) -> list[OptionChoice]:
    text: str = fix(ctx.value or "")
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
        case _:
            mons = Species.all()

    options = [
        OptionChoice(name=i.name, value=i.id)
        for i in mons
        if i.id in text or text in i.id
    ]

    options.sort(key=lambda x: x.name)
    return options
