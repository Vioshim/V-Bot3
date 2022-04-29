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

from dataclasses import asdict, dataclass, field
from json import JSONDecoder, JSONEncoder, load
from re import split
from typing import Any, Optional

from discord import PartialEmoji
from frozendict import frozendict
from rapidfuzz import process

from src.utils.functions import fix

__all__ = (
    "Typing",
    "Z_MOVE_RANGE",
    "MAX_MOVE_RANGE1",
    "MAX_MOVE_RANGE2",
)

ALL_TYPES = frozendict()

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

    name: str = ""
    icon: str = ""
    id: Optional[int] = None
    color: int = 0
    emoji: PartialEmoji = PartialEmoji(name="\N{MEDIUM BLACK CIRCLE}")
    z_move: str = ""
    max_move: str = ""
    chart: frozendict[int, float] = field(default_factory=frozendict)
    banner: str = ""

    def __post_init__(self):
        self.chart = frozendict({k: v for k, v in self.chart.items() if v != 1})

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
            chart = {x: a.get(x, 1) * b.get(x, 1) for x in a | b}
            return Typing(
                name=f"{self.name}/{other.name}",
                color=((self.color + other.color) ** 2) / 2,
                chart=frozendict(chart),
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

    def __repr__(self) -> str:
        return f"Typing.{self}"

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
        value: int | float,
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

    def when_attacked_by(self, *others: Typing) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        base = 1.0
        for other in others:
            if isinstance(other, str):
                other = self.from_ID(other)
            if isinstance(other, Typing):
                base *= self.chart.get(other.id, 1.0)
        return base

    def when_attacking(self, *others: Typing | str) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        base = 1.0
        for other in others:
            if isinstance(other, str):
                other = self.from_ID(other)
            if isinstance(other, Typing):
                base *= other.chart.get(self.id, 1.0)
        return base

    @property
    def terrain(self):
        return {
            "FAIRY": "Misty Terrain",
            "GRASS": "Grassy Terrain",
        }.get(item := str(self), f"{item} Terrain".title())

    @classmethod
    def all(cls) -> frozenset[Typing]:
        return frozenset(ALL_TYPES.values())

    @classmethod
    def deduce(cls, item: str) -> Optional[Typing]:
        """This is a method that determines the Typing out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        item : str
            String to search

        Returns
        -------
        Optional[Typing]
            Obtained result
        """
        if isinstance(item, cls):
            return item
        if data := ALL_TYPES.get(fix(item)):
            return data
        if data := process.extractOne(item, choices=cls.all(), processor=str, score_cutoff=60):
            return data[0]

    @classmethod
    def deduce_many(
        cls,
        *elems: str,
        range_check: bool = False,
    ) -> frozenset[Typing]:
        """This is a method that determines the moves out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        elems : str
            Strings to search
        range_check : bool, optional
            If it should limit to a max of 2 types.

        Returns
        -------
        frozenset[ALL_TYPES]
            Obtained result
        """
        items: list[Typing] = []
        aux: list[str] = []

        for elem in elems:
            if isinstance(elem, cls):
                items.append(elem)
            elif isinstance(elem, str):
                aux.append(elem)

        for elem in filter(bool, split(r"[^A-Za-z0-9 \.'-]", ",".join(aux))):

            if data := ALL_TYPES.get(elem):
                items.append(data)
            elif data := process.extractOne(elem, choices=cls.all(), processor=str, score_cutoff=60):
                items.append(data[0])

        if range_check and len(items) > 2:
            items = []

        return frozenset(items)

    @classmethod
    def from_ID(cls, item: str) -> Optional[Typing]:
        """This is a method that returns a Move given an exact ID.

        Parameters
        ----------
        item : str
            Move ID to check

        Returns
        -------
        Optional[Move]
            Obtained result
        """
        if isinstance(item, cls):
            return item
        if isinstance(item, str):
            return ALL_TYPES.get(fix(item))


class TypingEncoder(JSONEncoder):
    """Typing encoder"""

    def default(self, o):
        if isinstance(o, Typing):
            data = asdict(o)
            data["emoji"] = str(o.emoji)
            return data
        return super(TypingEncoder, self).default(o)


class TypingDecoder(JSONDecoder):
    """Typing decoder"""

    def __init__(self):
        super(TypingDecoder, self).__init__(
            object_hook=self.object_hook,
        )

    def object_hook(self, dct: dict[str, Any]):
        """Decoder method for dicts

        Parameters
        ----------
        dct : dict[str, Any]
            Input

        Returns
        -------
        Any
            Result
        """
        if all(x in dct for x in Typing.__slots__):
            if emoji := dct.get("emoji", ""):
                dct["emoji"] = PartialEmoji.from_str(emoji)
            if chart := dct.get("chart", {}):
                dct["chart"] = frozendict({int(k): float(v) for k, v in chart.items()})
            return Typing(**dct)
        return dct


with open("resources/types.json") as f:
    items: list[Typing] = load(f, cls=TypingDecoder)
    ALL_TYPES = frozendict({str(item): item for item in items})
