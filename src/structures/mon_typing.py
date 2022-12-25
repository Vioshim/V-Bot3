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

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from re import split
from typing import Any, Callable, Optional

from discord import PartialEmoji
from discord.utils import find, get
from frozendict import frozendict
from rapidfuzz import process

from src.utils.functions import fix

__all__ = ("TypingEnum",)

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
    """

    name: str = ""
    icon: str = ""
    ids: frozenset[int] = field(default_factory=frozenset)
    color: int = 0
    emoji: PartialEmoji = PartialEmoji(name="\N{MEDIUM BLACK CIRCLE}")
    z_move: str = ""
    max_move: str = ""
    chart: frozendict[int, float] = field(default_factory=frozendict)
    game_id: int = 0

    def __init__(self, data: dict[str, Any]) -> None:
        self.name = data.get("name", "")
        self.icon = data.get("icon", "")
        if type_id := data.get("id", None):
            self.ids = frozenset({type_id})
        else:
            self.ids = frozenset(data.get("ids", []))
        self.color = data.get("color", 0)
        self.emoji = PartialEmoji.from_str(data.get("emoji", "<:pokeball:952522808435544074>"))
        self.z_move = data.get("z_move", "")
        self.max_move = data.get("max_move", "")
        self.chart = frozendict(data.get("chart", {}))
        self.game_id = data.get("game_id", 0)

    @property
    def id(self):
        return next(iter(self.ids), 0)

    @classmethod
    def from_dict(cls, **data: Any):
        return Typing(data)

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
            chart = {x: o for x in a | b if (o := a.get(x, 1.0) * b.get(x, 1.0)) != 1.0}
            return Typing.from_dict(ids=self.ids | other.ids, name=f"{self.name}/{other.name}", chart=frozendict(chart))
        return self

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
        return any(x in self.chart for x in other.ids)

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

    def when_attacked_by(self, *others: Typing, inverse: bool = False) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        base = 1.0
        for other in filter(lambda x: isinstance(x, Typing), others):
            for item in other.ids:
                value = self.chart.get(item, 1.0)
                if inverse and value != 1.0:
                    value = 0.5 if value > 1 else 2
                base *= value
        return base

    def when_attacking(self, *others: Typing, inverse: bool = False) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        base = 1.0
        for other in filter(lambda x: isinstance(x, Typing), others):
            for item in self.ids:
                value = other.chart.get(item, 1.0)
                if inverse and value != 1.0:
                    value = 0.5 if value > 1 else 2
                base *= value
        return base


class TypingEnum(Typing, Enum):
    Normal = {
        "name": "Normal",
        "icon": "/Chart/NormalIC_lsh07JZFXF.png",
        "game_id": 0,
        "id": 1,
        "color": 11052922,
        "emoji": "<:Normal:952523352839450634>",
        "z_move": "Breakneck Blitz",
        "max_move": "Max Strike",
        "chart": {7: 2.0, 14: 0, 19: 2},
    }
    Fire = {
        "name": "Fire",
        "icon": "/Chart/FireIC_FSXZ0ewoZ.png",
        "game_id": 9,
        "id": 2,
        "color": 15630640,
        "emoji": "<:Fire:952523352667484160>",
        "z_move": "Inferno Overdrive",
        "max_move": "Max Flare",
        "chart": {3: 2.0, 9: 2.0, 13: 2.0, 2: 0.5, 5: 0.5, 6: 0.5, 12: 0.5, 17: 0.5, 18: 0.5, 19: 2},
    }
    Water = {
        "name": "Water",
        "icon": "/Chart/WaterIC_AePidQZ435.png",
        "game_id": 10,
        "id": 3,
        "color": 6525168,
        "emoji": "<:Water:952523352688451594>",
        "z_move": "Hydro Vortex",
        "max_move": "Max Geyser",
        "chart": {4: 2.0, 5: 2.0, 2: 0.5, 3: 0.5, 6: 0.5, 17: 0.5, 19: 2},
    }
    Electric = {
        "name": "Electric",
        "icon": "/Chart/ElectricIC_SAqZW5RtMs.png",
        "game_id": 12,
        "id": 4,
        "color": 16240684,
        "emoji": "<:Electric:952523352646492180>",
        "z_move": "Gigavolt Havoc",
        "max_move": "Max Lightning",
        "chart": {9: 2.0, 4: 0.5, 10: 0.5, 17: 0.5, 19: 2},
    }
    Grass = {
        "name": "Grass",
        "icon": "/Chart/GrassIC_U9S3zw7Hqs.png",
        "game_id": 11,
        "id": 5,
        "color": 8046412,
        "emoji": "<:Grass:952523352571011072>",
        "z_move": "Bloom Doom",
        "max_move": "Max Overgrowth",
        "chart": {2: 2.0, 6: 2.0, 8: 2.0, 10: 2.0, 12: 2.0, 4: 0.5, 5: 0.5, 9: 0.5, 3: 0.5, 19: 2},
    }
    Ice = {
        "name": "Ice",
        "icon": "/Chart/IceIC_40f5wWdnqb.png",
        "id": 6,
        "game_id": 14,
        "color": 9886166,
        "emoji": "<:Ice:952523352587784222>",
        "z_move": "Subzero Slammer",
        "max_move": "Max Hailstorm",
        "chart": {2: 2.0, 7: 2.0, 13: 2.0, 17: 2.0, 6: 0.5, 19: 2},
    }
    Fighting = {
        "name": "Fighting",
        "icon": "/Chart/FightingIC_no8wYHEEg.png",
        "id": 7,
        "game_id": 1,
        "color": 12725800,
        "emoji": "<:Fighting:952523352533266432>",
        "z_move": "All-Out Pummeling",
        "max_move": "Max Knuckle",
        "chart": {10: 2.0, 11: 2.0, 18: 2.0, 12: 0.5, 13: 0.5, 16: 0.5, 19: 2},
    }
    Poison = {
        "name": "Poison",
        "icon": "/Chart/PoisonIC_oQDclvCSdq.png",
        "game_id": 3,
        "id": 8,
        "color": 10698401,
        "emoji": "<:Poison:952523352633901106>",
        "z_move": "Acid Downpour",
        "max_move": "Max Ooze",
        "chart": {9: 2.0, 11: 2.0, 5: 0.5, 7: 0.5, 8: 0.5, 12: 0.5, 18: 0.5, 19: 2},
    }
    Ground = {
        "name": "Ground",
        "icon": "/Chart/GroundIC_s-APkZLs1S.png",
        "id": 9,
        "game_id": 4,
        "color": 14860133,
        "emoji": "<:Ground:952523352612958239>",
        "z_move": "Tectonic Rage",
        "max_move": "Max Quake",
        "chart": {3: 2.0, 5: 2.0, 6: 2.0, 8: 0.5, 13: 0.5, 4: 0, 19: 2},
    }
    Flying = {
        "name": "Flying",
        "icon": "/Chart/FlyingIC_c9yZsKBzO.png",
        "game_id": 2,
        "id": 10,
        "color": 11112435,
        "emoji": "<:Flying:952523352994619402>",
        "z_move": "Supersonic Skystrike",
        "max_move": "Max Airstream",
        "chart": {4: 2.0, 6: 2.0, 13: 2.0, 5: 0.5, 7: 0.5, 12: 0.5, 9: 0, 19: 2},
    }
    Psychic = {
        "name": "Psychic",
        "icon": "/Chart/PsychicIC_DWslZRN75-.png",
        "game_id": 13,
        "id": 11,
        "color": 16340359,
        "emoji": "<:Psychic:952523352872996934>",
        "z_move": "Shattered Psyche",
        "max_move": "Max Mindstorm",
        "chart": {12: 2.0, 14: 2.0, 16: 2.0, 7: 0.5, 11: 0.5, 19: 2},
    }
    Bug = {
        "name": "Bug",
        "icon": "/Chart/BugIC_aYtpLtj9te.png",
        "id": 12,
        "game_id": 6,
        "color": 10926362,
        "emoji": "<:Bug:952523352524877835>",
        "z_move": "Savage Spin-Out",
        "max_move": "Max Flutterby",
        "chart": {2: 2.0, 10: 2.0, 13: 2.0, 5: 0.5, 7: 0.5, 9: 0.5, 19: 2},
    }
    Rock = {
        "name": "Rock",
        "icon": "/Chart/RockIC_9g894kz-kf.png",
        "id": 13,
        "game_id": 5,
        "color": 11968822,
        "emoji": "<:Rock:952523352671662140>",
        "z_move": "Continental Crush",
        "max_move": "Max Rockfall",
        "chart": {3: 2.0, 5: 2.0, 7: 2.0, 9: 2.0, 17: 2.0, 1: 0.5, 2: 0.5, 8: 0.5, 10: 0.5, 19: 2},
    }
    Ghost = {
        "name": "Ghost",
        "icon": "/Chart/GhostIC_jeQRdkKWUU.png",
        "id": 14,
        "game_id": 7,
        "color": 7559063,
        "emoji": "<:Ghost:952523352575209573>",
        "z_move": "Never-Ending Nightmare",
        "max_move": "Max Phantasm",
        "chart": {14: 2.0, 16: 2.0, 8: 0.5, 12: 0.5, 1: 0, 7: 0, 19: 2},
    }
    Dragon = {
        "name": "Dragon",
        "icon": "/Chart/DragonIC_n9B85giAn.png",
        "id": 15,
        "game_id": 15,
        "color": 7288316,
        "emoji": "<:Dragon:952523352545837066>",
        "z_move": "Devastating Drake",
        "max_move": "Max Wyrmwind",
        "chart": {6: 2.0, 15: 2.0, 18: 2.0, 2: 0.5, 3: 0.5, 4: 0.5, 5: 0.5, 19: 2},
    }
    Dark = {
        "name": "Dark",
        "icon": "/Chart/DarkIC_FwzVeCOWx.png",
        "id": 16,
        "game_id": 16,
        "color": 7362374,
        "emoji": "<:Dark:952523352617144380>",
        "z_move": "Black Hole Eclipse",
        "max_move": "Max Darkness",
        "chart": {7: 2.0, 12: 2.0, 18: 2.0, 14: 0.5, 16: 0.5, 11: 0, 19: 2},
    }
    Steel = {
        "name": "Steel",
        "icon": "/Chart/SteelIC_0wxMPLo8K.png",
        "id": 17,
        "game_id": 8,
        "color": 12040142,
        "emoji": "<:Steel:952523352717799454>",
        "z_move": "Corkscrew Crash",
        "max_move": "Max Steelspike",
        "chart": {
            2: 2.0,
            7: 2.0,
            9: 2.0,
            1: 0.5,
            5: 0.5,
            6: 0.5,
            10: 0.5,
            11: 0.5,
            12: 0.5,
            13: 0.5,
            15: 0.5,
            17: 0.5,
            18: 0.5,
            8: 0,
            19: 2,
        },
    }
    Fairy = {
        "name": "Fairy",
        "icon": "/Chart/FairyIC_eeeXGKfZv0.png",
        "id": 18,
        "game_id": 17,
        "color": 14058925,
        "emoji": "<:Fairy:952523352164159539>",
        "z_move": "Twinkle Tackle",
        "max_move": "Max Starfall",
        "chart": {8: 2.0, 17: 2.0, 7: 0.5, 12: 0.5, 16: 0.5, 15: 0, 19: 2},
    }
    Shadow = {
        "name": "Shadow",
        "icon": "/Chart/Shadow_FazY5m9Va.png",
        "id": 19,
        "game_id": 18,
        "color": 4076373,
        "z_move": "Gale of Darkness",
        "max_move": "Max Nightmare",
        "chart": {x: 1.0 if x == 19 else 0.5 for x in range(1, 20)},
    }
    Typeless = {
        "name": "Typeless",
        "icon": "/Chart/Typeless_0kxw2KAj3.png",
        "id": 20,
        "game_id": 19,
        "color": 6856848,
        "z_move": "Wide Slash",
        "max_move": "Vacuum-Cut",
    }

    @property
    def terrain(self):
        match self:
            case self.Fairy:
                return "Misty Terrain"
            case self.Grass:
                return "Grassy Terrain"
            case _:
                return f"{self.name} Terrain"

    @property
    def z_move_range(self):
        return Z_MOVE_RANGE

    @property
    def max_move_range(self):
        match self:
            case self.Fighting | self.Poison | self.Shadow | self.Typeless:
                return MAX_MOVE_RANGE2
            case _:
                return MAX_MOVE_RANGE1

    @classmethod
    def all(cls, *ignore: TypingEnum):
        return frozenset({x for x in TypingEnum if x not in ignore})

    @classmethod
    def find(cls, predicate: Callable[[Typing], Any]):
        return find(predicate, TypingEnum)

    @classmethod
    def get(cls, **kwargs: Any):
        return get(TypingEnum, **kwargs)

    @classmethod
    @lru_cache(maxsize=None)
    def deduce(cls, item: str | TypingEnum) -> Optional[TypingEnum]:
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
        if isinstance(item, Typing):
            return TypingEnum(item)

        name = fix(item).title()
        if data := TypingEnum.get(name=name):
            return data
        if data := process.extractOne(
            name,
            TypingEnum,
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=85,
        ):
            return data[0]

    @classmethod
    def deduce_many(cls, *elems: str | TypingEnum):
        """This is a method that determines the moves out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        elems : str
            Strings to search

        Returns
        -------
        frozenset[TypingEnum]
            Obtained result
        """
        items = [TypingEnum(x) for x in elems if isinstance(x, Typing)]

        if aux := ",".join(x for x in elems if isinstance(x, str)):
            data = split(r"[^A-Za-z0-9 \.'-]", aux)
            items.extend(x for elem in data if elem and (x := cls.deduce(elem)))

        return frozenset(items)

    def when_attacked_by(self, *others: Typing | str, inverse: bool = False) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        data = [o for x in others if (o := TypingEnum.deduce(x) if isinstance(x, str) else TypingEnum(x))]
        return super(TypingEnum, self).when_attacked_by(*data, inverse=inverse)

    def when_attacking(self, *others: Typing | str, inverse: bool = False) -> float:
        """method to determine multiplier

        Returns
        -------
        float
            value
        """
        data = [o for x in others if (o := TypingEnum.deduce(x) if isinstance(x, str) else TypingEnum(x))]
        return super(TypingEnum, self).when_attacking(*data, inverse=inverse)
