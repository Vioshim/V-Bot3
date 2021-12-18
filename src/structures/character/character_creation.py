# Copyright 2021 Vioshim
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

from asyncio import to_thread
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from nested_lookup import nested_lookup

from src.enums import Abilities
from src.enums.mon_types import Types
from src.enums.pronouns import Pronoun
from src.structures.ability import SpAbility
from src.structures.character import (
    FakemonCharacter,
    FusionCharacter,
    LegendaryCharacter,
    MegaCharacter,
    MythicalCharacter,
    PokemonCharacter,
    UltraBeastCharacter,
)
from src.structures.movepool import Movepool
from src.structures.species import Fakemon, Fusion, Legendary, Mega, Mythical, Pokemon
from src.structures.species import Species as SpeciesBase
from src.structures.species import UltraBeast
from src.utils.doc_reader import docs_reader
from src.utils.functions import stats_check
from src.utils.matches import DATA_FINDER, G_DOCUMENT, MOVE_FINDER, TYPE_FINDER

PLACEHOLDER_NAMES = {
    "Name": "name",
    "Age": "age",
    "Species": "species",
    "Gender": "gender",
    "Ability": "ability",
    "Pronoun": "pronoun",
    "Backstory": "backstory",
    "Additional Information": "extra",
    "F. Species": "fakemon",
    "Artist": "artist",
    "Website": "website",
}
PLACEHOLDER_DEFAULTS = {
    "name": "OC's Name",
    "age": "OC's Age",
    "species": "OC's Species",
    "gender": "OC's Gender",
    "ability": "OC's Ability",
    "pronoun": "OC's Preferred Pronoun",
    "backstory": "Character's backstory",
    "extra": "Character's extra information",
    "fakemon": "OC's Fakemon Species",
    "artist": "Artist's Name",
    "website": "Art's Website",
}
PLACEHOLDER_SP = {
    "What is it Called?": "name",
    "How is it Called?": "name",
    "How did they obtain it?": "method",
    "What does the Special Ability do?": "description",
    "How does it make the character's life easier?": "pros",
    "How does it make the character's life harder?": "cons",
}
PLACEHOLDER_STATS = {
    "HP": "HP",
    "Attack": "ATK",
    "Defense": "DEF",
    "Special Attack": "SPA",
    "Special Defense": "SPD",
    "Speed": "SPE",
}


def kind_deduce(item: SpeciesBase | None, *args, **kwargs):
    """This class returns the character class based on the given species

    Attributes
    ----------
    item : SpeciesBase | None
        Species
    args : Any
        Args of the Character class
    kwargs : Any
        kwargs of the Character class

    Returns
    -------
    Character | None
        Character instance
    """
    match item:
        case x if isinstance(x, Pokemon):
            return PokemonCharacter(*args, **kwargs)
        case x if isinstance(x, Mega):
            return MegaCharacter(*args, **kwargs)
        case x if isinstance(x, Legendary):
            return LegendaryCharacter(*args, **kwargs)
        case x if isinstance(x, Mythical):
            return MythicalCharacter(*args, **kwargs)
        case x if isinstance(x, UltraBeast):
            return UltraBeastCharacter(*args, **kwargs)
        case x if isinstance(x, Fakemon):
            return FakemonCharacter(*args, **kwargs)
        case x if isinstance(x, Fusion):
            return FusionCharacter(*args, **kwargs)
        case _:
            return None


@dataclass(unsafe_hash=True, slots=True)
class Elements:
    """Element Character data"""

    movepool: Movepool = field(default_factory=Movepool)
    types: set[Types] = field(default_factory=set)
    fusion: set[str] = field(default_factory=set)
    abilities: set[Abilities] = field(default_factory=set)
    moves: set[str] = field(default_factory=set)
    stats: dict[str, Literal[1, 2, 3, 4, 5]] = field(default_factory=dict)
    sp_ability: Optional[SpAbility] = None
    kwargs: dict[str, str] = field(default_factory=dict)
    fakemon: Optional[str] = None
    pronoun: Pronoun = Pronoun.Them
    species: Optional[str] = None

    @property
    def kind(self):
        if self.fusion:
            return "FUSION"
        if self.fakemon:
            return "FAKEMON"
        if self.sp_ability:
            return "COMMON"
        return None

    def __getitem__(self, value: str):
        """Kwargs getter

        Parameters
        ----------
        value : str
            key

        Returns
        -------
        Optional[Any]
            data
        """
        return self.kwargs.get(value)

    def __setitem__(self, key: str, value: str):
        """Item setter

        Parameters
        ----------
        key : str
            assignation key
        value : str
            assignation value
        """
        if key == "ability":
            if not self.abilities:
                self.abilities.update(Abilities.deduce(value))
        elif key in ["gender", "pronoun"]:
            self.pronoun = Pronoun.deduce(value)
        elif key == "fakemon":
            self.fakemon = value
        elif key == "species":
            if self.stats:
                self.fakemon = value
            else:
                self.species = value
        else:
            self.kwargs[key] = value

    def __delitem__(self, key: str):
        self.kwargs.pop(key, None)


def check(value: Optional[str]) -> bool:
    """A checker function to determine what is useful
    out of a character template

    Parameters
    ----------
    value : Optional[str]
        item to be inspected

    Returns
    -------
    bool
        If this item should be parsed or not
    """
    if value in PLACEHOLDER_NAMES:
        return False
    if value in PLACEHOLDER_DEFAULTS.values():
        return False
    return str(value).title() not in ["None", "Move"]


async def doc_convert(url: str):
    if match := G_DOCUMENT.match(url):
        url = match.group(1)
    if doc := await to_thread(docs_reader, url):
        tables = nested_lookup(key="table", document=doc["body"]["content"])
        contents = nested_lookup(key="textRun", document=tables)
        content_values: list[str] = nested_lookup(key="content", document=contents)

        text = [strip.replace("\u2019", "'") for item in content_values if (strip := item.strip())]
        raw_stats: dict[str, int] = {
            stat: stats_check(*value)
            for index, item in enumerate(content_values)
            if all(
                (
                    stat := PLACEHOLDER_STATS.get(item.strip()),
                    len(content_values) > index,
                    len(value := content_values[index + 1:][:1]) == 1,
                )
            )
        }
        raw_moves: set[str] = set()
        raw_movepool: dict[str, set[str] | dict[int | set[str]]] = {}
        raw_abilities: set[str] = set()
        raw_fusion: set[str] = set()
        raw_types: set[str] = set()
        raw_kwargs: dict[str, Any] = dict()

        for index, item in enumerate(text, start=1):
            if index == len(text):
                continue
            if check(next_value := text[index]):
                if match := MOVE_FINDER.match(item):
                    x, y = match.groups()
                    argument = next_value.title()
                    if x == "Level":
                        idx = int(y)
                        raw_movepool.setdefault("level", {})
                        raw_movepool["level"].setdefault(idx, set())
                        raw_movepool["level"][idx].add(argument)
                    elif x == "Move":
                        raw_moves.add(argument)
                    else:
                        raw_movepool.setdefault(x, set())
                        raw_movepool[x].add(argument)
                elif match := DATA_FINDER.match(item):
                    if match.group(1) == "Ability":
                        raw_abilities.add(next_value)
                    else:
                        raw_fusion.add(next_value)
                elif TYPE_FINDER.match(item):
                    raw_types.add(next_value.upper())
                elif argument := PLACEHOLDER_NAMES.get(item):
                    raw_kwargs[argument] = next_value

        if raw_moves:
            raw_kwargs["moveset"] = raw_moves
        if raw_stats:
            raw_kwargs["stats"] = raw_stats
        if raw_movepool:
            raw_kwargs["movepool"] = raw_movepool
        if raw_abilities:
            raw_kwargs["abilities"] = raw_abilities

        raw_kwargs.pop("artist", None)
        raw_kwargs.pop("website", None)

        if inlineObjects := doc.get("inlineObjects"):
            if images := nested_lookup(key="contentUri", document=inlineObjects):
                raw_kwargs["image"] = images[0]

        return raw_kwargs
