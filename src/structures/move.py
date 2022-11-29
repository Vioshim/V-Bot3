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

from enum import Enum
from functools import lru_cache
from json import load
from re import split
from typing import Any, Callable, Optional

from discord import Embed, PartialEmoji
from discord.utils import find, get, utcnow
from frozendict import frozendict
from rapidfuzz import process

from src.structures.mon_typing import TypingEnum
from src.utils.etc import WHITE_BAR
from src.utils.functions import fix

__all__ = (
    "Move",
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

    @classmethod
    def from_id(self, value: int):
        match value:
            case 1:
                return self.PHYSICAL
            case 2:
                return self.SPECIAL
            case _:
                return self.STATUS


CHECK_FLAGS: dict[str, Callable[[Any], Optional[str]]] = {
    "Power": lambda x: f"Has {x} Power" if x else None,
    "Accuracy": lambda x: ("Bypasses" if x == 101 else f"{x}%") + " Accuracy",
    "PP": lambda x: f"Has {x} PP" if x > 1 else None,
    "Priority": lambda x: f"Priority: {x}" if x != 0 else None,
    "HitMin": lambda x: f"Min Hits: {x}" if x != 0 else None,
    "HitMax": lambda x: f"Max Hits: {x}" if x != 0 else None,
    "Inflict": lambda x: f"Inflict: {x}" if x != "0|0|0|0|0" else None,
    "CritStage": lambda x: f"Crit. Stages: {x}" if x != 0 else None,
    "Flinch": lambda x: f"Flinch Chance: {x}%" if x != 0 else None,
    "Recoil": lambda x: f"Recoil: {x}%" if x != 0 else None,
    "RawHealing": lambda x: (f"Raw Healing: {x}%" if x > 0 else f"Drains {x}% from User's HP")
    if x != 0
    else None,  # Check
    "RawTarget": lambda x: f"Raw Target: {x}" if x != 0 else None,  # Investigate
    "StatAmps": lambda x: f"Stat Amps: {x}" if x != "0|0|0|0|0|0|0|0|0" else None,
    "Affinity": lambda x: f"Affinity: {x}" if x != "None" else None,
    "Flag_MakesContact": lambda x: "It makes Contact" if x else None,
    "Flag_Charge": lambda x: "Move charges" if x else None,
    "Flag_Recharge": lambda x: "Move recharges" if x else None,
    "Flag_Protect": lambda x: "Affected by Protect" if x else None,
    "Flag_Reflectable": lambda x: "Affected by Reflect" if x else None,
    "Flag_Snatch": lambda x: "Affected by Snatch" if x else None,
    "Flag_Mirror": lambda x: "Affected by Mirror Move" if x else None,
    "Flag_Punch": lambda x: "1.2x w/Iron Fist" if x else None,
    "Flag_Sound": lambda x: "Sound-based Move" if x else None,
    "Flag_Dance": lambda x: "Dance-based Move" if x else None,
    "Flag_Gravity": lambda x: "Affected by Gravity" if x else None,
    "Flag_Defrost": lambda x: "Thaws out frozen targets" if x else None,
    "Flag_DistanceTriple": lambda x: "Triple Distance" if x else None,
    "Flag_Heal": lambda x: "Heals after hit" if x else None,
    "Flag_IgnoreSubstitute": lambda x: "Ignores Substitute" if x else None,
    "Flag_FailSkyBattle": lambda x: "Fails in Sky Battles" if x else None,
    "Flag_AnimateAlly": lambda x: "Can target ally" if x else None,
    "Flag_Metronome": lambda x: "Can't be used by metronome" if not x else None,
    "Flag_FailEncore": lambda x: "Encore fails against it" if x else None,
    "Flag_FailMeFirst": lambda x: "Me first fails against it" if x else None,
    "Flag_FutureAttack": lambda x: "Hits some time after" if x else None,
    "Flag_Pressure": lambda x: "Wild pokemon may ask for help" if x else None,
    "Flag_Combo": lambda x: "Move can be combined" if x else None,
    "Flag_NoSleepTalk": lambda x: "Can't be used by sleep talk" if x else None,
    "Flag_NoAssist": lambda x: "Can't be used by assist" if x else None,
    "Flag_FailCopycat": lambda x: "Can't be used by copycat" if x else None,
    "Flag_FailMimic": lambda x: "Can't be used by mimic" if x else None,
    "Flag_FailInstruct": lambda x: "Can't be used by instruct" if x else None,
    "Flag_Powder": lambda x: "Grass types are immune to its powder" if x else None,
    "Flag_Bite": lambda x: "1.5x w/Strong Jaw" if x else None,
    "Flag_Bullet": lambda x: "Affected by bulletproof" if x else None,
    "Flag_NoMultiHit": lambda x: "Stronger consecutive hits" if x else None,
    "Flag_NoEffectiveness": lambda x: "Ignores type chart" if x else None,
    "Flag_SheerForce": lambda x: "1.3x w/Sheer Force" if x else None,
    "Flag_Slicing": lambda x: "1.5x w/Sharpness" if x else None,
    "Flag_Wind": lambda x: "Wind-based. Activates Wind Power/Rider" if x else None,
    "Flag_CantUseTwice": lambda x: "Can't be used twice" if x else None,
}


class Move:
    """Class that represents a Move"""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = frozendict(data)

    @property
    def data(self):
        return self._data

    @property
    def move_id(self) -> int:
        return self.data["MoveID"]

    def __hash__(self) -> int:
        return self.move_id

    def __int__(self):
        return self.move_id

    @property
    def id(self) -> int:
        return self.data.get("id", 0)

    @property
    def metronome(self) -> bool:
        return self.data.get("Flag_Metronome", False)

    @property
    def name(self) -> str:
        return self.data["Name"]

    @property
    def category(self):
        return Category.from_id(self.data["Category"])

    @property
    def type(self) -> TypingEnum:
        return TypingEnum.get(game_id=self.data["Type"])

    @property
    def color(self):
        return self.type.color

    @property
    def emoji(self):
        return self.type.emoji

    @property
    def banned(self) -> bool:
        move_id: int = self.move_id
        aux = move_id in [165, 449]  # Struggle, Judgement
        aux |= 622 <= move_id <= 658  # Z-Moves
        aux |= 757 <= move_id <= 774  # Max-Moves
        aux |= 695 <= move_id <= 703 or move_id == 719 or 723 <= move_id <= 728  # Unique Z-Moves
        aux |= move_id == 0  # No ID
        return aux

    @property
    def description(self):
        return "\n".join(f"• {o}." for k, v in CHECK_FLAGS.items() if k in self.data and (o := v(self.data[k])))

    @property
    def embed(self):
        title = self.name
        if self.banned:
            title += " - Banned Move"
        embed = Embed(
            title=title,
            description=self.description[:4096],
            color=self.type.color,
            timestamp=utcnow(),
        )
        cat = self.category
        embed.set_footer(text=cat.title, icon_url=cat.emoji.url)
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

    def calculated_base(self, raw: dict[int, int]) -> int:
        """Obtains the calculated base for the move

        Returns
        -------
        int
            Calculated Base
        """
        base = self.data.get("Power", 0)
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
    @lru_cache(maxsize=None)
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


with open("resources/moves.json", mode="r", encoding="utf8") as f:
    DATA: list[Move] = [Move(x) for x in load(f) if x]

with open("resources/shadow_moves.json", mode="r", encoding="utf8") as f:
    DATA += [Move(x) for x in load(f) if x]

ALL_MOVES = frozendict({item.id: item for item in DATA})
ALL_MOVES_BY_NAME = frozendict({item.name: item for item in DATA})
