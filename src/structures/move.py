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

from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Optional

from discord import Embed
from discord.utils import utcnow

from src.enums.mon_types import Types
from src.utils.etc import WHITE_BAR

__all__ = (
    "Category",
    "Move",
)


class Category(IntEnum):
    """Class that represents a Move's category"""

    STATUS = auto()
    PHYSICAL = auto()
    SPECIAL = auto()


# noinspection PyArgumentList
@dataclass(unsafe_hash=True, slots=True)
class Move:
    """Class that represents a Move"""

    name: str
    type: Types = Types.NORMAL
    desc: Optional[str] = None
    shortDesc: Optional[str] = None
    accuracy: Optional[int] = None
    base: Optional[int] = None
    category: Category = Category.STATUS
    pp: Optional[int] = None
    banned: bool = False
    metronome: bool = True

    @property
    def embed(self):
        description = self.desc or self.shortDesc
        embed = Embed(
            title=self.name,
            description=description,
            color=self.type.color,
            timestamp=utcnow(),
        )
        embed.add_field(name="Power", value=f"{self.base}")
        embed.add_field(name="Accuracy", value=f"{self.accuracy}")
        embed.set_footer(text=self.category.name.title())
        embed.add_field(name="PP", value=f"{self.pp}")
        embed.set_thumbnail(url=self.type.emoji.url)
        embed.set_image(url=WHITE_BAR)
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
