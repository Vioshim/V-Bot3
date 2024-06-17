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

import operator
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import reduce
from itertools import combinations_with_replacement
from json import JSONEncoder, load
from typing import Any, Callable, Iterable, Optional, Type

from discord.utils import find, get
from frozendict import frozendict
from rapidfuzz import process

from src.structures.ability import Ability
from src.structures.mon_typing import TypingEnum
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.utils.functions import fix

__all__ = (
    "Species",
    "Fakemon",
    "UltraBeast",
    "Mythical",
    "Legendary",
    "Mega",
    "Fusion",
    "Pokemon",
    "CustomMega",
    "Variant",
    "CustomParadox",
    "CustomUltraBeast",
    "ALL_SPECIES",
    "SPECIES_BY_NAME",
)


class Colors(Enum):
    Green = 0x64D364
    Purple = 0xC183C1
    White = 0xFFF
    Blue = 0x94DBEE
    Red = 0xEC8484
    Brown = 0xC96
    Gray = 0xD1D1E0
    Pink = 0xF4BDC9
    Black = 0xBBB
    Yellow = 0xFF9


ALL_SPECIES = frozendict()
SPECIES_BY_NAME = frozendict()
PHRASES = {
    "GALAR": "Galarian",
    "HISUI": "Hisuian",
    "ALOLA": "Alolan",
    "KANTO": "Kantoian",
    "PALDEA": "Paldean",
}


def merge_strings(s1, s2):
    # Split strings into parts
    parts1 = re.split(r"(\s+)", s1)
    parts2 = re.split(r"(\s+)", s2)

    if len(parts1) != len(parts2):
        raise ValueError("The strings must have the same number of parts")

    merged_parts = []

    # Combine corresponding parts from both strings
    for part1, part2 in zip(parts1, parts2):
        if part1 == part2:
            merged_parts.append(part1)
        elif re.fullmatch(r"\s+", part1):
            merged_parts.append(part1)
        else:
            merged_parts.append(f"{part1}/{part2}")

    return "".join(merged_parts)


def merge_multiple_strings(strings: Iterable[str]):
    return reduce(merge_strings, strings)


@dataclass(unsafe_hash=True, slots=True)
class Species:
    __dict__ = {}
    id: str = ""
    name: str = ""
    shape: str = ""
    base_image: Optional[str] = None
    base_image_shiny: Optional[str] = None
    female_image: Optional[str] = None
    female_image_shiny: Optional[str] = None
    types: frozenset[TypingEnum] = field(default_factory=frozenset)
    height: float = 1.0
    weight: float = 50.0
    HP: int = 0
    ATK: int = 0
    DEF: int = 0
    SPA: int = 0
    SPD: int = 0
    SPE: int = 0
    banned: bool = False
    evolves_from: Optional[str] = None
    evolves_to: frozenset[str] = field(default_factory=frozenset)
    movepool: Movepool = field(default_factory=Movepool)
    abilities: frozenset[Ability] = field(default_factory=frozenset)
    egg_groups: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        self.evolves_to = frozenset(self.evolves_to)

        if isinstance(self.abilities, str):
            self.abilities = [self.abilities]
        self.abilities = Ability.deduce_many(*self.abilities)

        if isinstance(self.movepool, dict):
            self.movepool = Movepool.from_notif_dict(**self.movepool)

        if isinstance(self.types, str):
            self.types = [self.types]
        self.types = TypingEnum.deduce_many(*self.types)

        if isinstance(self.evolves_to, str):
            self.evolves_to = [self.evolves_to]
        self.evolves_to = frozenset(self.evolves_to)

        if isinstance(self.egg_groups, str):
            self.egg_groups = [self.egg_groups]
        self.egg_groups = frozenset(self.egg_groups)

    def __eq__(self, other: Species):
        return isinstance(other, Species) and str(self.id) == str(other.id)

    def image(self, gender: Optional[Pronoun], shiny: bool = False):
        match (gender, shiny):
            case (Pronoun.She, True):
                return self.female_image_shiny
            case (Pronoun.She, False):
                return self.female_image
            case (_, True):
                return self.base_image_shiny
            case _:
                return self.base_image

    @property
    def first_evo(self):
        return self.evol_line[0]

    @property
    def evol_line(self):
        items = [self]
        aux = self
        while isinstance(mon := aux.species_evolves_from, Species):
            items.append(aux := mon)
        return items[::-1]

    @classmethod
    def all(
        cls,
        *,
        include: Optional[Iterable[Type[Species]] | Type[Species]] = None,
        exclude: Optional[Iterable[Type[Species]] | Type[Species]] = None,
    ) -> frozenset[Species]:
        include = tuple(include) if isinstance(include, Iterable) else (include or cls)
        exclude = tuple(exclude) if isinstance(exclude, Iterable) else (exclude or None)

        def check(x: Species):
            condition = isinstance(x, include)
            if exclude is not None:
                condition &= not isinstance(x, exclude)
            return condition

        return frozenset(filter(check, ALL_SPECIES.values()))

    @classmethod
    def find(cls, predicate: Callable[[Species], Any]):
        return find(predicate, cls.all())

    @classmethod
    def get(cls, **kwargs):
        return get(cls.all(), **kwargs)

    @property
    def possible_types(self):
        items = {self.types} if self.types else []
        return frozenset(items)

    @property
    def total_movepool(self):
        if TypingEnum.Shadow in self.types:
            return Movepool.shadow()

        mon = self
        aux = self.movepool
        while mon := mon.species_evolves_from:
            if not aux:
                aux += mon.movepool
            else:
                moves = mon.movepool.without_moves(aux)
                aux += Movepool(egg=mon.movepool.egg, other=moves())
        return aux

    @property
    def species_evolves_to(self) -> list[Species]:
        return [mon for item in self.evolves_to if (mon := Species.from_ID(item))]

    @property
    def species_evolves_from(self) -> Optional[Species]:
        if mon := self.evolves_from:
            return Species.from_ID(mon)

    @classmethod
    def deduce(cls, item: str):
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for

        Returns
        -------
        Optional[Type[Species]]
            result
        """
        aux: list[str] = []
        items: list[cls] = []

        if not item:
            return frozenset(items)

        if isinstance(item, str) or not isinstance(item, Iterable):
            item = [item]

        for elem in item:
            if isinstance(elem, str):
                aux.append(elem)
            elif isinstance(elem, cls):
                items.append(elem)

        entries = list(cls.all())

        for word in filter(bool, [x.strip().title() for x in ",".join(aux).split(",")]):
            for key, value in PHRASES.items():
                phrase1, phrase2 = f"{value} ".title(), f"{key} ".title()
                if word.startswith(phrase1) or word.startswith(phrase2):
                    word = word.removeprefix(phrase1)
                    word = word.removeprefix(phrase2)
                    if key != "KANTO":
                        word = f"{word} {key}".title()
                    break

            if data := SPECIES_BY_NAME.get(word) or ALL_SPECIES.get(fix(word)):
                items.append(data)
            elif elements := process.extractOne(
                query=word,
                choices=entries,
                processor=lambda x: getattr(x, "name", x),
                score_cutoff=85,
            ):
                items.append(elements[0])

        return frozenset(items)

    @classmethod
    def single_deduce(cls, item: str):
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for

        Returns
        -------
        Optional[Type[Species]]
            result
        """
        aux: list[str] = []

        if not item:
            return

        if isinstance(item, str) or not isinstance(item, Iterable):
            item = [item]

        for elem in item:
            if isinstance(elem, str):
                aux.append(elem)
            if isinstance(elem, cls):
                return elem

        entries = list(cls.all())
        items = [o for x in ",".join(aux).split(",") if (o := x.strip().title())]

        for word in items:
            for key, value in PHRASES.items():
                phrase1, phrase2 = f"{value} ".title(), f"{key} ".title()
                if word.startswith(phrase1) or word.startswith(phrase2):
                    word = word.removeprefix(phrase1)
                    word = word.removeprefix(phrase2)
                    if key != "KANTO":
                        word = f"{word} {key}".title()
                    break

            if data := SPECIES_BY_NAME.get(word) or ALL_SPECIES.get(fix(word)):
                return data
            if elements := process.extractOne(
                query=word,
                choices=entries,
                processor=lambda x: getattr(x, "name", x),
                score_cutoff=85,
            ):
                return elements[0]

    @classmethod
    def any_deduce(cls, item: str):
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for

        Returns
        -------
        Optional[Type[Species]]
            result
        """
        if "," not in item and "_" not in item:
            return cls.single_deduce(item)

        # between 2 and 3
        if 2 <= len(items := set(cls.deduce(item))) <= 3:
            return Fusion(*items)

        if items:
            return items.pop()

    @classmethod
    def from_ID(cls, item: str):
        """This method returns the species given exact IDs

        Returns
        -------
        Optional[Species]
            result
        """
        if isinstance(item, cls):
            return item

        if isinstance(item, str):
            values = {i.id: i for i in cls.all()} or ALL_SPECIES
            items = {x for i in item.split("_") if (x := values.get(i))}
            if len(items) > 1:
                items = {Fusion(*items)}

            if items and isinstance(data := items.pop(), cls):
                return data

    @classmethod
    def hook(cls, dct: dict[str, Any], default=None):
        """Converter

        Parameters
        ----------
        dct : dict[str, Any]
            Input

        Returns
        -------
        Any
            Output
        """
        if "id" in dct:
            match dct.pop("kind", ""):
                case "Legendary":
                    return Legendary(**dct)
                case "Mythical":
                    return Mythical(**dct)
                case "UltraBeast":
                    return UltraBeast(**dct)
                case "Mega":
                    return Mega(**dct)
                case "Paradox":
                    return Paradox(**dct)
                case _:
                    return Pokemon(**dct)
        return default

    def as_data(self) -> dict[str, str] | str:
        return self.id

    @classmethod
    def from_data(cls, value: str | dict[str, str]):
        if not value or isinstance(value, str):
            return cls.from_ID(value)

        children_classes = {x.__name__.removeprefix("Custom").lower(): x for x in CustomSpecies.__subclasses__()}
        children_classes |= {x.__name__.removeprefix("Custom").lower(): x for x in GimmickSpecies.__subclasses__()}
        children_classes["base"] = Variant
        children_classes["ub"] = CustomUltraBeast

        item = value.copy()
        for k, v in children_classes.items():
            if data := item.pop(k, None):
                return v(base=data, **item)

        if data := item.get("fusion", []):
            if isinstance(data, dict):
                data = data.get("species", [])

            fusion = Fusion(*data)

            if not fusion.types:
                fusion.types = TypingEnum.deduce_many(*item.get("types", []))

            return fusion

        return Fakemon(**item)


@dataclass(unsafe_hash=True, slots=True)
class Pokemon(Species):
    "This class Represents a common Pokemon"


@dataclass(unsafe_hash=True, slots=True)
class Legendary(Species):
    "This class Represents a legendary"


@dataclass(unsafe_hash=True, slots=True)
class Mythical(Species):
    "This class Represents a Mythical"


@dataclass(unsafe_hash=True, slots=True)
class Mega(Species):
    "This class Represents a Mega"


@dataclass(unsafe_hash=True, slots=True)
class UltraBeast(Species):
    "This class Represents an UltraBeast"


@dataclass(unsafe_hash=True, slots=True)
class Paradox(Species):
    "This class Represents a Paradox"


@dataclass(unsafe_hash=True, slots=True)
class GMax(Species):
    "This class Represents a Gigantamax"


@dataclass(unsafe_hash=True, slots=True)
class Fusion(Species):
    "This class Represents a fusion"

    bases: frozenset[Species] = field(default_factory=frozenset)

    def __init__(self, *bases: Species | str):
        self.bases = frozenset({o for x in bases if (o := Species.single_deduce(x) if isinstance(x, str) else x)})
        mons = sorted(self.bases, key=lambda x: x.id)
        abilities = reduce(operator.or_, (x.abilities for x in mons), frozenset())
        amount = len(mons) or 1
        super(Fusion, self).__init__(
            id="_".join(x.id for x in mons),
            name=merge_multiple_strings([x.name for x in mons]),
            height=sum(x.height for x in mons) / amount,
            weight=sum(x.weight for x in mons) / amount,
            HP=sum(x.HP for x in mons) // amount,
            ATK=sum(x.ATK for x in mons) // amount,
            DEF=sum(x.DEF for x in mons) // amount,
            SPA=sum(x.SPA for x in mons) // amount,
            SPD=sum(x.SPD for x in mons) // amount,
            SPE=sum(x.SPE for x in mons) // amount,
            banned=any(x.banned for x in mons),
            movepool=reduce(operator.add, (x.movepool for x in mons), Movepool()),
            abilities=abilities,
            egg_groups=reduce(operator.or_, (x.egg_groups for x in mons), frozenset()),
        )
        if len(items := list(self.possible_types)) == 1:
            self.types = frozenset(items[0])

        self.evolves_to = frozenset(reduce(operator.or_, (x.evolves_to for x in mons), frozenset()))

    def __eq__(self, other: Fusion):
        if isinstance(other, Fusion):
            return self.bases == other.bases
        return super(Fusion, self).__eq__(other)

    @property
    def label_name(self):
        return ", ".join(x.name for x in sorted(self.bases, key=lambda x: x.id))

    @property
    def species_evolves_to(self) -> list[Fusion]:
        items = frozenset.union(*[x.evolves_to for x in self.bases])
        return [Fusion(*x) for i in range(2, len(items) + 1) for x in combinations_with_replacement(items, i)]

    @property
    def species_evolves_from(self):
        items = {x.evolves_from for x in self.bases if x.evolves_from}
        if len(items) == 1:
            return Species.from_ID(items.pop())

    @property
    def total_movepool(self):
        if TypingEnum.Shadow in self.types:
            return Movepool.shadow()

        return reduce(
            operator.add,
            (x.species_evolves_from.total_movepool for x in self.bases if x.species_evolves_from),
            self.movepool,
        )

    @property
    def evol_line(self):
        return reduce(operator.add, (x.evol_line for x in self.bases), [])

    @property
    def possible_types(self) -> frozenset[frozenset[TypingEnum]]:
        """This returns a list of valid types for the pokemon

        Returns
        -------
        frozenset[frozenset[Typing]]
            List of sets (valid types)
        """
        total = reduce(operator.or_, (x.types for x in self.bases), frozenset())
        return frozenset(map(frozenset, combinations_with_replacement(total, max(len(self.bases), 2))))

    @classmethod
    def deduce(cls, item: str) -> Optional[Fusion]:
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for

        Returns
        -------
        Optional[Fusion]
            result
        """
        if isinstance(mon := Species.any_deduce(item), cls):
            return mon

    @classmethod
    def from_ID(cls, item: str) -> Optional[Fusion]:
        """This method returns the species given exact IDs

        Returns
        -------
        Optional[Fusion]
            result
        """
        if isinstance(item, cls):
            return item

        if isinstance(item, str):
            values = {i.id: i for i in cls.all()} or ALL_SPECIES
            items = {x for i in item.split("_") if (x := values.get(i))}
            return Fusion(*items)

    def as_data(self):
        return {
            "fusion": {"species": [x.id for x in self.bases]},
            "types": [x.name for x in self.types],
        }


@dataclass(unsafe_hash=True, slots=True)
class CustomSpecies(Species):
    "This class Represents a Custom Pokemon"
    base: Optional[Species] = None

    def __init__(
        self,
        name: str = "",
        base: Optional[Species] = None,
        abilities: Optional[frozenset[Ability]] = None,
        movepool: Optional[Movepool] = None,
        types: Optional[frozenset[TypingEnum]] = None,
        evolves_from: Optional[str] = None,
    ):
        base = Species.single_deduce(base)

        if base is None:
            super().__init__(
                name=name,
                abilities=frozenset() if abilities is None else abilities.copy(),
                types=types or frozenset(),
                movepool=Movepool() if movepool is None else movepool.copy(),
                evolves_from=evolves_from,
            )
        else:
            super().__init__(
                id=base.id,
                name=name or base.name,
                shape=base.shape,
                height=base.height,
                weight=base.weight,
                HP=base.HP,
                ATK=base.ATK,
                DEF=base.DEF,
                SPA=base.SPA,
                SPD=base.SPD,
                SPE=base.SPE,
                banned=base.banned,
                abilities=(abilities or base.abilities).copy(),
                types=types or base.types.copy(),
                movepool=(movepool or base.movepool).copy(),
                evolves_from=evolves_from or base.id,
                base_image=base.base_image,
                base_image_shiny=base.base_image_shiny,
                female_image=base.female_image,
                female_image_shiny=base.female_image_shiny,
            )

        self.base = base

    @classmethod
    def deduce(cls, item: str):
        """Method deduce but filtered

        Parameters
        ----------
        item : str
            item to look for
        """
        items = set()
        if (mon := Species.single_deduce(item)) and not isinstance(mon, cls):
            cls_name = cls.__name__.removeprefix("Custom")
            items.add(cls(base=mon, name=f"{cls_name} {mon.name}"))
        return frozenset(items)

    @classmethod
    def from_ID(cls, item: str):
        """Method from ID but filtered

        Parameters
        ----------
        item : str
            placeholder
        """
        if (mon := Species.from_ID(item)) and not isinstance(mon, Fusion):
            cls_name = cls.__name__.removeprefix("Custom")
            return cls(base=mon, name=f"{cls_name} {mon.name}")

    def as_data(self):
        data: dict[str, Any] = {
            self.__class__.__name__.removeprefix("Custom").lower(): self.id,
        }

        if isinstance(self.base, Species):
            if self.name != self.base.name:
                data["name"] = self.name
            if self.abilities != self.base.abilities:
                data["abilities"] = [x.id for x in self.abilities]
            if self.types != self.base.types:
                data["types"] = [x.name for x in self.types]
            if self.movepool != self.base.movepool:
                data["movepool"] = self.movepool.as_dict
            if self.evolves_from != self.base.id:
                data["evolves_from"] = self.evolves_from
        else:
            data["name"] = self.name
            data["abilities"] = [x.id for x in self.abilities]
            data["types"] = [x.name for x in self.types]
            data["movepool"] = self.movepool.as_dict
            data["evolves_from"] = self.evolves_from

        return data

    def can_change_movepool(self):
        if isinstance(self.base, Species):
            return self.movepool != self.base.movepool
        return False


@dataclass(unsafe_hash=True, slots=True)
class GimmickSpecies(CustomSpecies):
    "This class Represents a Gimmick Species"


@dataclass(unsafe_hash=True, slots=True)
class CustomMega(GimmickSpecies):
    "This class Represents a Custom Mega"


@dataclass(unsafe_hash=True, slots=True)
class CustomTera(GimmickSpecies):
    "This class Represents a Custom Tera"


@dataclass(unsafe_hash=True, slots=True)
class CustomGMax(GimmickSpecies):
    "This class Represents a Custom GMax"


@dataclass(unsafe_hash=True, slots=True)
class Fakemon(CustomSpecies):
    "This class Represents a Fakemon"


@dataclass(unsafe_hash=True, slots=True)
class CustomParadox(CustomSpecies):
    "This class Represents a Custom Paradox"

    def __init__(
        self,
        base: Species,
        name: str = "",
        abilities: Optional[frozenset[Ability]] = None,
        movepool: Optional[Movepool] = None,
        types: Optional[frozenset[TypingEnum]] = None,
    ):
        super().__init__(
            base=base,
            name=name,
            abilities=frozenset(
                {
                    o
                    for x in (
                        "Protosynthesis",
                        "Quark Drive",
                    )
                    if (o := Ability.get(name=x))
                }
            ),
            movepool=movepool,
            types=types,
        )


@dataclass(unsafe_hash=True, slots=True)
class CustomUltraBeast(CustomSpecies):
    "This class Represents a Custom Ultra Beast"

    def __init__(
        self,
        base: Species,
        name: str = "",
        abilities: Optional[frozenset[Ability]] = None,
        movepool: Optional[Movepool] = None,
        types: Optional[frozenset[TypingEnum]] = None,
    ):
        super(CustomUltraBeast, self).__init__(
            base=base,
            name=name,
            abilities=frozenset({o for x in ("Beast Boost",) if (o := Ability.get(name=x))}),
            movepool=movepool,
            types=types,
        )


@dataclass(unsafe_hash=True, slots=True)
class Variant(CustomSpecies):
    "This class Represents a Variant"


@dataclass(unsafe_hash=True, slots=True)
class AuraBot(CustomSpecies):
    "This class Represents an Aura Bot"

    def __init__(
        self,
        base: Species,
        name: str = "",
        abilities: Optional[frozenset[Ability]] = None,
        movepool: Optional[Movepool] = None,
        types: Optional[frozenset[TypingEnum]] = None,
    ):
        super(AuraBot, self).__init__(
            base=base,
            name=name,
            abilities=abilities,
            movepool=movepool,
            types=types,
        )
        self.height /= 10
        self.weight /= 10


class SpeciesEncoder(JSONEncoder):
    """Species encoder"""

    def default(self, o):
        """[summary]

        Parameters
        ----------
        o : [type]
            [description]

        Returns
        -------
        [type]
            [description]
        """
        if isinstance(o, Species):
            item = asdict(o)
            item["abilities"] = sorted(i.id for i in o.abilities)
            item["types"] = [str(i) for i in o.types]
            item["movepool"] = o.movepool.as_dict
            item["evolves_to"] = sorted(o.evolves_to)
            item["kind"] = type(o).__name__
            return item
        return super(SpeciesEncoder, self).default(o)


with open("resources/species.json", mode="r", encoding="utf8") as f:
    DATA: list[Species] = load(f, object_hook=lambda x: Species.hook(x, x))
    ALL_SPECIES: frozendict[str, Species] = frozendict({item.id: item for item in DATA if isinstance(item, Species)})
    SPECIES_BY_NAME: frozendict[str, Species] = frozendict(
        {item.name: item for item in DATA if isinstance(item, Species)}
    )
