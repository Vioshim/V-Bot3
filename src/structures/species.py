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
from difflib import get_close_matches
from json import JSONDecoder, JSONEncoder, load
from re import split
from typing import Any, Callable, Iterable, Optional

from frozendict import frozendict

from src.structures.ability import Ability
from src.structures.mon_typing import Typing
from src.structures.movepool import Movepool
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
    "ALL_SPECIES",
    "SPECIES_BY_NAME",
)

ALL_SPECIES = frozendict()
SPECIES_BY_NAME = frozendict()
COLORS = {
    "Green": 0x64D364,
    "Purple": 0xC183C1,
    "White": 0xFFF,
    "Blue": 0x94DBEE,
    "Red": 0xEC8484,
    "Brown": 0xC96,
    "Gray": 0xD1D1E0,
    "Pink": 0xF4BDC9,
    "Black": 0xBBB,
    "Yellow": 0xFF9,
}
_BEASTBOOST = Ability.from_ID(item="BEASTBOOST")


@dataclass(unsafe_hash=True, slots=True)
class Species(metaclass=ABCMeta):
    id: str = ""
    name: str = ""
    shape: str = ""
    base_image: Optional[str] = None
    base_image_shiny: Optional[str] = None
    female_image: Optional[str] = None
    female_image_shiny: Optional[str] = None
    types: frozenset[Typing] = field(default_factory=frozenset)
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
        self.types = frozenset(self.types)
        self.abilities = frozenset(self.abilities)

    def __eq__(self, other: Species):
        if isinstance(other, Species):
            return str(self.id) == str(other.id)
        raise NotImplementedError(
            f"Can't compare Species with {other.__class__.__name__}"
        )

    @classmethod
    def all(cls) -> frozenset[Species]:
        items = filter(lambda x: isinstance(x, cls), ALL_SPECIES.values())
        return frozenset(items)

    @property
    def species_evolves_to(self) -> list[Species]:
        return [mon for item in self.evolves_to if (mon := self.from_ID(item))]

    @property
    def species_evolves_from(self) -> Optional[Species]:
        if mon := self.evolves_from:
            return self.from_ID(mon)

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
        items: set[cls] = set()

        if not item:
            return

        if isinstance(item, str) or not isinstance(item, Iterable):
            item = [item]

        for elem in item:
            if isinstance(elem, str):
                aux.append(elem)
            elif isinstance(elem, cls):
                items.add(elem)

        if entries := cls.all():
            MOD1 = {i.id: i for i in entries}
            MOD2 = {i.name: i for i in entries}
        else:
            MOD1 = ALL_SPECIES
            MOD2 = SPECIES_BY_NAME

        methods: list[tuple[dict[str, cls], Callable[[str], str]]] = [
            (MOD1, fix),
            (MOD2, lambda x: str(x).strip().title()),
        ]

        for word in split(r"[^A-Za-z0-9 \.'-]", ",".join(aux)):

            if not word:
                continue

            for elems, method in methods:

                word = method(word)

                if word.startswith(item := method("Galarian ")):
                    word = method(f"{word.replace(item, '')} Galar")
                elif word.startswith(item := method("Hisuian ")):
                    word = method(f"{word.replace(item, '')} Hisui")
                elif word.startswith(item := method("Kantoian ")):
                    word = word.replace(item, "")

                if data := elems.get(word):
                    items.add(data)
                else:
                    for data in get_close_matches(
                        word=word,
                        possibilities=elems,
                        n=1,
                        cutoff=0.85,
                    ):
                        items.add(elems[data])

        if len(items) == 2:
            mon1, mon2 = items
            return Fusion(mon1=mon1, mon2=mon2)

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
        elif isinstance(item, str):
            if to_search := cls.all():
                values = {i.id: i for i in to_search}
            else:
                values = ALL_SPECIES
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
        return False

    @property
    def max_amount_abilities(self) -> int:
        return 1


@dataclass(unsafe_hash=True, slots=True)
class UltraBeast(Species):
    """
    This class Represents a legendary
    """

    def __post_init__(self):
        self.evolves_to = frozenset(self.evolves_to)
        self.types = frozenset(self.types)
        self.abilities = frozenset(
            {
                _BEASTBOOST,
            }
        )

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

    HP: int = 3
    ATK: int = 3
    DEF: int = 3
    SPA: int = 3
    SPD: int = 3
    SPE: int = 3

    def __post_init__(self):
        stats = self.HP, self.ATK, self.DEF, self.SPA, self.SPD, self.SPE
        self.evolves_to = frozenset(self.evolves_to)
        self.types = frozenset(self.types)
        if sum(stats) > 18:
            raise Exception("Stats are very high, total max is 18")
        if min(stats) < 1:
            raise Exception("Minimum stat value is 1")
        if max(stats) > 5:
            raise Exception("Maximum stat value is 5")

    def set_stats(
        self,
        HP: int = 3,
        ATK: int = 3,
        DEF: int = 3,
        SPA: int = 3,
        SPD: int = 3,
        SPE: int = 3,
    ):
        stats = HP, ATK, DEF, SPA, SPD, SPE
        if sum(stats) > 18:
            raise Exception("Stats are very high, total max is 18")
        if min(stats) < 1:
            raise Exception("Minimum stat value is 1")
        if max(stats) > 5:
            raise Exception("Maximum stat value is 5")
        self.HP, self.ATK, self.DEF, self.SPA, self.SPD, self.SPE = stats

    @property
    def stats(self):
        return self.HP, self.ATK, self.DEF, self.SPA, self.SPD, self.SPE

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
        if mon := Species.deduce(item):
            if not isinstance(mon, cls):
                return cls(evolves_from=mon.id)

    @classmethod
    def from_ID(cls, item: str) -> None:
        """Method from ID but filtered, (fakemon that evolved from a canon species)

        Parameters
        ----------
        item : str
            placeholder
        """
        if mon := Species.from_ID(item):
            if not isinstance(mon, Fusion):
                return Fakemon(evolves_from=mon.id)


@dataclass(unsafe_hash=True, slots=True)
class CustomMega(Species):
    """
    This class Represents a Custom Mega
    """

    base: Species = None

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
        return False

    @classmethod
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
        if mon := Species.deduce(item):
            if not isinstance(mon, cls):
                return cls(base=mon)

    @classmethod
    def from_ID(cls, item: str) -> None:
        """Method from ID but filtered

        Parameters
        ----------
        item : str
            placeholder
        """
        if mon := Species.from_ID(item):
            if not isinstance(mon, Fusion):
                return CustomMega(base=mon)


@dataclass(unsafe_hash=True, slots=True)
class Variant(Species):
    """
    This class Represents a Variant
    """

    base: Optional[Species] = None

    def __init__(self, base: Species, name: str):
        super(Variant, self).__init__(
            id=f"{base.id}+",
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
            types=base.types,
            movepool=copy(base.movepool),
            abilities=copy(base.abilities),
        )
        self.base = base

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return (
            1
            if _BEASTBOOST in self.abilities
            else self.base.max_amount_abilities
        )

    @property
    def can_have_special_abilities(self) -> bool:
        return (
            _BEASTBOOST not in self.abilities
            and self.base.can_have_special_abilities
        )

    @classmethod
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
        if mon := Species.deduce(item):
            if not isinstance(mon, cls):
                return cls(base=mon, name=f"Variant {mon.name.title()}")

    @classmethod
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
        if (mon := Species.from_ID(item.removesuffix("+"))) and not isinstance(
            mon, Fusion
        ):
            return Variant(base=mon, name=f"Variant {mon.name.title()}")


@dataclass(unsafe_hash=True, slots=True)
class Fusion(Species):
    """
    This class Represents a fusion
    """

    mon1: Optional[Species] = None
    mon2: Optional[Species] = None

    def __init__(self, mon1: Species, mon2: Species):
        super(Fusion, self).__init__(
            id=f"{mon1.id}_{mon2.id}",
            name=f"{mon1.name}/{mon2.name}",
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
            abilities=mon1.abilities | mon2.abilities,
            evolves_from=None,
            evolves_to=frozenset(),
        )
        self.mon1 = mon1
        self.mon2 = mon2
        if len(items := self.possible_types) == 1:
            self.types = frozenset(items[0])
        item1 = self.mon1.evolves_to
        item2 = self.mon2.evolves_to
        self.evolves_to = frozenset(zip(item1, item2))
        if (item1 := mon1.evolves_from) and (item2 := mon2.evolves_from):
            self.evolves_from = item1, item2

    def __eq__(self, other: Fusion):
        if isinstance(other, Fusion):
            return self.bases == other.bases
        return super(Fusion, self).__eq__(other)

    @property
    def bases(self) -> frozenset[Species]:
        return frozenset((self.mon1, self.mon2))

    @property
    def species_evolves_to(self) -> list[Fusion]:
        return [
            Fusion(mon1=a, mon2=b)
            for a, b in zip(
                self.mon1.species_evolves_to,
                self.mon2.species_evolves_to,
            )
        ]

    @property
    def species_evolves_from(self) -> Optional[Fusion]:
        if all(
            (
                mon1 := self.mon1.species_evolves_from,
                mon2 := self.mon2.species_evolves_from,
            )
        ):
            return Fusion(mon1=mon1, mon2=mon2)

    @property
    def possible_types(self) -> list[set[Typing]]:
        """This returns a list of valid types for the pokemon

        Returns
        -------
        list[set[Types]]
            List of sets (valid types)
        """
        types1 = self.mon1.types
        types2 = self.mon2.types
        elements: list[set[Typing]] = []
        if items := frozenset(types1) | frozenset(types2):
            if len(items) <= 2:
                elements.append(items)
            elif common := types1.intersection(types2):
                uncommon = items - common
                elements.extend(
                    frozenset({x, y}) for x in common for y in uncommon
                )
            else:
                elements.extend(
                    frozenset({x, y}) for x in types1 for y in types2
                )
        return elements

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def can_have_special_abilities(self) -> bool:
        return False

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @classmethod
    def deduce(cls, item: str) -> Optional[Fusion]:
        """This is a function which allows to obtain the species given
        an ID or multiple values.

        Parameters
        ----------
        item : str
            Item to look for
        fusions_allowed : bool, optional
            If fusions should be used

        Returns
        -------
        Optional[Fusion]
            result
        """
        if isinstance(mon := Species.deduce(item), cls):
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
            item["abilities"] = [i.id for i in o.abilities]
            item["types"] = [str(i) for i in o.types]
            item["movepool"] = o.movepool.as_dict
            item["evolves_to"] = list(o.evolves_to)
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
            dct["abilities"] = Ability.deduce_many(*dct.get("abilities", []))
            dct["movepool"] = Movepool.from_dict(**dct.get("movepool", {}))
            dct["types"] = Typing.deduce_many(*dct.get("types", []))
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
    entries: list[Species] = load(f, cls=SpeciesDecoder)
    ALL_SPECIES: frozendict[str, Species] = frozendict(
        {item.id: item for item in entries}
    )
    SPECIES_BY_NAME: frozendict[str, Species] = frozendict(
        {item.name: item for item in entries}
    )
