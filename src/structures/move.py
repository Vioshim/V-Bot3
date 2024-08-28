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

from enum import IntEnum
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
ALL_MOVES_DEX: dict[str, dict[str, dict[str, str]]] = {"Physical": {}, "Special": {}, "Status": {}}


class Category(IntEnum):
    Status = 1080656476357525615
    Physical = 1080656480446971914
    Special = 1080656483190059038

    @property
    def url(self):
        return f"https://cdn.discordapp.com/emojis/{self.value}.png"

    @property
    def emoji(self):
        return PartialEmoji(name=self.name, id=self.value)

    @classmethod
    def from_id(cls, value: int):
        match value:
            case 1:
                return cls.Physical
            case 2:
                return cls.Special
            case _:
                return cls.Status


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
    "RawHealing": lambda x: (f"Raw Healing: {x}%" if x > 0 else f"Drains {x}% from User's HP") if x != 0 else None,
    "RawTarget": lambda x: f"Raw Target: {x}" if x != 0 else None,
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
    "Flag_Metronome": lambda x: None if x else "Can't be used by metronome",
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
    def dex(self):
        return self.dex_category()
    
    def dex_category(self, cat: Optional[Category] = None):
        cat = cat or self.category
        return ALL_MOVES_DEX.get(cat.name, {}).get(self.name, {})
    
    @property
    def move_id(self) -> int:
        return self.data.get("MoveID", 0)

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, o: Move) -> bool:
        return isinstance(o, Move) and self.id == o.id

    def __int__(self):
        return self.move_id

    @property
    def id(self):
        return fix(self.name)

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
        # fmt: off
        return (
            self.move_id in {0, 743, 1000}  # No ID, Max Guard, GMax Moves
            or self.is_z_move()
            or self.is_max_move()
        )
        # fmt: on

    def is_z_move(self):
        # fmt: off
        return (
            622 <= self.move_id <= 658  # Z-Moves
            or 695 <= self.move_id <= 703
            or self.move_id == 719
            or 723 <= self.move_id <= 728  # Unique Z-Moves
        )
        # fmt: on

    def is_max_move(self):
        return 757 <= self.move_id <= 774  # Max-Moves

    @property
    def z_effect(self) -> Optional[tuple[str, str]]:
        match self.name:
            case "Metronome" | "Nature Power" | "Assist":
                return "None", "Calls a Z Move"
            case "Healing Wish" | "Lunar Dance":
                return "None", "None"
            case (
                "Tail Whip"
                | "Leer"
                | "Meditate"
                | "Screech"
                | "Sharpen"
                | "Will-O-Wisp"
                | "Taunt"
                | "Odor Sleuth"
                | "Howl"
                | "Bulk Up"
                | "Power Trick"
                | "Hone Claws"
                | "Work Up"
                | "Rototiller"
                | "Topsy-Turvy"
                | "Laser Focus"
            ):
                return "Attack ↑", "Raises Attack by 1 stage"
            case "Splash":
                return "Attack ↑↑↑", "Raises Attack by 3 stage"
            case "Mirror Move":
                return "Attack ↑↑", "Raises Attack by 2 stages, calls a Z-move"
            case (
                "Growl"
                | "Roar"
                | "Poison Powder"
                | "Toxic"
                | "Harden"
                | "Withdraw"
                | "Reflect"
                | "Poison Gas"
                | "Spider Web"
                | "Spikes"
                | "Charm"
                | "Pain Split"
                | "Torment"
                | "Feather Dance"
                | "Tickle"
                | "Block"
                | "Toxic Spikes"
                | "Aqua Ring"
                | "Stealth Rock"
                | "Defend Order"
                | "Wide Guard"
                | "Quick Guard"
                | "Mat Block"
                | "Noble Roar"
                | "Flower Shield"
                | "Grassy Terrain"
                | "Fairy Lock"
                | "Play Nice"
                | "Spiky Shield"
                | "Venom Drench"
                | "Baby-Doll Eyes"
                | "Baneful Bunker"
                | "Strength Sap"
                | "Tearful Look"
            ):
                return "Defense ↑", "Raises Defense by 1 stage"
            case (
                "Growth"
                | "Confuse Ray"
                | "Mind Reader"
                | "Nightmare"
                | "Sweet Kiss"
                | "Teeter Dance"
                | "Fake Tears"
                | "Metal Sound"
                | "Gravity"
                | "Miracle Eye"
                | "Embargo"
                | "Telekinesis"
                | "Soak"
                | "Simple Beam"
                | "Reflect Type"
                | "Ion Deluge"
                | "Electrify"
                | "Gear Up"
                | "Psychic Terrain"
                | "Instruct"
            ):
                return "Special Attack ↑", "Raises Special Attack by 1 stage"
            case "Psycho Shift" | "Heal Block":
                return "Special Attack ↑↑", "Raises Special Attack by 2 stages"
            case (
                "Whirlwind"
                | "Stun Spore"
                | "Thunder Wave"
                | "Light Screen"
                | "Glare"
                | "Mean Look"
                | "Flatter"
                | "Charge"
                | "Wish"
                | "Ingrain"
                | "Mud Sport"
                | "Cosmic Power"
                | "Water Sport"
                | "Wonder Room"
                | "Magic Room"
                | "Entrainment"
                | "Crafty Shield"
                | "Misty Terrain"
                | "Confide"
                | "Eerie Impulse"
                | "Magnetic Flux"
                | "Spotlight"
            ):
                return "Special Defense ↑", "Raises Special Defense by 1 stage"
            case "Magic Coat" | "Imprison" | "Captivate" | "Aromatic Mist" | "Powder":
                return "Special Defense ↑↑", "Raises Special Defense by 2 stages"
            case (
                "Sing"
                | "Supersonic"
                | "Sleep Powder"
                | "String Shot"
                | "Hypnosis"
                | "Lovely Kiss"
                | "Scary Face"
                | "Lock-On"
                | "Sandstorm"
                | "Safeguard"
                | "Encore"
                | "Rain Dance"
                | "Sunny Day"
                | "Hail"
                | "Role Play"
                | "Yawn"
                | "Skill Swap"
                | "Grass Whistle"
                | "Gastro Acid"
                | "Power Swap"
                | "Guard Swap"
                | "Worry Seed"
                | "Guard Split"
                | "Power Split"
                | "After You"
                | "Quash"
                | "Sticky Web"
                | "Electric Terrain"
                | "Toxic Thread"
                | "Speed Swap"
                | "Aurora Veil"
            ):
                return "Speed ↑", "Raises Speed by 1 stage"
            case "Trick" | "Recycle" | "Snatch" | "Switcheroo" | "Ally Switch" | "Bestow":
                return "Speed ↑↑", "Raises Speed by 2 stages"
            case "Me First":
                return "Speed ↑↑", "Raises Speed by 2 stages, calls a Z-move"
            case "Mimic" | "Defense Curl" | "Focus Energy" | "Sweet Scent" | "Defog" | "Trick Room":
                return "Accuracy ↑", "Raises accuracy by 1 stage"
            case "Copycat":
                return "Accuracy ↑", "Raises accuracy by 1 stage, calls a Z-move"
            case (
                "Sand Attack"
                | "Smokescreen"
                | "Kinesis"
                | "Flash"
                | "Detect"
                | "Camouflage"
                | "Lucky Chant"
                | "Magnet Rise"
            ):
                return "Evasiveness ↑", "Raises evasiveness by 1 stage"
            case (
                "Conversion"
                | "Sketch"
                | "Trick-or-Treat"
                | "'Forest's Curse"
                | "Geomancy"
                | "Happy Hour"
                | "Celebrate"
                | "Hold Hands"
                | "Purify"
            ):
                return "Stats ↑", "Raises Attack, Defense, Sp. Atk, Sp. Def, and Speed by 1 stage"
            case "Foresight" | "Tailwind" | "Acupressure" | "Heart Swap" | "Sleep Talk":
                return "Boosts critical-hit ratio", "Boosts critical-hit ratio by 2 stages"
            case "Sleep Talk":
                return "Boosts critical-hit ratio", "Boosts critical-hit ratio by 2 stages, calls a Z-move"
            case (
                "Swords Dance"
                | "Disable"
                | "Leech Seed"
                | "Agility"
                | "Double Team"
                | "Recover"
                | "Minimize"
                | "Barrier"
                | "Amnesia"
                | "Soft-Boiled"
                | "Spore"
                | "Acid Armor"
                | "Rest"
                | "Substitute"
                | "Cotton Spore"
                | "Protect"
                | "Perish Song"
                | "Endure"
                | "Swagger"
                | "Milk Drink"
                | "Attract"
                | "Baton Pass"
                | "Morning Sun"
                | "Synthesis"
                | "Moonlight"
                | "Swallow"
                | "Follow Me"
                | "Helping Hand"
                | "Tail Glow"
                | "Slack Off"
                | "Iron Defense"
                | "Calm Mind"
                | "Dragon Dance"
                | "Roost"
                | "Rock Polish"
                | "Nasty Plot"
                | "Heal Order"
                | "Dark Void"
                | "Autotomize"
                | "Rage Powder"
                | "Quiver Dance"
                | "Coil"
                | "Shell Smash"
                | "Heal Pulse"
                | "Shift Gear"
                | "Cotton Guard"
                | "King's Shield"
                | "Shore Up"
                | "Floral Healing"
            ):
                return "Reset Stats", "Resets user's lowered stats"
            case (
                "Mist"
                | "Teleport"
                | "Haze"
                | "Transform"
                | "Conversion 2"
                | "Spite"
                | "Belly Drum"
                | "Heal Bell"
                | "Psych Up"
                | "Stockpile"
                | "Refresh"
                | "Aromatherapy"
            ):
                return "Restores HP", "Fully restores user's HP"
            case "Memento" | "Parting Shot":
                return "Restores replacement's HP", "Fully restores switched-in ally's HP"
            case "Destiny Bond" | "Grudge":
                return "Center of attention", "User becomes center of attention"
            case "Curse":
                return (
                    "Changes depending on the type",
                    "Fully restores user's HP (Ghost-type), Raises Attack by 1 stage (non Ghost-type)",
                )

    @property
    def description(self):
        return "\n".join(f"• {o}." for k, v in CHECK_FLAGS.items() if k in self.data and (o := v(self.data[k])))

    def embed_for(self, item: TypingEnum):
        title = self.name
        if self.banned:
            title += " - Banned Move"

        embed = Embed(
            title=title,
            description=self.description[:4096],
            color=item.color,
            timestamp=utcnow(),
        )

        if self.type != item:
            embed.set_author(name=f"Originally {self.type.name} Type ", icon_url=self.type.emoji.url)

        cat = self.category
        embed.set_footer(text=cat.name, icon_url=cat.emoji.url)
        embed.set_thumbnail(url=item.emoji.url)
        embed.set_image(url=WHITE_BAR)
        embed.add_field(name="Max Power", value=self.max_move_base)
        embed.add_field(name="Max Move", value=self.max_move_name)
        embed.add_field(name="Z Power", value=self.z_move_base)
        if effect := self.z_effect:
            _, effect = effect
            embed.add_field(name="Z Effect", value=effect, inline=False)
        return embed

    @property
    def embed(self):
        return self.embed_for(self.type)

    def z_move_embed_for(self, item: TypingEnum):
        if move := Move.get(name=item.z_move):
            description = move.description
        else:
            description = self.description

        embed = Embed(
            title=f"{self.calculated_base_z(item.z_move_range)}〛{self.type.z_move}",
            description=description[:4096],
            color=item.color,
            timestamp=utcnow(),
        )
        embed.set_author(
            name=f"Original Move: {self.name}",
            icon_url=self.type.emoji.url if self.type != item else None,
        )
        cat = self.category
        embed.set_footer(text=cat.name, icon_url=cat.emoji.url)
        embed.set_thumbnail(url=self.type.emoji.url)
        embed.set_image(url=WHITE_BAR)
        if effect := self.z_effect:
            _, effect = effect
            embed.add_field(name="Effect", value=effect, inline=False)

        return embed

    @property
    def z_move_embed(self):
        return self.z_move_embed_for(self.type)

    @property
    def max_move_name(self):
        return "Max Guard" if self.category == Category.Status else self.type.max_move

    def max_move_type_for(self, item: TypingEnum):
        return TypingEnum.Normal if self.category == Category.Status else item

    @property
    def max_move_type(self):
        return self.max_move_type_for(self.type)

    def max_move_embed_for(self, item: TypingEnum):
        if move := Move.get(name=item.max_move):
            description = move.description
        else:
            description = self.description

        embed = Embed(
            title=f"{self.calculated_base(item.max_move_range)}〛{item.max_move}",
            description=description[:4096],
            color=item.color,
            timestamp=utcnow(),
        )
        cat = self.category
        embed.set_author(
            name=f"Original Move: {self.name}",
            icon_url=item.emoji.url if item != self.type else None,
        )
        embed.set_footer(text=cat.name, icon_url=cat.emoji.url)
        embed.set_thumbnail(url=item.emoji.url)
        embed.set_image(url=WHITE_BAR)

        if cat != Category.Status:
            embed.add_field(name="Effect", value=item.max_effect, inline=False)

        return embed

    @property
    def max_move_embed(self):
        return self.max_move_embed_for(self.type)

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        """Repr method for movepool based on Crest's design.

        Returns
        -------
        str
            Representation of a move
        """
        return f"[{self.name}] - {self.type.name} ({self.category.name})".title()

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

    def calculated_base_z(self, raw: dict[int, int]):
        return {
            "Mega Drain": 120,
            "Weather Ball": 160,
            "Hex": 160,
            "Gear Grind": 180,
            "V-Create": 220,
            "Flying Press": 170,
            "Core Enforcer": 140,
            "Fissure": 180,
            "Guillotine": 180,
            "Horn Drill": 180,
            "Sheer Cold": 180,
        }.get(self.name, self.calculated_base(raw))

    @property
    def z_move_base(self) -> int:
        return self.calculated_base_z(self.type.z_move_range)

    @property
    def max_move_base(self) -> int:
        return self.calculated_base(self.type.max_move_range)

    @classmethod
    def all(cls, banned: Optional[bool] = None, shadow: Optional[bool] = None) -> frozenset[Move]:
        moves: set[Move] = set(ALL_MOVES.values())
        if isinstance(banned, bool):
            moves = {x for x in moves if x.banned == banned}
        if isinstance(shadow, bool):
            if shadow:
                moves = {x for x in moves if TypingEnum.Shadow == x.type}
            else:
                moves = {x for x in moves if TypingEnum.Shadow != x.type}
        return frozenset(moves)

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
    DATA.extend(Move(x) for x in load(f) if x)

for cat in Category:
    with open(f"resources/dex_{cat.name.lower()}.json", mode="r", encoding="utf8") as f:
        ALL_MOVES_DEX[cat.name] = load(f)


ALL_MOVES = frozendict({item.id: item for item in DATA})
ALL_MOVES_BY_NAME = frozendict({item.name: item for item in DATA})
