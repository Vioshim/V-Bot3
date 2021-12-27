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

from difflib import get_close_matches
from enum import Enum
from re import compile
from typing import Optional, Union

from discord import PartialEmoji
from frozendict import frozendict

from src.structures.mon_typing import Typing

"""
from src.structures.mon_typing import (
    MAX_MOVE_RANGE1,
    MAX_MOVE_RANGE2,
    Z_MOVE_RANGE,
    Typing,
)
"""

MATCHER = compile(r"(\w+)")
MAX_MOVE_RANGE1 = []
MAX_MOVE_RANGE2 = []
Z_MOVE_RANGE = []

__all__ = ("Types",)


class Types(Enum):
    """This is an enumration of Pokemon Types

    Attributes
    ----------
    id : int
        Type's ID
    chart : dict[int, float]
        Type's Chart
    z_move : str
        Type's Z-Move
    max_move : str
        Type's Max-Move
    emoji : PartialEmoji
        Type's Emoji
    color : int
        Type's Color as int
    banner : str
        Image that represents the banner

    Methods
    -------
    calc_z_move(origin=None)
        Returns the calculated Base for the type's Z-Move
    calc_max_move(origin=None)
        Returns the calculated Base for the type's Max-Move
    deduce(item="")
        Returns the type whose name fits the given string.
    """

    NORMAL = Typing(
        id=1,
        name="Normal",
        color=0xA8A77A,
        z_move="Breakneck Blitz",
        max_move="Max Strike",
        chart=frozendict({7: 2.0, 14: 0}),
        emoji=PartialEmoji(
            name="Normal",
            id=880800547450531900,
        ),
        icon="/Chart/NormalIC_lsh07JZFXF.png",
        banner="/Banners/Normal_7WLut6aBRu9.png",
    )
    FIRE = Typing(
        id=2,
        name="Fire",
        color=0xEE8130,
        z_move="Inferno Overdrive",
        max_move="Max Flare",
        emoji=PartialEmoji(
            name="Fire",
            id=880800547505049670,
        ),
        chart=frozendict(
            {
                3: 2.0,
                9: 2.0,
                13: 2.0,
                2: 0.5,
                5: 0.5,
                6: 0.5,
                12: 0.5,
                17: 0.5,
                18: 0.5,
            }
        ),
        icon="/Chart/FireIC_FSXZ0ewoZ.png",
        banner="/Banners/Fire_MWKQIWPHCI.png",
    )
    WATER = Typing(
        id=3,
        name="Water",
        color=0x6390F0,
        z_move="Hydro Vortex",
        max_move="Max Geyser",
        emoji=PartialEmoji(
            name="Water",
            id=880800547555397652,
        ),
        chart=frozendict(
            {
                4: 2.0,
                5: 2.0,
                2: 0.5,
                3: 0.5,
                6: 0.5,
                17: 0.5,
            }
        ),
        icon="/Chart/WaterIC_AePidQZ435.png",
        banner="/Banners/Water_QrO8_rrrQA.png",
    )
    ELECTRIC = Typing(
        id=4,
        name="Electric",
        color=0xF7D02C,
        emoji=PartialEmoji(
            name="Electric",
            id=880800547530223626,
        ),
        z_move="Gigavolt Havoc",
        max_move="Max Lightning",
        chart=frozendict(
            {
                9: 2.0,
                4: 0.5,
                10: 0.5,
                17: 0.5,
            }
        ),
        icon="/Chart/ElectricIC_SAqZW5RtMs.png",
        banner="/Banners/Electric__HK82VrgVP.png",
    )
    GRASS = Typing(
        id=5,
        name="Grass",
        color=0x7AC74C,
        z_move="Bloom Doom",
        max_move="Max Overgrowth",
        emoji=PartialEmoji(
            name="Grass",
            id=880800547547021322,
        ),
        chart=frozendict(
            {
                2: 2.0,
                6: 2.0,
                8: 2.0,
                11: 2.0,
                12: 2.0,
                4: 0.5,
                5: 0.5,
                9: 0.5,
                3: 0.5,
            }
        ),
        icon="/Chart/GrassIC_U9S3zw7Hqs.png",
        banner="/Banners/Grass_MibpgmlZSu.png",
    )
    ICE = Typing(
        id=6,
        name="Ice",
        color=0x96D9D6,
        z_move="Subzero Slammer",
        max_move="Max Hailstorm",
        chart=frozendict(
            {
                2: 2.0,
                7: 2.0,
                13: 2.0,
                17: 2.0,
                6: 0.5,
            }
        ),
        emoji=PartialEmoji(
            name="Ice",
            id=880800547182112799,
        ),
        icon="/Chart/IceIC_40f5wWdnqb.png",
        banner="/Banners/Ice_qf9cM_0BZ.png",
    )
    FIGHTING = Typing(
        id=7,
        name="Fighting",
        color=0xC22E28,
        z_move="All-Out Pummeling",
        max_move="Max Knuckle",
        chart=frozendict(
            {
                10: 2.0,
                11: 2.0,
                18: 2.0,
                12: 0.5,
                13: 0.5,
                16: 0.5,
            }
        ),
        emoji=PartialEmoji(
            name="Fighting",
            id=880800547123388508,
        ),
        icon="/Chart/FightingIC_no8wYHEEg.png",
        banner="/Banners/Fighting_KadL0Lfvu.png",
    )
    POISON = Typing(
        id=8,
        name="Poison",
        color=0xA33EA1,
        z_move="Acid Downpour",
        max_move="Max Ooze",
        emoji=PartialEmoji(
            name="Poison",
            id=880800547127582761,
        ),
        chart=frozendict(
            {
                9: 2.0,
                11: 2.0,
                5: 0.5,
                7: 0.5,
                8: 0.5,
                12: 0.5,
                18: 0.5,
            }
        ),
        icon="/Chart/PoisonIC_oQDclvCSdq.png",
        banner="/Banners/Poison_51HLU3KQT.png",
    )
    GROUND = Typing(
        id=9,
        name="Ground",
        color=0xE2BF65,
        z_move="Tectonic Rage",
        emoji=PartialEmoji(
            name="Ground",
            id=880800547614105600,
        ),
        max_move="Max Quake",
        chart=frozendict(
            {
                3: 2.0,
                5: 2.0,
                6: 2.0,
                8: 0.5,
                13: 0.5,
                4: 0,
            }
        ),
        icon="/Chart/GroundIC_s-APkZLs1S.png",
        banner="/Banners/Ground_0nzRnpGnrb.png",
    )
    FLYING = Typing(
        id=10,
        name="Flying",
        color=0xA98FF3,
        z_move="Supersonic Skystrike",
        max_move="Max Airstream",
        emoji=PartialEmoji(
            name="Flying",
            id=880800547341475892,
        ),
        chart=frozendict(
            {
                4: 2.0,
                6: 2.0,
                13: 2.0,
                5: 0.5,
                7: 0.5,
                12: 0.5,
                9: 0,
            }
        ),
        icon="/Chart/FlyingIC_c9yZsKBzO.png",
        banner="/Banners/Flying_ndzxuXXBd.png",
    )
    PSYCHIC = Typing(
        id=11,
        name="Psychic",
        color=0xA98FF3,
        z_move="Shattered Psyche",
        max_move="Max Mindstorm",
        emoji=PartialEmoji(
            name="Psychic",
            id=880800547505074256,
        ),
        chart=frozendict(
            {
                12: 2.0,
                14: 2.0,
                16: 2.0,
                7: 0.5,
                11: 0.5,
            }
        ),
        icon="/Chart/PsychicIC_DWslZRN75-.png",
        banner="/Banners/Psychic_DZdtI2j5sN.png",
    )
    BUG = Typing(
        id=12,
        name="Bug",
        color=0xA6B91A,
        z_move="Savage Spin-Out",
        max_move="Max Flutterby",
        emoji=PartialEmoji(
            name="Bug",
            id=880800547442163763,
        ),
        chart=frozendict(
            {
                2: 2.0,
                10: 2.0,
                13: 2.0,
                5: 0.5,
                7: 0.5,
                9: 0.5,
            }
        ),
        icon="/Chart/BugIC_aYtpLtj9te.png",
        banner="/Banners/Bug_NF9aQ4XCV0.png",
    )
    ROCK = Typing(
        id=13,
        name="Rock",
        color=0xB6A136,
        z_move="Continental Crush",
        max_move="Max Rockfall",
        emoji=PartialEmoji(
            name="Rock",
            id=880800547387617360,
        ),
        chart=frozendict(
            {
                3: 2.0,
                5: 2.0,
                7: 2.0,
                9: 2.0,
                17: 2.0,
                1: 0.5,
                2: 0.5,
                8: 0.5,
                10: 0.5,
            }
        ),
        icon="/Chart/RockIC_9g894kz-kf.png",
        banner="/Banners/Rock_io2kdnYrTQ.png",
    )
    GHOST = Typing(
        id=14,
        name="Ghost",
        color=0x735797,
        z_move="Never-Ending Nightmare",
        max_move="Max Phantasm",
        emoji=PartialEmoji(
            name="Ghost",
            id=880800547412774983,
        ),
        chart=frozendict(
            {
                14: 2.0,
                16: 2.0,
                8: 0.5,
                12: 0.5,
                1: 0,
                7: 0,
            }
        ),
        icon="/Chart/GhostIC_jeQRdkKWUU.png",
        banner="/Banners/Ghost_-8cmW_6pBqM.png",
    )
    DRAGON = Typing(
        id=15,
        name="Dragon",
        color=0x6F35FC,
        z_move="Devastating Drake",
        max_move="Max Wyrmwind",
        emoji=PartialEmoji(
            name="Dragon",
            id=880800547245031435,
        ),
        chart=frozendict(
            {
                6: 2.0,
                15: 2.0,
                18: 2.0,
                2: 0.5,
                3: 0.5,
                4: 0.5,
                5: 0.5,
            }
        ),
        icon="/Chart/DragonIC_n9B85giAn.png",
        banner="/Banners/Dragon_fxDjF0oKbiw.png",
    )
    DARK = Typing(
        id=16,
        name="Dark",
        color=0x705746,
        z_move="Black Hole Eclipse",
        emoji=PartialEmoji(
            name="Dark",
            id=880800547572183050,
        ),
        max_move="Max Darkness",
        chart=frozendict(
            {
                7: 2.0,
                12: 2.0,
                18: 2.0,
                14: 0.5,
                16: 0.5,
                11: 0,
            }
        ),
        icon="/Chart/DarkIC_FwzVeCOWx.png",
        banner="/Banners/Dark_ZKw4hIYdnp.png",
    )
    STEEL = Typing(
        id=17,
        name="Steel",
        color=0xB7B7CE,
        z_move="Corkscrew Crash",
        max_move="Max Steelspike",
        emoji=PartialEmoji(
            name="Steel",
            id=880800547534430238,
        ),
        chart=frozendict(
            {
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
            }
        ),
        icon="/Chart/SteelIC_0wxMPLo8K.png",
        banner="/Banners/Steel_lSEoLioGM.png",
    )
    FAIRY = Typing(
        id=18,
        name="Fairy",
        color=0xD685AD,
        z_move="Twinkle Tackle",
        max_move="Max Starfall",
        emoji=PartialEmoji(
            name="Fairy",
            id=880800547505045504,
        ),
        chart=frozendict(
            {
                8: 2.0,
                17: 2.0,
                7: 0.5,
                12: 0.5,
                16: 0.5,
                15: 0,
            }
        ),
        icon="/Chart/FairyIC_eeeXGKfZv0.png",
        banner="/Banners/Fairy_avtBHCy-TB.png",
    )

    def __str__(self) -> str:
        """str method

        Returns
        -------
        str
            Type's name
        """
        return self.value.name

    def __repr__(self) -> str:
        """repr method

        Returns
        -------
        str
            Types.{name}
        """
        return f"Types.{self.name}"

    def __contains__(self, other: Types) -> bool:
        """contains method

        Parameters
        ----------
        other : Types
            type to inspect

        Returns
        -------
        bool
            if included in the type chart
        """
        return other.value in self.value

    def __getitem__(self, other: Types) -> float:
        """Chart value comparing one from another

        Returns
        -------
        float
            value
        """
        return self.value[other.value.id]

    def __setitem__(self, idx: int, value) -> None:
        """setitem method

        Parameters
        ----------
        idx : int
            type id
        value : [type]
            chart value
        """
        self.value[idx] = value

    def __add__(self, other: Types) -> Typing:
        """Add method

        Parameters
        ----------
        other : Types
            Type to be added

        Returns
        -------
        Typing
            Resulting typing
        """
        return self.value + other.value

    def __int__(self) -> int:
        """int method

        Returns
        -------
        int
            Type's ID
        """
        return self.value.id

    @property
    def id(self) -> int:
        """Type's ID

        Returns
        -------
        int
            ID
        """
        return self.value.id

    @property
    def chart(self) -> dict[int, float]:
        """Type's Chart

        Returns
        -------
        dict[int, float]
            chart
        """
        return self.value.chart

    @property
    def z_move(self) -> str:
        """Type's Z-Move

        Returns
        -------
        str
            Z-move name
        """
        return self.value.z_move

    @property
    def max_move(self) -> str:
        """Type's Max-Move

        Returns
        -------
        str
            Max-move name
        """
        return self.value.max_move

    @property
    def emoji(self) -> PartialEmoji:
        """Type's Emoji

        Returns
        -------
        PartialEmoji
            Emoji
        """
        return self.value.emoji

    @property
    def color(self) -> int:
        """Type's Color

        Returns
        -------
        int
            color
        """
        return self.value.color

    @property
    def icon(self) -> str:
        """Type's Icon

        Returns
        -------
        str
            icon
        """
        return self.value.icon

    @property
    def banner(self) -> str:
        """Type's banner

        Returns
        -------
        str
            banner
        """
        return self.value.banner

    @property
    def terrain(self) -> str:
        return {
            Types.FAIRY: "Misty Terrain",
            Types.GRASS: "Grassy Terrain",
        }.get(self, f"{self.name} Terrain".title())

    @staticmethod
    def calc_z_move(
        origin: Optional[int] = None,
    ) -> int:
        """Obtains the calculated Z-move base for the typing

        Parameters
        ----------
        origin : Optional[int], optional
            Move's base, by default None

        Returns
        -------
        int
            Calculated Base
        """
        raw = Z_MOVE_RANGE
        info = filter(
            lambda x: x >= (origin or 0),
            raw.keys(),
        )
        return raw[next(info, 250)]

    def calc_max_move(
        self,
        origin: Optional[int] = None,
    ) -> int:
        """Obtains the calculated Max-move base for the typing

        Parameters
        ----------
        origin : Optional[int], optional
            Move's base, by default None

        Returns
        -------
        int
            Calculated Base
        """
        if self in [
            Types.FIGHTING,
            Types.POISON,
        ]:
            raw = MAX_MOVE_RANGE2
        else:
            raw = MAX_MOVE_RANGE1

        info = filter(
            lambda x: x >= (origin or 0),
            raw.keys(),
        )
        return raw[next(info, 250)]

    @classmethod
    def deduce(cls, item: Union[list[str], str]) -> set[Types]:
        """Deduce the provided typings out of a string

        Parameters
        ----------
        item : Union[list[str], str]
            list/String to inspect

        Returns
        -------
        set[Types]
            set with the typings
        """
        info = set()
        if isinstance(item, str):
            item = MATCHER.findall(item)
        for elem in item:
            for data in get_close_matches(word=elem.upper().strip(), possibilities=Types.__members__, n=1):
                info.add(Types[data])
        return info
