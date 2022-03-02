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

from dataclasses import asdict, dataclass
from difflib import get_close_matches
from json import JSONDecoder, JSONEncoder, load
from random import choice
from re import split
from typing import Any, Optional

from discord import Embed
from discord.utils import utcnow
from frozendict import frozendict

from src.structures.mon_typing import Typing
from src.utils.functions import fix

__all__ = (
    "Move",
    "MoveDecoder",
    "MoveEncoder",
    "ALL_MOVES",
    "ALL_MOVES_BY_NAME",
    "MAX_MOVE_RANGE1",
    "MAX_MOVE_RANGE2",
    "Z_MOVE_RANGE",
)

ALL_MOVES = frozendict()
ALL_MOVES_BY_NAME = frozendict()

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


@dataclass(unsafe_hash=True, slots=True)
class Move:
    """Class that represents a Move"""

    index: int
    id: str
    name: str
    type: Typing
    url: str
    image: str
    contest: Optional[str] = None
    desc: Optional[str] = None
    shortDesc: Optional[str] = None
    accuracy: Optional[int] = None
    base: Optional[int] = None
    category: str = "STATUS"
    pp: Optional[int] = None
    banned: bool = False
    metronome: bool = True

    @property
    def color(self):
        return self.type.color

    @property
    def embed(self):
        title = self.name
        if self.banned:
            title += " - Banned Move"
        description = self.desc or self.shortDesc
        embed = Embed(
            url=self.url,
            title=title,
            description=description,
            color=self.type.color,
            timestamp=utcnow(),
        )
        embed.add_field(name="Power", value=f"{self.base}")
        embed.add_field(name="Accuracy", value=f"{self.accuracy}")
        embed.set_footer(text=self.category.title())
        embed.add_field(name="PP", value=f"{self.pp}")
        embed.set_thumbnail(url=self.type.emoji.url)
        embed.set_image(url=self.image)
        return embed

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        """Repr method for movepool based on Crest's design.

        Returns
        -------
        str
            Representation of a move
        """
        return f"[{self.name}] - {self.type} ({self.category})".title()

    @property
    def z_move_base(self) -> int:
        """Obtains the calculated Z-move base for the move

        Returns
        -------
        int
            Calculated Base
        """
        base = self.base or 0
        elements = filter(lambda x: x >= base, Z_MOVE_RANGE)
        index = next(elements, 250)
        return Z_MOVE_RANGE[index]

    @property
    def max_move_base(self) -> int:
        """Obtains the calculated Max-move base for the move

        Returns
        -------
        int
            Calculated Base
        """
        if str(self.type) in ["FIGHTING", "POISON"]:
            raw = MAX_MOVE_RANGE2
        else:
            raw = MAX_MOVE_RANGE1
        base = self.base or 0
        elements = filter(lambda x: x >= base, raw)
        index = next(elements, 250)
        return raw[index]

    @classmethod
    def all(cls) -> frozenset[Move]:
        return frozenset(ALL_MOVES.values())

    @classmethod
    def from_ID(cls, item: str) -> Optional[Move]:
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
        if isinstance(item, Move):
            return item
        if isinstance(item, str):
            return ALL_MOVES.get(fix(item))

    @classmethod
    def deduce(cls, item: str) -> Optional[Move]:
        """This is a method that determines the Move out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        item : str
            String to search

        Returns
        -------
        Optional[Move]
            Obtained result
        """
        if data := cls.from_ID(item):
            return data
        for elem in get_close_matches(
            item,
            possibilities=ALL_MOVES,
            n=1,
            cutoff=0.85,
        ):
            return ALL_MOVES[elem]

    @classmethod
    def deduce_many(
        cls,
        *elems: str,
        limit: Optional[int] = None,
    ) -> frozenset[Move]:
        """This is a method that determines the moves out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        elems : str
            Strings to search
        limit : int
            If there's a limit of moves to get

        Returns
        -------
        frozenset[Move]
            Obtained result
        """
        items: set[Move] = set()
        aux: list[str] = []

        for elem in elems:
            if isinstance(elem, Move):
                items.add(elem)
            elif isinstance(elem, str):
                aux.append(elem)

        for elem in split(r"[^A-Za-z0-9 \.'-]", ",".join(aux)):
            if data := ALL_MOVES.get(elem := fix(elem)):
                items.add(data)
            else:
                for data in get_close_matches(
                    word=elem,
                    possibilities=ALL_MOVES,
                    n=1,
                    cutoff=0.85,
                ):
                    items.add(ALL_MOVES[data])

        return frozenset(list(items)[:limit])

    @classmethod
    def getMetronome(cls):
        """This is a method that returns a Move given Metronome's behaviour

        Returns
        -------
        Move
            Obtained result
        """
        return choice([item for item in ALL_MOVES.values() if item.metronome])


class MoveEncoder(JSONEncoder):
    """Move encoder"""

    def default(self, o):
        if isinstance(o, Move):
            data = asdict(o)
            data["type"] = o.type.name
            return data
        return super(MoveEncoder, self).default(o)


class MoveDecoder(JSONDecoder):
    """Move decoder"""

    def __init__(self):
        super(MoveDecoder, self).__init__(
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
        if mon_type := dct.get("type"):
            dct["type"] = Typing.from_ID(mon_type)
            return Move(**dct)
        return dct


with open("resources/moves.json") as f:
    items: list[Move] = load(f, cls=MoveDecoder)
    ALL_MOVES = frozendict({item.id: item for item in items})
    ALL_MOVES_BY_NAME = frozendict({item.name: item for item in items})
