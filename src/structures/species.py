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

from abc import ABCMeta, abstractmethod
from copy import copy
from dataclasses import asdict, dataclass, field
from enum import Enum
from functools import cached_property, lru_cache
from itertools import combinations
from json import JSONDecoder, JSONEncoder, load
from typing import Any, Callable, Iterable, Optional

from asyncpg import Record
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
    "Chimera",
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
_BEASTBOOST = Ability.from_ID(item="BEASTBOOST")
PHRASES = {
    "GALAR": "Galarian",
    "HISUI": "Hisuian",
    "ALOLA": "Alolan",
    "KANTO": "Kantoian",
}


@dataclass(unsafe_hash=True, slots=True)
class Species(metaclass=ABCMeta):
    id: str = ""
    name: str = ""
    shape: str = ""
    base_image: Optional[str] = None
    base_image_shiny: Optional[str] = None
    female_image: Optional[str] = None
    female_image_shiny: Optional[str] = None
    types: frozenset[TypingEnum] = field(default_factory=frozenset)
    height: int = 0
    weight: int = 0
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

    def __post_init__(self):
        self.evolves_to = frozenset(self.evolves_to)

        if isinstance(self.abilities, str):
            self.abilities = [self.abilities]
        self.abilities = Ability.deduce_many(*self.abilities)

        if isinstance(self.movepool, dict):
            self.movepool = Movepool.from_dict(**self.movepool)

        if isinstance(self.types, str):
            self.types = [self.types]
        self.types = TypingEnum.deduce_many(*self.types)

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
    def all(cls) -> frozenset[Species]:
        return frozenset(x for x in ALL_SPECIES.values() if isinstance(x, cls))

    @classmethod
    def find(cls, predicate: Callable[[Species], Any]):
        return find(predicate, cls.all())

    @classmethod
    def get(cls, **kwargs):
        return get(cls.all(), **kwargs)

    @cached_property
    def possible_types(self):
        return frozenset({self.types} if self.types else [])

    @cached_property
    def total_movepool(self):
        mon = self
        aux = self.movepool
        while mon := mon.species_evolves_from:
            if not aux:
                aux += mon.movepool
            else:
                moves = mon.movepool.without_moves(aux)
                aux += Movepool(egg=mon.movepool.egg, other=moves())
        return aux

    @cached_property
    def species_evolves_to(self) -> list[Species]:
        return [mon for item in self.evolves_to if (mon := Species.from_ID(item))]

    @cached_property
    def species_evolves_from(self) -> Optional[Species]:
        if mon := self.evolves_from:
            return Species.from_ID(mon)

    @property
    @abstractmethod
    def requires_image(self) -> bool:
        """This is a method that determines whether
        if a kind requires image

        Returns
        -------
        bool
            value
        """

    @property
    @abstractmethod
    def can_have_special_abilities(self) -> bool:
        """This is a method that determines whether
        if a kind can or not have a special ability

        Returns
        -------
        bool
            value
        """

    @property
    @abstractmethod
    def max_amount_abilities(self) -> int:
        """This is a method that determines
        how many abilities can be carried as max

        Returns
        -------
        int
            value
        """

    @classmethod
    @lru_cache
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
    @lru_cache
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
    @lru_cache
    def any_deduce(cls, item: str, chimera: bool = False):
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
        if items := set(cls.deduce(item)):
            if chimera:
                return Chimera(items)
            if len(items) == 2:
                mon1, mon2 = items
                return Fusion(mon1=mon1, mon2=mon2)
            return items.pop()

    @classmethod
    @lru_cache
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
            if len(items) == 2:
                items = {Fusion(*items)}
            if items and isinstance(data := items.pop(), cls):
                return data


@dataclass(unsafe_hash=True, slots=True)
class Pokemon(Species):
    """
    This class Represents a common Pokemon
    """

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def can_have_special_abilities(self):
        return True

    @property
    def max_amount_abilities(self) -> int:
        return min(len(self.abilities), 2)


@dataclass(unsafe_hash=True, slots=True)
class Legendary(Species):
    """
    This class Represents a legendary
    """

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def can_have_special_abilities(self):
        return False

    @property
    def max_amount_abilities(self) -> int:
        return min(len(self.abilities), 2)


@dataclass(unsafe_hash=True, slots=True)
class Mythical(Species):
    """
    This class Represents a Mythical
    """

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def can_have_special_abilities(self):
        return False

    @property
    def max_amount_abilities(self) -> int:
        return min(len(self.abilities), 2)


@dataclass(unsafe_hash=True, slots=True)
class Mega(Species):
    """
    This class Represents a legendary
    """

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def can_have_special_abilities(self):
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1


@dataclass(unsafe_hash=True, slots=True)
class UltraBeast(Species):
    """
    This class Represents a legendary
    """

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def can_have_special_abilities(self):
        return False

    @property
    def max_amount_abilities(self) -> int:
        return 1


@dataclass(unsafe_hash=True, slots=True)
class Fakemon(Species):
    """
    This class Represents a fakemon
    """

    @classmethod
    def from_record(cls, record: Record):
        if not record:
            return
        return Fakemon(id=record["id"], name=record["name"], evolves_from=record["evolves_from"])

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1 if _BEASTBOOST in self.abilities else 2

    @property
    def can_have_special_abilities(self) -> bool:
        return _BEASTBOOST not in self.abilities

    @classmethod
    @lru_cache
    def deduce(cls, item: str):
        """Method deduce but filtered, (fakemon that evolved from a canon species)

        Parameters
        ----------
        item : str
            item to look for

        Returns
        -------
        Optional[Fakemon]
            Result
        """
        if (mon := Species.single_deduce(item)) and not isinstance(mon, cls):
            return cls(evolves_from=mon.id)

    @classmethod
    @lru_cache
    def from_ID(cls, item: str) -> Optional[Fakemon]:
        """Method from ID but filtered, (fakemon that evolved from a canon species)

        Parameters
        ----------
        item : str
            placeholder
        """
        if (mon := Species.from_ID(item)) and not isinstance(mon, Fusion):
            return Fakemon(evolves_from=mon.id)


@dataclass(unsafe_hash=True, slots=True)
class Chimera(Species):
    """
    This class Represents a Chimera
    """

    bases: frozenset[Species] = field(default_factory=frozenset)

    def __init__(self, bases: frozenset[Species]):
        bases = {o for x in bases if (o := Species.from_ID(x) if isinstance(x, str) else x)}
        self.bases = frozenset(bases)
        amount = len(bases) or 1

        if abilities := [set(x.abilities) for x in bases]:
            abilities = set.union(*abilities)

        movepool = Movepool(egg=set.intersection(*[set(base.total_movepool()) for base in bases]))

        super(Chimera, self).__init__(
            id="_".join(sorted(x.id for x in bases)),
            name="/".join(sorted(x.name for x in bases)),
            height=round(sum(x.height for x in bases) / amount),
            weight=round(sum(x.weight for x in bases) / amount),
            HP=round(sum(x.HP for x in bases) / amount),
            ATK=round(sum(x.ATK for x in bases) / amount),
            DEF=round(sum(x.DEF for x in bases) / amount),
            SPA=round(sum(x.SPA for x in bases) / amount),
            SPD=round(sum(x.SPD for x in bases) / amount),
            SPE=round(sum(x.SPE for x in bases) / amount),
            banned=any(x.banned for x in bases),
            movepool=movepool,
            abilities=abilities,
        )

        shapes = {x.shape for x in bases}
        if len(shapes) == 1:
            self.shape = shapes.pop()

    def __eq__(self, other: Chimera):
        if isinstance(other, Chimera):
            return self.bases == other.bases
        return super(Chimera, self).__eq__(other)

    @cached_property
    def total_movepool(self):
        bases = [base for base in self.bases if base.id not in ["MEW", "DITTO", "SMEARGLE"]]
        items = [frozenset(base.total_movepool()) for base in bases]
        if items:
            return Movepool(egg=frozenset.intersection(*items))
        return Movepool()

    @cached_property
    def possible_types(self):
        """This returns a list of valid types for the pokemon

        Returns
        -------
        frozenset[frozenset[Typing]]
            List of sets (valid types)
        """
        elements = [*{x.types for x in self.bases}]
        if elements and all(x == elements[0] for x in elements):
            return frozenset({elements[0]})
        elements = frozenset[TypingEnum].union(*elements)
        items = [frozenset({x}) for x in elements]
        items.extend(combinations(elements, 2))
        return frozenset(items)

    @property
    def evol_line(self):
        return []

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @property
    def can_have_special_abilities(self) -> bool:
        return False

    @classmethod
    @lru_cache
    def deduce(cls, item: str) -> Optional[Chimera]:
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for

        Returns
        -------
        Optional[Chimera]
            result
        """
        if isinstance(mon := Species.any_deduce(item, chimera=True), cls):
            return mon


@dataclass(unsafe_hash=True, slots=True)
class CustomMega(Species):
    """
    This class Represents a Custom Mega
    """

    base: Optional[Species] = None

    def __init__(self, base: Species):
        super(CustomMega, self).__init__(
            id=base.id,
            name=f"Mega {base.name}",
            shape=base.shape,
            height=base.height,
            weight=base.weight,
            HP=base.HP,
            ATK=base.ATK,
            DEF=base.DEF,
            SPA=base.SPA,
            SPD=base.SPD,
            SPE=base.SPE,
            movepool=base.movepool,
            abilities=copy(base.abilities),
        )
        self.base = base

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @property
    def can_have_special_abilities(self) -> bool:
        return True

    @classmethod
    @lru_cache
    def deduce(cls, item: str) -> Optional[CustomMega]:
        """Method deduce but filtered

        Parameters
        ----------
        item : str
            item to look for

        Returns
        -------
        Optional[CustomMega]
            Result
        """
        if (mon := Species.single_deduce(item)) and not isinstance(mon, cls):
            return cls(base=mon)

    @classmethod
    @lru_cache
    def from_ID(cls, item: str) -> Optional[CustomMega]:
        """Method from ID but filtered

        Parameters
        ----------
        item : str
            placeholder
        """
        if (mon := Species.from_ID(item)) and not isinstance(mon, Fusion):
            return CustomMega(base=mon)


@dataclass(unsafe_hash=True, slots=True)
class Variant(Species):
    """
    This class Represents a Variant
    """

    base: Optional[Species] = None

    def __init__(
        self,
        base: Species,
        name: str,
        types: frozenset[TypingEnum] = None,
        evolves_from: Optional[str] = None,
        abilities: frozenset[Ability] = None,
        movepool: Optional[Movepool] = None,
    ):
        super(Variant, self).__init__(
            id=base.id,
            name=name.title(),
            shape=base.shape,
            height=base.height,
            weight=base.weight,
            HP=base.HP,
            ATK=base.ATK,
            DEF=base.DEF,
            SPA=base.SPA,
            SPD=base.SPD,
            SPE=base.SPE,
            types=types or base.types,
            movepool=movepool or copy(base.movepool),
            abilities=abilities or copy(base.abilities),
            base_image=base.base_image,
            base_image_shiny=base.base_image_shiny,
            female_image=base.female_image,
            female_image_shiny=base.female_image_shiny,
            evolves_from=evolves_from or base.evolves_from,
            evolves_to=base.evolves_to,
        )
        self.base = base

    @classmethod
    def from_record(cls, record: Record):
        if not record:
            return
        species = Species.from_ID(record["species"])
        species = Variant(base=species, name=record["name"])
        movepool_data = record["movepool"]
        if movepool := Movepool.from_dict(**movepool_data):
            species.movepool = movepool
        return species

    @property
    def requires_image(self) -> bool:
        return False

    @property
    def max_amount_abilities(self) -> int:
        return 1 if _BEASTBOOST in self.abilities else 2

    @property
    def can_have_special_abilities(self) -> bool:
        return _BEASTBOOST not in self.abilities and self.base.can_have_special_abilities

    @classmethod
    @lru_cache
    def deduce(cls, item: str) -> Optional[Variant]:
        """Method deduce but filtered

        Parameters
        ----------
        item : str
            item to look for

        Returns
        -------
        Optional[Variant]
            Result
        """
        if (mon := Species.single_deduce(item)) and not isinstance(mon, cls):
            return cls(base=mon, name=f"Variant {mon.name.title()}")

    @classmethod
    @lru_cache
    def from_ID(cls, item: str) -> Optional[Variant]:
        """Method from ID but filtered

        Parameters
        ----------
        item : str
            item to look for

        Returns
        -------
        Optional[Variant]
            Result
        """
        if not item:
            return
        if (mon := Species.from_ID(item)) and not isinstance(mon, Fusion):
            return Variant(base=mon, name=f"Variant {mon.name.title()}")


@dataclass(unsafe_hash=True, slots=True)
class Fusion(Species):
    """
    This class Represents a fusion
    """

    mon1: Optional[Species] = None
    mon2: Optional[Species] = None

    def __init__(self, mon1: Species, mon2: Species):
        ids = sorted((mon1.id, mon2.id))
        names = sorted((mon1.name, mon2.name))
        abilities = mon1.abilities | mon2.abilities
        self.mon1 = mon1
        self.mon2 = mon2
        super(Fusion, self).__init__(
            id="_".join(ids),
            name="/".join(names),
            height=round((mon1.height + mon2.height) / 2),
            weight=round((mon1.weight + mon2.weight) / 2),
            HP=round((mon1.HP + mon2.HP) / 2),
            ATK=round((mon1.ATK + mon2.ATK) / 2),
            DEF=round((mon1.DEF + mon2.DEF) / 2),
            SPA=round((mon1.SPA + mon2.SPA) / 2),
            SPD=round((mon1.SPD + mon2.SPD) / 2),
            SPE=round((mon1.SPE + mon2.SPE) / 2),
            banned=mon1.banned or mon2.banned,
            movepool=mon1.movepool + mon2.movepool,
            abilities=abilities,
            evolves_from=None,
            evolves_to=frozenset(),
        )
        if len(items := list(self.possible_types)) == 1:
            self.types = frozenset(items[0])
        item1 = self.mon1.evolves_to
        item2 = self.mon2.evolves_to
        self.evolves_to = frozenset(zip(item1, item2))
        if mon1.shape == mon2.shape:
            self.shape = mon1.shape
        if (item1 := mon1.evolves_from) and (item2 := mon2.evolves_from):
            self.evolves_from = item1, item2

    def __eq__(self, other: Fusion):
        if isinstance(other, Fusion):
            return self.bases == other.bases
        return super(Fusion, self).__eq__(other)

    @property
    def bases(self) -> frozenset[Species]:
        return frozenset((self.mon1, self.mon2))

    @cached_property
    def species_evolves_to(self) -> list[Fusion]:
        items = [Fusion(mon1=a, mon2=b) for a, b in zip(self.mon1.species_evolves_to, self.mon2.species_evolves_to)]

        for mon in self.mon1.species_evolves_to:
            if mon != self.mon2:
                mon = Fusion(mon1=mon, mon2=self.mon2)
            items.append(mon)

        for mon in self.mon2.species_evolves_to:
            if mon != self.mon1:
                mon = Fusion(mon1=self.mon1, mon2=mon)
            items.append(mon)

        return items

    @property
    def species_evolves_from(self):
        mon1 = self.mon1.species_evolves_from
        mon2 = self.mon2.species_evolves_from
        if mon1 and mon2 and mon1 != mon2:
            return Fusion(mon1=mon1, mon2=mon2)
        return mon1 or mon2

    @property
    def evol_line(self):
        return self.mon1.evol_line + self.mon2.evol_line

    @cached_property
    def total_species_evolves_from(self) -> list[Fusion]:
        items: list[Fusion] = []

        if mon1 := self.mon1.species_evolves_from:
            if mon1 != self.mon2:
                mon = Fusion(mon1=mon1, mon2=self.mon2)
            else:
                mon = mon1
            items.append(mon)

        if mon2 := self.mon2.species_evolves_from:
            if self.mon1 != mon2:
                mon = Fusion(mon1=self.mon1, mon2=mon2)
            else:
                mon = mon2
            items.append(mon)

        if mon1 and mon2:
            if mon1 != mon2:
                mon1 = Fusion(mon1=mon1, mon2=mon2)
            items.append(mon1)

        return items

    @cached_property
    def possible_types(self):
        """This returns a list of valid types for the pokemon

        Returns
        -------
        frozenset[frozenset[Typing]]
            List of sets (valid types)
        """
        types1 = self.mon1.types
        types2 = self.mon2.types
        if types1 == types2:
            return frozenset({types1})
        return frozenset(frozenset({x, y}) for x in types1 for y in types2)

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def can_have_special_abilities(self) -> bool:
        return all(x.can_have_special_abilities for x in self.bases)

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @classmethod
    @lru_cache
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


class SpeciesDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        super(SpeciesDecoder, self).__init__(
            object_hook=self.object_hook,
            *args,
            **kwargs,
        )

    def object_hook(self, dct: dict[str, Any]):
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
        if all(i in dct for i in Species.__slots__):
            match dct.pop("kind", ""):
                case "Legendary":
                    return Legendary(**dct)
                case "Mythical":
                    return Mythical(**dct)
                case "UltraBeast":
                    return UltraBeast(**dct)
                case "Mega":
                    return Mega(**dct)
                case _:
                    return Pokemon(**dct)
        return dct


with open("resources/species.json", mode="r") as f:
    DATA: list[Species] = load(f, cls=SpeciesDecoder)
    ALL_SPECIES: frozendict[str, Species] = frozendict({item.id: item for item in DATA})
    SPECIES_BY_NAME: frozendict[str, Species] = frozendict({item.name: item for item in DATA})
