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
from random import choice
from typing import Iterable, Optional, Union

from src.enums.mon_types import Types
from src.structures.move import Category, Move

__all__ = ("Moves",)


class Moves(Enum):
    def __repr__(self) -> str:
        return repr(self.value)

    def __str__(self) -> str:
        return str(self.value)

    @property
    def emoji(self):
        return self.value.type.emoji

    @property
    def banned(self) -> bool:
        return self.value.banned

    @property
    def metronome(self) -> bool:
        return self.value.metronome

    @classmethod
    def metronome_fetch(cls) -> Moves:
        """This move generates a random move based on Metronome's behaviour

        Returns
        -------
        Moves
            Obtained move
        """
        moves = [move for move in Moves if not move.banned and move.metronome]
        return choice(moves)

    @classmethod
    def fetch_by_name(cls, move: Union[Moves, str]) -> Optional[Moves]:
        """Obtain a move by name based on its similarity

        Parameters
        ----------
        move : Union[Moves, str]
            Move name to check

        Returns
        -------
        Optional[Moves]
            Move found, if not None
        """
        if isinstance(move, Moves):
            return move
        for data in get_close_matches(
            word=move.upper().replace("-", "").replace(" ", ""),
            possibilities=Moves.__members__,
            n=1,
        ):
            return Moves[data]

    @classmethod
    def deduce(cls, name: Union[str, Iterable[str]]) -> set[Moves]:
        """This method obtains a set of moves based on a string with commas.

        Parameters
        ----------
        name : str
            String to check

        Returns
        -------
        set[Moves]
            Set with the matches.
        """
        if isinstance(name, str):
            name = name.title()
        elif isinstance(name, Iterable):
            name = ",".join(name).title()
        return {data for item in name.split(",") if (data := cls.fetch_by_name(item))}

    ABSORB = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=20,
        category=Category.SPECIAL,
        name=r"Absorb",
        pp=25,
        type=Types.GRASS,
    )
    ACCELEROCK = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Accelerock",
        pp=20,
        type=Types.ROCK,
    )
    ACID = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the foe(s) Sp. Def by 1.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Acid",
        pp=30,
        type=Types.POISON,
    )
    ACIDARMOR = Move(
        desc=r"Raises the user's Defense by 2 stages.",
        shortDesc=r"Raises the user's Defense by 2.",
        name=r"Acid Armor",
        pp=20,
        type=Types.POISON,
    )
    ACIDSPRAY = Move(
        desc=r"Has a 100% chance to lower the target's Special Defense by 2 stages.",
        shortDesc=r"100% chance to lower the target's Sp. Def by 2.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Acid Spray",
        pp=20,
        type=Types.POISON,
    )
    ACROBATICS = Move(
        desc=r"Power doubles if the user has no held item.",
        shortDesc=r"Power doubles if the user has no held item.",
        accuracy=100,
        base=55,
        category=Category.PHYSICAL,
        name=r"Acrobatics",
        pp=15,
        type=Types.FLYING,
    )
    ACUPRESSURE = Move(
        desc=r"Raises a random stat by 2 stages as long as the stat is not already at stage 6. The user can choose to use this move on itself or an adjacent ally. Fails if no stat stage can be raised or if used on an ally with a substitute.",
        shortDesc=r"Raises a random stat of the user or an ally by 2.",
        name=r"Acupressure",
        pp=30,
    )
    AERIALACE = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.PHYSICAL,
        name=r"Aerial Ace",
        pp=20,
        type=Types.FLYING,
    )
    AEROBLAST = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=95,
        base=100,
        category=Category.SPECIAL,
        name=r"Aeroblast",
        pp=5,
        type=Types.FLYING,
    )
    AFTERYOU = Move(
        desc=r"The target makes its move immediately after the user this turn, no matter the priority of its selected move. Fails if the target would have moved next anyway, or if the target already moved this turn.",
        shortDesc=r"The target makes its move right after the user.",
        name=r"After You",
        pp=15,
    )
    AGILITY = Move(
        desc=r"Raises the user's Speed by 2 stages.",
        shortDesc=r"Raises the user's Speed by 2.",
        name=r"Agility",
        pp=30,
        type=Types.PSYCHIC,
    )
    AIRCUTTER = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio. Hits adjacent foes.",
        accuracy=95,
        base=60,
        category=Category.SPECIAL,
        name=r"Air Cutter",
        pp=25,
        type=Types.FLYING,
    )
    AIRSLASH = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=95,
        base=75,
        category=Category.SPECIAL,
        name=r"Air Slash",
        pp=15,
        type=Types.FLYING,
    )
    ALLYSWITCH = Move(
        desc=r"The user swaps positions with its ally. Fails if the user is the only Pokemon on its side.",
        shortDesc=r"The user swaps positions with its ally.",
        name=r"Ally Switch",
        pp=15,
        type=Types.PSYCHIC,
    )
    AMNESIA = Move(
        desc=r"Raises the user's Special Defense by 2 stages.",
        shortDesc=r"Raises the user's Sp. Def by 2.",
        name=r"Amnesia",
        pp=20,
        type=Types.PSYCHIC,
    )
    ANCHORSHOT = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Prevents the target from switching out.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Anchor Shot",
        pp=20,
        type=Types.STEEL,
    )
    ANCIENTPOWER = Move(
        desc=r"Has a 10% chance to raise the user's Attack, Defense, Special Attack, Special Defense, and Speed by 1 stage.",
        shortDesc=r"10% chance to raise all stats by 1 (not acc/eva).",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Ancient Power",
        pp=5,
        type=Types.ROCK,
    )
    APPLEACID = Move(
        desc=r"Has a 100% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"100% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Apple Acid",
        pp=10,
        type=Types.GRASS,
    )
    AQUAJET = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Aqua Jet",
        pp=20,
        type=Types.WATER,
    )
    AQUARING = Move(
        desc=r"The user has 1/16 of its maximum HP, rounded down, restored at the end of each turn while it remains active. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down. If the user uses Baton Pass, the replacement will receive the healing effect.",
        shortDesc=r"User recovers 1/16 max HP per turn.",
        name=r"Aqua Ring",
        pp=20,
        type=Types.WATER,
    )
    AQUATAIL = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=9,
        base=90,
        category=Category.PHYSICAL,
        name=r"Aqua Tail",
        pp=10,
        type=Types.WATER,
    )
    ARMTHRUST = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=100,
        base=15,
        category=Category.PHYSICAL,
        name=r"Arm Thrust",
        pp=20,
        type=Types.FIGHTING,
    )
    AROMATHERAPY = Move(
        desc=r"Every Pokemon in the user's party is cured of its major status condition. Active Pokemon with the Sap Sipper Ability are not cured, unless they are the user.",
        shortDesc=r"Cures the user's party of all status conditions.",
        name=r"Aromatherapy",
        pp=5,
        type=Types.GRASS,
    )
    AROMATICMIST = Move(
        desc=r"Raises the target's Special Defense by 1 stage. Fails if there is no ally adjacent to the user.",
        shortDesc=r"Raises an ally's Sp. Def by 1.",
        name=r"Aromatic Mist",
        pp=20,
        type=Types.FAIRY,
    )
    ASSIST = Move(
        desc=r"A random move among those known by the user's party members is selected for use. Does not select Assist, Baneful Bunker, Beak Blast, Belch, Bestow, Bounce, Celebrate, Chatter, Circle Throw, Copycat, Counter, Covet, Destiny Bond, Detect, Dig, Dive, Dragon Tail, Endure, Feint, Fly, Focus Punch, Follow Me, Helping Hand, Hold Hands, King's Shield, Mat Block, Me First, Metronome, Mimic, Mirror Coat, Mirror Move, Nature Power, Phantom Force, Protect, Rage Powder, Roar, Shadow Force, Shell Trap, Sketch, Sky Drop, Sleep Talk, Snatch, Spiky Shield, Spotlight, Struggle, Switcheroo, Thief, Transform, Trick, Whirlwind, or any Z-Move.",
        shortDesc=r"Uses a random move known by a team member.",
        name=r"Assist",
        pp=20,
    )
    ASSURANCE = Move(
        desc=r"Power doubles if the target has already taken damage this turn, other than direct damage from Belly Drum, confusion, Curse, or Pain Split.",
        shortDesc=r"Power doubles if target was damaged this turn.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Assurance",
        pp=10,
        type=Types.DARK,
    )
    ASTONISH = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=30,
        category=Category.PHYSICAL,
        name=r"Astonish",
        pp=15,
        type=Types.GHOST,
    )
    ASTRALBARRAGE = Move(
        desc=r"The user attacks by sending a frightful amount of small ghosts at opposing Pokémon.",
        shortDesc=r"Astral Barrage inflicts damage to all adjacent opponents.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Astral Barrage",
        pp=5,
        type=Types.GHOST,
    )
    ATTACKORDER = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Attack Order",
        pp=15,
        type=Types.BUG,
    )
    ATTRACT = Move(
        desc=r"Causes the target to become infatuated, making it unable to attack 50% of the time. Fails if both the user and the target are the same gender, if either is genderless, or if the target is already infatuated. The effect ends when either the user or the target is no longer active. Pokemon with the Oblivious Ability or protected by the Aroma Veil Ability are immune.",
        shortDesc=r"A target of the opposite gender gets infatuated.",
        accuracy=100,
        name=r"Attract",
        pp=15,
    )
    AURASPHERE = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=80,
        category=Category.SPECIAL,
        name=r"Aura Sphere",
        pp=20,
        type=Types.FIGHTING,
    )
    AURAWHEEL = Move(
        desc=r"Has a 100% chance to raise the user's Speed by 1 stage. If the user is a Morpeko in Full Belly Mode, this move is Electric type. If the user is a Morpeko in Hangry Mode, this move is Dark type. This move cannot be used successfully unless the user's current form, while considering Transform, is Full Belly or Hangry Mode Morpeko.",
        shortDesc=r"Morpeko: Electric; Hangry: Dark; 100% +1 Spe.",
        accuracy=100,
        base=110,
        category=Category.PHYSICAL,
        name=r"Aura Wheel",
        pp=10,
        type=Types.ELECTRIC,
    )
    AURORABEAM = Move(
        desc=r"Has a 10% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"10% chance to lower the target's Attack by 1.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Aurora Beam",
        pp=20,
        type=Types.ICE,
    )
    AURORAVEIL = Move(
        desc=r"For 5 turns, the user and its party members take 0.5x damage from physical and special attacks, or 0.66x damage if in a Double Battle; does not reduce damage further with Reflect or Light Screen. Critical hits ignore this protection. It is removed from the user's side if the user or an ally is successfully hit by Brick Break, Psychic Fangs, or Defog. Brick Break and Psychic Fangs remove the effect before damage is calculated. Lasts for 8 turns if the user is holding Light Clay. Fails unless the weather is Hail.",
        shortDesc=r"For 5 turns, damage to allies is halved. Hail only.",
        name=r"Aurora Veil",
        pp=20,
        type=Types.ICE,
    )
    AUTOTOMIZE = Move(
        desc=r"Raises the user's Speed by 2 stages. If the user's Speed was changed, the user's weight is reduced by 100 kg as long as it remains active. This effect is stackable but cannot reduce the user's weight to less than 0.1 kg.",
        shortDesc=r"Raises the user's Speed by 2; user loses 100 kg.",
        name=r"Autotomize",
        pp=15,
        type=Types.STEEL,
    )
    AVALANCHE = Move(
        desc=r"Power doubles if the user was hit by the target this turn.",
        shortDesc=r"Power doubles if user is damaged by the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Avalanche",
        pp=10,
        type=Types.ICE,
    )
    BABYDOLLEYES = Move(
        desc=r"Lowers the target's Attack by 1 stage.",
        shortDesc=r"Lowers the target's Attack by 1.",
        accuracy=100,
        name=r"Baby-Doll Eyes",
        pp=30,
        type=Types.FAIRY,
    )
    BADDYBAD = Move(
        desc=r"This move summons Reflect for 5 turns upon use.",
        shortDesc=r"Summons Reflect.",
        accuracy=95,
        base=80,
        category=Category.SPECIAL,
        name=r"Baddy Bad",
        pp=15,
        type=Types.DARK,
    )
    BANEFULBUNKER = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn, and Pokemon making contact with the user become poisoned. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Protects from moves. Contact: poison.",
        name=r"Baneful Bunker",
        pp=10,
        type=Types.POISON,
    )
    BARRAGE = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=85,
        base=15,
        category=Category.PHYSICAL,
        name=r"Barrage",
        pp=20,
    )
    BARRIER = Move(
        desc=r"Raises the user's Defense by 2 stages.",
        shortDesc=r"Raises the user's Defense by 2.",
        name=r"Barrier",
        pp=20,
        type=Types.PSYCHIC,
    )
    BATONPASS = Move(
        desc=r"The user is replaced with another Pokemon in its party. The selected Pokemon has the user's stat stage changes, confusion, and certain move effects transferred to it.",
        shortDesc=r"User switches, passing stat changes and more.",
        name=r"Baton Pass",
        pp=40,
    )
    BEAKBLAST = Move(
        desc=r"If the user is hit by a contact move this turn before it can execute this move, the attacker is burned.",
        shortDesc=r"Burns on contact with the user before it moves.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Beak Blast",
        pp=15,
        type=Types.FLYING,
    )
    BEATUP = Move(
        desc=r"Hits one time for the user and one time for each unfainted Pokemon without a major status condition in the user's party. The power of each hit is equal to 5+(X/10) where X is each participating Pokemon's base Attack; each hit is considered to come from the user.",
        shortDesc=r"All healthy allies aid in damaging the target.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Beat Up",
        pp=10,
        type=Types.DARK,
    )
    BEHEMOTHBASH = Move(
        desc=r"Damage doubles if the target is Dynamaxed.",
        shortDesc=r"Damage doubles if the target is Dynamaxed.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Behemoth Bash",
        pp=5,
        type=Types.STEEL,
    )
    BEHEMOTHBLADE = Move(
        desc=r"Damage doubles if the target is Dynamaxed.",
        shortDesc=r"Damage doubles if the target is Dynamaxed.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Behemoth Blade",
        pp=5,
        type=Types.STEEL,
    )
    BELCH = Move(
        desc=r"This move cannot be selected until the user eats a Berry, either by eating one that was held, stealing and eating one off another Pokemon with Bug Bite or Pluck, or eating one that was thrown at it with Fling. Once the condition is met, this move can be selected and used for the rest of the battle even if the user gains or uses another item or switches out. Consuming a Berry with Natural Gift does not count for the purposes of eating one.",
        shortDesc=r"Cannot be selected until the user eats a Berry.",
        accuracy=9,
        base=120,
        category=Category.SPECIAL,
        name=r"Belch",
        pp=10,
        type=Types.POISON,
    )
    BELLYDRUM = Move(
        desc=r"Raises the user's Attack by 12 stages in exchange for the user losing 1/2 of its maximum HP, rounded down. Fails if the user would faint or if its Attack stat stage is 6.",
        shortDesc=r"User loses 50% max HP. Maximizes Attack.",
        name=r"Belly Drum",
        pp=10,
    )
    BESTOW = Move(
        desc=r"The target receives the user's held item. Fails if the user has no item or is holding a Mail or Z-Crystal, if the target is already holding an item, if the user is a Kyogre holding a Blue Orb, a Groudon holding a Red Orb, a Giratina holding a Griseous Orb, an Arceus holding a Plate, a Genesect holding a Drive, a Silvally holding a Memory, a Pokemon that can Mega Evolve holding the Mega Stone for its species, or if the target is one of those Pokemon and the user is holding the respective item.",
        shortDesc=r"User passes its held item to the target.",
        name=r"Bestow",
        pp=15,
    )
    BIDE = Move(
        desc=r"The user spends two turns locked into this move and then, on the second turn after using this move, the user attacks the last Pokemon that hit it, inflicting double the damage in HP it lost to attacks during the two turns. If the last Pokemon that hit it is no longer active, the user attacks a random opposing Pokemon instead. If the user is prevented from moving during this move's use, the effect ends. This move does not check accuracy and does not ignore type immunity.",
        shortDesc=r"Waits 2 turns; deals double the damage taken.",
        category=Category.PHYSICAL,
        name=r"Bide",
        pp=10,
    )
    BIND = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 2-5 turns.",
        accuracy=85,
        base=15,
        category=Category.PHYSICAL,
        name=r"Bind",
        pp=20,
    )
    BITE = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Bite",
        pp=25,
        type=Types.DARK,
    )
    BLASTBURN = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.SPECIAL,
        name=r"Blast Burn",
        pp=5,
        type=Types.FIRE,
    )
    BLAZEKICK = Move(
        desc=r"Has a 10% chance to burn the target and a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio. 10% chance to burn.",
        accuracy=9,
        base=85,
        category=Category.PHYSICAL,
        name=r"Blaze Kick",
        pp=10,
        type=Types.FIRE,
    )
    BLIZZARD = Move(
        desc=r"Has a 10% chance to freeze the target. If the weather is Hail, this move does not check accuracy.",
        shortDesc=r"10% chance to freeze foe(s). Can't miss in hail.",
        accuracy=7,
        base=110,
        category=Category.SPECIAL,
        name=r"Blizzard",
        pp=5,
        type=Types.ICE,
    )
    BLOCK = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Prevents the target from switching out.",
        name=r"Block",
        pp=5,
    )
    BLUEFLARE = Move(
        desc=r"Has a 20% chance to burn the target.",
        shortDesc=r"20% chance to burn the target.",
        accuracy=85,
        base=130,
        category=Category.SPECIAL,
        name=r"Blue Flare",
        pp=5,
        type=Types.FIRE,
    )
    BODYPRESS = Move(
        desc=r"Damage is calculated using the user's Defense stat as its Attack, including stat stage changes. Other effects that modify the Attack stat are used as normal.",
        shortDesc=r"Uses user's Def stat as Atk in damage calculation.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Body Press",
        pp=10,
        type=Types.FIGHTING,
    )
    BODYSLAM = Move(
        desc=r"Has a 30% chance to paralyze the target. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Body Slam",
        pp=15,
    )
    BOLTBEAK = Move(
        desc=r"Power doubles if the user moves before the target.",
        shortDesc=r"Power doubles if user moves before the target.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Bolt Beak",
        pp=10,
        type=Types.ELECTRIC,
    )
    BOLTSTRIKE = Move(
        desc=r"Has a 20% chance to paralyze the target.",
        shortDesc=r"20% chance to paralyze the target.",
        accuracy=85,
        base=130,
        category=Category.PHYSICAL,
        name=r"Bolt Strike",
        pp=5,
        type=Types.ELECTRIC,
    )
    BONECLUB = Move(
        desc=r"Has a 10% chance to flinch the target.",
        shortDesc=r"10% chance to flinch the target.",
        accuracy=85,
        base=65,
        category=Category.PHYSICAL,
        name=r"Bone Club",
        pp=20,
        type=Types.GROUND,
    )
    BONEMERANG = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=9,
        base=50,
        category=Category.PHYSICAL,
        name=r"Bonemerang",
        pp=10,
        type=Types.GROUND,
    )
    BONERUSH = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=9,
        base=25,
        category=Category.PHYSICAL,
        name=r"Bone Rush",
        pp=10,
        type=Types.GROUND,
    )
    BOOMBURST = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent Pokemon.",
        accuracy=100,
        base=140,
        category=Category.SPECIAL,
        name=r"Boomburst",
        pp=10,
    )
    BOUNCE = Move(
        desc=r"Has a 30% chance to paralyze the target. This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks other than Gust, Hurricane, Sky Uppercut, Smack Down, Thousand Arrows, Thunder, and Twister, and Gust and Twister have doubled power when used against it. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Bounces turn 1. Hits turn 2. 30% paralyze.",
        accuracy=85,
        base=85,
        category=Category.PHYSICAL,
        name=r"Bounce",
        pp=5,
        type=Types.FLYING,
    )
    BOUNCYBUBBLE = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Bouncy Bubble",
        pp=20,
        type=Types.WATER,
    )
    BRANCHPOKE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Branch Poke",
        pp=40,
        type=Types.GRASS,
    )
    BRAVEBIRD = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 33% the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 33% recoil.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Brave Bird",
        pp=15,
        type=Types.FLYING,
    )
    BREAKINGSWIPE = Move(
        desc=r"Has a 100% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Attack by 1.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Breaking Swipe",
        pp=15,
        type=Types.DRAGON,
    )
    BRICKBREAK = Move(
        desc=r"If this attack does not miss, the effects of Reflect, Light Screen, and Aurora Veil end for the target's side of the field before damage is calculated.",
        shortDesc=r"Destroys screens, unless the target is immune.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Brick Break",
        pp=15,
        type=Types.FIGHTING,
    )
    BRINE = Move(
        desc=r"Power doubles if the target has less than or equal to half of its maximum HP remaining.",
        shortDesc=r"Power doubles if the target's HP is 50% or less.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Brine",
        pp=10,
        type=Types.WATER,
    )
    BRUTALSWING = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent Pokemon.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Brutal Swing",
        pp=20,
        type=Types.DARK,
    )
    BUBBLE = Move(
        desc=r"Has a 10% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"10% chance to lower the foe(s) Speed by 1.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Bubble",
        pp=30,
        type=Types.WATER,
    )
    BUBBLEBEAM = Move(
        desc=r"Has a 10% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"10% chance to lower the target's Speed by 1.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Bubble Beam",
        pp=20,
        type=Types.WATER,
    )
    BUGBITE = Move(
        desc=r"If this move is successful and the user has not fainted, it steals the target's held Berry if it is holding one and eats it immediately, gaining its effects even if the user's item is being ignored. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"User steals and eats the target's Berry.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Bug Bite",
        pp=20,
        type=Types.BUG,
    )
    BUGBUZZ = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Bug Buzz",
        pp=10,
        type=Types.BUG,
    )
    BULKUP = Move(
        desc=r"Raises the user's Attack and Defense by 1 stage.",
        shortDesc=r"Raises the user's Attack and Defense by 1.",
        name=r"Bulk Up",
        pp=20,
        type=Types.FIGHTING,
    )
    BULLDOZE = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance lower adjacent Pkmn Speed by 1.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Bulldoze",
        pp=20,
        type=Types.GROUND,
    )
    BULLETPUNCH = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Bullet Punch",
        pp=30,
        type=Types.STEEL,
    )
    BULLETSEED = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=100,
        base=25,
        category=Category.PHYSICAL,
        name=r"Bullet Seed",
        pp=30,
        type=Types.GRASS,
    )
    BURNINGJEALOUSY = Move(
        desc=r"Has a 100% chance to burn the target if it had a stat stage raised this turn.",
        shortDesc=r"100% burns a target that had a stat rise this turn.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Burning Jealousy",
        pp=5,
        type=Types.FIRE,
    )
    BURNUP = Move(
        desc=r"Fails unless the user is a Fire type. If this move is successful, the user's Fire type becomes typeless as long as it remains active.",
        shortDesc=r"User's Fire type becomes typeless; must be Fire.",
        accuracy=100,
        base=130,
        category=Category.SPECIAL,
        name=r"Burn Up",
        pp=5,
        type=Types.FIRE,
    )
    BUZZYBUZZ = Move(
        desc=r"Has a 100% chance to paralyze the foe.",
        shortDesc=r"100% chance to paralyze the foe.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Buzzy Buzz",
        pp=20,
        type=Types.ELECTRIC,
    )
    CALMMIND = Move(
        desc=r"Raises the user's Special Attack and Special Defense by 1 stage.",
        shortDesc=r"Raises the user's Sp. Atk and Sp. Def by 1.",
        name=r"Calm Mind",
        pp=20,
        type=Types.PSYCHIC,
    )
    CAMOUFLAGE = Move(
        desc=r"The user's type changes based on the battle terrain. Normal type on the regular Wi-Fi terrain, Electric type during Electric Terrain, Fairy type during Misty Terrain, Grass type during Grassy Terrain, and Psychic type during Psychic Terrain. Fails if the user's type cannot be changed or if the user is already purely that type.",
        shortDesc=r"Changes user's type by terrain (default Normal).",
        name=r"Camouflage",
        pp=20,
    )
    CAPTIVATE = Move(
        desc=r"Lowers the target's Special Attack by 2 stages. The target is unaffected if both the user and the target are the same gender, or if either is genderless. Pokemon with the Oblivious Ability are immune.",
        shortDesc=r"Lowers the foe(s) Sp. Atk by 2 if opposite gender.",
        accuracy=100,
        name=r"Captivate",
        pp=20,
    )
    CELEBRATE = Move(
        desc=r"No competitive use.",
        shortDesc=r"No competitive use.",
        name=r"Celebrate",
        pp=40,
    )
    CHARGE = Move(
        desc=r"Raises the user's Special Defense by 1 stage. If the user uses an Electric-type attack on the next turn, its power will be doubled.",
        shortDesc=r"+1 SpD, user's Electric move next turn 2x power.",
        name=r"Charge",
        pp=20,
        type=Types.ELECTRIC,
    )
    CHARGEBEAM = Move(
        desc=r"Has a 70% chance to raise the user's Special Attack by 1 stage.",
        shortDesc=r"70% chance to raise the user's Sp. Atk by 1.",
        accuracy=9,
        base=50,
        category=Category.SPECIAL,
        name=r"Charge Beam",
        pp=10,
        type=Types.ELECTRIC,
    )
    CHARM = Move(
        desc=r"Lowers the target's Attack by 2 stages.",
        shortDesc=r"Lowers the target's Attack by 2.",
        accuracy=100,
        name=r"Charm",
        pp=20,
        type=Types.FAIRY,
    )
    CHATTER = Move(
        desc=r"Has a 100% chance to confuse the target.",
        shortDesc=r"100% chance to confuse the target.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Chatter",
        pp=20,
        type=Types.FLYING,
    )
    CHIPAWAY = Move(
        desc=r"Ignores the target's stat stage changes, including evasiveness.",
        shortDesc=r"Ignores the target's stat stage changes.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Chip Away",
        pp=20,
    )
    CIRCLETHROW = Move(
        desc=r"If both the user and the target have not fainted, the target is forced to switch out and be replaced with a random unfainted ally. This effect fails if the target is under the effect of Ingrain, has the Suction Cups Ability, or this move hit a substitute.",
        shortDesc=r"Forces the target to switch to a random ally.",
        accuracy=9,
        base=60,
        category=Category.PHYSICAL,
        name=r"Circle Throw",
        pp=10,
        type=Types.FIGHTING,
    )
    CLAMP = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=85,
        base=35,
        category=Category.PHYSICAL,
        name=r"Clamp",
        pp=15,
        type=Types.WATER,
    )
    CLANGINGSCALES = Move(
        desc=r"Lowers the user's Defense by 1 stage.",
        shortDesc=r"Lowers the user's Defense by 1.",
        accuracy=100,
        base=110,
        category=Category.SPECIAL,
        name=r"Clanging Scales",
        pp=5,
        type=Types.DRAGON,
    )
    CLANGOROUSSOUL = Move(
        desc=r"Raises the user's Attack, Defense, Special Attack, Special Defense, and Speed by 1 stage in exchange for the user losing 33% of its maximum HP, rounded down. Fails if the user would faint or if its Attack, Defense, Special Attack, Special Defense, and Speed stat stages would not change.",
        shortDesc=r"User loses 33% of its max HP. +1 to all stats.",
        name=r"Clangorous Soul",
        pp=5,
        type=Types.DRAGON,
    )
    CLEARSMOG = Move(
        desc=r"Resets all of the target's stat stages to 0.",
        shortDesc=r"Resets all of the target's stat stages to 0.",
        base=50,
        category=Category.SPECIAL,
        name=r"Clear Smog",
        pp=15,
        type=Types.POISON,
    )
    CLOSECOMBAT = Move(
        desc=r"Lowers the user's Defense and Special Defense by 1 stage.",
        shortDesc=r"Lowers the user's Defense and Sp. Def by 1.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Close Combat",
        pp=5,
        type=Types.FIGHTING,
    )
    COACHING = Move(
        desc=r"Raises the target's Attack and Defense by 1 stage. Fails if there is no ally adjacent to the user.",
        shortDesc=r"Raises an ally's Attack and Defense by 1.",
        name=r"Coaching",
        pp=10,
        type=Types.FIGHTING,
    )
    COIL = Move(
        desc=r"Raises the user's Attack, Defense, and accuracy by 1 stage.",
        shortDesc=r"Raises user's Attack, Defense, accuracy by 1.",
        name=r"Coil",
        pp=20,
        type=Types.POISON,
    )
    COMETPUNCH = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=85,
        base=18,
        category=Category.PHYSICAL,
        name=r"Comet Punch",
        pp=15,
    )
    CONFIDE = Move(
        desc=r"Lowers the target's Special Attack by 1 stage.",
        shortDesc=r"Lowers the target's Sp. Atk by 1.",
        name=r"Confide",
        pp=20,
    )
    CONFUSERAY = Move(
        desc=r"Causes the target to become confused.",
        shortDesc=r"Confuses the target.",
        accuracy=100,
        name=r"Confuse Ray",
        pp=10,
        type=Types.GHOST,
    )
    CONFUSION = Move(
        desc=r"Has a 10% chance to confuse the target.",
        shortDesc=r"10% chance to confuse the target.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Confusion",
        pp=25,
        type=Types.PSYCHIC,
    )
    CONSTRICT = Move(
        desc=r"Has a 10% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"10% chance to lower the target's Speed by 1.",
        accuracy=100,
        base=10,
        category=Category.PHYSICAL,
        name=r"Constrict",
        pp=35,
    )
    CONVERSION = Move(
        desc=r"The user's type changes to match the original type of the move in its first move slot. Fails if the user cannot change its type, or if the type is one of the user's current types.",
        shortDesc=r"Changes user's type to match its first move.",
        name=r"Conversion",
        pp=30,
    )
    CONVERSION2 = Move(
        desc=r"The user's type changes to match a type that resists or is immune to the type of the last move used by the target, but not either of its current types. The determined type of the move is used rather than the original type. Fails if the target has not made a move, if the user cannot change its type, or if this move would only be able to select one of the user's current types.",
        shortDesc=r"Changes user's type to resist target's last move.",
        name=r"Conversion 2",
        pp=30,
    )
    COPYCAT = Move(
        desc=r"The user uses the last move used by any Pokemon, including itself. The base move of Max and G-Max Moves is considered for this purpose. Fails if no move has been used, or if the last move used was Assist, Baneful Bunker, Beak Blast, Belch, Bestow, Celebrate, Chatter, Circle Throw, Copycat, Counter, Covet, Crafty Shield, Destiny Bond, Detect, Dragon Tail, Dynamax Cannon, Endure, Feint, Focus Punch, Follow Me, Helping Hand, Hold Hands, King's Shield, Mat Block, Me First, Metronome, Mimic, Mirror Coat, Mirror Move, Nature Power, Obstruct, Protect, Rage Powder, Roar, Shell Trap, Sketch, Sleep Talk, Snatch, Spiky Shield, Spotlight, Struggle, Switcheroo, Thief, Transform, Trick, or Whirlwind.",
        shortDesc=r"Uses the last move used in the battle.",
        name=r"Copycat",
        pp=20,
    )
    COREENFORCER = Move(
        desc=r"If the user moves after the target, the target's Ability is rendered ineffective as long as it remains active. If the target uses Baton Pass, the replacement will remain under this effect. If the target's Ability is Battle Bond, Comatose, Disguise, Multitype, Power Construct, RKS System, Schooling, Shields Down, Stance Change, or Zen Mode, this effect does not happen, and receiving the effect through Baton Pass ends the effect immediately.",
        shortDesc=r"Nullifies the foe(s) Ability if the foe(s) move first.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Core Enforcer",
        pp=10,
        type=Types.DRAGON,
    )
    CORROSIVEGAS = Move(
        desc=r"The target loses its held item. This move cannot cause Pokemon with the Sticky Hold Ability to lose their held item or cause a Kyogre, a Groudon, a Giratina, an Arceus, a Genesect, a Silvally, a Zacian, or a Zamazenta to lose their Blue Orb, Red Orb, Griseous Orb, Plate, Drive, Memory, Rusted Sword, or Rusted Shield respectively. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"Removes adjacent Pokemon's held items.",
        accuracy=100,
        name=r"Corrosive Gas",
        pp=40,
        type=Types.POISON,
    )
    COSMICPOWER = Move(
        desc=r"Raises the user's Defense and Special Defense by 1 stage.",
        shortDesc=r"Raises the user's Defense and Sp. Def by 1.",
        name=r"Cosmic Power",
        pp=20,
        type=Types.PSYCHIC,
    )
    COTTONGUARD = Move(
        desc=r"Raises the user's Defense by 3 stages.",
        shortDesc=r"Raises the user's Defense by 3.",
        name=r"Cotton Guard",
        pp=10,
        type=Types.GRASS,
    )
    COTTONSPORE = Move(
        desc=r"Lowers the target's Speed by 2 stages.",
        shortDesc=r"Lowers the target's Speed by 2.",
        accuracy=100,
        name=r"Cotton Spore",
        pp=40,
        type=Types.GRASS,
    )
    COUNTER = Move(
        desc=r"Deals damage to the last opposing Pokemon to hit the user with a physical attack this turn equal to twice the HP lost by the user from that attack. If the user did not lose HP from the attack, this move deals 1 HP of damage instead. If that opposing Pokemon's position is no longer in use and there is another opposing Pokemon on the field, the damage is done to it instead. Only the last hit of a multi-hit attack is counted. Fails if the user was not hit by an opposing Pokemon's physical attack this turn.",
        shortDesc=r"If hit by physical attack, returns double damage.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Counter",
        pp=20,
        type=Types.FIGHTING,
    )
    COURTCHANGE = Move(
        desc=r"Switches the Mist, Light Screen, Reflect, Spikes, Safeguard, Tailwind, Toxic Spikes, Stealth Rock, Water Pledge, Fire Pledge, Grass Pledge, Sticky Web, Aurora Veil, G-Max Steelsurge, G-Max Cannonade, G-Max Vine Lash, and G-Max Wildfire effects from the user's side to the opposing side and vice versa.",
        shortDesc=r"Swaps user's field effects with the opposing side.",
        accuracy=100,
        name=r"Court Change",
        pp=10,
    )
    COVET = Move(
        desc=r"If this attack was successful and the user has not fainted, it steals the target's held item if the user is not holding one. The target's item is not stolen if it is a Mail or Z-Crystal, or if the target is a Kyogre holding a Blue Orb, a Groudon holding a Red Orb, a Giratina holding a Griseous Orb, an Arceus holding a Plate, a Genesect holding a Drive, a Silvally holding a Memory, or a Pokemon that can Mega Evolve holding the Mega Stone for its species. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"If the user has no item, it steals the target's.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Covet",
        pp=25,
    )
    CRABHAMMER = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=9,
        base=100,
        category=Category.PHYSICAL,
        name=r"Crabhammer",
        pp=10,
        type=Types.WATER,
    )
    CRAFTYSHIELD = Move(
        desc=r"The user and its party members are protected from non-damaging attacks made by other Pokemon, including allies, during this turn. Fails if the user moves last this turn or if this move is already in effect for the user's side.",
        shortDesc=r"Protects allies from Status moves this turn.",
        name=r"Crafty Shield",
        pp=10,
        type=Types.FAIRY,
    )
    CROSSCHOP = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=8,
        base=100,
        category=Category.PHYSICAL,
        name=r"Cross Chop",
        pp=5,
        type=Types.FIGHTING,
    )
    CROSSPOISON = Move(
        desc=r"Has a 10% chance to poison the target and a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio. 10% chance to poison.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Cross Poison",
        pp=20,
        type=Types.POISON,
    )
    CRUNCH = Move(
        desc=r"Has a 20% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"20% chance to lower the target's Defense by 1.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Crunch",
        pp=15,
        type=Types.DARK,
    )
    CRUSHCLAW = Move(
        desc=r"Has a 50% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"50% chance to lower the target's Defense by 1.",
        accuracy=95,
        base=75,
        category=Category.PHYSICAL,
        name=r"Crush Claw",
        pp=10,
    )
    CRUSHGRIP = Move(
        desc=r"Power is equal to 120 * (target's current HP / target's maximum HP) rounded half down, but not less than 1.",
        shortDesc=r"More power the more HP the target has left.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Crush Grip",
        pp=5,
    )
    CURSE = Move(
        desc=r"If the user is not a Ghost type, lowers the user's Speed by 1 stage and raises the user's Attack and Defense by 1 stage. If the user is a Ghost type, the user loses 1/2 of its maximum HP, rounded down and even if it would cause fainting, in exchange for the target losing 1/4 of its maximum HP, rounded down, at the end of each turn while it is active. If the target uses Baton Pass, the replacement will continue to be affected. Fails if there is no target or if the target is already affected.",
        shortDesc=r"Curses if Ghost, else -1 Spe, +1 Atk, +1 Def.",
        name=r"Curse",
        pp=10,
        type=Types.GHOST,
    )
    CUT = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=95,
        base=50,
        category=Category.PHYSICAL,
        name=r"Cut",
        pp=30,
    )
    DARKESTLARIAT = Move(
        desc=r"Ignores the target's stat stage changes, including evasiveness.",
        shortDesc=r"Ignores the target's stat stage changes.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Darkest Lariat",
        pp=10,
        type=Types.DARK,
    )
    DARKPULSE = Move(
        desc=r"Has a 20% chance to flinch the target.",
        shortDesc=r"20% chance to flinch the target.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Dark Pulse",
        pp=15,
        type=Types.DARK,
    )
    DARKVOID = Move(
        desc=r"Causes the target to fall asleep. This move cannot be used successfully unless the user's current form, while considering Transform, is Darkrai.",
        shortDesc=r"Darkrai: Causes the foe(s) to fall asleep.",
        accuracy=5,
        name=r"Dark Void",
        pp=10,
        type=Types.DARK,
    )
    DAZZLINGGLEAM = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent foes.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Dazzling Gleam",
        pp=10,
        type=Types.FAIRY,
    )
    DECORATE = Move(
        desc=r"Raises the target's Attack and Special Attack by 2 stages.",
        shortDesc=r"Raises the target's Attack and Sp. Atk by 2.",
        name=r"Decorate",
        pp=15,
        type=Types.FAIRY,
    )
    DEFENDORDER = Move(
        desc=r"Raises the user's Defense and Special Defense by 1 stage.",
        shortDesc=r"Raises the user's Defense and Sp. Def by 1.",
        name=r"Defend Order",
        pp=10,
        type=Types.BUG,
    )
    DEFENSECURL = Move(
        desc=r"Raises the user's Defense by 1 stage. As long as the user remains active, the power of the user's Ice Ball and Rollout will be doubled (this effect is not stackable).",
        shortDesc=r"Raises the user's Defense by 1.",
        name=r"Defense Curl",
        pp=40,
    )
    DEFOG = Move(
        desc=r"Lowers the target's evasiveness by 1 stage. If this move is successful and whether or not the target's evasiveness was affected, the effects of Reflect, Light Screen, Aurora Veil, Safeguard, Mist, Spikes, Toxic Spikes, Stealth Rock, and Sticky Web end for the target's side, and the effects of Spikes, Toxic Spikes, Stealth Rock, and Sticky Web end for the user's side. Ignores a target's substitute, although a substitute will still block the lowering of evasiveness. If there is a terrain active and this move is successful, the terrain will be cleared.",
        shortDesc=r"-1 evasion; clears terrain and hazards on both sides.",
        name=r"Defog",
        pp=15,
        type=Types.FLYING,
    )
    DESTINYBOND = Move(
        desc=r"Until the user's next move, if an opposing Pokemon's attack knocks the user out, that Pokemon faints as well, unless the attack was Doom Desire or Future Sight. Fails if the user used this move successfully as its last move, disregarding moves used through the Dancer Ability.",
        shortDesc=r"If an opponent knocks out the user, it also faints.",
        name=r"Destiny Bond",
        pp=5,
        type=Types.GHOST,
    )
    DETECT = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Prevents moves from affecting the user this turn.",
        name=r"Detect",
        pp=5,
        type=Types.FIGHTING,
    )
    DIAMONDSTORM = Move(
        desc=r"Has a 50% chance to raise the user's Defense by 2 stages.",
        shortDesc=r"50% chance to raise user's Def by 2 for each hit.",
        accuracy=95,
        base=100,
        category=Category.PHYSICAL,
        name=r"Diamond Storm",
        pp=5,
        type=Types.ROCK,
    )
    DIG = Move(
        desc=r"This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks other than Earthquake and Magnitude but takes double damage from them, and is also unaffected by weather. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Digs underground turn 1, strikes turn 2.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Dig",
        pp=10,
        type=Types.GROUND,
    )
    DISABLE = Move(
        desc=r"For 4 turns, the target's last move used becomes disabled. Fails if one of the target's moves is already disabled, if the target has not made a move, if the target no longer knows the move, or if the move was a Max or G-Max Move.",
        shortDesc=r"For 4 turns, disables the target's last move used.",
        accuracy=100,
        name=r"Disable",
        pp=20,
    )
    DISARMINGVOICE = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy. Hits foes.",
        base=40,
        category=Category.SPECIAL,
        name=r"Disarming Voice",
        pp=15,
        type=Types.FAIRY,
    )
    DISCHARGE = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze adjacent Pokemon.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Discharge",
        pp=15,
        type=Types.ELECTRIC,
    )
    DIVE = Move(
        desc=r"This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks other than Surf and Whirlpool but takes double damage from them, and is also unaffected by weather. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Dives underwater turn 1, strikes turn 2.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Dive",
        pp=10,
        type=Types.WATER,
    )
    DIZZYPUNCH = Move(
        desc=r"Has a 20% chance to confuse the target.",
        shortDesc=r"20% chance to confuse the target.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Dizzy Punch",
        pp=10,
    )
    DOOMDESIRE = Move(
        desc=r"Deals damage two turns after this move is used. At the end of that turn, the damage is calculated at that time and dealt to the Pokemon at the position the target had when the move was used. If the user is no longer active at the time, damage is calculated based on the user's natural Special Attack stat, types, and level, with no boosts from its held item or Ability. Fails if this move or Future Sight is already in effect for the target's position.",
        shortDesc=r"Hits two turns after being used.",
        accuracy=100,
        base=140,
        category=Category.SPECIAL,
        name=r"Doom Desire",
        pp=5,
        type=Types.STEEL,
    )
    DOUBLEEDGE = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 33% the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 33% recoil.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Double-Edge",
        pp=15,
    )
    DOUBLEHIT = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=9,
        base=35,
        category=Category.PHYSICAL,
        name=r"Double Hit",
        pp=10,
    )
    DOUBLEIRONBASH = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit. Has a 30% chance to flinch the target.",
        shortDesc=r"Hits twice. 30% chance to flinch.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Double Iron Bash",
        pp=5,
        type=Types.STEEL,
    )
    DOUBLEKICK = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=100,
        base=30,
        category=Category.PHYSICAL,
        name=r"Double Kick",
        pp=30,
        type=Types.FIGHTING,
    )
    DOUBLESLAP = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=85,
        base=15,
        category=Category.PHYSICAL,
        name=r"Double Slap",
        pp=10,
    )
    DOUBLETEAM = Move(
        desc=r"Raises the user's evasiveness by 1 stage.",
        shortDesc=r"Raises the user's evasiveness by 1.",
        name=r"Double Team",
        pp=15,
    )
    DRACOMETEOR = Move(
        desc=r"Lowers the user's Special Attack by 2 stages.",
        shortDesc=r"Lowers the user's Sp. Atk by 2.",
        accuracy=9,
        base=130,
        category=Category.SPECIAL,
        name=r"Draco Meteor",
        pp=5,
        type=Types.DRAGON,
    )
    DRAGONASCENT = Move(
        desc=r"Lowers the user's Defense and Special Defense by 1 stage.",
        shortDesc=r"Lowers the user's Defense and Sp. Def by 1.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Dragon Ascent",
        pp=5,
        type=Types.FLYING,
    )
    DRAGONBREATH = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Dragon Breath",
        pp=20,
        type=Types.DRAGON,
    )
    DRAGONCLAW = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Dragon Claw",
        pp=15,
        type=Types.DRAGON,
    )
    DRAGONDANCE = Move(
        desc=r"Raises the user's Attack and Speed by 1 stage.",
        shortDesc=r"Raises the user's Attack and Speed by 1.",
        name=r"Dragon Dance",
        pp=20,
        type=Types.DRAGON,
    )
    DRAGONDARTS = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit. In Double Battles, this move attempts to hit the targeted Pokemon and its ally once each. If hitting one of these Pokemon would be prevented by immunity, protection, semi-invulnerability, an Ability, or accuracy, it attempts to hit the other Pokemon twice instead. If this move is redirected, it hits that target twice.",
        shortDesc=r"Hits twice. Doubles: Tries to hit each foe once.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Dragon Darts",
        pp=10,
        type=Types.DRAGON,
    )
    DRAGONENERGY = Move(
        desc=r"Dragon Energy does damage proportionately based on the user's HP. This move's base power reduces as the user's HP reduces and is calculated by the formula: 150 x HP/Max_HP.",
        shortDesc=r"Converting its life-force into power, the user attacks opposing Pokémon. The lower the user's HP, the lower the move's power.",
        accuracy=100,
        base=150,
        category=Category.SPECIAL,
        name=r"Dragon Energy",
        pp=5,
        type=Types.DRAGON,
    )
    DRAGONHAMMER = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Dragon Hammer",
        pp=15,
        type=Types.DRAGON,
    )
    DRAGONPULSE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=85,
        category=Category.SPECIAL,
        name=r"Dragon Pulse",
        pp=10,
        type=Types.DRAGON,
    )
    DRAGONRAGE = Move(
        desc=r"Deals 40 HP of damage to the target.",
        shortDesc=r"Deals 40 HP of damage to the target.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Dragon Rage",
        pp=10,
        type=Types.DRAGON,
    )
    DRAGONRUSH = Move(
        desc=r"Has a 20% chance to flinch the target. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"20% chance to flinch the target.",
        accuracy=75,
        base=100,
        category=Category.PHYSICAL,
        name=r"Dragon Rush",
        pp=10,
        type=Types.DRAGON,
    )
    DRAGONTAIL = Move(
        desc=r"If both the user and the target have not fainted, the target is forced to switch out and be replaced with a random unfainted ally. This effect fails if the target used Ingrain previously, has the Suction Cups Ability, or this move hit a substitute.",
        shortDesc=r"Forces the target to switch to a random ally.",
        accuracy=9,
        base=60,
        category=Category.PHYSICAL,
        name=r"Dragon Tail",
        pp=10,
        type=Types.DRAGON,
    )
    DRAININGKISS = Move(
        desc=r"The user recovers 3/4 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 75% of the damage dealt.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Draining Kiss",
        pp=10,
        type=Types.FAIRY,
    )
    DRAINPUNCH = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Drain Punch",
        pp=10,
        type=Types.FIGHTING,
    )
    DREAMEATER = Move(
        desc=r"The target is unaffected by this move unless it is asleep. The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User gains 1/2 HP inflicted. Sleeping target only.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Dream Eater",
        pp=15,
        type=Types.PSYCHIC,
    )
    DRILLPECK = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Drill Peck",
        pp=20,
        type=Types.FLYING,
    )
    DRILLRUN = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=95,
        base=80,
        category=Category.PHYSICAL,
        name=r"Drill Run",
        pp=10,
        type=Types.GROUND,
    )
    DRUMBEATING = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the target's Speed by 1.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Drum Beating",
        pp=10,
        type=Types.GRASS,
    )
    DUALCHOP = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=9,
        base=40,
        category=Category.PHYSICAL,
        name=r"Dual Chop",
        pp=15,
        type=Types.DRAGON,
    )
    DUALWINGBEAT = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=9,
        base=40,
        category=Category.PHYSICAL,
        name=r"Dual Wingbeat",
        pp=10,
        type=Types.FLYING,
    )
    DYNAMAXCANNON = Move(
        desc=r"Damage doubles if the target is Dynamaxed.",
        shortDesc=r"Damage doubles if the target is Dynamaxed.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Dynamax Cannon",
        pp=5,
        type=Types.DRAGON,
    )
    DYNAMICPUNCH = Move(
        desc=r"Has a 100% chance to confuse the target.",
        shortDesc=r"100% chance to confuse the target.",
        accuracy=5,
        base=100,
        category=Category.PHYSICAL,
        name=r"Dynamic Punch",
        pp=5,
        type=Types.FIGHTING,
    )
    EARTHPOWER = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Earth Power",
        pp=10,
        type=Types.GROUND,
    )
    EARTHQUAKE = Move(
        desc=r"Damage doubles if the target is using Dig.",
        shortDesc=r"Hits adjacent Pokemon. Double damage on Dig.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Earthquake",
        pp=10,
        type=Types.GROUND,
    )
    ECHOEDVOICE = Move(
        desc=r"For every consecutive turn that this move is used by at least one Pokemon, this move's power is multiplied by the number of turns to pass, but not more than 5.",
        shortDesc=r"Power increases when used on consecutive turns.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Echoed Voice",
        pp=15,
    )
    EERIEIMPULSE = Move(
        desc=r"Lowers the target's Special Attack by 2 stages.",
        shortDesc=r"Lowers the target's Sp. Atk by 2.",
        accuracy=100,
        name=r"Eerie Impulse",
        pp=15,
        type=Types.ELECTRIC,
    )
    EERIESPELL = Move(
        desc=r"Eerie Spell deals damage and decreases the PP of the last move the target used by 3. Pokémon with the Ability Soundproof are not affected by this move.",
        shortDesc=r"The user attacks with its tremendous psychic power. This also removes 3 PP from the target's last move.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Eerie Spell",
        pp=5,
        type=Types.PSYCHIC,
    )
    EGGBOMB = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=75,
        base=100,
        category=Category.PHYSICAL,
        name=r"Egg Bomb",
        pp=10,
    )
    ELECTRICTERRAIN = Move(
        desc=r"For 5 turns, the terrain becomes Electric Terrain. During the effect, the power of Electric-type attacks made by grounded Pokemon is multiplied by 1.3 and grounded Pokemon cannot fall asleep; Pokemon already asleep do not wake up. Camouflage transforms the user into an Electric type, Nature Power becomes Thunderbolt, and Secret Power has a 30% chance to cause paralysis. Fails if the current terrain is Electric Terrain.",
        shortDesc=r"5 turns. Grounded: +Electric power, can't sleep.",
        name=r"Electric Terrain",
        pp=10,
        type=Types.ELECTRIC,
    )
    ELECTRIFY = Move(
        desc=r"Causes the target's move to become Electric type this turn. Among effects that can change a move's type, this effect happens last. Fails if the target already moved this turn.",
        shortDesc=r"Changes the target's move to Electric this turn.",
        name=r"Electrify",
        pp=20,
        type=Types.ELECTRIC,
    )
    ELECTROBALL = Move(
        desc=r"The power of this move depends on (user's current Speed / target's current Speed) rounded down. Power is equal to 150 if the result is 4 or more, 120 if 3, 80 if 2, 60 if 1, 40 if less than 1. If the target's current Speed is 0, this move's power is 40.",
        shortDesc=r"More power the faster the user is than the target.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Electro Ball",
        pp=10,
        type=Types.ELECTRIC,
    )
    ELECTROWEB = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Speed by 1.",
        accuracy=95,
        base=55,
        category=Category.SPECIAL,
        name=r"Electroweb",
        pp=15,
        type=Types.ELECTRIC,
    )
    EMBARGO = Move(
        desc=r"For 5 turns, the target's held item has no effect. An item's effect of causing forme changes is unaffected, but any other effects from such items are negated. During the effect, Fling and Natural Gift are prevented from being used by the target. Items thrown at the target with Fling will still activate for it. If the target uses Baton Pass, the replacement will remain unable to use items.",
        shortDesc=r"For 5 turns, the target's item has no effect.",
        accuracy=100,
        name=r"Embargo",
        pp=15,
        type=Types.DARK,
    )
    EMBER = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Ember",
        pp=25,
        type=Types.FIRE,
    )
    ENCORE = Move(
        desc=r"For its next 3 turns, the target is forced to repeat its last move used. If the affected move runs out of PP, the effect ends. Fails if the target is already under this effect, if it has not made a move, if the move has 0 PP, if the move is Assist, Copycat, Encore, Me First, Metronome, Mimic, Mirror Move, Nature Power, Sketch, Sleep Talk, Struggle, or Transform, or if the target is Dynamaxed.",
        shortDesc=r"Target repeats its last move for its next 3 turns.",
        accuracy=100,
        name=r"Encore",
        pp=5,
    )
    ENDEAVOR = Move(
        desc=r"Deals damage to the target equal to (target's current HP - user's current HP). The target is unaffected if its current HP is less than or equal to the user's current HP.",
        shortDesc=r"Lowers the target's HP to the user's HP.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Endeavor",
        pp=5,
    )
    ENDURE = Move(
        desc=r"The user will survive attacks made by other Pokemon during this turn with at least 1 HP. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"User survives attacks this turn with at least 1 HP.",
        name=r"Endure",
        pp=10,
    )
    ENERGYBALL = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Energy Ball",
        pp=10,
        type=Types.GRASS,
    )
    ENTRAINMENT = Move(
        desc=r"Causes the target's Ability to become the same as the user's. Fails if the target's Ability is Battle Bond, Comatose, Disguise, Multitype, Power Construct, RKS System, Schooling, Shields Down, Stance Change, Truant, or the same Ability as the user, or if the user's Ability is Battle Bond, Comatose, Disguise, Flower Gift, Forecast, Illusion, Imposter, Multitype, Neutralizing Gas, Power Construct, Power of Alchemy, Receiver, RKS System, Schooling, Shields Down, Stance Change, Trace, or Zen Mode.",
        shortDesc=r"The target's Ability changes to match the user's.",
        accuracy=100,
        name=r"Entrainment",
        pp=15,
    )
    ERUPTION = Move(
        desc=r"Power is equal to (user's current HP * 150 / user's maximum HP) rounded down, but not less than 1.",
        shortDesc=r"Less power as user's HP decreases. Hits foe(s).",
        accuracy=100,
        base=150,
        category=Category.SPECIAL,
        name=r"Eruption",
        pp=5,
        type=Types.FIRE,
    )
    ETERNABEAM = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=160,
        category=Category.SPECIAL,
        name=r"Eternabeam",
        pp=10,
        type=Types.DRAGON,
    )
    EXPANDINGFORCE = Move(
        desc=r"If the current terrain is Psychic Terrain and the user is grounded, this move hits all opposing Pokemon and has its power multiplied by 1.5.",
        shortDesc=r"User on Psychic Terrain: 1.5x power, hits foes.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Expanding Force",
        pp=10,
        type=Types.PSYCHIC,
    )
    EXPLOSION = Move(
        desc=r"The user faints after using this move, even if this move fails for having no target. This move is prevented from executing if any active Pokemon has the Damp Ability.",
        shortDesc=r"Hits adjacent Pokemon. The user faints.",
        accuracy=100,
        base=250,
        category=Category.PHYSICAL,
        name=r"Explosion",
        pp=5,
    )
    EXTRASENSORY = Move(
        desc=r"Has a 10% chance to flinch the target.",
        shortDesc=r"10% chance to flinch the target.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Extrasensory",
        pp=20,
        type=Types.PSYCHIC,
    )
    EXTREMESPEED = Move(
        desc=r"No additional effect.",
        shortDesc=r"Nearly always goes first.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Extreme Speed",
        pp=5,
    )
    FACADE = Move(
        desc=r"Power doubles if the user is burned, paralyzed, or poisoned. The physical damage halving effect from the user's burn is ignored.",
        shortDesc=r"Power doubles if user is burn/poison/paralyzed.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Facade",
        pp=20,
    )
    FAIRYLOCK = Move(
        desc=r"Prevents all active Pokemon from switching next turn. A Pokemon can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. Fails if the effect is already active.",
        shortDesc=r"Prevents all Pokemon from switching next turn.",
        name=r"Fairy Lock",
        pp=10,
        type=Types.FAIRY,
    )
    FAIRYWIND = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Fairy Wind",
        pp=30,
        type=Types.FAIRY,
    )
    FAKEOUT = Move(
        desc=r"Has a 100% chance to flinch the target. Fails unless it is the user's first turn on the field.",
        shortDesc=r"Hits first. First turn out only. 100% flinch chance.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Fake Out",
        pp=10,
    )
    FAKETEARS = Move(
        desc=r"Lowers the target's Special Defense by 2 stages.",
        shortDesc=r"Lowers the target's Sp. Def by 2.",
        accuracy=100,
        name=r"Fake Tears",
        pp=20,
        type=Types.DARK,
    )
    FALSESURRENDER = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=80,
        category=Category.PHYSICAL,
        name=r"False Surrender",
        pp=10,
        type=Types.DARK,
    )
    FALSESWIPE = Move(
        desc=r"Leaves the target with at least 1 HP.",
        shortDesc=r"Always leaves the target with at least 1 HP.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"False Swipe",
        pp=40,
    )
    FEATHERDANCE = Move(
        desc=r"Lowers the target's Attack by 2 stages.",
        shortDesc=r"Lowers the target's Attack by 2.",
        accuracy=100,
        name=r"Feather Dance",
        pp=15,
        type=Types.FLYING,
    )
    FEINT = Move(
        desc=r"If this move is successful, it breaks through the target's Baneful Bunker, Detect, King's Shield, Protect, or Spiky Shield for this turn, allowing other Pokemon to attack the target normally. If the target's side is protected by Crafty Shield, Mat Block, Quick Guard, or Wide Guard, that protection is also broken for this turn and other Pokemon may attack the target's side normally.",
        shortDesc=r"Nullifies Detect, Protect, and Quick/Wide Guard.",
        accuracy=100,
        base=30,
        category=Category.PHYSICAL,
        name=r"Feint",
        pp=10,
    )
    FEINTATTACK = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.PHYSICAL,
        name=r"Feint Attack",
        pp=20,
        type=Types.DARK,
    )
    FELLSTINGER = Move(
        desc=r"Raises the user's Attack by 3 stages if this move knocks out the target.",
        shortDesc=r"Raises user's Attack by 3 if this KOes the target.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Fell Stinger",
        pp=25,
        type=Types.BUG,
    )
    FIERYDANCE = Move(
        desc=r"Has a 50% chance to raise the user's Special Attack by 1 stage.",
        shortDesc=r"50% chance to raise the user's Sp. Atk by 1.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Fiery Dance",
        pp=10,
        type=Types.FIRE,
    )
    FIERYWRATH = Move(
        desc=r"The user transforms its wrath into a fire-like aura to attack. This may also make opposing Pokémon flinch.",
        shortDesc=r"None",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Fiery Wrath",
        pp=10,
        type=Types.DARK,
    )
    FINALGAMBIT = Move(
        desc=r"Deals damage to the target equal to the user's current HP. If this move is successful, the user faints.",
        shortDesc=r"Does damage equal to the user's HP. User faints.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Final Gambit",
        pp=5,
        type=Types.FIGHTING,
    )
    FIREBLAST = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target.",
        accuracy=85,
        base=110,
        category=Category.SPECIAL,
        name=r"Fire Blast",
        pp=5,
        type=Types.FIRE,
    )
    FIREFANG = Move(
        desc=r"Has a 10% chance to burn the target and a 10% chance to flinch it.",
        shortDesc=r"10% chance to burn. 10% chance to flinch.",
        accuracy=95,
        base=65,
        category=Category.PHYSICAL,
        name=r"Fire Fang",
        pp=15,
        type=Types.FIRE,
    )
    FIRELASH = Move(
        desc=r"Has a 100% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"100% chance to lower the target's Defense by 1.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Fire Lash",
        pp=15,
        type=Types.FIRE,
    )
    FIREPLEDGE = Move(
        desc=r"If one of the user's allies chose to use Grass Pledge or Water Pledge this turn and has not moved yet, it takes its turn immediately after the user and the user's move does nothing. If combined with Grass Pledge, the ally uses Fire Pledge with 150 power and a sea of fire appears on the target's side for 4 turns, which causes damage to non-Fire types equal to 1/8 of their maximum HP, rounded down, at the end of each turn during effect, including the last turn. If combined with Water Pledge, the ally uses Water Pledge with 150 power and a rainbow appears on the user's side for 4 turns, which doubles secondary effect chances but does not stack with the Serene Grace Ability. When used as a combined move, this move gains STAB no matter what the user's type is. This move does not consume the user's Fire Gem.",
        shortDesc=r"Use with Grass or Water Pledge for added effect.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Fire Pledge",
        pp=10,
        type=Types.FIRE,
    )
    FIREPUNCH = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Fire Punch",
        pp=15,
        type=Types.FIRE,
    )
    FIRESPIN = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=85,
        base=35,
        category=Category.SPECIAL,
        name=r"Fire Spin",
        pp=15,
        type=Types.FIRE,
    )
    FIRSTIMPRESSION = Move(
        desc=r"Fails unless it is the user's first turn on the field.",
        shortDesc=r"Hits first. First turn out only.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"First Impression",
        pp=10,
        type=Types.BUG,
    )
    FISHIOUSREND = Move(
        desc=r"Power doubles if the user moves before the target.",
        shortDesc=r"Power doubles if user moves before the target.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Fishious Rend",
        pp=10,
        type=Types.WATER,
    )
    FISSURE = Move(
        desc=r"Deals damage to the target equal to the target's maximum HP. Ignores accuracy and evasiveness modifiers. This attack's accuracy is equal to (user's level - target's level + 30)%, and fails if the target is at a higher level. Pokemon with the Sturdy Ability are immune.",
        shortDesc=r"OHKOs the target. Fails if user is a lower level.",
        accuracy=3,
        category=Category.PHYSICAL,
        name=r"Fissure",
        pp=5,
        type=Types.GROUND,
    )
    FLAIL = Move(
        desc=r"The power of this move is 20 if X is 33 to 48, 40 if X is 17 to 32, 80 if X is 10 to 16, 100 if X is 5 to 9, 150 if X is 2 to 4, and 200 if X is 0 or 1, where X is equal to (user's current HP * 48 / user's maximum HP) rounded down.",
        shortDesc=r"More power the less HP the user has left.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Flail",
        pp=15,
    )
    FLAMEBURST = Move(
        desc=r"If this move is successful, the target's ally loses 1/16 of its maximum HP, rounded down, unless it has the Magic Guard Ability.",
        shortDesc=r"Damages Pokemon next to the target as well.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Flame Burst",
        pp=15,
        type=Types.FIRE,
    )
    FLAMECHARGE = Move(
        desc=r"Has a 100% chance to raise the user's Speed by 1 stage.",
        shortDesc=r"100% chance to raise the user's Speed by 1.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Flame Charge",
        pp=20,
        type=Types.FIRE,
    )
    FLAMEWHEEL = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target. Thaws user.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Flame Wheel",
        pp=25,
        type=Types.FIRE,
    )
    FLAMETHROWER = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Flamethrower",
        pp=15,
        type=Types.FIRE,
    )
    FLAREBLITZ = Move(
        desc=r"Has a 10% chance to burn the target. If the target lost HP, the user takes recoil damage equal to 33% the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 33% recoil. 10% chance to burn. Thaws user.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Flare Blitz",
        pp=15,
        type=Types.FIRE,
    )
    FLASH = Move(
        desc=r"Lowers the target's accuracy by 1 stage.",
        shortDesc=r"Lowers the target's accuracy by 1.",
        accuracy=100,
        name=r"Flash",
        pp=20,
    )
    FLASHCANNON = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Flash Cannon",
        pp=10,
        type=Types.STEEL,
    )
    FLATTER = Move(
        desc=r"Raises the target's Special Attack by 1 stage and confuses it.",
        shortDesc=r"Raises the target's Sp. Atk by 1 and confuses it.",
        accuracy=100,
        name=r"Flatter",
        pp=15,
        type=Types.DARK,
    )
    FLEURCANNON = Move(
        desc=r"Lowers the user's Special Attack by 2 stages.",
        shortDesc=r"Lowers the user's Sp. Atk by 2.",
        accuracy=9,
        base=130,
        category=Category.SPECIAL,
        name=r"Fleur Cannon",
        pp=5,
        type=Types.FAIRY,
    )
    FLING = Move(
        desc=r"The power of this move is based on the user's held item. The held item is lost and it activates for the target if applicable. If there is no target or the target avoids this move by protecting itself, the user's held item is still lost. The user can regain a thrown item with Recycle or the Harvest Ability. Fails if the user has no held item, if the held item cannot be thrown, if the user is under the effect of Embargo or Magic Room, or if the user has the Klutz Ability.",
        shortDesc=r"Flings the user's item at the target. Power varies.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Fling",
        pp=10,
        type=Types.DARK,
    )
    FLIPTURN = Move(
        desc=r"If this move is successful and the user has not fainted, the user switches out even if it is trapped and is replaced immediately by a selected party member. The user does not switch out if there are no unfainted party members, or if the target switched out using an Eject Button or through the effect of the Emergency Exit or Wimp Out Abilities.",
        shortDesc=r"User switches out after damaging the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Flip Turn",
        pp=20,
        type=Types.WATER,
    )
    FLOATYFALL = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=95,
        base=90,
        category=Category.PHYSICAL,
        name=r"Floaty Fall",
        pp=15,
        type=Types.FLYING,
    )
    FLORALHEALING = Move(
        desc=r"The target restores 1/2 of its maximum HP, rounded half up. If the terrain is Grassy Terrain, the target instead restores 2/3 of its maximum HP, rounded half down.",
        shortDesc=r"Heals the target by 50% of its max HP.",
        name=r"Floral Healing",
        pp=10,
        type=Types.FAIRY,
    )
    FLOWERSHIELD = Move(
        desc=r"Raises the Defense of all active Grass-type Pokemon by 1 stage. Fails if there are no active Grass-type Pokemon.",
        shortDesc=r"Raises Defense by 1 of all active Grass types.",
        name=r"Flower Shield",
        pp=10,
        type=Types.FAIRY,
    )
    FLY = Move(
        desc=r"This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks other than Gust, Hurricane, Sky Uppercut, Smack Down, Thousand Arrows, Thunder, and Twister, and Gust and Twister have doubled power when used against it. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Flies up on first turn, then strikes the next turn.",
        accuracy=95,
        base=90,
        category=Category.PHYSICAL,
        name=r"Fly",
        pp=15,
        type=Types.FLYING,
    )
    FLYINGPRESS = Move(
        desc=r"This move combines Flying in its type effectiveness against the target. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"Combines Flying in its type effectiveness.",
        accuracy=95,
        base=100,
        category=Category.PHYSICAL,
        name=r"Flying Press",
        pp=10,
        type=Types.FIGHTING,
    )
    FOCUSBLAST = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=7,
        base=120,
        category=Category.SPECIAL,
        name=r"Focus Blast",
        pp=5,
        type=Types.FIGHTING,
    )
    FOCUSENERGY = Move(
        desc=r"Raises the user's chance for a critical hit by 2 stages. Fails if the user already has the effect. Baton Pass can be used to transfer this effect to an ally.",
        shortDesc=r"Raises the user's critical hit ratio by 2.",
        name=r"Focus Energy",
        pp=30,
    )
    FOCUSPUNCH = Move(
        desc=r"The user loses its focus and does nothing if it is hit by a damaging attack this turn before it can execute the move.",
        shortDesc=r"Fails if the user takes damage before it hits.",
        accuracy=100,
        base=150,
        category=Category.PHYSICAL,
        name=r"Focus Punch",
        pp=20,
        type=Types.FIGHTING,
    )
    FOLLOWME = Move(
        desc=r"Until the end of the turn, all single-target attacks from the opposing side are redirected to the user. Such attacks are redirected to the user before they can be reflected by Magic Coat or the Magic Bounce Ability, or drawn in by the Lightning Rod or Storm Drain Abilities. Fails if it is not a Double Battle or Battle Royal. This effect is ignored while the user is under the effect of Sky Drop.",
        shortDesc=r"The foes' moves target the user on the turn used.",
        name=r"Follow Me",
        pp=20,
    )
    FORCEPALM = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Force Palm",
        pp=10,
        type=Types.FIGHTING,
    )
    FORESIGHT = Move(
        desc=r"As long as the target remains active, its evasiveness stat stage is ignored during accuracy checks against it if it is greater than 0, and Normal- and Fighting-type attacks can hit the target if it is a Ghost type. Fails if the target is already affected, or affected by Miracle Eye or Odor Sleuth.",
        shortDesc=r"Fighting, Normal hit Ghost. Evasiveness ignored.",
        name=r"Foresight",
        pp=40,
    )
    FORESTSCURSE = Move(
        desc=r"Causes the Grass type to be added to the target, effectively making it have two or three types. Fails if the target is already a Grass type. If Trick-or-Treat adds a type to the target, it replaces the type added by this move and vice versa.",
        shortDesc=r"Adds Grass to the target's type(s).",
        accuracy=100,
        name=r"Forest's Curse",
        pp=20,
        type=Types.GRASS,
    )
    FOULPLAY = Move(
        desc=r"Damage is calculated using the target's Attack stat, including stat stage changes. The user's Ability, item, and burn are used as normal.",
        shortDesc=r"Uses target's Attack stat in damage calculation.",
        accuracy=100,
        base=95,
        category=Category.PHYSICAL,
        name=r"Foul Play",
        pp=15,
        type=Types.DARK,
    )
    FREEZEDRY = Move(
        desc=r"Has a 10% chance to freeze the target. This move's type effectiveness against Water is changed to be super effective no matter what this move's type is.",
        shortDesc=r"10% chance to freeze. Super effective on Water.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Freeze-Dry",
        pp=20,
        type=Types.ICE,
    )
    FREEZESHOCK = Move(
        desc=r"Has a 30% chance to paralyze the target. This attack charges on the first turn and executes on the second. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Charges turn 1. Hits turn 2. 30% paralyze.",
        accuracy=9,
        base=140,
        category=Category.PHYSICAL,
        name=r"Freeze Shock",
        pp=5,
        type=Types.ICE,
    )
    FREEZINGGLARE = Move(
        desc=r"The user shoots its psychic power from its eyes to attack. This may also leave the target frozen.",
        shortDesc=r"The user shoots its psychic power from its eyes to attack. This may also leave the target frozen.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Freezing Glare",
        pp=10,
        type=Types.PSYCHIC,
    )
    FREEZYFROST = Move(
        desc=r"Resets the stat stages of all active Pokemon to 0.",
        shortDesc=r"Eliminates all stat changes.",
        accuracy=9,
        base=100,
        category=Category.SPECIAL,
        name=r"Freezy Frost",
        pp=10,
        type=Types.ICE,
    )
    FRENZYPLANT = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.SPECIAL,
        name=r"Frenzy Plant",
        pp=5,
        type=Types.GRASS,
    )
    FROSTBREATH = Move(
        desc=r"This move is always a critical hit unless the target is under the effect of Lucky Chant or has the Battle Armor or Shell Armor Abilities.",
        shortDesc=r"Always results in a critical hit.",
        accuracy=9,
        base=60,
        category=Category.SPECIAL,
        name=r"Frost Breath",
        pp=10,
        type=Types.ICE,
    )
    FRUSTRATION = Move(
        desc=r"Power is equal to the greater of ((255 - user's Happiness) * 2/5) rounded down, or 1.",
        shortDesc=r"Max 102 power at minimum Happiness.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Frustration",
        pp=20,
    )
    FURYATTACK = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=85,
        base=15,
        category=Category.PHYSICAL,
        name=r"Fury Attack",
        pp=20,
    )
    FURYCUTTER = Move(
        desc=r"Power doubles with each successful hit, up to a maximum of 160 power. The power is reset if this move misses or another move is used.",
        shortDesc=r"Power doubles with each hit, up to 160.",
        accuracy=95,
        base=40,
        category=Category.PHYSICAL,
        name=r"Fury Cutter",
        pp=20,
        type=Types.BUG,
    )
    FURYSWIPES = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=8,
        base=18,
        category=Category.PHYSICAL,
        name=r"Fury Swipes",
        pp=15,
    )
    FUSIONBOLT = Move(
        desc=r"Power doubles if the last move used by any Pokemon this turn was Fusion Flare.",
        shortDesc=r"Power doubles if used after Fusion Flare this turn.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Fusion Bolt",
        pp=5,
        type=Types.ELECTRIC,
    )
    FUSIONFLARE = Move(
        desc=r"Power doubles if the last move used by any Pokemon this turn was Fusion Bolt.",
        shortDesc=r"Power doubles if used after Fusion Bolt this turn.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Fusion Flare",
        pp=5,
        type=Types.FIRE,
    )
    FUTURESIGHT = Move(
        desc=r"Deals damage two turns after this move is used. At the end of that turn, the damage is calculated at that time and dealt to the Pokemon at the position the target had when the move was used. If the user is no longer active at the time, damage is calculated based on the user's natural Special Attack stat, types, and level, with no boosts from its held item or Ability. Fails if this move or Doom Desire is already in effect for the target's position.",
        shortDesc=r"Hits two turns after being used.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Future Sight",
        pp=10,
        type=Types.PSYCHIC,
    )
    GASTROACID = Move(
        desc=r"Causes the target's Ability to be rendered ineffective as long as it remains active. If the target uses Baton Pass, the replacement will remain under this effect. If the target's Ability is Battle Bond, Comatose, Disguise, Multitype, Power Construct, RKS System, Schooling, Shields Down, Stance Change, or Zen Mode, this move fails, and receiving the effect through Baton Pass ends the effect immediately.",
        shortDesc=r"Nullifies the target's Ability.",
        accuracy=100,
        name=r"Gastro Acid",
        pp=10,
        type=Types.POISON,
    )
    GEARGRIND = Move(
        desc=r"Hits twice. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times in one turn.",
        accuracy=85,
        base=50,
        category=Category.PHYSICAL,
        name=r"Gear Grind",
        pp=15,
        type=Types.STEEL,
    )
    GEARUP = Move(
        desc=r"Raises the Attack and Special Attack of Pokemon on the user's side with the Plus or Minus Abilities by 1 stage.",
        shortDesc=r"Raises Atk, Sp. Atk of allies with Plus/Minus by 1.",
        name=r"Gear Up",
        pp=20,
        type=Types.STEEL,
    )
    GEOMANCY = Move(
        desc=r"Raises the user's Special Attack, Special Defense, and Speed by 2 stages. This attack charges on the first turn and executes on the second. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Charges, then raises SpA, SpD, Spe by 2 turn 2.",
        name=r"Geomancy",
        pp=10,
        type=Types.FAIRY,
    )
    GIGADRAIN = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=75,
        category=Category.SPECIAL,
        name=r"Giga Drain",
        pp=10,
        type=Types.GRASS,
    )
    GIGAIMPACT = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.PHYSICAL,
        name=r"Giga Impact",
        pp=5,
    )
    GLACIALLANCE = Move(
        desc=r"The user attacks by hurling a blizzard-cloaked icicle lance at opposing Pokémon.",
        shortDesc=r"The user attacks by hurling a blizzard-cloaked icicle lance at opposing Pokémon.",
        accuracy=100,
        base=130,
        category=Category.PHYSICAL,
        name=r"Glacial Lance",
        pp=5,
        type=Types.ICE,
    )
    GLACIATE = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Speed by 1.",
        accuracy=95,
        base=65,
        category=Category.SPECIAL,
        name=r"Glaciate",
        pp=10,
        type=Types.ICE,
    )
    GLARE = Move(
        desc=r"Paralyzes the target.",
        shortDesc=r"Paralyzes the target.",
        accuracy=100,
        name=r"Glare",
        pp=30,
    )
    GLITZYGLOW = Move(
        desc=r"This move summons Light Screen for 5 turns upon use.",
        shortDesc=r"Summons Light Screen.",
        accuracy=95,
        base=80,
        category=Category.SPECIAL,
        name=r"Glitzy Glow",
        pp=15,
        type=Types.PSYCHIC,
    )
    GRASSKNOT = Move(
        desc=r"This move's power is 20 if the target weighs less than 10 kg, 40 if less than 25 kg, 60 if less than 50 kg, 80 if less than 100 kg, 100 if less than 200 kg, and 120 if greater than or equal to 200 kg.",
        shortDesc=r"More power the heavier the target.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Grass Knot",
        pp=20,
        type=Types.GRASS,
    )
    GRASSPLEDGE = Move(
        desc=r"If one of the user's allies chose to use Fire Pledge or Water Pledge this turn and has not moved yet, it takes its turn immediately after the user and the user's move does nothing. If combined with Fire Pledge, the ally uses Fire Pledge with 150 power and a sea of fire appears on the target's side for 4 turns, which causes damage to non-Fire types equal to 1/8 of their maximum HP, rounded down, at the end of each turn during effect, including the last turn. If combined with Water Pledge, the ally uses Grass Pledge with 150 power and a swamp appears on the target's side for 4 turns, which quarters the Speed of each Pokemon on that side. When used as a combined move, this move gains STAB no matter what the user's type is. This move does not consume the user's Grass Gem.",
        shortDesc=r"Use with Fire or Water Pledge for added effect.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Grass Pledge",
        pp=10,
        type=Types.GRASS,
    )
    GRASSWHISTLE = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=55,
        name=r"Grass Whistle",
        pp=15,
        type=Types.GRASS,
    )
    GRASSYGLIDE = Move(
        desc=r"If the current terrain is Grassy Terrain and the user is grounded, this move has its priority increased by 1.",
        shortDesc=r"User on Grassy Terrain: +1 priority.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Grassy Glide",
        pp=20,
        type=Types.GRASS,
    )
    GRASSYTERRAIN = Move(
        desc=r"For 5 turns, the terrain becomes Grassy Terrain. During the effect, the power of Grass-type attacks used by grounded Pokemon is multiplied by 1.3, the power of Bulldoze, Earthquake, and Magnitude used against grounded Pokemon is multiplied by 0.5, and grounded Pokemon have 1/16 of their maximum HP, rounded down, restored at the end of each turn, including the last turn. Camouflage transforms the user into a Grass type, Nature Power becomes Energy Ball, and Secret Power has a 30% chance to cause sleep. Fails if the current terrain is Grassy Terrain.",
        shortDesc=r"5 turns. Grounded: +Grass power, +1/16 max HP.",
        name=r"Grassy Terrain",
        pp=10,
        type=Types.GRASS,
    )
    GRAVAPPLE = Move(
        desc=r"Has a 100% chance to lower the target's Defense by 1 stage. Power is multiplied by 1.5 during Gravity's effect.",
        shortDesc=r"Target: 100% -1 Def. During Gravity: 1.5x power.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Grav Apple",
        pp=10,
        type=Types.GRASS,
    )
    GRAVITY = Move(
        desc=r"For 5 turns, the evasiveness of all active Pokemon is multiplied by 0.6. At the time of use, Bounce, Fly, Magnet Rise, Sky Drop, and Telekinesis end immediately for all active Pokemon. During the effect, Bounce, Fly, Flying Press, High Jump Kick, Jump Kick, Magnet Rise, Sky Drop, Splash, and Telekinesis are prevented from being used by all active Pokemon. Ground-type attacks, Spikes, Toxic Spikes, Sticky Web, and the Arena Trap Ability can affect Flying types or Pokemon with the Levitate Ability. Fails if this move is already in effect.",
        shortDesc=r"5 turns: no Ground immunities, 1.67x accuracy.",
        name=r"Gravity",
        pp=5,
        type=Types.PSYCHIC,
    )
    GROWL = Move(
        desc=r"Lowers the target's Attack by 1 stage.",
        shortDesc=r"Lowers the foe(s) Attack by 1.",
        accuracy=100,
        name=r"Growl",
        pp=40,
    )
    GROWTH = Move(
        desc=r"Raises the user's Attack and Special Attack by 1 stage. If the weather is Sunny Day or Desolate Land, this move raises the user's Attack and Special Attack by 2 stages. If the user is holding Utility Umbrella, this move will only raise the user's Attack and Special Attack by 1 stage, even if the weather is Sunny Day or Desolate Land.",
        shortDesc=r"Raises user's Attack and Sp. Atk by 1; 2 in Sun.",
        name=r"Growth",
        pp=20,
    )
    GRUDGE = Move(
        desc=r"Until the user's next turn, if an opposing Pokemon's attack knocks the user out, that move loses all its remaining PP.",
        shortDesc=r"If the user faints, the attack used loses all its PP.",
        name=r"Grudge",
        pp=5,
        type=Types.GHOST,
    )
    GUARDSPLIT = Move(
        desc=r"The user and the target have their Defense and Special Defense stats set to be equal to the average of the user and the target's Defense and Special Defense stats, respectively, rounded down. Stat stage changes are unaffected.",
        shortDesc=r"Averages Defense and Sp. Def stats with target.",
        name=r"Guard Split",
        pp=10,
        type=Types.PSYCHIC,
    )
    GUARDSWAP = Move(
        desc=r"The user swaps its Defense and Special Defense stat stage changes with the target.",
        shortDesc=r"Swaps Defense and Sp. Def changes with target.",
        name=r"Guard Swap",
        pp=10,
        type=Types.PSYCHIC,
    )
    GUILLOTINE = Move(
        desc=r"Deals damage to the target equal to the target's maximum HP. Ignores accuracy and evasiveness modifiers. This attack's accuracy is equal to (user's level - target's level + 30)%, and fails if the target is at a higher level. Pokemon with the Sturdy Ability are immune.",
        shortDesc=r"OHKOs the target. Fails if user is a lower level.",
        banned=True,
        category=Category.PHYSICAL,
        name=r"Guillotine",
        pp=5,
    )
    GUNKSHOT = Move(
        desc=r"Has a 30% chance to poison the target.",
        shortDesc=r"30% chance to poison the target.",
        accuracy=8,
        base=120,
        category=Category.PHYSICAL,
        name=r"Gunk Shot",
        pp=5,
        type=Types.POISON,
    )
    GUST = Move(
        desc=r"Power doubles if the target is using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop.",
        shortDesc=r"Power doubles during Bounce, Fly, and Sky Drop.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Gust",
        pp=35,
        type=Types.FLYING,
    )
    GYROBALL = Move(
        desc=r"Power is equal to (25 * target's current Speed / user's current Speed) + 1, rounded down, but not more than 150. If the user's current Speed is 0, this move's power is 1.",
        shortDesc=r"More power the slower the user than the target.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Gyro Ball",
        pp=5,
        type=Types.STEEL,
    )
    HAIL = Move(
        desc=r"For 5 turns, the weather becomes Hail. At the end of each turn except the last, all active Pokemon lose 1/16 of their maximum HP, rounded down, unless they are an Ice type or have the Ice Body, Magic Guard, Overcoat, or Snow Cloak Abilities. Lasts for 8 turns if the user is holding Icy Rock. Fails if the current weather is Hail.",
        shortDesc=r"For 5 turns, hail crashes down.",
        name=r"Hail",
        pp=10,
        type=Types.ICE,
    )
    HAMMERARM = Move(
        desc=r"Lowers the user's Speed by 1 stage.",
        shortDesc=r"Lowers the user's Speed by 1.",
        accuracy=9,
        base=100,
        category=Category.PHYSICAL,
        name=r"Hammer Arm",
        pp=10,
        type=Types.FIGHTING,
    )
    HAPPYHOUR = Move(
        desc=r"No competitive use.",
        shortDesc=r"No competitive use.",
        name=r"Happy Hour",
        pp=30,
    )
    HARDEN = Move(
        desc=r"Raises the user's Defense by 1 stage.",
        shortDesc=r"Raises the user's Defense by 1.",
        name=r"Harden",
        pp=30,
    )
    HAZE = Move(
        desc=r"Resets the stat stages of all active Pokemon to 0.",
        shortDesc=r"Eliminates all stat changes.",
        name=r"Haze",
        pp=30,
        type=Types.ICE,
    )
    HEADBUTT = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Headbutt",
        pp=15,
    )
    HEADCHARGE = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/4 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/4 recoil.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Head Charge",
        pp=15,
    )
    HEADSMASH = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/2 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/2 recoil.",
        accuracy=8,
        base=150,
        category=Category.PHYSICAL,
        name=r"Head Smash",
        pp=5,
        type=Types.ROCK,
    )
    HEALBELL = Move(
        desc=r"Every Pokemon in the user's party is cured of its major status condition. Active Pokemon with the Soundproof Ability are not cured, unless they are the user.",
        shortDesc=r"Cures the user's party of all status conditions.",
        name=r"Heal Bell",
        pp=5,
    )
    HEALBLOCK = Move(
        desc=r"For 5 turns, the target is prevented from restoring any HP as long as it remains active. During the effect, healing and draining moves are unusable, and Abilities and items that grant healing will not heal the user. If an affected Pokemon uses Baton Pass, the replacement will remain unable to restore its HP. Pain Split and the Regenerator Ability are unaffected.",
        shortDesc=r"For 5 turns, the foe(s) is prevented from healing.",
        accuracy=100,
        name=r"Heal Block",
        pp=15,
        type=Types.PSYCHIC,
    )
    HEALINGWISH = Move(
        desc=r"The user faints and the next injured or statused Pokemon brought in has its HP fully restored along with having any major status condition cured. The healing happens before hazards take effect. Is not consumed if the Pokemon sent out is not injured or statused. Fails if the user is the last unfainted Pokemon in its party.",
        shortDesc=r"User faints. Next hurt Pokemon is fully healed.",
        name=r"Healing Wish",
        pp=10,
        type=Types.PSYCHIC,
    )
    HEALORDER = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user by 50% of its max HP.",
        name=r"Heal Order",
        pp=10,
        type=Types.BUG,
    )
    HEALPULSE = Move(
        desc=r"The target restores 1/2 of its maximum HP, rounded half up. If the user has the Mega Launcher Ability, the target instead restores 3/4 of its maximum HP, rounded half down.",
        shortDesc=r"Heals the target by 50% of its max HP.",
        name=r"Heal Pulse",
        pp=10,
        type=Types.PSYCHIC,
    )
    HEARTSTAMP = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Heart Stamp",
        pp=25,
        type=Types.PSYCHIC,
    )
    HEARTSWAP = Move(
        desc=r"The user swaps all its stat stage changes with the target.",
        shortDesc=r"Swaps all stat changes with target.",
        name=r"Heart Swap",
        pp=10,
        type=Types.PSYCHIC,
    )
    HEATCRASH = Move(
        desc=r"The power of this move depends on (user's weight / target's weight) rounded down. Power is equal to 120 if the result is 5 or more, 100 if 4, 80 if 3, 60 if 2, and 40 if 1 or less. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"More power the heavier the user than the target.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Heat Crash",
        pp=10,
        type=Types.FIRE,
    )
    HEATWAVE = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the foe(s).",
        accuracy=9,
        base=95,
        category=Category.SPECIAL,
        name=r"Heat Wave",
        pp=10,
        type=Types.FIRE,
    )
    HEAVYSLAM = Move(
        desc=r"The power of this move depends on (user's weight / target's weight) rounded down. Power is equal to 120 if the result is 5 or more, 100 if 4, 80 if 3, 60 if 2, and 40 if 1 or less. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"More power the heavier the user than the target.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Heavy Slam",
        pp=10,
        type=Types.STEEL,
    )
    HELPINGHAND = Move(
        desc=r"The power of the target's attack this turn is multiplied by 1.5 (this effect is stackable). Fails if there is no ally adjacent to the user or if the ally already moved this turn, but does not fail if the ally is using a two-turn move.",
        shortDesc=r"One adjacent ally's move power is 1.5x this turn.",
        name=r"Helping Hand",
        pp=20,
    )
    HEX = Move(
        desc=r"Power doubles if the target has a major status condition.",
        shortDesc=r"Power doubles if the target has a status ailment.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Hex",
        pp=10,
        type=Types.GHOST,
    )
    HIDDENPOWER = Move(
        desc=r"This move's type depends on the user's individual values (IVs) and can be any type but Fairy and Normal.",
        shortDesc=r"Varies in type based on the user's IVs.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Hidden Power",
        pp=15,
    )
    HIGHHORSEPOWER = Move(
        desc=r"High Horsepower deals damage and has no secondary effect.",
        shortDesc=r"The user fiercely attacks the target using its entire body.",
        accuracy=95,
        base=95,
        category=Category.PHYSICAL,
        name=r"High Horsepower",
        pp=10,
        type=Types.GROUND,
    )
    HIGHJUMPKICK = Move(
        desc=r"The target is attacked with a knee kick from a jump. If it misses, the user is hurt instead.",
        shortDesc=r"The target is attacked with a knee kick from a jump. If it misses, the user is hurt instead.",
        accuracy=9,
        base=130,
        category=Category.PHYSICAL,
        name=r"High Jump Kick",
        pp=10,
        type=Types.FIGHTING,
    )
    HOLDBACK = Move(
        desc=r"Leaves the target with at least 1 HP.",
        shortDesc=r"Always leaves the target with at least 1 HP.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Hold Back",
        pp=40,
    )
    HOLDHANDS = Move(
        desc=r"No competitive use. Fails if there is no ally adjacent to the user.",
        shortDesc=r"No competitive use.",
        name=r"Hold Hands",
        pp=40,
    )
    HONECLAWS = Move(
        desc=r"Raises the user's Attack and accuracy by 1 stage.",
        shortDesc=r"Raises the user's Attack and accuracy by 1.",
        name=r"Hone Claws",
        pp=15,
        type=Types.DARK,
    )
    HORNATTACK = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Horn Attack",
        pp=25,
    )
    HORNDRILL = Move(
        desc=r"Deals damage to the target equal to the target's maximum HP. Ignores accuracy and evasiveness modifiers. This attack's accuracy is equal to (user's level - target's level + 30)%, and fails if the target is at a higher level. Pokemon with the Sturdy Ability are immune.",
        shortDesc=r"OHKOs the target. Fails if user is a lower level.",
        banned=True,
        category=Category.PHYSICAL,
        name=r"Horn Drill",
        pp=5,
    )
    HORNLEECH = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Horn Leech",
        pp=10,
        type=Types.GRASS,
    )
    HOWL = Move(
        desc=r"Raises the Attack of the user and all allies 1 stage.",
        shortDesc=r"Raises the user's and ally's Attack by 1.",
        name=r"Howl",
        pp=40,
    )
    HURRICANE = Move(
        desc=r"Has a 30% chance to confuse the target. This move can hit a target using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop. If the weather is Primordial Sea or Rain Dance, this move does not check accuracy. If the weather is Desolate Land or Sunny Day, this move's accuracy is 50%. If this move is used against a Pokemon holding Utility Umbrella, this move's accuracy remains at 70%.",
        shortDesc=r"30% chance to confuse target. Can't miss in rain.",
        accuracy=7,
        base=110,
        category=Category.SPECIAL,
        name=r"Hurricane",
        pp=10,
        type=Types.FLYING,
    )
    HYDROCANNON = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.SPECIAL,
        name=r"Hydro Cannon",
        pp=5,
        type=Types.WATER,
    )
    HYDROPUMP = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=8,
        base=110,
        category=Category.SPECIAL,
        name=r"Hydro Pump",
        pp=5,
        type=Types.WATER,
    )
    HYPERBEAM = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.SPECIAL,
        name=r"Hyper Beam",
        pp=5,
    )
    HYPERFANG = Move(
        desc=r"Has a 10% chance to flinch the target.",
        shortDesc=r"10% chance to flinch the target.",
        accuracy=9,
        base=80,
        category=Category.PHYSICAL,
        name=r"Hyper Fang",
        pp=15,
    )
    HYPERSPACEFURY = Move(
        desc=r"Lowers the user's Defense by 1 stage. This move cannot be used successfully unless the user's current form, while considering Transform, is Hoopa Unbound. If this move is successful, it breaks through the target's Baneful Bunker, Detect, King's Shield, Protect, or Spiky Shield for this turn, allowing other Pokemon to attack the target normally. If the target's side is protected by Crafty Shield, Mat Block, Quick Guard, or Wide Guard, that protection is also broken for this turn and other Pokemon may attack the target's side normally.",
        shortDesc=r"Hoopa-U: Lowers user's Def by 1; breaks protect.",
        base=100,
        category=Category.PHYSICAL,
        name=r"Hyperspace Fury",
        pp=5,
        type=Types.DARK,
    )
    HYPERSPACEHOLE = Move(
        desc=r"If this move is successful, it breaks through the target's Baneful Bunker, Detect, King's Shield, Protect, or Spiky Shield for this turn, allowing other Pokemon to attack the target normally. If the target's side is protected by Crafty Shield, Mat Block, Quick Guard, or Wide Guard, that protection is also broken for this turn and other Pokemon may attack the target's side normally.",
        shortDesc=r"Breaks the target's protection for this turn.",
        base=80,
        category=Category.SPECIAL,
        name=r"Hyperspace Hole",
        pp=5,
        type=Types.PSYCHIC,
    )
    HYPERVOICE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent foes.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Hyper Voice",
        pp=10,
    )
    HYPNOSIS = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=6,
        name=r"Hypnosis",
        pp=20,
        type=Types.PSYCHIC,
    )
    ICEBALL = Move(
        desc=r"If this move is successful, the user is locked into this move and cannot make another move until it misses, 5 turns have passed, or the attack cannot be used. Power doubles with each successful hit of this move and doubles again if Defense Curl was used previously by the user. If this move is called by Sleep Talk, the move is used for one turn. If this move hits an active Disguise during the effect, the power multiplier is paused but the turn counter is not, potentially allowing the multiplier to be used on the user's next move after this effect ends.",
        shortDesc=r"Power doubles with each hit. Repeats for 5 turns.",
        accuracy=9,
        base=30,
        category=Category.PHYSICAL,
        name=r"Ice Ball",
        pp=20,
        type=Types.ICE,
    )
    ICEBEAM = Move(
        desc=r"Has a 10% chance to freeze the target.",
        shortDesc=r"10% chance to freeze the target.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Ice Beam",
        pp=10,
        type=Types.ICE,
    )
    ICEBURN = Move(
        desc=r"Has a 30% chance to burn the target. This attack charges on the first turn and executes on the second. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Charges turn 1. Hits turn 2. 30% burn.",
        accuracy=9,
        base=140,
        category=Category.SPECIAL,
        name=r"Ice Burn",
        pp=5,
        type=Types.ICE,
    )
    ICEFANG = Move(
        desc=r"Has a 10% chance to freeze the target and a 10% chance to flinch it.",
        shortDesc=r"10% chance to freeze. 10% chance to flinch.",
        accuracy=95,
        base=65,
        category=Category.PHYSICAL,
        name=r"Ice Fang",
        pp=15,
        type=Types.ICE,
    )
    ICEHAMMER = Move(
        desc=r"Lowers the user's Speed by 1 stage.",
        shortDesc=r"Lowers the user's Speed by 1.",
        accuracy=9,
        base=100,
        category=Category.PHYSICAL,
        name=r"Ice Hammer",
        pp=10,
        type=Types.ICE,
    )
    ICEPUNCH = Move(
        desc=r"Has a 10% chance to freeze the target.",
        shortDesc=r"10% chance to freeze the target.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Ice Punch",
        pp=15,
        type=Types.ICE,
    )
    ICESHARD = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Ice Shard",
        pp=30,
        type=Types.ICE,
    )
    ICICLECRASH = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=9,
        base=85,
        category=Category.PHYSICAL,
        name=r"Icicle Crash",
        pp=10,
        type=Types.ICE,
    )
    ICICLESPEAR = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=100,
        base=25,
        category=Category.PHYSICAL,
        name=r"Icicle Spear",
        pp=30,
        type=Types.ICE,
    )
    ICYWIND = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Speed by 1.",
        accuracy=95,
        base=55,
        category=Category.SPECIAL,
        name=r"Icy Wind",
        pp=15,
        type=Types.ICE,
    )
    IMPRISON = Move(
        desc=r"The user prevents all opposing Pokemon from using any moves that the user also knows as long as the user remains active.",
        shortDesc=r"No foe can use any move known by the user.",
        name=r"Imprison",
        pp=10,
        type=Types.PSYCHIC,
    )
    INCINERATE = Move(
        desc=r"The target loses its held item if it is a Berry or a Gem. This move cannot cause Pokemon with the Sticky Hold Ability to lose their held item. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"Destroys the foe(s) Berry/Gem.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Incinerate",
        pp=15,
        type=Types.FIRE,
    )
    INFERNO = Move(
        desc=r"Has a 100% chance to burn the target.",
        shortDesc=r"100% chance to burn the target.",
        accuracy=5,
        base=100,
        category=Category.SPECIAL,
        name=r"Inferno",
        pp=5,
        type=Types.FIRE,
    )
    INFESTATION = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=100,
        base=20,
        category=Category.SPECIAL,
        name=r"Infestation",
        pp=20,
        type=Types.BUG,
    )
    INGRAIN = Move(
        desc=r"The user has 1/16 of its maximum HP restored at the end of each turn, but it is prevented from switching out and other Pokemon cannot force the user to switch out. The user can still switch out if it uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the user leaves the field using Baton Pass, the replacement will remain trapped and still receive the healing effect. During the effect, the user can be hit normally by Ground-type attacks and be affected by Spikes, Toxic Spikes, and Sticky Web, even if the user is a Flying type or has the Levitate Ability.",
        shortDesc=r"Traps/grounds user; heals 1/16 max HP per turn.",
        name=r"Ingrain",
        pp=20,
        type=Types.GRASS,
    )
    INSTRUCT = Move(
        desc=r"The target immediately uses its last used move. Fails if the target has not made a move, if the move has 0 PP, if the target is preparing to use Beak Blast, Focus Punch, or Shell Trap, or if the move is Assist, Beak Blast, Belch, Bide, Celebrate, Copycat, Dynamax Cannon, Focus Punch, Ice Ball, Instruct, King's Shield, Me First, Metronome, Mimic, Mirror Move, Nature Power, Outrage, Petal Dance, Rollout, Shell Trap, Sketch, Sleep Talk, Struggle, Thrash, Transform, Uproar, any two-turn move, any recharge move, or any Z-Move.",
        shortDesc=r"The target immediately uses its last used move.",
        name=r"Instruct",
        pp=15,
        type=Types.PSYCHIC,
    )
    IONDELUGE = Move(
        desc=r"Causes Normal-type moves to become Electric type this turn. The effect happens after other effects that change a move's type.",
        shortDesc=r"Normal moves become Electric type this turn.",
        name=r"Ion Deluge",
        pp=25,
        type=Types.ELECTRIC,
    )
    IRONDEFENSE = Move(
        desc=r"Raises the user's Defense by 2 stages.",
        shortDesc=r"Raises the user's Defense by 2.",
        name=r"Iron Defense",
        pp=15,
        type=Types.STEEL,
    )
    IRONHEAD = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Iron Head",
        pp=15,
        type=Types.STEEL,
    )
    IRONTAIL = Move(
        desc=r"Has a 30% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"30% chance to lower the target's Defense by 1.",
        accuracy=75,
        base=100,
        category=Category.PHYSICAL,
        name=r"Iron Tail",
        pp=15,
        type=Types.STEEL,
    )
    JAWLOCK = Move(
        desc=r"Prevents the user and the target from switching out. The user and the target can still switch out if either of them is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if either the user or the target leaves the field.",
        shortDesc=r"Prevents both user and target from switching out.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Jaw Lock",
        pp=15,
        type=Types.DARK,
    )
    JUDGMENT = Move(
        desc=r"This move's type depends on the user's held Plate.",
        shortDesc=r"Type varies based on the held Plate.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Judgment",
        pp=10,
    )
    JUMPKICK = Move(
        desc=r"If this attack is not successful, the user loses half of its maximum HP, rounded down, as crash damage. Pokemon with the Magic Guard Ability are unaffected by crash damage.",
        shortDesc=r"User is hurt by 50% of its max HP if it misses.",
        accuracy=95,
        base=100,
        category=Category.PHYSICAL,
        name=r"Jump Kick",
        pp=10,
        type=Types.FIGHTING,
    )
    JUNGLEHEALING = Move(
        desc=r"Each Pokemon on the user's side restores 1/4 of its maximum HP, rounded half up, and has its status condition cured.",
        shortDesc=r"User and allies: healed 1/4 max HP, status cured.",
        name=r"Jungle Healing",
        pp=10,
        type=Types.GRASS,
    )
    KARATECHOP = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Karate Chop",
        pp=25,
        type=Types.FIGHTING,
    )
    KINESIS = Move(
        desc=r"Lowers the target's accuracy by 1 stage.",
        shortDesc=r"Lowers the target's accuracy by 1.",
        accuracy=8,
        name=r"Kinesis",
        pp=15,
        type=Types.PSYCHIC,
    )
    KINGSSHIELD = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn, and Pokemon trying to make contact with the user have their Attack lowered by 1 stage. Non-damaging moves go through this protection. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Protects from damaging attacks. Contact: -1 Atk.",
        name=r"King's Shield",
        pp=10,
        type=Types.STEEL,
    )
    KNOCKOFF = Move(
        desc=r"If the target is holding an item that can be removed from it, ignoring the Sticky Hold Ability, this move's power is multiplied by 1.5. If the user has not fainted, the target loses its held item. This move cannot cause Pokemon with the Sticky Hold Ability to lose their held item or cause a Kyogre, a Groudon, a Giratina, an Arceus, a Genesect, a Silvally, a Zacian, or a Zamazenta to lose their Blue Orb, Red Orb, Griseous Orb, Plate, Drive, Memory, Rusted Sword, or Rusted Shield respectively. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"1.5x damage if foe holds an item. Removes item.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Knock Off",
        pp=20,
        type=Types.DARK,
    )
    LANDSWRATH = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent foes.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Land's Wrath",
        pp=10,
        type=Types.GROUND,
    )
    LASERFOCUS = Move(
        desc=r"Until the end of the next turn, the user's attacks will be critical hits.",
        shortDesc=r"Until the end of the next turn, user's moves crit.",
        name=r"Laser Focus",
        pp=30,
    )
    LASHOUT = Move(
        desc=r"Power doubles if the user had a stat stage lowered this turn.",
        shortDesc=r"2x power if the user had a stat lowered this turn.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Lash Out",
        pp=5,
        type=Types.DARK,
    )
    LASTRESORT = Move(
        desc=r"This move fails unless the user knows this move and at least one other move, and has used all the other moves it knows at least once each since it became active or Transformed.",
        shortDesc=r"Fails unless each known move has been used.",
        accuracy=100,
        base=140,
        category=Category.PHYSICAL,
        name=r"Last Resort",
        pp=5,
    )
    LAVAPLUME = Move(
        desc=r"Has a 30% chance to burn the target.",
        shortDesc=r"30% chance to burn adjacent Pokemon.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Lava Plume",
        pp=15,
        type=Types.FIRE,
    )
    LEAFAGE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Leafage",
        pp=40,
        type=Types.GRASS,
    )
    LEAFBLADE = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Leaf Blade",
        pp=15,
        type=Types.GRASS,
    )
    LEAFSTORM = Move(
        desc=r"Lowers the user's Special Attack by 2 stages.",
        shortDesc=r"Lowers the user's Sp. Atk by 2.",
        accuracy=9,
        base=130,
        category=Category.SPECIAL,
        name=r"Leaf Storm",
        pp=5,
        type=Types.GRASS,
    )
    LEAFTORNADO = Move(
        desc=r"Has a 50% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"50% chance to lower the target's accuracy by 1.",
        accuracy=9,
        base=65,
        category=Category.SPECIAL,
        name=r"Leaf Tornado",
        pp=10,
        type=Types.GRASS,
    )
    LEECHLIFE = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Leech Life",
        pp=10,
        type=Types.BUG,
    )
    LEECHSEED = Move(
        desc=r"The Pokemon at the user's position steals 1/8 of the target's maximum HP, rounded down, at the end of each turn. If Big Root is held by the recipient, the HP recovered is 1.3x normal, rounded half down. If the target uses Baton Pass, the replacement will continue being leeched. If the target switches out or uses Rapid Spin successfully, the effect ends. Grass-type Pokemon are immune to this move on use, but not its effect.",
        shortDesc=r"1/8 of target's HP is restored to user every turn.",
        accuracy=9,
        name=r"Leech Seed",
        pp=10,
        type=Types.GRASS,
    )
    LEER = Move(
        desc=r"Lowers the target's Defense by 1 stage.",
        shortDesc=r"Lowers the foe(s) Defense by 1.",
        accuracy=100,
        name=r"Leer",
        pp=30,
    )
    LICK = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=30,
        category=Category.PHYSICAL,
        name=r"Lick",
        pp=30,
        type=Types.GHOST,
    )
    LIFEDEW = Move(
        desc=r"Each Pokemon on the user's side restores 1/4 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user and its allies by 1/4 their max HP.",
        name=r"Life Dew",
        pp=10,
        type=Types.WATER,
    )
    LIGHTOFRUIN = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/2 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/2 recoil.",
        accuracy=9,
        base=140,
        category=Category.SPECIAL,
        name=r"Light of Ruin",
        pp=5,
        type=Types.FAIRY,
    )
    LIGHTSCREEN = Move(
        desc=r"For 5 turns, the user and its party members take 0.5x damage from special attacks, or 0.66x damage if in a Double Battle. Damage is not reduced further with Aurora Veil. Critical hits ignore this effect. It is removed from the user's side if the user or an ally is successfully hit by Brick Break, Psychic Fangs, or Defog. Lasts for 8 turns if the user is holding Light Clay. Fails if the effect is already active on the user's side.",
        shortDesc=r"For 5 turns, special damage to allies is halved.",
        name=r"Light Screen",
        pp=30,
        type=Types.PSYCHIC,
    )
    LIQUIDATION = Move(
        desc=r"Has a 20% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"20% chance to lower the target's Defense by 1.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Liquidation",
        pp=10,
        type=Types.WATER,
    )
    LOCKON = Move(
        desc=r"Until the end of the next turn, the target cannot avoid the user's moves, even if the target is in the middle of a two-turn move. The effect ends if either the user or the target leaves the field. Fails if this effect is active for the user.",
        shortDesc=r"User's next move will not miss the target.",
        name=r"Lock-On",
        pp=5,
    )
    LOVELYKISS = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=75,
        name=r"Lovely Kiss",
        pp=10,
    )
    LOWKICK = Move(
        desc=r"This move's power is 20 if the target weighs less than 10 kg, 40 if less than 25 kg, 60 if less than 50 kg, 80 if less than 100 kg, 100 if less than 200 kg, and 120 if greater than or equal to 200 kg.",
        shortDesc=r"More power the heavier the target.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Low Kick",
        pp=20,
        type=Types.FIGHTING,
    )
    LOWSWEEP = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the target's Speed by 1.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Low Sweep",
        pp=20,
        type=Types.FIGHTING,
    )
    LUCKYCHANT = Move(
        desc=r"For 5 turns, the user and its party members cannot be struck by a critical hit. Fails if the effect is already active on the user's side.",
        shortDesc=r"For 5 turns, shields user's party from critical hits.",
        name=r"Lucky Chant",
        pp=30,
    )
    LUNARDANCE = Move(
        desc=r"The user faints and the Pokemon brought out to replace it has its HP and PP fully restored along with having any major status condition cured. The new Pokemon is sent out at the end of the turn, and the healing happens before hazards take effect. Fails if the user is the last unfainted Pokemon in its party.",
        shortDesc=r"User faints. Replacement is fully healed, with PP.",
        name=r"Lunar Dance",
        pp=10,
        type=Types.PSYCHIC,
    )
    LUNGE = Move(
        desc=r"Has a 100% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"100% chance to lower the target's Attack by 1.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Lunge",
        pp=15,
        type=Types.BUG,
    )
    LUSTERPURGE = Move(
        desc=r"Has a 50% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"50% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Luster Purge",
        pp=5,
        type=Types.PSYCHIC,
    )
    MACHPUNCH = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Mach Punch",
        pp=30,
        type=Types.FIGHTING,
    )
    MAGICALLEAF = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.SPECIAL,
        name=r"Magical Leaf",
        pp=20,
        type=Types.GRASS,
    )
    MAGICCOAT = Move(
        desc=r"Until the end of the turn, the user is unaffected by certain non-damaging moves directed at it and will instead use such moves against the original user. Moves reflected in this way are unable to be reflected again by this or the Magic Bounce Ability's effect. Spikes, Stealth Rock, Sticky Web, and Toxic Spikes can only be reflected once per side, by the leftmost Pokemon under this or the Magic Bounce Ability's effect. The Lightning Rod and Storm Drain Abilities redirect their respective moves before this move takes effect.",
        shortDesc=r"Bounces back certain non-damaging moves.",
        name=r"Magic Coat",
        pp=15,
        type=Types.PSYCHIC,
    )
    MAGICPOWDER = Move(
        desc=r"Causes the target to become a Psychic type. Fails if the target is an Arceus or a Silvally, or if the target is already purely Psychic type.",
        shortDesc=r"Changes the target's type to Psychic.",
        accuracy=100,
        name=r"Magic Powder",
        pp=20,
        type=Types.PSYCHIC,
    )
    MAGICROOM = Move(
        desc=r"For 5 turns, the held items of all active Pokemon have no effect. An item's effect of causing forme changes is unaffected, but any other effects from such items are negated. During the effect, Fling and Natural Gift are prevented from being used by all active Pokemon. If this move is used during the effect, the effect ends.",
        shortDesc=r"For 5 turns, all held items have no effect.",
        name=r"Magic Room",
        pp=10,
        type=Types.PSYCHIC,
    )
    MAGMASTORM = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=75,
        base=100,
        category=Category.SPECIAL,
        name=r"Magma Storm",
        pp=5,
        type=Types.FIRE,
    )
    MAGNETBOMB = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.PHYSICAL,
        name=r"Magnet Bomb",
        pp=20,
        type=Types.STEEL,
    )
    MAGNETICFLUX = Move(
        desc=r"Raises the Defense and Special Defense of Pokemon on the user's side with the Plus or Minus Abilities by 1 stage.",
        shortDesc=r"Raises Def, Sp. Def of allies with Plus/Minus by 1.",
        name=r"Magnetic Flux",
        pp=20,
        type=Types.ELECTRIC,
    )
    MAGNETRISE = Move(
        desc=r"For 5 turns, the user is immune to Ground-type attacks and the effects of Spikes, Toxic Spikes, Sticky Web, and the Arena Trap Ability as long as it remains active. If the user uses Baton Pass, the replacement will gain the effect. Ingrain, Smack Down, Thousand Arrows, and Iron Ball override this move if the user is under any of their effects. Fails if the user is already under this effect or the effects of Ingrain, Smack Down, or Thousand Arrows.",
        shortDesc=r"For 5 turns, the user has immunity to Ground.",
        name=r"Magnet Rise",
        pp=10,
        type=Types.ELECTRIC,
    )
    MAGNITUDE = Move(
        desc=r"The power of this move varies; 5% chances for 10 and 150 power, 10% chances for 30 and 110 power, 20% chances for 50 and 90 power, and 30% chance for 70 power. Damage doubles if the target is using Dig.",
        shortDesc=r"Hits adjacent Pokemon. Power varies; 2x on Dig.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Magnitude",
        pp=30,
        type=Types.GROUND,
    )
    MATBLOCK = Move(
        desc=r"The user and its party members are protected from damaging attacks made by other Pokemon, including allies, during this turn. Fails unless it is the user's first turn on the field, if the user moves last this turn, or if this move is already in effect for the user's side.",
        shortDesc=r"Protects allies from damaging attacks. Turn 1 only.",
        name=r"Mat Block",
        pp=10,
        type=Types.FIGHTING,
    )
    MEANLOOK = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Prevents the target from switching out.",
        name=r"Mean Look",
        pp=5,
    )
    MEDITATE = Move(
        desc=r"Raises the user's Attack by 1 stage.",
        shortDesc=r"Raises the user's Attack by 1.",
        name=r"Meditate",
        pp=40,
        type=Types.PSYCHIC,
    )
    MEFIRST = Move(
        desc=r"The user uses the move the target chose for use this turn against it, if possible, with its power multiplied by 1.5. The move must be a damaging move other than Beak Blast, Chatter, Counter, Covet, Focus Punch, Me First, Metal Burst, Mirror Coat, Shell Trap, Struggle, Thief, or any Z-Move. Fails if the target moves before the user. Ignores the target's substitute for the purpose of copying the move.",
        shortDesc=r"Copies a foe at 1.5x power. User must be faster.",
        name=r"Me First",
        pp=20,
    )
    MEGADRAIN = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Mega Drain",
        pp=15,
        type=Types.GRASS,
    )
    MEGAHORN = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=85,
        base=120,
        category=Category.PHYSICAL,
        name=r"Megahorn",
        pp=10,
        type=Types.BUG,
    )
    MEGAKICK = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=75,
        base=120,
        category=Category.PHYSICAL,
        name=r"Mega Kick",
        pp=5,
    )
    MEGAPUNCH = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=85,
        base=80,
        category=Category.PHYSICAL,
        name=r"Mega Punch",
        pp=20,
    )
    MEMENTO = Move(
        desc=r"Lowers the target's Attack and Special Attack by 2 stages. The user faints unless this move misses or there is no target. Fails entirely if this move hits a substitute, but does not fail if the target's stats cannot be changed.",
        shortDesc=r"Lowers target's Attack, Sp. Atk by 2. User faints.",
        accuracy=100,
        name=r"Memento",
        pp=10,
        type=Types.DARK,
    )
    METALBURST = Move(
        desc=r"Deals damage to the last opposing Pokemon to hit the user with an attack this turn equal to 1.5 times the HP lost by the user from that attack, rounded down. If the user did not lose HP from the attack, this move deals 1 HP of damage instead. If that opposing Pokemon's position is no longer in use and there is another opposing Pokemon on the field, the damage is done to it instead. Only the last hit of a multi-hit attack is counted. Fails if the user was not hit by an opposing Pokemon's attack this turn.",
        shortDesc=r"If hit by an attack, returns 1.5x damage.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Metal Burst",
        pp=10,
        type=Types.STEEL,
    )
    METALCLAW = Move(
        desc=r"Has a 10% chance to raise the user's Attack by 1 stage.",
        shortDesc=r"10% chance to raise the user's Attack by 1.",
        accuracy=95,
        base=50,
        category=Category.PHYSICAL,
        name=r"Metal Claw",
        pp=35,
        type=Types.STEEL,
    )
    METALSOUND = Move(
        desc=r"Lowers the target's Special Defense by 2 stages.",
        shortDesc=r"Lowers the target's Sp. Def by 2.",
        accuracy=85,
        name=r"Metal Sound",
        pp=40,
        type=Types.STEEL,
    )
    METEORASSAULT = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=100,
        base=150,
        category=Category.PHYSICAL,
        name=r"Meteor Assault",
        pp=5,
        type=Types.FIGHTING,
    )
    METEORBEAM = Move(
        desc=r"This attack charges on the first turn and executes on the second. Raises the user's Special Attack by 1 stage on the first turn. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Raises user's Sp. Atk by 1 on turn 1. Hits turn 2.",
        accuracy=9,
        base=120,
        category=Category.SPECIAL,
        name=r"Meteor Beam",
        pp=10,
        type=Types.ROCK,
    )
    METEORMASH = Move(
        desc=r"Has a 20% chance to raise the user's Attack by 1 stage.",
        shortDesc=r"20% chance to raise the user's Attack by 1.",
        accuracy=9,
        base=90,
        category=Category.PHYSICAL,
        name=r"Meteor Mash",
        pp=10,
        type=Types.STEEL,
    )
    METRONOME = Move(
        desc=r"A random move is selected for use, other than After You, Apple Acid, Assist, Aura Wheel, Baneful Bunker, Beak Blast, Behemoth Bash, Behemoth Blade, Belch, Bestow, Body Press, Branch Poke, Breaking Swipe, Celebrate, Chatter, Clangorous Soul, Copycat, Counter, Covet, Crafty Shield, Decorate, Destiny Bond, Detect, Diamond Storm, Double Iron Bash, Dragon Ascent, Drum Beating, Dynamax Cannon, Endure, Eternabeam, False Surrender, Feint, Fleur Cannon, Focus Punch, Follow Me, Freeze Shock, Grav Apple, Helping Hand, Hold Hands, Hyperspace Fury, Hyperspace Hole, Ice Burn, Instruct, King's Shield, Life Dew, Light of Ruin, Mat Block, Me First, Meteor Assault, Metronome, Mimic, Mind Blown, Mirror Coat, Mirror Move, Moongeist Beam, Nature Power, Nature's Madness, Obstruct, Origin Pulse, Overdrive, Photon Geyser, Plasma Fists, Precipice Blades, Protect, Pyro Ball, Quash, Quick Guard, Rage Powder, Relic Song, Secret Sword, Shell Trap, Sketch, Sleep Talk, Snap Trap, Snarl, Snatch, Snore, Spectral Thief, Spiky Shield, Spirit Break, Spotlight, Steam Eruption, Steel Beam, Strange Steam, Struggle, Sunsteel Strike, Switcheroo, Techno Blast, Thief, Thousand Arrows, Thousand Waves, Transform, Trick, V-create, or Wide Guard.",
        shortDesc=r"Picks a random move.",
        name=r"Metronome",
        pp=10,
    )
    MILKDRINK = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user by 50% of its max HP.",
        name=r"Milk Drink",
        pp=10,
    )
    MIMIC = Move(
        desc=r"While the user remains active, this move is replaced by the last move used by the target. The copied move has the maximum PP for that move. Fails if the target has not made a move, if the user has Transformed, if the user already knows the move, or if the move is Chatter, Mimic, Sketch, Struggle, Transform, or any Z-Move.",
        shortDesc=r"The last move the target used replaces this one.",
        name=r"Mimic",
        pp=10,
    )
    MINDBLOWN = Move(
        desc=r"Whether or not this move is successful and even if it would cause fainting, the user loses 1/2 of its maximum HP, rounded up, unless the user has the Magic Guard Ability. This move is prevented from executing and the user does not lose HP if any active Pokemon has the Damp Ability, or if this move is Fire type and the user is affected by Powder or the weather is Primordial Sea.",
        shortDesc=r"User loses 50% max HP. Hits adjacent Pokemon.",
        accuracy=100,
        base=150,
        category=Category.SPECIAL,
        name=r"Mind Blown",
        pp=5,
        type=Types.FIRE,
    )
    MINDREADER = Move(
        desc=r"Until the end of the next turn, the target cannot avoid the user's moves, even if the target is in the middle of a two-turn move. The effect ends if either the user or the target leaves the field. Fails if this effect is active for the user.",
        shortDesc=r"User's next move will not miss the target.",
        name=r"Mind Reader",
        pp=5,
    )
    MINIMIZE = Move(
        desc=r"Raises the user's evasiveness by 2 stages. Whether or not the user's evasiveness was changed, Body Slam, Dragon Rush, Flying Press, Heat Crash, Heavy Slam, Malicious Moonsault, Steamroller, and Stomp will not check accuracy and have their damage doubled if used against the user while it is active.",
        shortDesc=r"Raises the user's evasiveness by 2.",
        name=r"Minimize",
        pp=10,
    )
    MIRACLEEYE = Move(
        desc=r"As long as the target remains active, its evasiveness stat stage is ignored during accuracy checks against it if it is greater than 0, and Psychic-type attacks can hit the target if it is a Dark type. Fails if the target is already affected, or affected by Foresight or Odor Sleuth.",
        shortDesc=r"Psychic hits Dark. Evasiveness ignored.",
        name=r"Miracle Eye",
        pp=40,
        type=Types.PSYCHIC,
    )
    MIRRORCOAT = Move(
        desc=r"Deals damage to the last opposing Pokemon to hit the user with a special attack this turn equal to twice the HP lost by the user from that attack. If the user did not lose HP from the attack, this move deals 1 HP of damage instead. If that opposing Pokemon's position is no longer in use and there is another opposing Pokemon on the field, the damage is done to it instead. Only the last hit of a multi-hit attack is counted. Fails if the user was not hit by an opposing Pokemon's special attack this turn.",
        shortDesc=r"If hit by special attack, returns double damage.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Mirror Coat",
        pp=20,
        type=Types.PSYCHIC,
    )
    MIRRORMOVE = Move(
        desc=r"The user uses the last move used by the target. The copied move is used against that target, if possible. Fails if the target has not made a move, or if the last move used cannot be copied by this move.",
        shortDesc=r"User uses the target's last used move against it.",
        name=r"Mirror Move",
        pp=20,
        type=Types.FLYING,
    )
    MIRRORSHOT = Move(
        desc=r"Has a 30% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"30% chance to lower the target's accuracy by 1.",
        accuracy=85,
        base=65,
        category=Category.SPECIAL,
        name=r"Mirror Shot",
        pp=10,
        type=Types.STEEL,
    )
    MIST = Move(
        desc=r"For 5 turns, the user and its party members are protected from having their stat stages lowered by other Pokemon. Fails if the effect is already active on the user's side.",
        shortDesc=r"For 5 turns, protects user's party from stat drops.",
        name=r"Mist",
        pp=30,
        type=Types.ICE,
    )
    MISTBALL = Move(
        desc=r"Has a 50% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"50% chance to lower the target's Sp. Atk by 1.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Mist Ball",
        pp=5,
        type=Types.PSYCHIC,
    )
    MISTYEXPLOSION = Move(
        desc=r"If the current terrain is Misty Terrain and the user is grounded, this move's power is multiplied by 1.5. The user faints after using this move, even if this move fails for having no target. This move is prevented from executing if any active Pokemon has the Damp Ability.",
        shortDesc=r"User faints. User on Misty Terrain: 1.5x power.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Misty Explosion",
        pp=5,
        type=Types.FAIRY,
    )
    MISTYTERRAIN = Move(
        desc=r"For 5 turns, the terrain becomes Misty Terrain. During the effect, the power of Dragon-type attacks used against grounded Pokemon is multiplied by 0.5 and grounded Pokemon cannot be inflicted with a major status condition nor confusion. Camouflage transforms the user into a Fairy type, Nature Power becomes Moonblast, and Secret Power has a 30% chance to lower Special Attack by 1 stage. Fails if the current terrain is Misty Terrain.",
        shortDesc=r"5 turns. Can't status,-Dragon power vs grounded.",
        name=r"Misty Terrain",
        pp=10,
        type=Types.FAIRY,
    )
    MOONBLAST = Move(
        desc=r"Has a 30% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"30% chance to lower the target's Sp. Atk by 1.",
        accuracy=100,
        base=95,
        category=Category.SPECIAL,
        name=r"Moonblast",
        pp=15,
        type=Types.FAIRY,
    )
    MOONGEISTBEAM = Move(
        desc=r"This move and its effects ignore the Abilities of other Pokemon.",
        shortDesc=r"Ignores the Abilities of other Pokemon.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Moongeist Beam",
        pp=5,
        type=Types.GHOST,
    )
    MOONLIGHT = Move(
        desc=r"The user restores 1/2 of its maximum HP if Delta Stream or no weather conditions are in effect or if the user is holding Utility Umbrella, 2/3 of its maximum HP if the weather is Desolate Land or Sunny Day, and 1/4 of its maximum HP if the weather is Hail, Primordial Sea, Rain Dance, or Sandstorm, all rounded half down.",
        shortDesc=r"Heals the user by a weather-dependent amount.",
        name=r"Moonlight",
        pp=5,
        type=Types.FAIRY,
    )
    MORNINGSUN = Move(
        desc=r"The user restores 1/2 of its maximum HP if Delta Stream or no weather conditions are in effect or if the user is holding Utility Umbrella, 2/3 of its maximum HP if the weather is Desolate Land or Sunny Day, and 1/4 of its maximum HP if the weather is Hail, Primordial Sea, Rain Dance, or Sandstorm, all rounded half down.",
        shortDesc=r"Heals the user by a weather-dependent amount.",
        name=r"Morning Sun",
        pp=5,
    )
    MUDBOMB = Move(
        desc=r"Has a 30% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"30% chance to lower the target's accuracy by 1.",
        accuracy=85,
        base=65,
        category=Category.SPECIAL,
        name=r"Mud Bomb",
        pp=10,
        type=Types.GROUND,
    )
    MUDSHOT = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the target's Speed by 1.",
        accuracy=95,
        base=55,
        category=Category.SPECIAL,
        name=r"Mud Shot",
        pp=15,
        type=Types.GROUND,
    )
    MUDSLAP = Move(
        desc=r"Has a 100% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"100% chance to lower the target's accuracy by 1.",
        accuracy=100,
        base=20,
        category=Category.SPECIAL,
        name=r"Mud-Slap",
        pp=10,
        type=Types.GROUND,
    )
    MUDSPORT = Move(
        desc=r"For 5 turns, all Electric-type attacks used by any active Pokemon have their power multiplied by 0.33. Fails if this effect is already active.",
        shortDesc=r"For 5 turns, Electric-type attacks have 1/3 power.",
        name=r"Mud Sport",
        pp=15,
        type=Types.GROUND,
    )
    MUDDYWATER = Move(
        desc=r"Has a 30% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"30% chance to lower the foe(s) accuracy by 1.",
        accuracy=85,
        base=90,
        category=Category.SPECIAL,
        name=r"Muddy Water",
        pp=10,
        type=Types.WATER,
    )
    MULTIATTACK = Move(
        desc=r"This move's type depends on the user's held Memory.",
        shortDesc=r"Type varies based on the held Memory.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Multi-Attack",
        pp=10,
    )
    MYSTICALFIRE = Move(
        desc=r"Has a 100% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"100% chance to lower the target's Sp. Atk by 1.",
        accuracy=100,
        base=75,
        category=Category.SPECIAL,
        name=r"Mystical Fire",
        pp=10,
        type=Types.FIRE,
    )
    NASTYPLOT = Move(
        desc=r"Raises the user's Special Attack by 2 stages.",
        shortDesc=r"Raises the user's Sp. Atk by 2.",
        name=r"Nasty Plot",
        pp=20,
        type=Types.DARK,
    )
    NATURALGIFT = Move(
        desc=r"The type and power of this move depend on the user's held Berry, and the Berry is lost. Fails if the user is not holding a Berry, if the user has the Klutz Ability, or if Embargo or Magic Room is in effect for the user.",
        shortDesc=r"Power and type depends on the user's Berry.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Natural Gift",
        pp=15,
    )
    NATUREPOWER = Move(
        desc=r"This move calls another move for use based on the battle terrain. Tri Attack on the regular Wi-Fi terrain, Thunderbolt during Electric Terrain, Moonblast during Misty Terrain, Energy Ball during Grassy Terrain, and Psychic during Psychic Terrain.",
        shortDesc=r"Attack depends on terrain (default Tri Attack).",
        name=r"Nature Power",
        pp=20,
    )
    NATURESMADNESS = Move(
        desc=r"Deals damage to the target equal to half of its current HP, rounded down, but not less than 1 HP.",
        shortDesc=r"Does damage equal to 1/2 target's current HP.",
        accuracy=9,
        category=Category.SPECIAL,
        name=r"Nature's Madness",
        pp=10,
        type=Types.FAIRY,
    )
    NEEDLEARM = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Needle Arm",
        pp=15,
        type=Types.GRASS,
    )
    NIGHTDAZE = Move(
        desc=r"Has a 40% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"40% chance to lower the target's accuracy by 1.",
        accuracy=95,
        base=85,
        category=Category.SPECIAL,
        name=r"Night Daze",
        pp=10,
        type=Types.DARK,
    )
    NIGHTMARE = Move(
        desc=r"Causes the target to lose 1/4 of its maximum HP, rounded down, at the end of each turn as long as it is asleep. This move does not affect the target unless it is asleep. The effect ends when the target wakes up, even if it falls asleep again in the same turn.",
        shortDesc=r"A sleeping target is hurt by 1/4 max HP per turn.",
        accuracy=100,
        name=r"Nightmare",
        pp=15,
        type=Types.GHOST,
    )
    NIGHTSHADE = Move(
        desc=r"Deals damage to the target equal to the user's level.",
        shortDesc=r"Does damage equal to the user's level.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Night Shade",
        pp=15,
        type=Types.GHOST,
    )
    NIGHTSLASH = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Night Slash",
        pp=15,
        type=Types.DARK,
    )
    NOBLEROAR = Move(
        desc=r"Lowers the target's Attack and Special Attack by 1 stage.",
        shortDesc=r"Lowers the target's Attack and Sp. Atk by 1.",
        accuracy=100,
        name=r"Noble Roar",
        pp=30,
    )
    NORETREAT = Move(
        desc=r"Raises the user's Attack, Defense, Special Attack, Special Defense, and Speed by 1 stage, but it becomes prevented from switching out. The user can still switch out if it uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the user leaves the field using Baton Pass, the replacement will remain trapped. Fails if the user has already been prevented from switching by this effect.",
        shortDesc=r"Raises all stats by 1 (not acc/eva). Traps user.",
        name=r"No Retreat",
        pp=5,
        type=Types.FIGHTING,
    )
    NUZZLE = Move(
        desc=r"Has a 100% chance to paralyze the target.",
        shortDesc=r"100% chance to paralyze the target.",
        accuracy=100,
        base=20,
        category=Category.PHYSICAL,
        name=r"Nuzzle",
        pp=20,
        type=Types.ELECTRIC,
    )
    OBLIVIONWING = Move(
        desc=r"The user recovers 3/4 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 75% of the damage dealt.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Oblivion Wing",
        pp=10,
        type=Types.FLYING,
    )
    OBSTRUCT = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn, and Pokemon trying to make contact with the user have their Defense lowered by 2 stages. Non-damaging moves go through this protection. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Max Guard, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Protects from damaging attacks. Contact: -2 Def.",
        name=r"Obstruct",
        pp=10,
        type=Types.DARK,
    )
    OCTAZOOKA = Move(
        desc=r"Has a 50% chance to lower the target's accuracy by 1 stage.",
        shortDesc=r"50% chance to lower the target's accuracy by 1.",
        accuracy=85,
        base=65,
        category=Category.SPECIAL,
        name=r"Octazooka",
        pp=10,
        type=Types.WATER,
    )
    OCTOLOCK = Move(
        desc=r"Prevents the target from switching out. At the end of each turn during effect, the target's Defense and Special Defense are lowered by 1 stage. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Traps target, lowers Def and SpD by 1 each turn.",
        accuracy=100,
        name=r"Octolock",
        pp=15,
        type=Types.FIGHTING,
    )
    ODORSLEUTH = Move(
        desc=r"As long as the target remains active, its evasiveness stat stage is ignored during accuracy checks against it if it is greater than 0, and Normal- and Fighting-type attacks can hit the target if it is a Ghost type. Fails if the target is already affected, or affected by Foresight or Miracle Eye.",
        shortDesc=r"Fighting, Normal hit Ghost. Evasiveness ignored.",
        name=r"Odor Sleuth",
        pp=40,
    )
    OMINOUSWIND = Move(
        desc=r"Has a 10% chance to raise the user's Attack, Defense, Special Attack, Special Defense, and Speed by 1 stage.",
        shortDesc=r"10% chance to raise all stats by 1 (not acc/eva).",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Ominous Wind",
        pp=5,
        type=Types.GHOST,
    )
    ORIGINPULSE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent foes.",
        accuracy=85,
        base=110,
        category=Category.SPECIAL,
        name=r"Origin Pulse",
        pp=10,
        type=Types.WATER,
    )
    OUTRAGE = Move(
        desc=r"The user spends two or three turns locked into this move and becomes confused immediately after its move on the last turn of the effect if it is not already. This move targets an opposing Pokemon at random on each turn. If the user is prevented from moving, is asleep at the beginning of a turn, or the attack is not successful against the target on the first turn of the effect or the second turn of a three-turn effect, the effect ends without causing confusion. If this move is called by Sleep Talk and the user is asleep, the move is used for one turn and does not confuse the user.",
        shortDesc=r"Lasts 2-3 turns. Confuses the user afterwards.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Outrage",
        pp=10,
        type=Types.DRAGON,
    )
    OVERDRIVE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits foe(s).",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Overdrive",
        pp=10,
        type=Types.ELECTRIC,
    )
    OVERHEAT = Move(
        desc=r"Lowers the user's Special Attack by 2 stages.",
        shortDesc=r"Lowers the user's Sp. Atk by 2.",
        accuracy=9,
        base=130,
        category=Category.SPECIAL,
        name=r"Overheat",
        pp=5,
        type=Types.FIRE,
    )
    PAINSPLIT = Move(
        desc=r"The user and the target's HP become the average of their current HP, rounded down, but not more than the maximum HP of either one.",
        shortDesc=r"Shares HP of user and target equally.",
        name=r"Pain Split",
        pp=20,
    )
    PALEOWAVE = Move(
        desc=r"Has a 20% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"20% chance to lower the target's Attack by 1.",
        accuracy=100,
        base=85,
        category=Category.SPECIAL,
        name=r"Paleo Wave",
        pp=15,
        type=Types.ROCK,
    )
    PARABOLICCHARGE = Move(
        desc=r"The user recovers 1/2 the HP lost by the target, rounded half up. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down.",
        shortDesc=r"User recovers 50% of the damage dealt.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Parabolic Charge",
        pp=20,
        type=Types.ELECTRIC,
    )
    PARTINGSHOT = Move(
        desc=r"Lowers the target's Attack and Special Attack by 1 stage. If this move is successful, the user switches out even if it is trapped and is replaced immediately by a selected party member. The user does not switch out if the target's Attack and Special Attack stat stages were both unchanged, or if there are no unfainted party members.",
        shortDesc=r"Lowers target's Atk, Sp. Atk by 1. User switches.",
        accuracy=100,
        name=r"Parting Shot",
        pp=20,
        type=Types.DARK,
    )
    PAYBACK = Move(
        desc=r"Power doubles if the user moves after the target this turn, including actions taken through Instruct or the Dancer Ability. Switching in does not count as an action.",
        shortDesc=r"Power doubles if the user moves after the target.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Payback",
        pp=10,
        type=Types.DARK,
    )
    PAYDAY = Move(
        desc=r"No additional effect.",
        shortDesc=r"Scatters coins.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Pay Day",
        pp=20,
    )
    PECK = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=35,
        category=Category.PHYSICAL,
        name=r"Peck",
        pp=35,
        type=Types.FLYING,
    )
    PERISHSONG = Move(
        desc=r"Each active Pokemon receives a perish count of 4 if it doesn't already have a perish count. At the end of each turn including the turn used, the perish count of all active Pokemon lowers by 1 and Pokemon faint if the number reaches 0. The perish count is removed from Pokemon that switch out. If a Pokemon uses Baton Pass while it has a perish count, the replacement will gain the perish count and continue to count down.",
        shortDesc=r"All active Pokemon will faint in 3 turns.",
        name=r"Perish Song",
        pp=5,
    )
    PETALBLIZZARD = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent Pokemon.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Petal Blizzard",
        pp=15,
        type=Types.GRASS,
    )
    PETALDANCE = Move(
        desc=r"The user spends two or three turns locked into this move and becomes confused immediately after its move on the last turn of the effect if it is not already. This move targets an opposing Pokemon at random on each turn. If the user is prevented from moving, is asleep at the beginning of a turn, or the attack is not successful against the target on the first turn of the effect or the second turn of a three-turn effect, the effect ends without causing confusion. If this move is called by Sleep Talk and the user is asleep, the move is used for one turn and does not confuse the user.",
        shortDesc=r"Lasts 2-3 turns. Confuses the user afterwards.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Petal Dance",
        pp=10,
        type=Types.GRASS,
    )
    PHANTOMFORCE = Move(
        desc=r"If this move is successful, it breaks through the target's Baneful Bunker, Detect, King's Shield, Protect, or Spiky Shield for this turn, allowing other Pokemon to attack the target normally. If the target's side is protected by Crafty Shield, Mat Block, Quick Guard, or Wide Guard, that protection is also broken for this turn and other Pokemon may attack the target's side normally. This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Disappears turn 1. Hits turn 2. Breaks protection.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Phantom Force",
        pp=10,
        type=Types.GHOST,
    )
    PHOTONGEYSER = Move(
        desc=r"This move becomes a physical attack if the user's Attack is greater than its Special Attack, including stat stage changes. This move and its effects ignore the Abilities of other Pokemon.",
        shortDesc=r"Physical if user's Atk > Sp. Atk. Ignores Abilities.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Photon Geyser",
        pp=5,
        type=Types.PSYCHIC,
    )
    PIKAPAPOW = Move(
        desc=r"Power is equal to the greater of (user's Happiness * 2/5) rounded down, or 1.",
        shortDesc=r"Max happiness: 102 power. Can't miss.",
        category=Category.SPECIAL,
        name=r"Pika Papow",
        pp=20,
        type=Types.ELECTRIC,
    )
    PINMISSILE = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=95,
        base=25,
        category=Category.PHYSICAL,
        name=r"Pin Missile",
        pp=20,
        type=Types.BUG,
    )
    PLASMAFISTS = Move(
        desc=r"If this move is successful, causes Normal-type moves to become Electric type this turn.",
        shortDesc=r"Normal moves become Electric type this turn.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Plasma Fists",
        pp=15,
        type=Types.ELECTRIC,
    )
    PLAYNICE = Move(
        desc=r"Lowers the target's Attack by 1 stage.",
        shortDesc=r"Lowers the target's Attack by 1.",
        name=r"Play Nice",
        pp=20,
    )
    PLAYROUGH = Move(
        desc=r"Has a 10% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"10% chance to lower the target's Attack by 1.",
        accuracy=9,
        base=90,
        category=Category.PHYSICAL,
        name=r"Play Rough",
        pp=10,
        type=Types.FAIRY,
    )
    PLUCK = Move(
        desc=r"If this move is successful and the user has not fainted, it steals the target's held Berry if it is holding one and eats it immediately, gaining its effects even if the user's item is being ignored. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"User steals and eats the target's Berry.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Pluck",
        pp=20,
        type=Types.FLYING,
    )
    POISONFANG = Move(
        desc=r"Has a 50% chance to badly poison the target.",
        shortDesc=r"50% chance to badly poison the target.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Poison Fang",
        pp=15,
        type=Types.POISON,
    )
    POISONGAS = Move(
        desc=r"Poisons the target.",
        shortDesc=r"Poisons the foe(s).",
        accuracy=9,
        name=r"Poison Gas",
        pp=40,
        type=Types.POISON,
    )
    POISONJAB = Move(
        desc=r"Has a 30% chance to poison the target.",
        shortDesc=r"30% chance to poison the target.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Poison Jab",
        pp=20,
        type=Types.POISON,
    )
    POISONPOWDER = Move(
        desc=r"Poisons the target.",
        shortDesc=r"Poisons the target.",
        accuracy=75,
        name=r"Poison Powder",
        pp=35,
        type=Types.POISON,
    )
    POISONSTING = Move(
        desc=r"Has a 30% chance to poison the target.",
        shortDesc=r"30% chance to poison the target.",
        accuracy=100,
        base=15,
        category=Category.PHYSICAL,
        name=r"Poison Sting",
        pp=35,
        type=Types.POISON,
    )
    POISONTAIL = Move(
        desc=r"Has a 10% chance to poison the target and a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio. 10% chance to poison.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Poison Tail",
        pp=25,
        type=Types.POISON,
    )
    POLLENPUFF = Move(
        desc=r"If the target is an ally, this move restores 1/2 of its maximum HP, rounded down, instead of dealing damage.",
        shortDesc=r"If the target is an ally, heals 50% of its max HP.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Pollen Puff",
        pp=15,
        type=Types.BUG,
    )
    POLTERGEIST = Move(
        desc=r"Fails if the target has no held item.",
        shortDesc=r"Fails if the target has no held item.",
        accuracy=9,
        base=110,
        category=Category.PHYSICAL,
        name=r"Poltergeist",
        pp=5,
        type=Types.GHOST,
    )
    POUND = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Pound",
        pp=35,
    )
    POWDER = Move(
        desc=r"If the target uses a Fire-type move this turn, it is prevented from executing and the target loses 1/4 of its maximum HP, rounded half up. This effect does not happen if the Fire-type move is prevented by Primordial Sea.",
        shortDesc=r"If using a Fire move, target loses 1/4 max HP.",
        accuracy=100,
        name=r"Powder",
        pp=20,
        type=Types.BUG,
    )
    POWDERSNOW = Move(
        desc=r"Has a 10% chance to freeze the target.",
        shortDesc=r"10% chance to freeze the foe(s).",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Powder Snow",
        pp=25,
        type=Types.ICE,
    )
    POWERGEM = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Power Gem",
        pp=20,
        type=Types.ROCK,
    )
    POWERSPLIT = Move(
        desc=r"The user and the target have their Attack and Special Attack stats set to be equal to the average of the user and the target's Attack and Special Attack stats, respectively, rounded down. Stat stage changes are unaffected.",
        shortDesc=r"Averages Attack and Sp. Atk stats with target.",
        name=r"Power Split",
        pp=10,
        type=Types.PSYCHIC,
    )
    POWERSWAP = Move(
        desc=r"The user swaps its Attack and Special Attack stat stage changes with the target.",
        shortDesc=r"Swaps Attack and Sp. Atk stat stages with target.",
        name=r"Power Swap",
        pp=10,
        type=Types.PSYCHIC,
    )
    POWERTRICK = Move(
        desc=r"The user swaps its Attack and Defense stats, and stat stage changes remain on their respective stats. This move can be used again to swap the stats back. If the user uses Baton Pass, the replacement will have its Attack and Defense stats swapped if the effect is active. If the user has its stats recalculated by changing forme while its stats are swapped, this effect is ignored but is still active for the purposes of Baton Pass.",
        shortDesc=r"Switches user's Attack and Defense stats.",
        name=r"Power Trick",
        pp=10,
        type=Types.PSYCHIC,
    )
    POWERTRIP = Move(
        desc=r"Power is equal to 20+(X*20) where X is the user's total stat stage changes that are greater than 0.",
        shortDesc=r" + 20 power for each of the user's stat boosts.",
        accuracy=100,
        base=20,
        category=Category.PHYSICAL,
        name=r"Power Trip",
        pp=10,
        type=Types.DARK,
    )
    POWERUPPUNCH = Move(
        desc=r"Has a 100% chance to raise the user's Attack by 1 stage.",
        shortDesc=r"100% chance to raise the user's Attack by 1.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Power-Up Punch",
        pp=20,
        type=Types.FIGHTING,
    )
    POWERWHIP = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=85,
        base=120,
        category=Category.PHYSICAL,
        name=r"Power Whip",
        pp=10,
        type=Types.GRASS,
    )
    PRECIPICEBLADES = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect. Hits adjacent foes.",
        accuracy=85,
        base=120,
        category=Category.PHYSICAL,
        name=r"Precipice Blades",
        pp=10,
        type=Types.GROUND,
    )
    PRESENT = Move(
        desc=r"If this move is successful, it deals damage or heals the target. 40% chance for 40 power, 30% chance for 80 power, 10% chance for 120 power, and 20% chance to heal the target by 1/4 of its maximum HP, rounded down.",
        shortDesc=r"40, 80, 120 power, or heals target 1/4 max HP.",
        accuracy=9,
        category=Category.PHYSICAL,
        name=r"Present",
        pp=15,
    )
    PRISMATICLASER = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=100,
        base=160,
        category=Category.SPECIAL,
        name=r"Prismatic Laser",
        pp=10,
        type=Types.PSYCHIC,
    )
    PROTECT = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Prevents moves from affecting the user this turn.",
        name=r"Protect",
        pp=10,
    )
    PSYBEAM = Move(
        desc=r"Has a 10% chance to confuse the target.",
        shortDesc=r"10% chance to confuse the target.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Psybeam",
        pp=20,
        type=Types.PSYCHIC,
    )
    PSYCHUP = Move(
        desc=r"The user copies all of the target's current stat stage changes.",
        shortDesc=r"Copies the target's current stat stages.",
        name=r"Psych Up",
        pp=10,
    )
    PSYCHIC = Move(
        desc=r"Has a 10% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"10% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Psychic",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYCHICFANGS = Move(
        desc=r"If this attack does not miss, the effects of Reflect, Light Screen, and Aurora Veil end for the target's side of the field before damage is calculated.",
        shortDesc=r"Destroys screens, unless the target is immune.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Psychic Fangs",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYCHICTERRAIN = Move(
        desc=r"For 5 turns, the terrain becomes Psychic Terrain. During the effect, the power of Psychic-type attacks made by grounded Pokemon is multiplied by 1.3 and grounded Pokemon cannot be hit by moves with priority greater than 0, unless the target is an ally. Camouflage transforms the user into a Psychic type, Nature Power becomes Psychic, and Secret Power has a 30% chance to lower the target's Speed by 1 stage. Fails if the current terrain is Psychic Terrain.",
        shortDesc=r"5 turns. Grounded: +Psychic power, priority-safe.",
        name=r"Psychic Terrain",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYCHOBOOST = Move(
        desc=r"Lowers the user's Special Attack by 2 stages.",
        shortDesc=r"Lowers the user's Sp. Atk by 2.",
        accuracy=9,
        base=140,
        category=Category.SPECIAL,
        name=r"Psycho Boost",
        pp=5,
        type=Types.PSYCHIC,
    )
    PSYCHOCUT = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Psycho Cut",
        pp=20,
        type=Types.PSYCHIC,
    )
    PSYCHOSHIFT = Move(
        desc=r"The user's major status condition is transferred to the target, and the user is then cured. Fails if the user has no major status condition or if the target already has one.",
        shortDesc=r"Transfers the user's status ailment to the target.",
        accuracy=100,
        name=r"Psycho Shift",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYSHOCK = Move(
        desc=r"Deals damage to the target based on its Defense instead of Special Defense.",
        shortDesc=r"Damages target based on Defense, not Sp. Def.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Psyshock",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYSTRIKE = Move(
        desc=r"Deals damage to the target based on its Defense instead of Special Defense.",
        shortDesc=r"Damages target based on Defense, not Sp. Def.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Psystrike",
        pp=10,
        type=Types.PSYCHIC,
    )
    PSYWAVE = Move(
        desc=r"Deals damage to the target equal to (user's level) * (X + 50) / 100, where X is a random number from 0 to 100, rounded down, but not less than 1 HP.",
        shortDesc=r"Random damage equal to 0.5x-1.5x user's level.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Psywave",
        pp=15,
        type=Types.PSYCHIC,
    )
    PUNISHMENT = Move(
        desc=r"Power is equal to 60+(X*20) where X is the target's total stat stage changes that are greater than 0, but not more than 200 power.",
        shortDesc=r"60 power +20 for each of the target's stat boosts.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Punishment",
        pp=5,
        type=Types.DARK,
    )
    PURIFY = Move(
        desc=r"The target is cured if it has a major status condition. If the target was cured, the user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Cures target's status; heals user 1/2 max HP if so.",
        name=r"Purify",
        pp=20,
        type=Types.POISON,
    )
    PURSUIT = Move(
        desc=r"If an opposing Pokemon switches out this turn, this move hits that Pokemon before it leaves the field, even if it was not the original target. If the user moves after an opponent using Parting Shot, U-turn, or Volt Switch, but not Baton Pass, it will hit that opponent before it leaves the field. Power doubles and no accuracy check is done if the user hits an opponent switching out, and the user's turn is over; if an opponent faints from this, the replacement Pokemon does not become active until the end of the turn.",
        shortDesc=r"If a foe is switching out, hits it at 2x power.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Pursuit",
        pp=20,
        type=Types.DARK,
    )
    PYROBALL = Move(
        desc=r"Has a 10% chance to burn the target.",
        shortDesc=r"10% chance to burn the target. Thaws user.",
        accuracy=9,
        base=120,
        category=Category.PHYSICAL,
        name=r"Pyro Ball",
        pp=5,
        type=Types.FIRE,
    )
    QUASH = Move(
        desc=r"Causes the target to take its turn after all other Pokemon this turn, no matter the priority of its selected move. Fails if the target already moved this turn.",
        shortDesc=r"Forces the target to move last this turn.",
        accuracy=100,
        name=r"Quash",
        pp=15,
        type=Types.DARK,
    )
    QUICKATTACK = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Quick Attack",
        pp=30,
    )
    QUICKGUARD = Move(
        desc=r"The user and its party members are protected from attacks with original or altered priority greater than 0 made by other Pokemon, including allies, during this turn. This move modifies the same 1/X chance of being successful used by other protection moves, where X starts at 1 and triples each time this move is successfully used, but does not use the chance to check for failure. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn or if this move is already in effect for the user's side.",
        shortDesc=r"Protects allies from priority attacks this turn.",
        name=r"Quick Guard",
        pp=15,
        type=Types.FIGHTING,
    )
    QUIVERDANCE = Move(
        desc=r"Raises the user's Special Attack, Special Defense, and Speed by 1 stage.",
        shortDesc=r"Raises the user's Sp. Atk, Sp. Def, Speed by 1.",
        name=r"Quiver Dance",
        pp=20,
        type=Types.BUG,
    )
    RAGE = Move(
        desc=r"Once this move is successfully used, the user's Attack is raised by 1 stage every time it is hit by another Pokemon's attack as long as this move is chosen for use.",
        shortDesc=r"Raises the user's Attack by 1 if hit during use.",
        accuracy=100,
        base=20,
        category=Category.PHYSICAL,
        name=r"Rage",
        pp=20,
    )
    RAGEPOWDER = Move(
        desc=r"Until the end of the turn, all single-target attacks from the opposing side are redirected to the user. Such attacks are redirected to the user before they can be reflected by Magic Coat or the Magic Bounce Ability, or drawn in by the Lightning Rod or Storm Drain Abilities. Fails if it is not a Double Battle or Battle Royal. This effect is ignored while the user is under the effect of Sky Drop.",
        shortDesc=r"The foes' moves target the user on the turn used.",
        name=r"Rage Powder",
        pp=20,
        type=Types.BUG,
    )
    RAINDANCE = Move(
        desc=r"For 5 turns, the weather becomes Rain Dance. The damage of Water-type attacks is multiplied by 1.5 and the damage of Fire-type attacks is multiplied by 0.5 during the effect. Lasts for 8 turns if the user is holding Damp Rock. Fails if the current weather is Rain Dance.",
        shortDesc=r"For 5 turns, heavy rain powers Water moves.",
        name=r"Rain Dance",
        pp=5,
        type=Types.WATER,
    )
    RAPIDSPIN = Move(
        desc=r"If this move is successful and the user has not fainted, the effects of Leech Seed and binding moves end for the user, and all hazards are removed from the user's side of the field. Has a 100% chance to raise the user's Speed by 1 stage.",
        shortDesc=r"Free user from hazards/bind/Leech Seed; +1 Spe.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Rapid Spin",
        pp=40,
    )
    RAZORLEAF = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio. Hits adjacent foes.",
        accuracy=95,
        base=55,
        category=Category.PHYSICAL,
        name=r"Razor Leaf",
        pp=25,
        type=Types.GRASS,
    )
    RAZORSHELL = Move(
        desc=r"Has a 50% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"50% chance to lower the target's Defense by 1.",
        accuracy=95,
        base=75,
        category=Category.PHYSICAL,
        name=r"Razor Shell",
        pp=10,
        type=Types.WATER,
    )
    RAZORWIND = Move(
        desc=r"Has a higher chance for a critical hit. This attack charges on the first turn and executes on the second. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Charges, then hits foe(s) turn 2. High crit ratio.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Razor Wind",
        pp=10,
    )
    RECOVER = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user by 50% of its max HP.",
        name=r"Recover",
        pp=10,
    )
    RECYCLE = Move(
        desc=r"The user regains the item it last used. Fails if the user is holding an item, if the user has not held an item, if the item was a popped Air Balloon, if the item was picked up by a Pokemon with the Pickup Ability, or if the item was lost to Bug Bite, Covet, Incinerate, Knock Off, Pluck, or Thief. Items thrown with Fling can be regained.",
        shortDesc=r"Restores the item the user last used.",
        name=r"Recycle",
        pp=10,
    )
    REFLECT = Move(
        desc=r"For 5 turns, the user and its party members take 0.5x damage from physical attacks, or 0.66x damage if in a Double Battle. Damage is not reduced further with Aurora Veil. Critical hits ignore this effect. It is removed from the user's side if the user or an ally is successfully hit by Brick Break, Psychic Fangs, or Defog. Lasts for 8 turns if the user is holding Light Clay. Fails if the effect is already active on the user's side.",
        shortDesc=r"For 5 turns, physical damage to allies is halved.",
        name=r"Reflect",
        pp=20,
        type=Types.PSYCHIC,
    )
    REFLECTTYPE = Move(
        desc=r"Causes the user's types to become the same as the current types of the target. If the target's current types include typeless and a non-added type, typeless is ignored. If the target's current types include typeless and an added type from Forest's Curse or Trick-or-Treat, typeless is copied as the Normal type instead. Fails if the user is an Arceus or a Silvally, or if the target's current type is typeless alone.",
        shortDesc=r"User becomes the same type as the target.",
        name=r"Reflect Type",
        pp=15,
    )
    REFRESH = Move(
        desc=r"The user cures its burn, poison, or paralysis. Fails if the user is not burned, poisoned, or paralyzed.",
        shortDesc=r"User cures its burn, poison, or paralysis.",
        name=r"Refresh",
        pp=20,
    )
    RELICSONG = Move(
        desc=r"Has a 10% chance to cause the target to fall asleep. If this move is successful on at least one target and the user is a Meloetta, it changes to Pirouette Forme if it is currently in Aria Forme, or changes to Aria Forme if it is currently in Pirouette Forme. This forme change does not happen if the Meloetta has the Sheer Force Ability. The Pirouette Forme reverts to Aria Forme when Meloetta is not active.",
        shortDesc=r"10% chance to sleep foe(s). Meloetta transforms.",
        accuracy=100,
        base=75,
        category=Category.SPECIAL,
        name=r"Relic Song",
        pp=10,
    )
    REST = Move(
        desc=r"The user falls asleep for the next two turns and restores all of its HP, curing itself of any major status condition in the process. Fails if the user has full HP, is already asleep, or if another effect is preventing sleep.",
        shortDesc=r"User sleeps 2 turns and restores HP and status.",
        name=r"Rest",
        pp=10,
        type=Types.PSYCHIC,
    )
    RETALIATE = Move(
        desc=r"Power doubles if one of the user's party members fainted last turn.",
        shortDesc=r"Power doubles if an ally fainted last turn.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Retaliate",
        pp=5,
    )
    RETURN = Move(
        desc=r"Power is equal to the greater of (user's Happiness * 2/5) rounded down, or 1.",
        shortDesc=r"Max 102 power at maximum Happiness.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Return",
        pp=20,
    )
    REVELATIONDANCE = Move(
        desc=r"This move's type depends on the user's primary type. If the user's primary type is typeless, this move's type is the user's secondary type if it has one, otherwise the added type from Forest's Curse or Trick-or-Treat. This move is typeless if the user's type is typeless alone.",
        shortDesc=r"Type varies based on the user's primary type.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Revelation Dance",
        pp=15,
    )
    REVENGE = Move(
        desc=r"Power doubles if the user was hit by the target this turn.",
        shortDesc=r"Power doubles if user is damaged by the target.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Revenge",
        pp=10,
        type=Types.FIGHTING,
    )
    REVERSAL = Move(
        desc=r"The power of this move is 20 if X is 33 to 48, 40 if X is 17 to 32, 80 if X is 10 to 16, 100 if X is 5 to 9, 150 if X is 2 to 4, and 200 if X is 0 or 1, where X is equal to (user's current HP * 48 / user's maximum HP) rounded down.",
        shortDesc=r"More power the less HP the user has left.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Reversal",
        pp=15,
        type=Types.FIGHTING,
    )
    RISINGVOLTAGE = Move(
        desc=r"If the current terrain is Electric Terrain and the target is grounded, this move's power is doubled.",
        shortDesc=r"2x power if target is grounded in Electric Terrain.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Rising Voltage",
        pp=20,
        type=Types.ELECTRIC,
    )
    ROAR = Move(
        desc=r"The target is forced to switch out and be replaced with a random unfainted ally. Fails if the target is the last unfainted Pokemon in its party, or if the target used Ingrain previously or has the Suction Cups Ability.",
        shortDesc=r"Forces the target to switch to a random ally.",
        name=r"Roar",
        pp=20,
    )
    ROAROFTIME = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.SPECIAL,
        name=r"Roar of Time",
        pp=5,
        type=Types.DRAGON,
    )
    ROCKBLAST = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=9,
        base=25,
        category=Category.PHYSICAL,
        name=r"Rock Blast",
        pp=10,
        type=Types.ROCK,
    )
    ROCKCLIMB = Move(
        desc=r"Has a 20% chance to confuse the target.",
        shortDesc=r"20% chance to confuse the target.",
        accuracy=85,
        base=90,
        category=Category.PHYSICAL,
        name=r"Rock Climb",
        pp=20,
    )
    ROCKPOLISH = Move(
        desc=r"Raises the user's Speed by 2 stages.",
        shortDesc=r"Raises the user's Speed by 2.",
        name=r"Rock Polish",
        pp=20,
        type=Types.ROCK,
    )
    ROCKSLIDE = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the foe(s).",
        accuracy=9,
        base=75,
        category=Category.PHYSICAL,
        name=r"Rock Slide",
        pp=10,
        type=Types.ROCK,
    )
    ROCKSMASH = Move(
        desc=r"Has a 50% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"50% chance to lower the target's Defense by 1.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Rock Smash",
        pp=15,
        type=Types.FIGHTING,
    )
    ROCKTHROW = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=9,
        base=50,
        category=Category.PHYSICAL,
        name=r"Rock Throw",
        pp=15,
        type=Types.ROCK,
    )
    ROCKTOMB = Move(
        desc=r"Has a 100% chance to lower the target's Speed by 1 stage.",
        shortDesc=r"100% chance to lower the target's Speed by 1.",
        accuracy=95,
        base=60,
        category=Category.PHYSICAL,
        name=r"Rock Tomb",
        pp=15,
        type=Types.ROCK,
    )
    ROCKWRECKER = Move(
        desc=r"If this move is successful, the user must recharge on the following turn and cannot select a move.",
        shortDesc=r"User cannot move next turn.",
        accuracy=9,
        base=150,
        category=Category.PHYSICAL,
        name=r"Rock Wrecker",
        pp=5,
        type=Types.ROCK,
    )
    ROLEPLAY = Move(
        desc=r"The user's Ability changes to match the target's Ability. Fails if the user's Ability is Battle Bond, Comatose, Disguise, Multitype, Power Construct, RKS System, Schooling, Shields Down, Stance Change, or already matches the target, or if the target's Ability is Battle Bond, Comatose, Disguise, Flower Gift, Forecast, Illusion, Imposter, Multitype, Neutralizing Gas, Power Construct, Power of Alchemy, Receiver, RKS System, Schooling, Shields Down, Stance Change, Trace, Wonder Guard, or Zen Mode.",
        shortDesc=r"User replaces its Ability with the target's.",
        name=r"Role Play",
        pp=10,
        type=Types.PSYCHIC,
    )
    ROLLINGKICK = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=85,
        base=60,
        category=Category.PHYSICAL,
        name=r"Rolling Kick",
        pp=15,
        type=Types.FIGHTING,
    )
    ROLLOUT = Move(
        desc=r"If this move is successful, the user is locked into this move and cannot make another move until it misses, 5 turns have passed, or the attack cannot be used. Power doubles with each successful hit of this move and doubles again if Defense Curl was used previously by the user. If this move is called by Sleep Talk, the move is used for one turn. If this move hits an active Disguise during the effect, the power multiplier is paused but the turn counter is not, potentially allowing the multiplier to be used on the user's next move after this effect ends.",
        shortDesc=r"Power doubles with each hit. Repeats for 5 turns.",
        accuracy=9,
        base=30,
        category=Category.PHYSICAL,
        name=r"Rollout",
        pp=20,
        type=Types.ROCK,
    )
    ROOST = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up. Until the end of the turn, Flying-type users lose their Flying type and pure Flying-type users become Normal type. Does nothing if the user's HP is full.",
        shortDesc=r"Heals 50% HP. Flying-type removed 'til turn ends.",
        name=r"Roost",
        pp=10,
        type=Types.FLYING,
    )
    ROTOTILLER = Move(
        desc=r"Raises the Attack and Special Attack of all grounded Grass-type Pokemon on the field by 1 stage.",
        shortDesc=r"Raises Atk/Sp. Atk of grounded Grass types by 1.",
        name=r"Rototiller",
        pp=10,
        type=Types.GROUND,
    )
    ROUND = Move(
        desc=r"If there are other active Pokemon that chose this move for use this turn, those Pokemon take their turn immediately after the user, in Speed order, and this move's power is 120 for each other user.",
        shortDesc=r"Power doubles if others used Round this turn.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Round",
        pp=15,
    )
    SACREDFIRE = Move(
        desc=r"Has a 50% chance to burn the target.",
        shortDesc=r"50% chance to burn the target. Thaws user.",
        accuracy=95,
        base=100,
        category=Category.PHYSICAL,
        name=r"Sacred Fire",
        pp=5,
        type=Types.FIRE,
    )
    SACREDSWORD = Move(
        desc=r"Ignores the target's stat stage changes, including evasiveness.",
        shortDesc=r"Ignores the target's stat stage changes.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Sacred Sword",
        pp=15,
        type=Types.FIGHTING,
    )
    SAFEGUARD = Move(
        desc=r"For 5 turns, the user and its party members cannot have major status conditions or confusion inflicted on them by other Pokemon. It is removed from the user's side if the user or an ally is successfully hit by Defog. Fails if the effect is already active on the user's side.",
        shortDesc=r"For 5 turns, protects user's party from status.",
        name=r"Safeguard",
        pp=25,
    )
    SANDATTACK = Move(
        desc=r"Lowers the target's accuracy by 1 stage.",
        shortDesc=r"Lowers the target's accuracy by 1.",
        accuracy=100,
        name=r"Sand Attack",
        pp=15,
        type=Types.GROUND,
    )
    SANDSTORM = Move(
        desc=r"For 5 turns, the weather becomes Sandstorm. At the end of each turn except the last, all active Pokemon lose 1/16 of their maximum HP, rounded down, unless they are a Ground, Rock, or Steel type, or have the Magic Guard, Overcoat, Sand Force, Sand Rush, or Sand Veil Abilities. During the effect, the Special Defense of Rock-type Pokemon is multiplied by 1.5 when taking damage from a special attack. Lasts for 8 turns if the user is holding Smooth Rock. Fails if the current weather is Sandstorm.",
        shortDesc=r"For 5 turns, a sandstorm rages.",
        name=r"Sandstorm",
        pp=10,
        type=Types.ROCK,
    )
    SANDTOMB = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=85,
        base=35,
        category=Category.PHYSICAL,
        name=r"Sand Tomb",
        pp=15,
        type=Types.GROUND,
    )
    SAPPYSEED = Move(
        desc=r"This move summons Leech Seed on the foe.",
        shortDesc=r"Summons Leech Seed.",
        accuracy=9,
        base=100,
        category=Category.PHYSICAL,
        name=r"Sappy Seed",
        pp=10,
        type=Types.GRASS,
    )
    SCALD = Move(
        desc=r"Has a 30% chance to burn the target. The target thaws out if it is frozen.",
        shortDesc=r"30% chance to burn the target. Thaws target.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Scald",
        pp=15,
        type=Types.WATER,
    )
    SCALESHOT = Move(
        desc=r"Hits two to five times. Lowers the user's Defense by 1 stage and raises the user's Speed by 1 stage after the last hit. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times. User: -1 Def, +1 Spe after last hit.",
        accuracy=9,
        base=25,
        category=Category.PHYSICAL,
        name=r"Scale Shot",
        pp=20,
        type=Types.DRAGON,
    )
    SCARYFACE = Move(
        desc=r"Lowers the target's Speed by 2 stages.",
        shortDesc=r"Lowers the target's Speed by 2.",
        accuracy=100,
        name=r"Scary Face",
        pp=10,
    )
    SCORCHINGSANDS = Move(
        desc=r"Has a 30% chance to burn the target. The target thaws out if it is frozen.",
        shortDesc=r"30% chance to burn the target. Thaws target.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Scorching Sands",
        pp=10,
        type=Types.GROUND,
    )
    SCRATCH = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Scratch",
        pp=35,
    )
    SCREECH = Move(
        desc=r"Lowers the target's Defense by 2 stages.",
        shortDesc=r"Lowers the target's Defense by 2.",
        accuracy=85,
        name=r"Screech",
        pp=40,
    )
    SEARINGSHOT = Move(
        desc=r"Has a 30% chance to burn the target.",
        shortDesc=r"30% chance to burn adjacent Pokemon.",
        accuracy=100,
        base=100,
        category=Category.SPECIAL,
        name=r"Searing Shot",
        pp=5,
        type=Types.FIRE,
    )
    SECRETPOWER = Move(
        desc=r"Has a 30% chance to cause a secondary effect on the target based on the battle terrain. Causes paralysis on the regular Wi-Fi terrain, causes paralysis during Electric Terrain, lowers Special Attack by 1 stage during Misty Terrain, causes sleep during Grassy Terrain and lowers Speed by 1 stage during Psychic Terrain.",
        shortDesc=r"Effect varies with terrain. (30% paralysis chance)",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Secret Power",
        pp=20,
    )
    SECRETSWORD = Move(
        desc=r"Deals damage to the target based on its Defense instead of Special Defense.",
        shortDesc=r"Damages target based on Defense, not Sp. Def.",
        accuracy=100,
        base=85,
        category=Category.SPECIAL,
        name=r"Secret Sword",
        pp=10,
        type=Types.FIGHTING,
    )
    SEEDBOMB = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Seed Bomb",
        pp=15,
        type=Types.GRASS,
    )
    SEEDFLARE = Move(
        desc=r"Has a 40% chance to lower the target's Special Defense by 2 stages.",
        shortDesc=r"40% chance to lower the target's Sp. Def by 2.",
        accuracy=85,
        base=120,
        category=Category.SPECIAL,
        name=r"Seed Flare",
        pp=5,
        type=Types.GRASS,
    )
    SEISMICTOSS = Move(
        desc=r"Deals damage to the target equal to the user's level.",
        shortDesc=r"Does damage equal to the user's level.",
        accuracy=100,
        category=Category.PHYSICAL,
        name=r"Seismic Toss",
        pp=20,
        type=Types.FIGHTING,
    )
    SELFDESTRUCT = Move(
        desc=r"The user faints after using this move, even if this move fails for having no target. This move is prevented from executing if any active Pokemon has the Damp Ability.",
        shortDesc=r"Hits adjacent Pokemon. The user faints.",
        accuracy=100,
        base=200,
        category=Category.PHYSICAL,
        name=r"Self-Destruct",
        pp=5,
    )
    SHADOWBALL = Move(
        desc=r"Has a 20% chance to lower the target's Special Defense by 1 stage.",
        shortDesc=r"20% chance to lower the target's Sp. Def by 1.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Shadow Ball",
        pp=15,
        type=Types.GHOST,
    )
    SHADOWBONE = Move(
        desc=r"Has a 20% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"20% chance to lower the target's Defense by 1.",
        accuracy=100,
        base=85,
        category=Category.PHYSICAL,
        name=r"Shadow Bone",
        pp=10,
        type=Types.GHOST,
    )
    SHADOWCLAW = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Shadow Claw",
        pp=15,
        type=Types.GHOST,
    )
    SHADOWFORCE = Move(
        desc=r"If this move is successful, it breaks through the target's Baneful Bunker, Detect, King's Shield, Protect, or Spiky Shield for this turn, allowing other Pokemon to attack the target normally. If the target's side is protected by Crafty Shield, Mat Block, Quick Guard, or Wide Guard, that protection is also broken for this turn and other Pokemon may attack the target's side normally. This attack charges on the first turn and executes on the second. On the first turn, the user avoids all attacks. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Disappears turn 1. Hits turn 2. Breaks protection.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Shadow Force",
        pp=5,
        type=Types.GHOST,
    )
    SHADOWPUNCH = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.PHYSICAL,
        name=r"Shadow Punch",
        pp=20,
        type=Types.GHOST,
    )
    SHADOWSNEAK = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Shadow Sneak",
        pp=30,
        type=Types.GHOST,
    )
    SHADOWSTRIKE = Move(
        desc=r"Has a 50% chance to lower the target's Defense by 1 stage.",
        shortDesc=r"50% chance to lower the target's Defense by 1.",
        accuracy=95,
        base=80,
        category=Category.PHYSICAL,
        name=r"Shadow Strike",
        pp=10,
        type=Types.GHOST,
    )
    SHARPEN = Move(
        desc=r"Raises the user's Attack by 1 stage.",
        shortDesc=r"Raises the user's Attack by 1.",
        name=r"Sharpen",
        pp=30,
    )
    SHEERCOLD = Move(
        desc=r"Deals damage to the target equal to the target's maximum HP. Ignores accuracy and evasiveness modifiers. This attack's accuracy is equal to (user's level - target's level + X)%, where X is 30 if the user is an Ice type and 20 otherwise, and fails if the target is at a higher level. Ice-type Pokemon and Pokemon with the Sturdy Ability are immune.",
        shortDesc=r"OHKOs non-Ice targets. Fails if user's lower level.",
        banned=True,
        category=Category.SPECIAL,
        name=r"Sheer Cold",
        pp=5,
        type=Types.ICE,
    )
    SHELLSIDEARM = Move(
        desc=r"Has a 20% chance to poison the target. This move becomes a physical attack that makes contact if the value of ((((2 * the user's level / 5 + 2) * 90 * X) / Y) / 50) where X is the user's Attack stat and Y is the target's Defense stat, is greater than the same value where X is the user's Special Attack stat and Y is the target's Special Defense stat. No stat modifiers other than stat stage changes are considered for this purpose. If the two values are equal, this move chooses a damage category at random.",
        shortDesc=r"20% psn. Physical+contact if it would be stronger.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Shell Side Arm",
        pp=10,
        type=Types.POISON,
    )
    SHELLSMASH = Move(
        desc=r"Lowers the user's Defense and Special Defense by 1 stage. Raises the user's Attack, Special Attack, and Speed by 2 stages.",
        shortDesc=r"Lowers Def, SpD by 1; raises Atk, SpA, Spe by 2.",
        name=r"Shell Smash",
        pp=15,
    )
    SHELLTRAP = Move(
        desc=r"Fails unless the user is hit by a physical attack from an opponent this turn before it can execute the move. If the user was hit and has not fainted, it attacks immediately after being hit, and the effect ends. If the opponent's physical attack had a secondary effect removed by the Sheer Force Ability, it does not count for the purposes of this effect.",
        shortDesc=r"User must take physical damage before moving.",
        accuracy=100,
        base=150,
        category=Category.SPECIAL,
        name=r"Shell Trap",
        pp=5,
        type=Types.FIRE,
    )
    SHIFTGEAR = Move(
        desc=r"Raises the user's Speed by 2 stages and its Attack by 1 stage.",
        shortDesc=r"Raises the user's Speed by 2 and Attack by 1.",
        name=r"Shift Gear",
        pp=10,
        type=Types.STEEL,
    )
    SHOCKWAVE = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=60,
        category=Category.SPECIAL,
        name=r"Shock Wave",
        pp=20,
        type=Types.ELECTRIC,
    )
    SHOREUP = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half down. If the weather is Sandstorm, the user instead restores 2/3 of its maximum HP, rounded half down.",
        shortDesc=r"User restores 1/2 its max HP; 2/3 in Sandstorm.",
        name=r"Shore Up",
        pp=10,
        type=Types.GROUND,
    )
    SIGNALBEAM = Move(
        desc=r"Has a 10% chance to confuse the target.",
        shortDesc=r"10% chance to confuse the target.",
        accuracy=100,
        base=75,
        category=Category.SPECIAL,
        name=r"Signal Beam",
        pp=15,
        type=Types.BUG,
    )
    SILVERWIND = Move(
        desc=r"Has a 10% chance to raise the user's Attack, Defense, Special Attack, Special Defense, and Speed by 1 stage.",
        shortDesc=r"10% chance to raise all stats by 1 (not acc/eva).",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Silver Wind",
        pp=5,
        type=Types.BUG,
    )
    SIMPLEBEAM = Move(
        desc=r"Causes the target's Ability to become Simple. Fails if the target's Ability is Battle Bond, Comatose, Disguise, Multitype, Power Construct, RKS System, Schooling, Shields Down, Simple, Stance Change, Truant, or Zen Mode.",
        shortDesc=r"The target's Ability becomes Simple.",
        accuracy=100,
        name=r"Simple Beam",
        pp=15,
    )
    SING = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=55,
        name=r"Sing",
        pp=15,
    )
    SIZZLYSLIDE = Move(
        desc=r"Has a 100% chance to burn the foe.",
        shortDesc=r"100% chance to burn the foe.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Sizzly Slide",
        pp=20,
        type=Types.FIRE,
    )
    SKETCH = Move(
        desc=r"This move is permanently replaced by the last move used by the target. The copied move has the maximum PP for that move. Fails if the target has not made a move, if the user has Transformed, or if the move is Chatter, Sketch, Struggle, or any move the user knows.",
        shortDesc=r"Permanently copies the last move target used.",
        name=r"Sketch",
    )
    SKILLSWAP = Move(
        desc=r"The user swaps its Ability with the target's Ability. Fails if either the user or the target's Ability is Battle Bond, Comatose, Disguise, Gulp Missile, Hunger Switch, Ice Face, Illusion, Multitype, Neutralizing Gas, Power Construct, RKS System, Schooling, Shields Down, Stance Change, Wonder Guard, or Zen Mode.",
        shortDesc=r"The user and the target trade Abilities.",
        name=r"Skill Swap",
        pp=10,
        type=Types.PSYCHIC,
    )
    SKITTERSMACK = Move(
        desc=r"Has a 100% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"100% chance to lower target's Sp. Atk by 1.",
        accuracy=9,
        base=70,
        category=Category.PHYSICAL,
        name=r"Skitter Smack",
        pp=10,
        type=Types.BUG,
    )
    SKULLBASH = Move(
        desc=r"This attack charges on the first turn and executes on the second. Raises the user's Defense by 1 stage on the first turn. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Raises user's Defense by 1 on turn 1. Hits turn 2.",
        accuracy=100,
        base=130,
        category=Category.PHYSICAL,
        name=r"Skull Bash",
        pp=10,
    )
    SKYATTACK = Move(
        desc=r"Has a 30% chance to flinch the target and a higher chance for a critical hit. This attack charges on the first turn and executes on the second. If the user is holding a Power Herb, the move completes in one turn.",
        shortDesc=r"Charges, then hits turn 2. 30% flinch. High crit.",
        accuracy=9,
        base=140,
        category=Category.PHYSICAL,
        name=r"Sky Attack",
        pp=5,
        type=Types.FLYING,
    )
    SKYDROP = Move(
        desc=r"This attack takes the target into the air with the user on the first turn and executes on the second. Pokemon weighing 200 kg or more cannot be lifted. On the first turn, the user and the target avoid all attacks other than Gust, Hurricane, Sky Uppercut, Smack Down, Thousand Arrows, Thunder, and Twister. The user and the target cannot make a move between turns, but the target can select a move to use. This move cannot damage Flying-type Pokemon. Fails on the first turn if the target is an ally, if the target has a substitute, or if the target is using Bounce, Dig, Dive, Fly, Phantom Force, Shadow Force, or Sky Drop.",
        shortDesc=r"User and foe fly up turn 1. Damages on turn 2.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Sky Drop",
        pp=10,
        type=Types.FLYING,
    )
    SKYUPPERCUT = Move(
        desc=r"This move can hit a target using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop.",
        shortDesc=r"Can hit Pokemon using Bounce, Fly, or Sky Drop.",
        accuracy=9,
        base=85,
        category=Category.PHYSICAL,
        name=r"Sky Uppercut",
        pp=15,
        type=Types.FIGHTING,
    )
    SLACKOFF = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user by 50% of its max HP.",
        name=r"Slack Off",
        pp=10,
    )
    SLAM = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=75,
        base=80,
        category=Category.PHYSICAL,
        name=r"Slam",
        pp=20,
    )
    SLASH = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Slash",
        pp=20,
    )
    SLEEPPOWDER = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=75,
        name=r"Sleep Powder",
        pp=15,
        type=Types.GRASS,
    )
    SLEEPTALK = Move(
        desc=r"One of the user's known moves, besides this move, is selected for use at random. Fails if the user is not asleep. The selected move does not have PP deducted from it, and can currently have 0 PP. This move cannot select Assist, Beak Blast, Belch, Bide, Celebrate, Chatter, Copycat, Dynamax Cannon, Focus Punch, Hold Hands, Me First, Metronome, Mimic, Mirror Move, Nature Power, Shell Trap, Sketch, Sleep Talk, Struggle, Uproar, any two-turn move, or any Max Move.",
        shortDesc=r"User must be asleep. Uses another known move.",
        name=r"Sleep Talk",
        pp=10,
    )
    SLUDGE = Move(
        desc=r"Has a 30% chance to poison the target.",
        shortDesc=r"30% chance to poison the target.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Sludge",
        pp=20,
        type=Types.POISON,
    )
    SLUDGEBOMB = Move(
        desc=r"Has a 30% chance to poison the target.",
        shortDesc=r"30% chance to poison the target.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Sludge Bomb",
        pp=10,
        type=Types.POISON,
    )
    SLUDGEWAVE = Move(
        desc=r"Has a 10% chance to poison the target.",
        shortDesc=r"10% chance to poison adjacent Pokemon.",
        accuracy=100,
        base=95,
        category=Category.SPECIAL,
        name=r"Sludge Wave",
        pp=10,
        type=Types.POISON,
    )
    SMACKDOWN = Move(
        desc=r"This move can hit a target using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop. If this move hits a target under the effect of Bounce, Fly, Magnet Rise, or Telekinesis, the effect ends. If the target is a Flying type that has not used Roost this turn or a Pokemon with the Levitate Ability, it loses its immunity to Ground-type attacks and the Arena Trap Ability as long as it remains active. During the effect, Magnet Rise fails for the target and Telekinesis fails against the target.",
        shortDesc=r"Removes the target's Ground immunity.",
        accuracy=100,
        base=50,
        category=Category.PHYSICAL,
        name=r"Smack Down",
        pp=15,
        type=Types.ROCK,
    )
    SMARTSTRIKE = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy.",
        base=70,
        category=Category.PHYSICAL,
        name=r"Smart Strike",
        pp=10,
        type=Types.STEEL,
    )
    SMELLINGSALTS = Move(
        desc=r"Power doubles if the target is paralyzed. If the user has not fainted, the target is cured of paralysis.",
        shortDesc=r"Power doubles if target is paralyzed, and cures it.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Smelling Salts",
        pp=10,
    )
    SMOG = Move(
        desc=r"Has a 40% chance to poison the target.",
        shortDesc=r"40% chance to poison the target.",
        accuracy=7,
        base=30,
        category=Category.SPECIAL,
        name=r"Smog",
        pp=20,
        type=Types.POISON,
    )
    SMOKESCREEN = Move(
        desc=r"Lowers the target's accuracy by 1 stage.",
        shortDesc=r"Lowers the target's accuracy by 1.",
        accuracy=100,
        name=r"Smokescreen",
        pp=20,
    )
    SNAPTRAP = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=100,
        base=35,
        category=Category.PHYSICAL,
        name=r"Snap Trap",
        pp=15,
        type=Types.GRASS,
    )
    SNARL = Move(
        desc=r"Has a 100% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Sp. Atk by 1.",
        accuracy=95,
        base=55,
        category=Category.SPECIAL,
        name=r"Snarl",
        pp=15,
        type=Types.DARK,
    )
    SNATCH = Move(
        desc=r"If another Pokemon uses certain non-damaging moves this turn, the user steals that move to use itself. If multiple Pokemon use one of those moves this turn, the applicable moves are all stolen by the first Pokemon in turn order that used this move this turn. This effect is ignored while the user is under the effect of Sky Drop.",
        shortDesc=r"User steals certain support moves to use itself.",
        name=r"Snatch",
        pp=10,
        type=Types.DARK,
    )
    SNIPESHOT = Move(
        desc=r"Has a higher chance for a critical hit. This move cannot be redirected to a different target by any effect.",
        shortDesc=r"High critical hit ratio. Cannot be redirected.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Snipe Shot",
        pp=15,
        type=Types.WATER,
    )
    SNORE = Move(
        desc=r"Has a 30% chance to flinch the target. Fails if the user is not asleep.",
        shortDesc=r"User must be asleep. 30% chance to flinch target.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Snore",
        pp=15,
    )
    SOAK = Move(
        desc=r"Causes the target to become a Water type. Fails if the target is an Arceus or a Silvally, or if the target is already purely Water type.",
        shortDesc=r"Changes the target's type to Water.",
        accuracy=100,
        name=r"Soak",
        pp=20,
        type=Types.WATER,
    )
    SOFTBOILED = Move(
        desc=r"The user restores 1/2 of its maximum HP, rounded half up.",
        shortDesc=r"Heals the user by 50% of its max HP.",
        name=r"Soft-Boiled",
        pp=10,
    )
    SOLARBEAM = Move(
        desc=r"This attack charges on the first turn and executes on the second. Power is halved if the weather is Hail, Primordial Sea, Rain Dance, or Sandstorm and the user is not holding Utility Umbrella. If the user is holding a Power Herb or the weather is Desolate Land or Sunny Day, the move completes in one turn. If the user is holding Utility Umbrella and the weather is Desolate Land or Sunny Day, the move still requires a turn to charge.",
        shortDesc=r"Charges turn 1. Hits turn 2. No charge in sunlight.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Solar Beam",
        pp=10,
        type=Types.GRASS,
    )
    SOLARBLADE = Move(
        desc=r"This attack charges on the first turn and executes on the second. Power is halved if the weather is Hail, Primordial Sea, Rain Dance, or Sandstorm and the user is not holding Utility Umbrella. If the user is holding a Power Herb or the weather is Desolate Land or Sunny Day, the move completes in one turn. If the user is holding Utility Umbrella and the weather is Desolate Land or Sunny Day, the move still requires a turn to charge.",
        shortDesc=r"Charges turn 1. Hits turn 2. No charge in sunlight.",
        accuracy=100,
        base=125,
        category=Category.PHYSICAL,
        name=r"Solar Blade",
        pp=10,
        type=Types.GRASS,
    )
    SONICBOOM = Move(
        desc=r"Deals 20 HP of damage to the target.",
        shortDesc=r"Always does 20 HP of damage.",
        accuracy=9,
        category=Category.SPECIAL,
        name=r"Sonic Boom",
        pp=20,
    )
    SPACIALREND = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=95,
        base=100,
        category=Category.SPECIAL,
        name=r"Spacial Rend",
        pp=5,
        type=Types.DRAGON,
    )
    SPARK = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Spark",
        pp=20,
        type=Types.ELECTRIC,
    )
    SPARKLINGARIA = Move(
        desc=r"If the user has not fainted, the target is cured of its burn.",
        shortDesc=r"The target is cured of its burn.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Sparkling Aria",
        pp=10,
        type=Types.WATER,
    )
    SPARKLYSWIRL = Move(
        desc=r"Every Pokemon in the user's party is cured of its major status condition.",
        shortDesc=r"Cures the user's party of all status conditions.",
        accuracy=85,
        base=120,
        category=Category.SPECIAL,
        name=r"Sparkly Swirl",
        pp=5,
        type=Types.FAIRY,
    )
    SPECTRALTHIEF = Move(
        desc=r"The target's stat stages greater than 0 are stolen from it and applied to the user before dealing damage.",
        shortDesc=r"Steals target's boosts before dealing damage.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Spectral Thief",
        pp=10,
        type=Types.GHOST,
    )
    SPEEDSWAP = Move(
        desc=r"The user swaps its Speed stat with the target. Stat stage changes are unaffected.",
        shortDesc=r"Swaps Speed stat with target.",
        name=r"Speed Swap",
        pp=10,
        type=Types.PSYCHIC,
    )
    SPIDERWEB = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Prevents the target from switching out.",
        name=r"Spider Web",
        pp=10,
        type=Types.BUG,
    )
    SPIKECANNON = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=100,
        base=20,
        category=Category.PHYSICAL,
        name=r"Spike Cannon",
        pp=15,
    )
    SPIKES = Move(
        desc=r"Sets up a hazard on the opposing side of the field, damaging each opposing Pokemon that switches in, unless it is a Flying-type Pokemon or has the Levitate Ability. Can be used up to three times before failing. Opponents lose 1/8 of their maximum HP with one layer, 1/6 of their maximum HP with two layers, and 1/4 of their maximum HP with three layers, all rounded down. Can be removed from the opposing side if any opposing Pokemon uses Rapid Spin or Defog successfully, or is hit by Defog.",
        shortDesc=r"Hurts grounded foes on switch-in. Max 3 layers.",
        name=r"Spikes",
        pp=20,
        type=Types.GROUND,
    )
    SPIKYSHIELD = Move(
        desc=r"The user is protected from most attacks made by other Pokemon during this turn, and Pokemon making contact with the user lose 1/8 of their maximum HP, rounded down. This move has a 1/X chance of being successful, where X starts at 1 and triples each time this move is successfully used. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn.",
        shortDesc=r"Protects from moves. Contact: loses 1/8 max HP.",
        name=r"Spiky Shield",
        pp=10,
        type=Types.GRASS,
    )
    SPIRITBREAK = Move(
        desc=r"Has a 100% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"100% chance to lower the target's Sp. Atk by 1.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Spirit Break",
        pp=10,
        type=Types.FAIRY,
    )
    SPIRITSHACKLE = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Prevents the target from switching out.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Spirit Shackle",
        pp=10,
        type=Types.GHOST,
    )
    SPITUP = Move(
        desc=r"Power is equal to 100 times the user's Stockpile count. Fails if the user's Stockpile count is 0. Whether or not this move is successful, the user's Defense and Special Defense decrease by as many stages as Stockpile had increased them, and the user's Stockpile count resets to 0.",
        shortDesc=r"More power with more uses of Stockpile.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Spit Up",
        pp=10,
    )
    SPITE = Move(
        desc=r"Causes the target's last move used to lose 4 PP. Fails if the target has not made a move, if the move has 0 PP, or if it no longer knows the move.",
        shortDesc=r"Lowers the PP of the target's last move by 4.",
        accuracy=100,
        name=r"Spite",
        pp=10,
        type=Types.GHOST,
    )
    SPLASH = Move(
        desc=r"No competitive use.",
        shortDesc=r"No competitive use.",
        name=r"Splash",
        pp=40,
    )
    SPLISHYSPLASH = Move(
        desc=r"Has a 30% chance to paralyze the target.",
        shortDesc=r"30% chance to paralyze the target.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Splishy Splash",
        pp=15,
        type=Types.WATER,
    )
    SPORE = Move(
        desc=r"Causes the target to fall asleep.",
        shortDesc=r"Causes the target to fall asleep.",
        accuracy=100,
        name=r"Spore",
        pp=15,
        type=Types.GRASS,
    )
    SPOTLIGHT = Move(
        desc=r"Until the end of the turn, all single-target attacks from opponents of the target are redirected to the target. Such attacks are redirected to the target before they can be reflected by Magic Coat or the Magic Bounce Ability, or drawn in by the Lightning Rod or Storm Drain Abilities. Fails if it is not a Double Battle or Battle Royal.",
        shortDesc=r"Target's foes' moves are redirected to it this turn.",
        name=r"Spotlight",
        pp=15,
    )
    STEALTHROCK = Move(
        desc=r"Sets up a hazard on the opposing side of the field, damaging each opposing Pokemon that switches in. Fails if the effect is already active on the opposing side. Foes lose 1/32, 1/16, 1/8, 1/4, or 1/2 of their maximum HP, rounded down, based on their weakness to the Rock type; 0.25x, 0.5x, neutral, 2x, or 4x, respectively. Can be removed from the opposing side if any opposing Pokemon uses Rapid Spin or Defog successfully, or is hit by Defog.",
        shortDesc=r"Hurts foes on switch-in. Factors Rock weakness.",
        name=r"Stealth Rock",
        pp=20,
        type=Types.ROCK,
    )
    STEAMERUPTION = Move(
        desc=r"Has a 30% chance to burn the target. The target thaws out if it is frozen.",
        shortDesc=r"30% chance to burn the target. Thaws target.",
        accuracy=95,
        base=110,
        category=Category.SPECIAL,
        name=r"Steam Eruption",
        pp=5,
        type=Types.WATER,
    )
    STEAMROLLER = Move(
        desc=r"Has a 30% chance to flinch the target. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Steamroller",
        pp=20,
        type=Types.BUG,
    )
    STEELBEAM = Move(
        desc=r"Whether or not this move is successful and even if it would cause fainting, the user loses 1/2 of its maximum HP, rounded up, unless the user has the Magic Guard Ability.",
        shortDesc=r"User loses 50% max HP.",
        accuracy=95,
        base=140,
        category=Category.SPECIAL,
        name=r"Steel Beam",
        pp=5,
        type=Types.STEEL,
    )
    STEELROLLER = Move(
        desc=r"Fails if there is no terrain active. Ends the effects of Electric Terrain, Grassy Terrain, Misty Terrain, and Psychic Terrain.",
        shortDesc=r"Fails if there is no terrain active. Ends the effects of terrain.",
        accuracy=100,
        base=130,
        category=Category.PHYSICAL,
        name=r"Steel Roller",
        pp=5,
        type=Types.STEEL,
    )
    STEELWING = Move(
        desc=r"Has a 10% chance to raise the user's Defense by 1 stage.",
        shortDesc=r"10% chance to raise the user's Defense by 1.",
        accuracy=9,
        base=70,
        category=Category.PHYSICAL,
        name=r"Steel Wing",
        pp=25,
        type=Types.STEEL,
    )
    STICKYWEB = Move(
        desc=r"Sets up a hazard on the opposing side of the field, lowering the Speed by 1 stage of each opposing Pokemon that switches in, unless it is a Flying-type Pokemon or has the Levitate Ability. Fails if the effect is already active on the opposing side. Can be removed from the opposing side if any opposing Pokemon uses Rapid Spin or Defog successfully, or is hit by Defog.",
        shortDesc=r"Lowers Speed of grounded foes by 1 on switch-in.",
        name=r"Sticky Web",
        pp=20,
        type=Types.BUG,
    )
    STOCKPILE = Move(
        desc=r"Raises the user's Defense and Special Defense by 1 stage. The user's Stockpile count increases by 1. Fails if the user's Stockpile count is 3. The user's Stockpile count is reset to 0 when it is no longer active.",
        shortDesc=r"Raises user's Defense, Sp. Def by 1. Max 3 uses.",
        name=r"Stockpile",
        pp=20,
    )
    STOMP = Move(
        desc=r"Has a 30% chance to flinch the target. Damage doubles and no accuracy check is done if the target has used Minimize while active.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=65,
        category=Category.PHYSICAL,
        name=r"Stomp",
        pp=20,
    )
    STOMPINGTANTRUM = Move(
        desc=r"Power doubles if the user's last move on the previous turn, including moves called by other moves or those used through Instruct, Magic Coat, Snatch, or the Dancer or Magic Bounce Abilities, failed to do any of its normal effects, not including damage from an unsuccessful High Jump Kick, Jump Kick, or Mind Blown, or if the user was prevented from moving by any effect other than recharging or Sky Drop. A move that was blocked by Baneful Bunker, Detect, King's Shield, Protect, Spiky Shield, Crafty Shield, Mat Block, Quick Guard, or Wide Guard will not double this move's power, nor will Bounce or Fly ending early due to the effect of Gravity, Smack Down, or Thousand Arrows.",
        shortDesc=r"Power doubles if the user's last move failed.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Stomping Tantrum",
        pp=10,
        type=Types.GROUND,
    )
    STONEEDGE = Move(
        desc=r"Has a higher chance for a critical hit.",
        shortDesc=r"High critical hit ratio.",
        accuracy=8,
        base=100,
        category=Category.PHYSICAL,
        name=r"Stone Edge",
        pp=5,
        type=Types.ROCK,
    )
    STOREDPOWER = Move(
        desc=r"Power is equal to 20+(X*20) where X is the user's total stat stage changes that are greater than 0.",
        shortDesc=r" + 20 power for each of the user's stat boosts.",
        accuracy=100,
        base=20,
        category=Category.SPECIAL,
        name=r"Stored Power",
        pp=10,
        type=Types.PSYCHIC,
    )
    STORMTHROW = Move(
        desc=r"This move is always a critical hit unless the target is under the effect of Lucky Chant or has the Battle Armor or Shell Armor Abilities.",
        shortDesc=r"Always results in a critical hit.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Storm Throw",
        pp=10,
        type=Types.FIGHTING,
    )
    STRANGESTEAM = Move(
        desc=r"Has a 20% chance to confuse the target.",
        shortDesc=r"20% chance to confuse the target.",
        accuracy=95,
        base=90,
        category=Category.SPECIAL,
        name=r"Strange Steam",
        pp=10,
        type=Types.FAIRY,
    )
    STRENGTH = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Strength",
        pp=15,
    )
    STRENGTHSAP = Move(
        desc=r"Lowers the target's Attack by 1 stage. The user restores its HP equal to the target's Attack stat calculated with its stat stage before this move was used. If Big Root is held by the user, the HP recovered is 1.3x normal, rounded half down. Fails if the target's Attack stat stage is -6.",
        shortDesc=r"User heals HP=target's Atk stat. Lowers Atk by 1.",
        accuracy=100,
        name=r"Strength Sap",
        pp=10,
        type=Types.GRASS,
    )
    STRINGSHOT = Move(
        desc=r"Lowers the target's Speed by 2 stages.",
        shortDesc=r"Lowers the foe(s) Speed by 2.",
        accuracy=95,
        name=r"String Shot",
        pp=40,
        type=Types.BUG,
    )
    STRUGGLE = Move(
        desc=r"Deals typeless damage to a random opposing Pokemon. If this move was successful, the user loses 1/4 of its maximum HP, rounded half up, and the Rock Head Ability does not prevent this. This move is automatically used if none of the user's known moves can be selected.",
        shortDesc=r"User loses 1/4 of its max HP.",
        base=50,
        category=Category.PHYSICAL,
        name=r"Struggle",
    )
    STRUGGLEBUG = Move(
        desc=r"Has a 100% chance to lower the target's Special Attack by 1 stage.",
        shortDesc=r"100% chance to lower the foe(s) Sp. Atk by 1.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Struggle Bug",
        pp=20,
        type=Types.BUG,
    )
    STUFFCHEEKS = Move(
        desc=r"The user eats its Berry and raises its Defense by 2 stages. This effect is not prevented by the Klutz or Unnerve Abilities, or the effects of Embargo or Magic Room. Fails if the user is not holding a Berry.",
        shortDesc=r"User eats its Berry and raises its Defense by 2.",
        name=r"Stuff Cheeks",
        pp=10,
    )
    STUNSPORE = Move(
        desc=r"Paralyzes the target.",
        shortDesc=r"Paralyzes the target.",
        accuracy=75,
        name=r"Stun Spore",
        pp=30,
        type=Types.GRASS,
    )
    SUBMISSION = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/4 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/4 recoil.",
        accuracy=8,
        base=80,
        category=Category.PHYSICAL,
        name=r"Submission",
        pp=20,
        type=Types.FIGHTING,
    )
    SUBSTITUTE = Move(
        desc=r"The user takes 1/4 of its maximum HP, rounded down, and puts it into a substitute to take its place in battle. The substitute is removed once enough damage is inflicted on it, or if the user switches out or faints. Baton Pass can be used to transfer the substitute to an ally, and the substitute will keep its remaining HP. Until the substitute is broken, it receives damage from all attacks made by other Pokemon and shields the user from status effects and stat stage changes caused by other Pokemon. Sound-based moves and Pokemon with the Infiltrator Ability ignore substitutes. The user still takes normal damage from weather and status effects while behind its substitute. If the substitute breaks during a multi-hit attack, the user will take damage from any remaining hits. If a substitute is created while the user is trapped by a binding move, the binding effect ends immediately. Fails if the user does not have enough HP remaining to create a substitute without fainting, or if it already has a substitute.",
        shortDesc=r"User takes 1/4 its max HP to put in a substitute.",
        name=r"Substitute",
        pp=10,
    )
    SUCKERPUNCH = Move(
        desc=r"Fails if the target did not select a physical attack, special attack, or Me First for use this turn, or if the target moves before the user.",
        shortDesc=r"Usually goes first. Fails if target is not attacking.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Sucker Punch",
        pp=5,
        type=Types.DARK,
    )
    SUNNYDAY = Move(
        desc=r"For 5 turns, the weather becomes Sunny Day. The damage of Fire-type attacks is multiplied by 1.5 and the damage of Water-type attacks is multiplied by 0.5 during the effect. Lasts for 8 turns if the user is holding Heat Rock. Fails if the current weather is Sunny Day.",
        shortDesc=r"For 5 turns, intense sunlight powers Fire moves.",
        name=r"Sunny Day",
        pp=5,
        type=Types.FIRE,
    )
    SUNSTEELSTRIKE = Move(
        desc=r"This move and its effects ignore the Abilities of other Pokemon.",
        shortDesc=r"Ignores the Abilities of other Pokemon.",
        accuracy=100,
        base=100,
        category=Category.PHYSICAL,
        name=r"Sunsteel Strike",
        pp=5,
        type=Types.STEEL,
    )
    SUPERFANG = Move(
        desc=r"Deals damage to the target equal to half of its current HP, rounded down, but not less than 1 HP.",
        shortDesc=r"Does damage equal to 1/2 target's current HP.",
        accuracy=9,
        category=Category.PHYSICAL,
        name=r"Super Fang",
        pp=10,
    )
    SUPERPOWER = Move(
        desc=r"Lowers the user's Attack and Defense by 1 stage.",
        shortDesc=r"Lowers the user's Attack and Defense by 1.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Superpower",
        pp=5,
        type=Types.FIGHTING,
    )
    SUPERSONIC = Move(
        desc=r"Causes the target to become confused.",
        shortDesc=r"Causes the target to become confused.",
        accuracy=55,
        name=r"Supersonic",
        pp=20,
    )
    SURF = Move(
        desc=r"Damage doubles if the target is using Dive.",
        shortDesc=r"Hits adjacent Pokemon. Double damage on Dive.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Surf",
        pp=15,
        type=Types.WATER,
    )
    SURGINGSTRIKES = Move(
        desc=r"Hits three times. This move is always a critical hit unless the target is under the effect of Lucky Chant or has the Battle Armor or Shell Armor Abilities.",
        shortDesc=r"Always results in a critical hit. Hits 3 times.",
        accuracy=100,
        base=25,
        category=Category.PHYSICAL,
        name=r"Surging Strikes",
        pp=5,
        type=Types.WATER,
    )
    SWAGGER = Move(
        desc=r"Raises the target's Attack by 2 stages and confuses it.",
        shortDesc=r"Raises the target's Attack by 2 and confuses it.",
        accuracy=85,
        name=r"Swagger",
        pp=15,
    )
    SWALLOW = Move(
        desc=r"The user restores its HP based on its Stockpile count. Restores 1/4 of its maximum HP if it's 1, 1/2 of its maximum HP if it's 2, both rounded half down, and all of its HP if it's 3. Fails if the user's Stockpile count is 0. The user's Defense and Special Defense decrease by as many stages as Stockpile had increased them, and the user's Stockpile count resets to 0.",
        shortDesc=r"Heals the user based on uses of Stockpile.",
        name=r"Swallow",
        pp=10,
    )
    SWEETKISS = Move(
        desc=r"Causes the target to become confused.",
        shortDesc=r"Causes the target to become confused.",
        accuracy=75,
        name=r"Sweet Kiss",
        pp=10,
        type=Types.FAIRY,
    )
    SWEETSCENT = Move(
        desc=r"Lowers the target's evasiveness by 2 stages.",
        shortDesc=r"Lowers the foe(s) evasiveness by 2.",
        accuracy=100,
        name=r"Sweet Scent",
        pp=20,
    )
    SWIFT = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy. Hits foes.",
        base=60,
        category=Category.SPECIAL,
        name=r"Swift",
        pp=20,
    )
    SWITCHEROO = Move(
        desc=r"The user swaps its held item with the target's held item. Fails if either the user or the target is holding a Mail or Z-Crystal, if neither is holding an item, if the user is trying to give or take a Mega Stone to or from the species that can Mega Evolve with it, or if the user is trying to give or take a Blue Orb, a Red Orb, a Griseous Orb, a Plate, a Drive, or a Memory to or from a Kyogre, a Groudon, a Giratina, an Arceus, a Genesect, or a Silvally, respectively. The target is immune to this move if it has the Sticky Hold Ability.",
        shortDesc=r"User switches its held item with the target's.",
        accuracy=100,
        name=r"Switcheroo",
        pp=10,
        type=Types.DARK,
    )
    SWORDSDANCE = Move(
        desc=r"Raises the user's Attack by 2 stages.",
        shortDesc=r"Raises the user's Attack by 2.",
        name=r"Swords Dance",
        pp=20,
    )
    SYNCHRONOISE = Move(
        desc=r"The target is immune if it does not share a type with the user.",
        shortDesc=r"Hits adjacent Pokemon sharing the user's type.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Synchronoise",
        pp=10,
        type=Types.PSYCHIC,
    )
    SYNTHESIS = Move(
        desc=r"The user restores 1/2 of its maximum HP if Delta Stream or no weather conditions are in effect or if the user is holding Utility Umbrella, 2/3 of its maximum HP if the weather is Desolate Land or Sunny Day, and 1/4 of its maximum HP if the weather is Hail, Primordial Sea, Rain Dance, or Sandstorm, all rounded half down.",
        shortDesc=r"Heals the user by a weather-dependent amount.",
        name=r"Synthesis",
        pp=5,
        type=Types.GRASS,
    )
    TACKLE = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.PHYSICAL,
        name=r"Tackle",
        pp=35,
    )
    TAILGLOW = Move(
        desc=r"Raises the user's Special Attack by 3 stages.",
        shortDesc=r"Raises the user's Sp. Atk by 3.",
        name=r"Tail Glow",
        pp=20,
        type=Types.BUG,
    )
    TAILSLAP = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times.",
        shortDesc=r"Hits 2-5 times in one turn.",
        accuracy=85,
        base=25,
        category=Category.PHYSICAL,
        name=r"Tail Slap",
        pp=10,
    )
    TAILWHIP = Move(
        desc=r"Lowers the target's Defense by 1 stage.",
        shortDesc=r"Lowers the foe(s) Defense by 1.",
        accuracy=100,
        name=r"Tail Whip",
        pp=30,
    )
    TAILWIND = Move(
        desc=r"For 4 turns, the user and its party members have their Speed doubled. Fails if this move is already in effect for the user's side.",
        shortDesc=r"For 4 turns, allies' Speed is doubled.",
        name=r"Tailwind",
        pp=15,
        type=Types.FLYING,
    )
    TAKEDOWN = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/4 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/4 recoil.",
        accuracy=85,
        base=90,
        category=Category.PHYSICAL,
        name=r"Take Down",
        pp=20,
    )
    TARSHOT = Move(
        desc=r"Lowers the target's Speed by 1 stage. Until the target switches out, the effectiveness of Fire-type moves is doubled against it.",
        shortDesc=r"Target gets -1 Spe and becomes weaker to Fire.",
        accuracy=100,
        name=r"Tar Shot",
        pp=20,
        type=Types.ROCK,
    )
    TAUNT = Move(
        desc=r"Prevents the target from using non-damaging moves for its next three turns. Pokemon with the Oblivious Ability or protected by the Aroma Veil Ability are immune.",
        shortDesc=r"Target can't use status moves its next 3 turns.",
        accuracy=100,
        name=r"Taunt",
        pp=20,
        type=Types.DARK,
    )
    TEARFULLOOK = Move(
        desc=r"Lowers the target's Attack and Special Attack by 1 stage.",
        shortDesc=r"Lowers the target's Attack and Sp. Atk by 1.",
        name=r"Tearful Look",
        pp=20,
    )
    TEATIME = Move(
        desc=r"All active Pokemon consume their held Berries. This effect is not prevented by substitutes, the Klutz or Unnerve Abilities, or the effects of Embargo or Magic Room. Fails if no active Pokemon is holding a Berry.",
        shortDesc=r"All active Pokemon consume held Berries.",
        name=r"Teatime",
        pp=10,
    )
    TECHNOBLAST = Move(
        desc=r"This move's type depends on the user's held Drive.",
        shortDesc=r"Type varies based on the held Drive.",
        accuracy=100,
        base=120,
        category=Category.SPECIAL,
        name=r"Techno Blast",
        pp=5,
    )
    TEETERDANCE = Move(
        desc=r"Causes the target to become confused.",
        shortDesc=r"Confuses adjacent Pokemon.",
        accuracy=100,
        name=r"Teeter Dance",
        pp=20,
    )
    TELEKINESIS = Move(
        desc=r"For 3 turns, the target cannot avoid any attacks made against it, other than OHKO moves, as long as it remains active. During the effect, the target is immune to Ground-type attacks and the effects of Spikes, Toxic Spikes, Sticky Web, and the Arena Trap Ability as long as it remains active. If the target uses Baton Pass, the replacement will gain the effect. Ingrain, Smack Down, Thousand Arrows, and Iron Ball override this move if the target is under any of their effects. Fails if the target is already under this effect or the effects of Ingrain, Smack Down, or Thousand Arrows. The target is immune to this move on use if its species is Diglett, Dugtrio, Alolan Diglett, Alolan Dugtrio, Sandygast, Palossand, or Gengar while Mega-Evolved. Mega Gengar cannot be under this effect by any means.",
        shortDesc=r"For 3 turns, target floats but moves can't miss it.",
        name=r"Telekinesis",
        pp=15,
        type=Types.PSYCHIC,
    )
    TELEPORT = Move(
        desc=r"If this move is successful and the user has not fainted, the user switches out even if it is trapped and is replaced immediately by a selected party member. The user does not switch out if there are no unfainted party members.",
        shortDesc=r"User switches out.",
        name=r"Teleport",
        pp=20,
        type=Types.PSYCHIC,
    )
    TERRAINPULSE = Move(
        desc=r"Power doubles if the user is grounded and a terrain is active, and this move's type changes to match. Electric type during Electric Terrain, Grass type during Grassy Terrain, Fairy type during Misty Terrain, and Psychic type during Psychic Terrain.",
        shortDesc=r"User on terrain: power doubles, type varies.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Terrain Pulse",
        pp=10,
    )
    THIEF = Move(
        desc=r"If this attack was successful and the user has not fainted, it steals the target's held item if the user is not holding one. The target's item is not stolen if it is a Mail or Z-Crystal, or if the target is a Kyogre holding a Blue Orb, a Groudon holding a Red Orb, a Giratina holding a Griseous Orb, an Arceus holding a Plate, a Genesect holding a Drive, a Silvally holding a Memory, or a Pokemon that can Mega Evolve holding the Mega Stone for its species. Items lost to this move cannot be regained with Recycle or the Harvest Ability.",
        shortDesc=r"If the user has no item, it steals the target's.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Thief",
        pp=25,
        type=Types.DARK,
    )
    THOUSANDARROWS = Move(
        desc=r"This move can hit airborne Pokemon, which includes Flying-type Pokemon, Pokemon with the Levitate Ability, Pokemon holding an Air Balloon, and Pokemon under the effect of Magnet Rise or Telekinesis. If the target is a Flying type and is not already grounded, this move deals neutral damage regardless of its other type(s). This move can hit a target using Bounce, Fly, or Sky Drop. If this move hits a target under the effect of Bounce, Fly, Magnet Rise, or Telekinesis, the effect ends. If the target is a Flying type that has not used Roost this turn or a Pokemon with the Levitate Ability, it loses its immunity to Ground-type attacks and the Arena Trap Ability as long as it remains active. During the effect, Magnet Rise fails for the target and Telekinesis fails against the target.",
        shortDesc=r"Grounds adjacent foes. First hit neutral on Flying.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Thousand Arrows",
        pp=10,
        type=Types.GROUND,
    )
    THOUSANDWAVES = Move(
        desc=r"Prevents the target from switching out. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. If the target leaves the field using Baton Pass, the replacement will remain trapped. The effect ends if the user leaves the field.",
        shortDesc=r"Hits adjacent foes. Prevents them from switching.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Thousand Waves",
        pp=10,
        type=Types.GROUND,
    )
    THRASH = Move(
        desc=r"The user spends two or three turns locked into this move and becomes confused immediately after its move on the last turn of the effect if it is not already. This move targets an opposing Pokemon at random on each turn. If the user is prevented from moving, is asleep at the beginning of a turn, or the attack is not successful against the target on the first turn of the effect or the second turn of a three-turn effect, the effect ends without causing confusion. If this move is called by Sleep Talk and the user is asleep, the move is used for one turn and does not confuse the user.",
        shortDesc=r"Lasts 2-3 turns. Confuses the user afterwards.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Thrash",
        pp=10,
    )
    THROATCHOP = Move(
        desc=r"For 2 turns, the target cannot use sound-based moves.",
        shortDesc=r"For 2 turns, the target cannot use sound moves.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Throat Chop",
        pp=15,
        type=Types.DARK,
    )
    THUNDER = Move(
        desc=r"Has a 30% chance to paralyze the target. This move can hit a target using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop. If the weather is Primordial Sea or Rain Dance, this move does not check accuracy. If the weather is Desolate Land or Sunny Day, this move's accuracy is 50%. If this move is used against a Pokemon holding Utility Umbrella, this move's accuracy remains at 70%.",
        shortDesc=r"30% chance to paralyze. Can't miss in rain.",
        accuracy=7,
        base=110,
        category=Category.SPECIAL,
        name=r"Thunder",
        pp=10,
        type=Types.ELECTRIC,
    )
    THUNDERBOLT = Move(
        desc=r"Has a 10% chance to paralyze the target.",
        shortDesc=r"10% chance to paralyze the target.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Thunderbolt",
        pp=15,
        type=Types.ELECTRIC,
    )
    THUNDERCAGE = Move(
        desc=r"The user traps the target in a cage of sparking electricity for four to five turns.",
        shortDesc=r"The user traps the target in a cage of sparking electricity for four to five turns.",
        accuracy=9,
        base=80,
        category=Category.SPECIAL,
        name=r"Thunder Cage",
        pp=15,
        type=Types.ELECTRIC,
    )
    THUNDERFANG = Move(
        desc=r"Has a 10% chance to paralyze the target and a 10% chance to flinch it.",
        shortDesc=r"10% chance to paralyze. 10% chance to flinch.",
        accuracy=95,
        base=65,
        category=Category.PHYSICAL,
        name=r"Thunder Fang",
        pp=15,
        type=Types.ELECTRIC,
    )
    THUNDEROUSKICK = Move(
        desc=r"The user overwhelms the target with lightning-like movement before delivering a kick. This also lowers the target's Defense stat.",
        shortDesc=r"Thunderous Kick inflicts damage and lowers the target's Defense stat.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Thunderous Kick",
        pp=10,
        type=Types.FIGHTING,
    )
    THUNDERPUNCH = Move(
        desc=r"Has a 10% chance to paralyze the target.",
        shortDesc=r"10% chance to paralyze the target.",
        accuracy=100,
        base=75,
        category=Category.PHYSICAL,
        name=r"Thunder Punch",
        pp=15,
        type=Types.ELECTRIC,
    )
    THUNDERSHOCK = Move(
        desc=r"Has a 10% chance to paralyze the target.",
        shortDesc=r"10% chance to paralyze the target.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Thunder Shock",
        pp=30,
        type=Types.ELECTRIC,
    )
    THUNDERWAVE = Move(
        desc=r"Paralyzes the target. This move does not ignore type immunity.",
        shortDesc=r"Paralyzes the target.",
        accuracy=9,
        name=r"Thunder Wave",
        pp=20,
        type=Types.ELECTRIC,
    )
    TICKLE = Move(
        desc=r"Lowers the target's Attack and Defense by 1 stage.",
        shortDesc=r"Lowers the target's Attack and Defense by 1.",
        accuracy=100,
        name=r"Tickle",
        pp=20,
    )
    TOPSYTURVY = Move(
        desc=r"The target's positive stat stages become negative and vice versa. Fails if all of the target's stat stages are 0.",
        shortDesc=r"Inverts the target's stat stages.",
        name=r"Topsy-Turvy",
        pp=20,
        type=Types.DARK,
    )
    TORMENT = Move(
        desc=r"Prevents the target from selecting the same move for use two turns in a row. This effect ends when the target is no longer active.",
        shortDesc=r"Target can't select the same move twice in a row.",
        accuracy=100,
        name=r"Torment",
        pp=15,
        type=Types.DARK,
    )
    TOXIC = Move(
        desc=r"Badly poisons the target. If a Poison-type Pokemon uses this move, the target cannot avoid the attack, even if the target is in the middle of a two-turn move.",
        shortDesc=r"Badly poisons the target. Poison types can't miss.",
        accuracy=9,
        name=r"Toxic",
        pp=10,
        type=Types.POISON,
    )
    TOXICSPIKES = Move(
        desc=r"Sets up a hazard on the opposing side of the field, poisoning each opposing Pokemon that switches in, unless it is a Flying-type Pokemon or has the Levitate Ability. Can be used up to two times before failing. Opposing Pokemon become poisoned with one layer and badly poisoned with two layers. Can be removed from the opposing side if any opposing Pokemon uses Rapid Spin or Defog successfully, is hit by Defog, or a grounded Poison-type Pokemon switches in. Safeguard prevents the opposing party from being poisoned on switch-in, but a substitute does not.",
        shortDesc=r"Poisons grounded foes on switch-in. Max 2 layers.",
        name=r"Toxic Spikes",
        pp=20,
        type=Types.POISON,
    )
    TOXICTHREAD = Move(
        desc=r"Lowers the target's Speed by 1 stage and poisons it.",
        shortDesc=r"Lowers the target's Speed by 1 and poisons it.",
        accuracy=100,
        name=r"Toxic Thread",
        pp=20,
        type=Types.POISON,
    )
    TRANSFORM = Move(
        desc=r"The user transforms into the target. The target's current stats, stat stages, types, moves, Ability, weight, gender, and sprite are copied. The user's level and HP remain the same and each copied move receives only 5 PP, with a maximum of 5 PP each. The user can no longer change formes if it would have the ability to do so. This move fails if it hits a substitute, if either the user or the target is already transformed, or if either is behind an Illusion.",
        shortDesc=r"Copies target's stats, moves, types, and Ability.",
        name=r"Transform",
        pp=10,
    )
    TRIATTACK = Move(
        desc=r"Has a 20% chance to either burn, freeze, or paralyze the target.",
        shortDesc=r"20% chance to paralyze or burn or freeze target.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Tri Attack",
        pp=10,
    )
    TRICK = Move(
        desc=r"The user swaps its held item with the target's held item. Fails if either the user or the target is holding a Mail or Z-Crystal, if neither is holding an item, if the user is trying to give or take a Mega Stone to or from the species that can Mega Evolve with it, or if the user is trying to give or take a Blue Orb, a Red Orb, a Griseous Orb, a Plate, a Drive, or a Memory to or from a Kyogre, a Groudon, a Giratina, an Arceus, a Genesect, or a Silvally, respectively. The target is immune to this move if it has the Sticky Hold Ability.",
        shortDesc=r"User switches its held item with the target's.",
        accuracy=100,
        name=r"Trick",
        pp=10,
        type=Types.PSYCHIC,
    )
    TRICKORTREAT = Move(
        desc=r"Causes the Ghost type to be added to the target, effectively making it have two or three types. Fails if the target is already a Ghost type. If Forest's Curse adds a type to the target, it replaces the type added by this move and vice versa.",
        shortDesc=r"Adds Ghost to the target's type(s).",
        accuracy=100,
        name=r"Trick-or-Treat",
        pp=20,
        type=Types.GHOST,
    )
    TRICKROOM = Move(
        desc=r"For 5 turns, the Speed of every Pokemon is recalculated for the purposes of determining turn order. During the effect, each Pokemon's Speed is considered to be (10000 - its normal Speed) and if this value is greater than 8191, 8192 is subtracted from it. If this move is used during the effect, the effect ends.",
        shortDesc=r"Goes last. For 5 turns, turn order is reversed.",
        name=r"Trick Room",
        pp=5,
        type=Types.PSYCHIC,
    )
    TRIPLEAXEL = Move(
        desc=r"Hits three times. Power increases to 40 for the second hit and 60 for the third. This move checks accuracy for each hit, and the attack ends if the target avoids a hit. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit three times.",
        shortDesc=r"Hits 3 times. Each hit can miss, but power rises.",
        accuracy=9,
        base=20,
        category=Category.PHYSICAL,
        name=r"Triple Axel",
        pp=10,
        type=Types.ICE,
    )
    TRIPLEKICK = Move(
        desc=r"Hits three times. Power increases to 20 for the second hit and 30 for the third. This move checks accuracy for each hit, and the attack ends if the target avoids a hit. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit three times.",
        shortDesc=r"Hits 3 times. Each hit can miss, but power rises.",
        accuracy=9,
        base=10,
        category=Category.PHYSICAL,
        name=r"Triple Kick",
        pp=10,
        type=Types.FIGHTING,
    )
    TROPKICK = Move(
        desc=r"Has a 100% chance to lower the target's Attack by 1 stage.",
        shortDesc=r"100% chance to lower the target's Attack by 1.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Trop Kick",
        pp=15,
        type=Types.GRASS,
    )
    TRUMPCARD = Move(
        desc=r"The power of this move is based on the amount of PP remaining after normal PP reduction and the Pressure Ability resolve. 200 power for 0 PP, 80 power for 1 PP, 60 power for 2 PP, 50 power for 3 PP, and 40 power for 4 or more PP.",
        shortDesc=r"More power the fewer PP this move has left.",
        category=Category.SPECIAL,
        name=r"Trump Card",
        pp=5,
    )
    TWINEEDLE = Move(
        desc=r"Hits twice, with each hit having a 20% chance to poison the target. If the first hit breaks the target's substitute, it will take damage for the second hit.",
        shortDesc=r"Hits 2 times. Each hit has 20% chance to poison.",
        accuracy=100,
        base=25,
        category=Category.PHYSICAL,
        name=r"Twineedle",
        pp=20,
        type=Types.BUG,
    )
    TWISTER = Move(
        desc=r"Has a 20% chance to flinch the target. Power doubles if the target is using Bounce, Fly, or Sky Drop, or is under the effect of Sky Drop.",
        shortDesc=r"20% chance to flinch the foe(s).",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Twister",
        pp=20,
        type=Types.DRAGON,
    )
    UTURN = Move(
        desc=r"If this move is successful and the user has not fainted, the user switches out even if it is trapped and is replaced immediately by a selected party member. The user does not switch out if there are no unfainted party members, or if the target switched out using an Eject Button or through the effect of the Emergency Exit or Wimp Out Abilities.",
        shortDesc=r"User switches out after damaging the target.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"U-turn",
        pp=20,
        type=Types.BUG,
    )
    UPROAR = Move(
        desc=r"The user spends three turns locked into this move. This move targets an opponent at random on each turn. On the first of the three turns, all sleeping active Pokemon wake up. During the three turns, no active Pokemon can fall asleep by any means, and Pokemon switched in during the effect do not wake up. If the user is prevented from moving or the attack is not successful against the target during one of the turns, the effect ends.",
        shortDesc=r"Lasts 3 turns. Active Pokemon cannot fall asleep.",
        accuracy=100,
        base=90,
        category=Category.SPECIAL,
        name=r"Uproar",
        pp=10,
    )
    VACUUMWAVE = Move(
        desc=r"No additional effect.",
        shortDesc=r"Usually goes first.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Vacuum Wave",
        pp=30,
        type=Types.FIGHTING,
    )
    VCREATE = Move(
        desc=r"Lowers the user's Speed, Defense, and Special Defense by 1 stage.",
        shortDesc=r"Lowers the user's Defense, Sp. Def, Speed by 1.",
        accuracy=95,
        base=180,
        category=Category.PHYSICAL,
        name=r"V-create",
        pp=5,
        type=Types.FIRE,
    )
    VEEVEEVOLLEY = Move(
        desc=r"Power is equal to the greater of (user's Happiness * 2/5) rounded down, or 1.",
        shortDesc=r"Max happiness: 102 power. Can't miss.",
        category=Category.PHYSICAL,
        name=r"Veevee Volley",
        pp=20,
    )
    VENOMDRENCH = Move(
        desc=r"Lowers the target's Attack, Special Attack, and Speed by 1 stage if the target is poisoned. Fails if the target is not poisoned.",
        shortDesc=r"Lowers Atk/Sp. Atk/Speed of poisoned foes by 1.",
        accuracy=100,
        name=r"Venom Drench",
        pp=20,
        type=Types.POISON,
    )
    VENOSHOCK = Move(
        desc=r"Power doubles if the target is poisoned.",
        shortDesc=r"Power doubles if the target is poisoned.",
        accuracy=100,
        base=65,
        category=Category.SPECIAL,
        name=r"Venoshock",
        pp=10,
        type=Types.POISON,
    )
    VINEWHIP = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=45,
        category=Category.PHYSICAL,
        name=r"Vine Whip",
        pp=25,
        type=Types.GRASS,
    )
    VISEGRIP = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=55,
        category=Category.PHYSICAL,
        name=r"Vise Grip",
        pp=30,
    )
    VITALTHROW = Move(
        desc=r"This move does not check accuracy.",
        shortDesc=r"This move does not check accuracy. Goes last.",
        base=70,
        category=Category.PHYSICAL,
        name=r"Vital Throw",
        pp=10,
        type=Types.FIGHTING,
    )
    VOLTSWITCH = Move(
        desc=r"If this move is successful and the user has not fainted, the user switches out even if it is trapped and is replaced immediately by a selected party member. The user does not switch out if there are no unfainted party members, or if the target switched out using an Eject Button or through the effect of the Emergency Exit or Wimp Out Abilities.",
        shortDesc=r"User switches out after damaging the target.",
        accuracy=100,
        base=70,
        category=Category.SPECIAL,
        name=r"Volt Switch",
        pp=20,
        type=Types.ELECTRIC,
    )
    VOLTTACKLE = Move(
        desc=r"Has a 10% chance to paralyze the target. If the target lost HP, the user takes recoil damage equal to 33% the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 33% recoil. 10% chance to paralyze target.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Volt Tackle",
        pp=15,
        type=Types.ELECTRIC,
    )
    WAKEUPSLAP = Move(
        desc=r"Power doubles if the target is asleep. If the user has not fainted, the target wakes up.",
        shortDesc=r"Power doubles if target is asleep, and wakes it.",
        accuracy=100,
        base=70,
        category=Category.PHYSICAL,
        name=r"Wake-Up Slap",
        pp=10,
        type=Types.FIGHTING,
    )
    WATERFALL = Move(
        desc=r"Has a 20% chance to flinch the target.",
        shortDesc=r"20% chance to flinch the target.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Waterfall",
        pp=15,
        type=Types.WATER,
    )
    WATERGUN = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=40,
        category=Category.SPECIAL,
        name=r"Water Gun",
        pp=25,
        type=Types.WATER,
    )
    WATERPLEDGE = Move(
        desc=r"If one of the user's allies chose to use Fire Pledge or Grass Pledge this turn and has not moved yet, it takes its turn immediately after the user and the user's move does nothing. If combined with Fire Pledge, the ally uses Water Pledge with 150 power and a rainbow appears on the user's side for 4 turns, which doubles secondary effect chances but does not stack with the Serene Grace Ability. If combined with Grass Pledge, the ally uses Grass Pledge with 150 power and a swamp appears on the target's side for 4 turns, which quarters the Speed of each Pokemon on that side. When used as a combined move, this move gains STAB no matter what the user's type is. This move does not consume the user's Water Gem, and cannot be redirected by the Storm Drain Ability.",
        shortDesc=r"Use with Grass or Fire Pledge for added effect.",
        accuracy=100,
        base=80,
        category=Category.SPECIAL,
        name=r"Water Pledge",
        pp=10,
        type=Types.WATER,
    )
    WATERPULSE = Move(
        desc=r"Has a 20% chance to confuse the target.",
        shortDesc=r"20% chance to confuse the target.",
        accuracy=100,
        base=60,
        category=Category.SPECIAL,
        name=r"Water Pulse",
        pp=20,
        type=Types.WATER,
    )
    WATERSHURIKEN = Move(
        desc=r"Hits two to five times. Has a 1/3 chance to hit two or three times, and a 1/6 chance to hit four or five times. If one of the hits breaks the target's substitute, it will take damage for the remaining hits. If the user has the Skill Link Ability, this move will always hit five times. If the user is an Ash-Greninja with the Battle Bond Ability, this move has a power of 20 and always hits three times.",
        shortDesc=r"Usually goes first. Hits 2-5 times in one turn.",
        accuracy=100,
        base=15,
        category=Category.SPECIAL,
        name=r"Water Shuriken",
        pp=20,
        type=Types.WATER,
    )
    WATERSPORT = Move(
        desc=r"For 5 turns, all Fire-type attacks used by any active Pokemon have their power multiplied by 0.33. Fails if this effect is already active.",
        shortDesc=r"For 5 turns, Fire-type attacks have 1/3 power.",
        name=r"Water Sport",
        pp=15,
        type=Types.WATER,
    )
    WATERSPOUT = Move(
        desc=r"Power is equal to (user's current HP * 150 / user's maximum HP) rounded down, but not less than 1.",
        shortDesc=r"Less power as user's HP decreases. Hits foe(s).",
        accuracy=100,
        base=150,
        category=Category.SPECIAL,
        name=r"Water Spout",
        pp=5,
        type=Types.WATER,
    )
    WEATHERBALL = Move(
        desc=r"Power doubles if a weather condition other than Delta Stream is active, and this move's type changes to match. Ice type during Hail, Water type during Primordial Sea or Rain Dance, Rock type during Sandstorm, and Fire type during Desolate Land or Sunny Day. If the user is holding Utility Umbrella and uses Weather Ball during Primordial Sea, Rain Dance, Desolate Land, or Sunny Day, the move is still Normal-type and does not have a base power boost.",
        shortDesc=r"Power doubles and type varies in each weather.",
        accuracy=100,
        base=50,
        category=Category.SPECIAL,
        name=r"Weather Ball",
        pp=10,
    )
    WHIRLPOOL = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=85,
        base=35,
        category=Category.SPECIAL,
        name=r"Whirlpool",
        pp=15,
        type=Types.WATER,
    )
    WHIRLWIND = Move(
        desc=r"The target is forced to switch out and be replaced with a random unfainted ally. Fails if the target is the last unfainted Pokemon in its party, or if the target used Ingrain previously or has the Suction Cups Ability.",
        shortDesc=r"Forces the target to switch to a random ally.",
        name=r"Whirlwind",
        pp=20,
    )
    WICKEDBLOW = Move(
        desc=r"This move is always a critical hit unless the target is under the effect of Lucky Chant or has the Battle Armor or Shell Armor Abilities.",
        shortDesc=r"Always results in a critical hit.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Wicked Blow",
        pp=5,
        type=Types.DARK,
    )
    WIDEGUARD = Move(
        desc=r"The user and its party members are protected from moves made by other Pokemon, including allies, during this turn that target all adjacent foes or all adjacent Pokemon. This move modifies the same 1/X chance of being successful used by other protection moves, where X starts at 1 and triples each time this move is successfully used, but does not use the chance to check for failure. X resets to 1 if this move fails, if the user's last move used is not Baneful Bunker, Detect, Endure, King's Shield, Obstruct, Protect, Quick Guard, Spiky Shield, or Wide Guard, or if it was one of those moves and the user's protection was broken. Fails if the user moves last this turn or if this move is already in effect for the user's side.",
        shortDesc=r"Protects allies from multi-target moves this turn.",
        name=r"Wide Guard",
        pp=10,
        type=Types.ROCK,
    )
    WILDCHARGE = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 1/4 the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 1/4 recoil.",
        accuracy=100,
        base=90,
        category=Category.PHYSICAL,
        name=r"Wild Charge",
        pp=15,
        type=Types.ELECTRIC,
    )
    WILLOWISP = Move(
        desc=r"Burns the target.",
        shortDesc=r"Burns the target.",
        accuracy=85,
        name=r"Will-O-Wisp",
        pp=15,
        type=Types.FIRE,
    )
    WINGATTACK = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=60,
        category=Category.PHYSICAL,
        name=r"Wing Attack",
        pp=35,
        type=Types.FLYING,
    )
    WISH = Move(
        desc=r"At the end of the next turn, the Pokemon at the user's position has 1/2 of the user's maximum HP restored to it, rounded half up. Fails if this move is already in effect for the user's position.",
        shortDesc=r"Next turn, 50% of the user's max HP is restored.",
        name=r"Wish",
        pp=10,
    )
    WITHDRAW = Move(
        desc=r"Raises the user's Defense by 1 stage.",
        shortDesc=r"Raises the user's Defense by 1.",
        name=r"Withdraw",
        pp=40,
        type=Types.WATER,
    )
    WONDERROOM = Move(
        desc=r"For 5 turns, all active Pokemon have their Defense and Special Defense stats swapped. Stat stage changes are unaffected. If this move is used during the effect, the effect ends.",
        shortDesc=r"For 5 turns, all Defense and Sp. Def stats switch.",
        name=r"Wonder Room",
        pp=10,
        type=Types.PSYCHIC,
    )
    WOODHAMMER = Move(
        desc=r"If the target lost HP, the user takes recoil damage equal to 33% the HP lost by the target, rounded half up, but not less than 1 HP.",
        shortDesc=r"Has 33% recoil.",
        accuracy=100,
        base=120,
        category=Category.PHYSICAL,
        name=r"Wood Hammer",
        pp=15,
        type=Types.GRASS,
    )
    WORKUP = Move(
        desc=r"Raises the user's Attack and Special Attack by 1 stage.",
        shortDesc=r"Raises the user's Attack and Sp. Atk by 1.",
        name=r"Work Up",
        pp=30,
    )
    WORRYSEED = Move(
        desc=r"Causes the target's Ability to become Insomnia. Fails if the target's Ability is Battle Bond, Comatose, Disguise, Insomnia, Multitype, Power Construct, RKS System, Schooling, Shields Down, Stance Change, Truant, or Zen Mode.",
        shortDesc=r"The target's Ability becomes Insomnia.",
        accuracy=100,
        name=r"Worry Seed",
        pp=10,
        type=Types.GRASS,
    )
    WRAP = Move(
        desc=r"Prevents the target from switching for four or five turns (seven turns if the user is holding Grip Claw). Causes damage to the target equal to 1/8 of its maximum HP (1/6 if the user is holding Binding Band) rounded down, at the end of each turn during effect. The target can still switch out if it is holding Shed Shell or uses Baton Pass, Parting Shot, Teleport, U-turn, or Volt Switch. The effect ends if either the user or the target leaves the field, or if the target uses Rapid Spin or Substitute successfully. This effect is not stackable or reset by using this or another binding move.",
        shortDesc=r"Traps and damages the target for 4-5 turns.",
        accuracy=9,
        base=15,
        category=Category.PHYSICAL,
        name=r"Wrap",
        pp=20,
    )
    WRINGOUT = Move(
        desc=r"Power is equal to 120 * (target's current HP / target's maximum HP) rounded half down, but not less than 1.",
        shortDesc=r"More power the more HP the target has left.",
        accuracy=100,
        category=Category.SPECIAL,
        name=r"Wring Out",
        pp=5,
    )
    XSCISSOR = Move(
        desc=r"No additional effect.",
        shortDesc=r"No additional effect.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"X-Scissor",
        pp=15,
        type=Types.BUG,
    )
    YAWN = Move(
        desc=r"Causes the target to fall asleep at the end of the next turn. Fails when used if the target cannot fall asleep or if it already has a major status condition. At the end of the next turn, if the target is still active, does not have a major status condition, and can fall asleep, it falls asleep. If the target becomes affected, this effect cannot be prevented by Safeguard or a substitute, or by falling asleep and waking up during the effect.",
        shortDesc=r"Puts the target to sleep after 1 turn.",
        name=r"Yawn",
        pp=10,
    )
    ZAPCANNON = Move(
        desc=r"Has a 100% chance to paralyze the target.",
        shortDesc=r"100% chance to paralyze the target.",
        accuracy=5,
        base=120,
        category=Category.SPECIAL,
        name=r"Zap Cannon",
        pp=5,
        type=Types.ELECTRIC,
    )
    ZENHEADBUTT = Move(
        desc=r"Has a 20% chance to flinch the target.",
        shortDesc=r"20% chance to flinch the target.",
        accuracy=9,
        base=80,
        category=Category.PHYSICAL,
        name=r"Zen Headbutt",
        pp=15,
        type=Types.PSYCHIC,
    )
    ZINGZAP = Move(
        desc=r"Has a 30% chance to flinch the target.",
        shortDesc=r"30% chance to flinch the target.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Zing Zap",
        pp=10,
        type=Types.ELECTRIC,
    )
    ZIPPYZAP = Move(
        desc=r"Has a 100% chance to raise the user's evasion by 1 stage.",
        shortDesc=r"Goes first. Raises user's evasion by 1.",
        accuracy=100,
        base=80,
        category=Category.PHYSICAL,
        name=r"Zippy Zap",
        pp=10,
        type=Types.ELECTRIC,
    )
