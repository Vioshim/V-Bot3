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
from difflib import get_close_matches
from json import JSONDecoder, JSONEncoder, load
from re import split
from typing import Any, Callable, Optional

from discord import PartialEmoji
from discord.utils import find, get
from frozendict import frozendict

from src.utils.functions import fix

__all__ = ("Typing", "Z_MOVE_RANGE", "MAX_MOVE_RANGE1", "MAX_MOVE_RANGE2")

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
    ids: frozenset[int]
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
    ids: frozenset[int] = field(default_factory=frozenset)
    color: int = 0
    emoji: PartialEmoji = PartialEmoji(name="\N{MEDIUM BLACK CIRCLE}")
    z_move: str = ""
    max_move: str = ""
    chart: frozendict[int, float] = field(default_factory=frozendict)
    banner: str = ""

    def __post_init__(self):
        if isinstance(self.ids, (int, float)):
            self.ids = frozenset({self.ids})
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
                ids=self.ids | other.ids,
                name=f"{self.name}/{other.name}",
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
        return any(x in self.chart for x in self.ids)

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
        for item in type_id.ids:
            chart[item] = value
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
        value = 1.0
        for item in other.ids:
            value *= self.chart.get(item, 1.0)
        return value

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
                for item in other.ids:
                    base *= self.chart.get(item, 1.0)
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
                for item in self.ids:
                    base *= other.chart.get(item, 1.0)
        return base

    @property
    def terrain(self):
        return {"FAIRY": "Misty Terrain", "GRASS": "Grassy Terrain"}.get(item := str(self), f"{item} Terrain".title())

    @classmethod
    def all(cls) -> frozenset[Typing]:
        return frozenset(ALL_TYPES.values())

    @classmethod
    def find(cls, predicate: Callable[[Typing], Any]):
        return find(predicate, cls.all())

    @classmethod
    def get(cls, **kwargs: Any):
        return get(cls.all(), **kwargs)

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
        for elem in get_close_matches(item, possibilities=ALL_TYPES, n=1, cutoff=0.85):
            return ALL_TYPES[elem]

    @classmethod
    def deduce_many(cls, *elems: str, range_check: bool = False) -> frozenset[Typing]:
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

        for elem in split(r"[^A-Za-z0-9 \.'-]", ",".join(aux)):

            if not elem:
                continue

            if data := ALL_TYPES.get(elem := fix(elem)):
                items.append(data)
            else:
                for data in get_close_matches(word=elem, possibilities=ALL_TYPES, n=1, cutoff=0.85):
                    items.append(ALL_TYPES[data])

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
        super(TypingDecoder, self).__init__(object_hook=self.object_hook)

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
        items = set(Typing.__slots__)
        items -= {"id"}
        if all(x in dct for x in items):
            if emoji := dct.get("emoji", ""):
                dct["emoji"] = PartialEmoji.from_str(emoji)
            if chart := dct.get("chart", {}):
                dct["chart"] = frozendict({int(k): float(v) for k, v in chart.items()})
            if type_id := dct.pop("id", 0):
                dct["ids"] = frozenset({type_id})
            return Typing(**dct)
        return dct


with open("resources/types.json") as f:
    DATA: list[Typing] = load(f, cls=TypingDecoder)
    ALL_TYPES = frozendict({str(item): item for item in DATA})
