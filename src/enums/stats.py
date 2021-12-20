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

from dataclasses import asdict, dataclass
from enum import Enum


@dataclass(unsafe_hash=True)
class StatItem:
    HP: int = 3
    ATK: int = 3
    DEF: int = 3
    SPA: int = 3
    SPE: int = 3
    SPD: int = 3

    def __repr__(self) -> str:
        """repr method

        Returns
        -------
        str
            UI friendly representation
        """
        return " ".join(f"{k}:{v}" for k, v in asdict(self).items())


class Stats(StatItem, Enum):
    """
    Class which represents the most common fakemon stats
    """

    PHYSICAL_ATTACKER = (2, 4, 5, 1, 2, 4)
    PHYSICAL_BALANCED = (3, 5, 5, 1, 1, 3)
    PHYSICAL_DEFENDER = (4, 5, 4, 2, 1, 2)
    OVERALL_ATTACKER = (1, 1, 5, 5, 1, 5)
    OVERALL_BALANCED = (3, 3, 3, 3, 3, 3)
    OVERALL_DEFENDER = (5, 5, 1, 1, 5, 1)
    SPECIAL_ATTACKER = (2, 2, 1, 5, 4, 4)
    SPECIAL_BALANCED = (3, 1, 1, 5, 5, 3)
    SPECIAL_DEFENDER = (4, 1, 2, 4, 5, 2)

    def __str__(self) -> str:
        """str method

        Returns
        -------
        str
            Name
        """
        return self.name.replace("_", " ").title()

    @property
    def emoji(self) -> str:
        """Emoji which represents the set

        Returns
        -------
        str
            Emoji
        """
        _, name = self.name.split("_")
        if name == "ATTACKER":
            return "\N{CROSSED SWORDS}"
        if name == "DEFENDER":
            return "\N{SHIELD}"
        return "\N{SCALES}"
