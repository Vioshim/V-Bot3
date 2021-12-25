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

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from copy import copy
from dataclasses import dataclass, field
from typing import Optional

from src.enums.abilities import Abilities
from src.enums.mon_types import Types
from src.structures.movepool import Movepool

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
)


@dataclass(unsafe_hash=True)
class Species(metaclass=ABCMeta):
    id: str = ""
    name: str = ""
    shape: str = ""
    color: str = ""
    base_image: Optional[str] = None
    base_image_shiny: Optional[str] = None
    female_image: Optional[str] = None
    female_image_shiny: Optional[str] = None
    types: frozenset[Types] = field(default_factory=frozenset)
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
    abilities: frozenset[Abilities] = field(default_factory=frozenset)

    def __post_init__(self):
        self.evolves_to = frozenset(self.evolves_to)
        self.types = frozenset(self.types)
        self.abilities = frozenset(self.abilities)

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


@dataclass(unsafe_hash=True)
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


@dataclass(unsafe_hash=True)
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


@dataclass(unsafe_hash=True)
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


@dataclass(unsafe_hash=True)
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


@dataclass(unsafe_hash=True)
class UltraBeast(Species):
    """
    This class Represents a legendary
    """

    def __post_init__(self):
        self.abilities = frozenset(
            {
                Abilities.BEASTBOOST,
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


@dataclass(unsafe_hash=True)
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
        if sum(stats) > 18:
            raise Exception("Stats are very high, total max is 18")
        if min(stats) < 1:
            raise Exception("Minimum stat value is 1")
        if max(stats) > 5:
            raise Exception("Maximum stat value is 5")

    # noinspection PyPep8Naming
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
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1 if Abilities.BEASTBOOST in self.abilities else 2

    @property
    def can_have_special_abilities(self) -> bool:
        return Abilities.BEASTBOOST not in self.abilities


@dataclass(unsafe_hash=True)
class CustomMega(Species):
    """
    This class Represents a Custom Mega
    """

    def __init__(self, base: Species):
        self.id: str = f"C_MEGA_{base.id}"
        self.name: str = f"Mega {base.name}"
        self.shape: str = base.shape
        self.color: str = base.color
        self.height: int = base.height
        self.weight: int = base.weight
        self.HP: int = base.HP
        self.ATK: int = base.ATK
        self.DEF: int = base.DEF
        self.SPA: int = base.SPA
        self.SPD: int = base.SPD
        self.SPE: int = base.SPE
        self.movepool: Movepool = base.movepool
        self.abilities: frozenset[Abilities] = copy(base.abilities)

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @property
    def can_have_special_abilities(self) -> bool:
        return False


@dataclass(unsafe_hash=True)
class Variant(Species):
    """
    This class Represents a Variant
    """

    def __init__(self, base: Species):
        self.base = base
        self.id = f"VARIANT_{base.id}"
        self.name = f"Variant {base.name}"
        self.shape: str = base.shape
        self.color: str = base.color
        self.height: int = base.height
        self.weight: int = base.weight
        self.HP: int = base.HP
        self.ATK: int = base.ATK
        self.DEF: int = base.DEF
        self.SPA: int = base.SPA
        self.SPD: int = base.SPD
        self.SPE: int = base.SPE
        self.movepool: Movepool = copy(base.movepool)
        self.abilities: frozenset[Abilities] = copy(base.abilities)

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return (
            1
            if Abilities.BEASTBOOST in self.abilities
            else self.base.max_amount_abilities
        )

    @property
    def can_have_special_abilities(self) -> bool:
        return (
            Abilities.BEASTBOOST not in self.abilities
            and self.base.can_have_special_abilities
        )


@dataclass(unsafe_hash=True)
class Fusion(Species):
    """
    This class Represents a fusion
    """

    mon1: Optional[Species] = None
    mon2: Optional[Species] = None
    evolves_from: Optional[tuple[str, str]] = None
    evolves_to: frozenset[tuple[str, str]] = field(default_factory=frozenset)

    def __init__(self, mon1: Species, mon2: Species):
        super(Fusion, self).__init__()
        self.id = f"{mon1.id}_{mon2.id}"
        self.mon1 = mon1
        self.mon2 = mon2
        self.name = f"{mon1.name}/{mon2.name}"
        self.height = round((mon1.height + mon2.height) / 2)
        self.weight = round((mon1.weight + mon2.weight) / 2)
        if len(items := self.possible_types) == 1:
            self.types = frozenset(items[0])
        self.HP = round((mon1.HP + mon2.HP) / 2)
        self.ATK = round((mon1.ATK + mon2.ATK) / 2)
        self.DEF = round((mon1.DEF + mon2.DEF) / 2)
        self.SPA = round((mon1.SPA + mon2.SPA) / 2)
        self.SPD = round((mon1.SPD + mon2.SPD) / 2)
        self.SPE = round((mon1.SPE + mon2.SPE) / 2)
        self.movepool = mon1.movepool + mon2.movepool
        self.abilities = mon1.abilities | mon2.abilities
        if (item1 := mon1.evolves_from) and (item2 := mon2.evolves_from):
            if isinstance(item1, str):
                item1 = Species[item1]
            if isinstance(item2, str):
                item2 = Species[item2]
            self.evolves_from = Fusion(item1, item2)
        if (item1 := mon1.evolves_to) and (item2 := mon2.evolves_to):
            data = set()
            for item1, item2 in zip(item1, item2):
                if isinstance(item1, str):
                    item1 = Species[item1]
                if isinstance(item2, str):
                    item2 = Species[item2]
                data.add(Fusion(item1, item2))
            self.evolves_to = frozenset(data)

    def __post_init__(self):
        self.types = frozenset(self.types)
        self.abilities = frozenset(self.abilities)

    @property
    def possible_types(self) -> list[set[Types]]:
        """This returns a list of valid types for the pokemon

        Returns
        -------
        list[set[Types]]
            List of sets (valid types)
        """
        types1 = self.mon1.types
        types2 = self.mon2.types
        elements: list[set[Types]] = []
        if items := set(types1) | set(types2):
            if len(items) <= 2:
                elements.append(items)
            elif common := types1.intersection(types2):
                uncommon = items - common
                elements.extend({x, y} for x in common for y in uncommon)
            else:
                elements.extend({x, y} for x in types1 for y in types2)
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
