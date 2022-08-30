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
from enum import Enum
from functools import lru_cache
from json import JSONDecoder, JSONEncoder, load
from random import choice
from re import split
from typing import Any, Callable, Optional

from discord import Embed, PartialEmoji
from discord.utils import find, get, utcnow
from frozendict import frozendict
from rapidfuzz import process

from src.structures.mon_typing import TypingEnum
from src.utils.functions import fix

__all__ = (
    "Move",
    "MoveDecoder",
    "MoveEncoder",
    "ALL_MOVES",
    "ALL_MOVES_BY_NAME",
)

ALL_MOVES = frozendict()
ALL_MOVES_BY_NAME = frozendict()


class Category(Enum):
    STATUS = PartialEmoji(name="Status", id=1001887872221200506)
    PHYSICAL = PartialEmoji(name="Physical", id=1001887867796205598)
    SPECIAL = PartialEmoji(name="Special", id=1001887870266658916)

    @property
    def title(self) -> str:
        return self.name.title()

    @property
    def emoji(self) -> PartialEmoji:
        return self.value


@dataclass(unsafe_hash=True, slots=True)
class Move:
    """Class that represents a Move"""

    index: int
    id: str
    name: str
    type: TypingEnum
    url: str
    image: str
    contest: Optional[str] = None
    desc: Optional[str] = None
    shortDesc: Optional[str] = None
    accuracy: Optional[int] = None
    base: Optional[int] = None
    category: Category = Category.STATUS
    pp: Optional[int] = None
    banned: bool = False
    metronome: bool = True

    @property
    def color(self):
        return self.type.color

    @property
    def emoji(self):
        return self.type.emoji

    @property
    def embed(self):
        title = self.name
        if self.banned:
            title += " - Banned Move"
        description = self.desc or self.shortDesc
        embed = Embed(url=self.url, title=title, description=description, color=self.type.color, timestamp=utcnow())
        embed.add_field(name="Power", value=f"{self.base}")
        embed.add_field(name="Accuracy", value=f"{self.accuracy}")
        cat = self.category
        embed.set_footer(text=cat.title, icon_url=cat.emoji.url)
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
        return f"[{self.name}] - {self.type} ({self.category.name})".title()

    def calculated_base(self, raw: dict[int, int]) -> int:
        """Obtains the calculated base for the move

        Returns
        -------
        int
            Calculated Base
        """
        base = self.base or 0
        elements = filter(lambda x: x >= base, raw)
        index = next(elements, 250)
        return raw[index]

    @property
    def z_move_base(self) -> int:
        return self.calculated_base(self.type.z_move_range)

    @property
    def max_move_base(self) -> int:
        return self.calculated_base(self.type.max_move_range)

    @classmethod
    def all(cls) -> frozenset[Move]:
        return frozenset(ALL_MOVES.values())

    @classmethod
    def find(cls, predicate: Callable[[Move], Any]):
        return find(predicate, cls.all())

    @classmethod
    def get(cls, **kwargs):
        return get(cls.all(), **kwargs)

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
        if isinstance(item, cls):
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
        if value := process.extractOne(
            item,
            ALL_MOVES,
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=85,
        ):
            return value[0]

    @classmethod
    @lru_cache(maxsize=None)
    def deduce_many(cls, *elems: str | Move) -> frozenset[Move]:
        """This is a method that determines the moves out of
        the existing entries, it has a 85% of precision.
        Parameters
        ----------
        elems : str
            Strings to search
        Returns
        -------
        frozenset[Move]
            Obtained result
        """
        items = {elem for elem in elems if isinstance(elem, Move)}

        if aux := ",".join(elem for elem in elems if isinstance(elem, str)):
            data = split(r"[^A-Za-z0-9 \.'-]", aux)
            items.update(x for elem in data if (x := cls.deduce(elem)))

        return frozenset(items)

    @classmethod
    def getMetronome(cls) -> Move:
        """This is a method that returns a Move given Metronome's behaviour

        Returns
        -------
        Move
            Obtained result
        """
        return choice([item for item in cls.all() if item.metronome])


class MoveEncoder(JSONEncoder):
    """Move encoder"""

    def default(self, o):
        if isinstance(o, Move):
            data = asdict(o)
            data["type"] = o.type.name
            data["category"] = o.category.name
            return data
        return super(MoveEncoder, self).default(o)


class MoveDecoder(JSONDecoder):
    """Move decoder"""

    def __init__(self):
        super(MoveDecoder, self).__init__(object_hook=self.object_hook)

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
            try:
                dct["category"] = Category[dct["category"]]
            except KeyError:
                dct["category"] = Category.STATUS
            dct["type"] = TypingEnum.deduce(mon_type)
            return Move(**dct)
        return dct


with open("resources/moves.json", mode="r", encoding="utf8") as f:
    DATA: list[Move] = load(f, cls=MoveDecoder)
    ALL_MOVES = frozendict({item.id: item for item in DATA})
    ALL_MOVES_BY_NAME = frozendict({item.name: item for item in DATA})
