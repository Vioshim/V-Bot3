#  Copyright 2021 Vioshim
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from random import choice
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
)


@dataclass(unsafe_hash=True, slots=True)
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
    movepool: Movepool = field(default_factory=Movepool)
    abilities: frozenset[Abilities] = field(default_factory=frozenset)

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
        return 2


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
        return 2


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
        return 2


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
        return 2


@dataclass(unsafe_hash=True, slots=True)
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
        if sum(stats) > 18:
            raise Exception("Stats are very high, total max is 18")
        if min(stats) < 1:
            raise Exception("Minimum stat value is 1")
        if max(stats) > 5:
            raise Exception("Maximum stat value is 5")

    # noinspection PyPep8Naming
    def set_stats(
            self, HP: int = 3, ATK: int = 3, DEF: int = 3, SPA: int = 3, SPD: int = 3, SPE: int = 3
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


@dataclass(unsafe_hash=True, slots=True)
class Fusion(Species):
    """
    This class Represents a fusion
    """

    mon1: Optional[Species] = None
    mon2: Optional[Species] = None

    def __init__(self, mon1: Species, mon2: Species):
        super(Fusion, self).__init__()
        self.id = f"{mon1.id}_{mon2.id}"
        self.mon1 = mon1
        self.mon2 = mon2
        self.name = f"{mon1.name}/{mon2.name}"
        self.height = round((mon1.height + mon2.height) / 2)
        self.weight = round((mon1.weight + mon2.weight) / 2)
        if items := self.possible_types:
            if len(items) == 1:
                self.types = frozenset(items[0])
            elif not self.types:
                self.types = frozenset(choice(items))
            elif self.types not in items:
                raise Exception("Invalid typing")
        self.HP = round((mon1.HP + mon2.HP) / 2)
        self.ATK = round((mon1.ATK + mon2.ATK) / 2)
        self.DEF = round((mon1.DEF + mon2.DEF) / 2)
        self.SPA = round((mon1.SPA + mon2.SPA) / 2)
        self.SPD = round((mon1.SPD + mon2.SPD) / 2)
        self.SPE = round((mon1.SPE + mon2.SPE) / 2)
        self.movepool = mon1.movepool + mon2.movepool
        self.abilities = mon1.abilities | mon2.abilities

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
