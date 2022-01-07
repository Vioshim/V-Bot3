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
        return 1 if Abilities.BEASTBOOST in self.abilities else 2

    @property
    def can_have_special_abilities(self) -> bool:
        return Abilities.BEASTBOOST not in self.abilities


@dataclass(unsafe_hash=True, slots=True)
class CustomMega(Species):
    """
    This class Represents a Custom Mega
    """

    def __init__(self, base: Species):
        super(CustomMega, self).__init__(
            id=base.id,
            name=f"Mega {base.name}",
            shape=base.shape,
            color=base.color,
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

    @property
    def requires_image(self) -> bool:
        return True

    @property
    def max_amount_abilities(self) -> int:
        return 1

    @property
    def can_have_special_abilities(self) -> bool:
        return False


@dataclass(unsafe_hash=True, slots=True)
class Variant(Species):
    """
    This class Represents a Variant
    """

    base: Species = None

    def __init__(self, base: Species, name: str):
        super(Variant, self).__init__(
            id=base.id,
            name=name.title(),
            shape=base.shape,
            color=base.color,
            height=base.height,
            weight=base.weight,
            HP=base.HP,
            ATK=base.ATK,
            DEF=base.DEF,
            SPA=base.SPA,
            SPD=base.SPD,
            SPE=base.SPE,
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
            if Abilities.BEASTBOOST in self.abilities
            else self.base.max_amount_abilities
        )

    @property
    def can_have_special_abilities(self) -> bool:
        return (
            Abilities.BEASTBOOST not in self.abilities
            and self.base.can_have_special_abilities
        )


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

    @property
    def fusion_evolves_to(self):
        return frozenset(Fusion(a, b) for a, b in self.evolves_to)

    @property
    def fusion_evolves_from(self) -> Optional[Fusion]:
        if item := self.evolves_from:
            return Fusion(*item)

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
