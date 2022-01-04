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

from dataclasses import dataclass, field
from typing import Union

from discord import PartialEmoji
from frozendict import frozendict

__all__ = ("Typing", "Z_MOVE_RANGE", "MAX_MOVE_RANGE1", "MAX_MOVE_RANGE2")

Z_MOVE_RANGE = frozendict(
    {
        0: 0,
        55: 100,
        65: 120,
        75: 140,
        85: 160,
        95: 175,
        100: 190,
        110: 195,
        125: 190,
        130: 195,
        140: 200,
        250: 200,
    }
)
MAX_MOVE_RANGE1 = frozendict(
    {
        0: 0,
        40: 90,
        50: 100,
        60: 110,
        70: 120,
        100: 130,
        140: 140,
        250: 150,
    }
)
MAX_MOVE_RANGE2 = frozendict(
    {
        0: 0,
        40: 70,
        50: 75,
        60: 80,
        70: 85,
        100: 90,
        140: 95,
        250: 100,
    }
)


@dataclass(unsafe_hash=True, slots=True)
class Typing:
    """This is the basic information a type has.

    Attributes
    -----------
    name: str
        Typing's name
    icon: str
        Image of the typing.
    id: int
        Type's ID, Defaults to 0
    color: int
        Type's Color, Defaults to 0
    z_move: str
        Type's Z-Move name
    max_move: str
        Type's Max-Move name
    chart: frozendict[int, float]
        dict with the type charts' values that involve the typing
        format is {ID: multiplier} e.g.: {7: 2.0}
    banner : str
        Typing's banner
    """

    name: str = field(default_factory=str)
    icon: str = field(default_factory=str)
    id: int = 0
    color: int = 0
    emoji: PartialEmoji = PartialEmoji(name="\N{MEDIUM BLACK CIRCLE}")
    z_move: str = field(default_factory=str)
    max_move: str = field(default_factory=str)
    chart: frozendict[int, float] = field(default_factory=frozendict)
    banner: str = field(default_factory=str)
    icon: str = field(default_factory=str)

    def __add__(self, other: Typing) -> Typing:
        """Add Method

        Parameters
        ----------
        other : Typing
            A type to be added

        Returns
        -------
        Typing
            Type with resulting chart
        """
        if (a := self.chart) != (b := other.chart):
            return Typing(
                name=f"{self.name}/{other.name}",
                color=((self.color + other.color) ** 2) / 2,
                chart=frozendict(
                    {
                        x: multi
                        for x in a | b
                        if (multi := a.get(x, 1) * b.get(x, 1)) != 1
                    }
                ),
            )
        return self

    def __str__(self) -> str:
        """str method

        Returns
        -------
        str
            Upper name
        """
        return self.name.upper()

    def __contains__(self, other: Typing) -> bool:
        """contains method

        Parameters
        ----------
        other : Typing
            Type to check

        Returns
        -------
        bool
            If included in the chart
        """
        return other.id in self.chart

    def __int__(self) -> int:
        """int method

        Returns
        -------
        int
            Type's ID
        """
        return self.id

    def __setitem__(
        self,
        type_id: Typing,
        value: Union[int, float],
    ) -> None:
        """Setitem method for assigning chart values

        Parameters
        ----------
        type_id : Typing
            Type to compare
        value : int
            reference value
        """
        chart = dict(self.chart)
        chart[int(type_id)] = value
        self.chart = frozendict(chart)

    def __getitem__(self, other: Typing) -> float:
        """getitem method for obtaining chart value

        Parameters
        ----------
        other : Typing
            Type to compare

        Returns
        -------
        float
            chart value
        """
        return self.chart.get(int(other), 1.0)
