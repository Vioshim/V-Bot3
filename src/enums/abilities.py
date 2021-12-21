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
from typing import Iterable, Union

from src.structures.ability import Ability

__all__ = ("Abilities",)


class Abilities(Enum):
    """This is an enumration of Pokemon Abilities

    Attributes
    ----------
    name : str
        Ability's Name
    description : str
        Ability's Description

    Methods
    -------
    deduce(item="")
        Returns the abilities whose name fits the given string.
    """

    @property
    def description(self):
        return self.value.description

    @classmethod
    def deduce(cls, item: Union[str, Iterable[str]]) -> set[Abilities]:
        """Deduce the provided abilities out of a string

        Parameters
        ----------
        item : str
            String to inspect

        Returns
        -------
        set[Abilities]
            set with the abilities
        """
        if isinstance(item, Iterable):
            item = ",".join(item)

        info = set()
        elements = {x.value.name: x.name for x in Abilities}
        for elem in item.split(","):
            for data in get_close_matches(
                word=elem.title().strip(),
                possibilities=elements,
                n=1,
            ):
                info.add(Abilities[elements[data]])
        return info

    NOABILITY = Ability(name="No Ability", description="Does nothing.")
    ADAPTABILITY = Ability(
        name="Adaptability",
        description="This Pokemon's same-type attack bonus (STAB) is 2 instead of 1.5.",
    )
    AERILATE = Ability(
        name="Aerilate",
        description="This Pokemon's Normal-type moves become Flying type and have 1.2x power.",
    )
    AFTERMATH = Ability(
        name="Aftermath",
        description="If this Pokemon is KOed with a contact move, that move's user loses 1/4 its max HP.",
    )
    AIRLOCK = Ability(
        name="Air Lock",
        description="While this Pokemon is active, the effects of weather conditions are disabled.",
    )
    ANALYTIC = Ability(
        name="Analytic",
        description="This Pokemon's attacks have 1.3x power if it is the last to move in a turn.",
    )
    ANGERPOINT = Ability(
        name="Anger Point",
        description="If this Pokemon (not its substitute) takes a critical hit, its Attack is raised 12 stages.",
    )
    ANTICIPATION = Ability(
        name="Anticipation",
        description="On switch-in, this Pokemon shudders if any foe has a supereffective or OHKO move.",
    )
    ARENATRAP = Ability(
        name="Arena Trap",
        description="Prevents adjacent foes from choosing to switch unless they are airborne.",
    )
    AROMAVEIL = Ability(
        name="Aroma Veil",
        description="Protects user/allies from Attract, Disable, Encore, Heal Block, Taunt, and Torment.",
    )
    ASONE = Ability(
        name="As One",
        description="(Separate abilities on Glastrier and Spectrier.)",
    )
    ASONEGLASTRIER = Ability(
        name="As One (Glastrier)",
        description="The combination of Unnerve and Chilling Neigh.",
    )
    ASONESPECTRIER = Ability(
        name="As One (Spectrier)",
        description="The combination of Unnerve and Grim Neigh.",
    )
    AURABREAK = Ability(
        name="Aura Break",
        description="While this Pokemon is active, the Dark Aura and Fairy Aura power modifier is 0.75x.",
    )
    BADDREAMS = Ability(
        name="Bad Dreams",
        description="Causes sleeping adjacent foes to lose 1/8 of their max HP at the end of each turn.",
    )
    BALLFETCH = Ability(name="Ball Fetch", description="No competitive use.")
    BATTERY = Ability(
        name="Battery",
        description="This Pokemon's allies have the power of their special attacks multiplied by 1.3.",
    )
    BATTLEARMOR = Ability(
        name="Battle Armor",
        description="This Pokemon cannot be struck by a critical hit.",
    )
    BATTLEBOND = Ability(
        name="Battle Bond",
        description="After KOing a Pokemon: becomes Ash-Greninja, Water Shuriken: 20 power, hits 3x.",
    )
    BEASTBOOST = Ability(
        name="Beast Boost",
        description="This Pokemon's highest stat is raised by 1 if it attacks and KOes another Pokemon.",
    )
    BERSERK = Ability(
        name="Berserk",
        description="This Pokemon's Sp. Atk is raised by 1 when it reaches 1/2 or less of its max HP.",
    )
    BIGPECKS = Ability(
        name="Big Pecks",
        description="Prevents other Pokemon from lowering this Pokemon's Defense stat stage.",
    )
    BLAZE = Ability(
        name="Blaze",
        description="At 1/3 or less of its max HP, this Pokemon's attacking stat is 1.5x with Fire attacks.",
    )
    BULLETPROOF = Ability(
        name="Bulletproof",
        description="Makes user immune to ballistic moves (Shadow Ball, Sludge Bomb, Focus Blast, etc).",
    )
    CHEEKPOUCH = Ability(
        name="Cheek Pouch",
        description="If this Pokemon eats a Berry, it restores 1/3 of its max HP after the Berry's effect.",
    )
    CHILLINGNEIGH = Ability(
        name="Chilling Neigh",
        description="This Pokemon's Attack is raised by 1 stage if it attacks and KOes another Pokemon.",
    )
    CHLOROPHYLL = Ability(
        name="Chlorophyll",
        description="If Sunny Day is active, this Pokemon's Speed is doubled.",
    )
    CLEARBODY = Ability(
        name="Clear Body",
        description="Prevents other Pokemon from lowering this Pokemon's stat stages.",
    )
    CLOUDNINE = Ability(
        name="Cloud Nine",
        description="While this Pokemon is active, the effects of weather conditions are disabled.",
    )
    COLORCHANGE = Ability(
        name="Color Change",
        description="This Pokemon's type changes to the type of a move it's hit by, unless it has the type.",
    )
    COMATOSE = Ability(
        name="Comatose",
        description="This Pokemon cannot be statused, and is considered to be asleep.",
    )
    COMPETITIVE = Ability(
        name="Competitive",
        description="This Pokemon's Sp. Atk is raised by 2 for each of its stats that is lowered by a foe.",
    )
    COMPOUNDEYES = Ability(
        name="Compound Eyes",
        description="This Pokemon's moves have their accuracy multiplied by 1.3.",
    )
    CONTRARY = Ability(
        name="Contrary",
        description="If this Pokemon has a stat stage raised it is lowered instead, and vice versa.",
    )
    CORROSION = Ability(
        name="Corrosion",
        description="This Pokemon can poison or badly poison other Pokemon regardless of their typing.",
    )
    COTTONDOWN = Ability(
        name="Cotton Down",
        description="If this Pokemon is hit, it lowers the Speed of all other Pokemon on the field 1 stage.",
    )
    CURIOUSMEDICINE = Ability(
        name="Curious Medicine",
        description="On switch-in, this Pokemon's allies have their stat stages reset to 0.",
    )
    CURSEDBODY = Ability(
        name="Cursed Body",
        description="If this Pokemon is hit by an attack, there is a 30% chance that move gets disabled.",
    )
    CUTECHARM = Ability(
        name="Cute Charm",
        description="30% chance of infatuating Pokemon of the opposite gender if they make contact.",
    )
    DAMP = Ability(
        name="Damp",
        description="Prevents Explosion/Mind Blown/Misty Explosion/Self-Destruct/Aftermath while active.",
    )
    DANCER = Ability(
        name="Dancer",
        description="After another Pokemon uses a dance move, this Pokemon uses the same move.",
    )
    DARKAURA = Ability(
        name="Dark Aura",
        description="While this Pokemon is active, a Dark move used by any Pokemon has 1.33x power.",
    )
    DAUNTLESSSHIELD = Ability(
        name="Dauntless Shield",
        description="On switch-in, this Pokemon's Defense is raised by 1 stage.",
    )
    DAZZLING = Ability(
        name="Dazzling",
        description="While this Pokemon is active, allies are protected from opposing priority moves.",
    )
    DEFEATIST = Ability(
        name="Defeatist",
        description="While this Pokemon has 1/2 or less of its max HP, its Attack and Sp. Atk are halved.",
    )
    DEFIANT = Ability(
        name="Defiant",
        description="This Pokemon's Attack is raised by 2 for each of its stats that is lowered by a foe.",
    )
    DELTASTREAM = Ability(
        name="Delta Stream",
        description="On switch-in, strong winds begin until this Ability is not active in battle.",
    )
    DESOLATELAND = Ability(
        name="Desolate Land",
        description="On switch-in, extremely harsh sunlight begins until this Ability is not active in battle.",
    )
    DISGUISE = Ability(
        name="Disguise",
        description="(Mimikyu only) The first hit it takes is blocked, and it takes 1/8 HP damage instead.",
    )
    DOWNLOAD = Ability(
        name="Download",
        description="On switch-in, Attack or Sp. Atk is raised 1 stage based on the foes' weaker Defense.",
    )
    DRAGONSMAW = Ability(
        name="Dragon's Maw",
        description="This Pokemon's attacking stat is multiplied by 1.5 while using a Dragon-type attack.",
    )
    DRIZZLE = Ability(
        name="Drizzle",
        description="On switch-in, this Pokemon summons Rain Dance.",
    )
    DROUGHT = Ability(
        name="Drought",
        description="On switch-in, this Pokemon summons Sunny Day.",
    )
    DRYSKIN = Ability(
        name="Dry Skin",
        description="This Pokemon is healed 1/4 by Water, 1/8 by Rain; is hurt 1.25x by Fire, 1/8 by Sun.",
    )
    EARLYBIRD = Ability(
        name="Early Bird",
        description="This Pokemon's sleep counter drops by 2 instead of 1.",
    )
    EFFECTSPORE = Ability(
        name="Effect Spore",
        description="30% chance of poison/paralysis/sleep on others making contact with this Pokemon.",
    )
    ELECTRICSURGE = Ability(
        name="Electric Surge",
        description="On switch-in, this Pokemon summons Electric Terrain.",
    )
    EMERGENCYEXIT = Ability(
        name="Emergency Exit",
        description="This Pokemon switches out when it reaches 1/2 or less of its maximum HP.",
    )
    FAIRYAURA = Ability(
        name="Fairy Aura",
        description="While this Pokemon is active, a Fairy move used by any Pokemon has 1.33x power.",
    )
    FILTER = Ability(
        name="Filter",
        description="This Pokemon receives 3/4 damage from supereffective attacks.",
    )
    FLAMEBODY = Ability(
        name="Flame Body",
        description="30% chance a Pokemon making contact with this Pokemon will be burned.",
    )
    FLAREBOOST = Ability(
        name="Flare Boost",
        description="While this Pokemon is burned, its special attacks have 1.5x power.",
    )
    FLASHFIRE = Ability(
        name="Flash Fire",
        description="This Pokemon's Fire attacks do 1.5x damage if hit by one Fire move; Fire immunity.",
    )
    FLOWERGIFT = Ability(
        name="Flower Gift",
        description="If user is Cherrim and Sunny Day is active, it and allies' Attack and Sp. Def are 1.5x.",
    )
    FLOWERVEIL = Ability(
        name="Flower Veil",
        description="This side's Grass types can't have stats lowered or status inflicted by other Pokemon.",
    )
    FLUFFY = Ability(
        name="Fluffy",
        description="This Pokemon takes 1/2 damage from contact moves, 2x damage from Fire moves.",
    )
    FORECAST = Ability(
        name="Forecast",
        description="Castform's type changes to the current weather condition's type, except Sandstorm.",
    )
    FOREWARN = Ability(
        name="Forewarn",
        description="On switch-in, this Pokemon is alerted to the foes' move with the highest power.",
    )
    FRIENDGUARD = Ability(
        name="Friend Guard",
        description="This Pokemon's allies receive 3/4 damage from other Pokemon's attacks.",
    )
    FRISK = Ability(
        name="Frisk",
        description="On switch-in, this Pokemon identifies the held items of all opposing Pokemon.",
    )
    FULLMETALBODY = Ability(
        name="Full Metal Body",
        description="Prevents other Pokemon from lowering this Pokemon's stat stages.",
    )
    FURCOAT = Ability(
        name="Fur Coat", description="This Pokemon's Defense is doubled."
    )
    GALEWINGS = Ability(
        name="Gale Wings",
        description="If this Pokemon is at full HP, its Flying-type moves have their priority increased by 1.",
    )
    GALVANIZE = Ability(
        name="Galvanize",
        description="This Pokemon's Normal-type moves become Electric type and have 1.2x power.",
    )
    GLUTTONY = Ability(
        name="Gluttony",
        description="When this Pokemon has 1/2 or less of its maximum HP, it uses certain Berries early.",
    )
    GOOEY = Ability(
        name="Gooey",
        description="Pokemon making contact with this Pokemon have their Speed lowered by 1 stage.",
    )
    GORILLATACTICS = Ability(
        name="Gorilla Tactics",
        description="This Pokemon's Attack is 1.5x, but it can only select the first move it executes.",
    )
    GRASSPELT = Ability(
        name="Grass Pelt",
        description="If Grassy Terrain is active, this Pokemon's Defense is multiplied by 1.5.",
    )
    GRASSYSURGE = Ability(
        name="Grassy Surge",
        description="On switch-in, this Pokemon summons Grassy Terrain.",
    )
    GRIMNEIGH = Ability(
        name="Grim Neigh",
        description="This Pokemon's Sp. Atk is raised by 1 stage if it attacks and KOes another Pokemon.",
    )
    GULPMISSILE = Ability(
        name="Gulp Missile",
        description="When hit after Surf/Dive, attacker takes 1/4 max HP and -1 Defense or paralysis.",
    )
    GUTS = Ability(
        name="Guts",
        description="If this Pokemon is statused, its Attack is 1.5x; ignores burn halving physical damage.",
    )
    HARVEST = Ability(
        name="Harvest",
        description="If last item used is a Berry, 50% chance to restore it each end of turn. 100% in Sun.",
    )
    HEALER = Ability(
        name="Healer",
        description="30% chance of curing an adjacent ally's status at the end of each turn.",
    )
    HEATPROOF = Ability(
        name="Heatproof",
        description="The power of Fire-type attacks against this Pokemon is halved; burn damage halved.",
    )
    HEAVYMETAL = Ability(
        name="Heavy Metal", description="This Pokemon's weight is doubled."
    )
    HONEYGATHER = Ability(
        name="Honey Gather", description="No competitive use."
    )
    HUGEPOWER = Ability(
        name="Huge Power", description="This Pokemon's Attack is doubled."
    )
    HUNGERSWITCH = Ability(
        name="Hunger Switch",
        description="If Morpeko, it changes between Full Belly and Hangry Mode at the end of each turn.",
    )
    HUSTLE = Ability(
        name="Hustle",
        description="This Pokemon's Attack is 1.5x and accuracy of its physical attacks is 0.8x.",
    )
    HYDRATION = Ability(
        name="Hydration",
        description="This Pokemon has its status cured at the end of each turn if Rain Dance is active.",
    )
    HYPERCUTTER = Ability(
        name="Hyper Cutter",
        description="Prevents other Pokemon from lowering this Pokemon's Attack stat stage.",
    )
    ICEBODY = Ability(
        name="Ice Body",
        description="If Hail is active, this Pokemon heals 1/16 of its max HP each turn; immunity to Hail.",
    )
    ICEFACE = Ability(
        name="Ice Face",
        description="If Eiscue, the first physical hit it takes deals 0 damage. This effect is restored in Hail.",
    )
    ICESCALES = Ability(
        name="Ice Scales",
        description="This Pokemon receives 1/2 damage from special attacks.",
    )
    ILLUMINATE = Ability(name="Illuminate", description="No competitive use.")
    ILLUSION = Ability(
        name="Illusion",
        description="This Pokemon appears as the last Pokemon in the party until it takes direct damage.",
    )
    IMMUNITY = Ability(
        name="Immunity",
        description="This Pokemon cannot be poisoned. Gaining this Ability while poisoned cures it.",
    )
    IMPOSTER = Ability(
        name="Imposter",
        description="On switch-in, this Pokemon Transforms into the opposing Pokemon that is facing it.",
    )
    INFILTRATOR = Ability(
        name="Infiltrator",
        description="Moves ignore substitutes and foe's Reflect/Light Screen/Safeguard/Mist/Aurora Veil.",
    )
    INNARDSOUT = Ability(
        name="Innards Out",
        description="If this Pokemon is KOed with a move, that move's user loses an equal amount of HP.",
    )
    INNERFOCUS = Ability(
        name="Inner Focus",
        description="This Pokemon cannot be made to flinch. Immune to Intimidate.",
    )
    INSOMNIA = Ability(
        name="Insomnia",
        description="This Pokemon cannot fall asleep. Gaining this Ability while asleep cures it.",
    )
    INTIMIDATE = Ability(
        name="Intimidate",
        description="On switch-in, this Pokemon lowers the Attack of adjacent opponents by 1 stage.",
    )
    INTREPIDSWORD = Ability(
        name="Intrepid Sword",
        description="On switch-in, this Pokemon's Attack is raised by 1 stage.",
    )
    IRONBARBS = Ability(
        name="Iron Barbs",
        description="Pokemon making contact with this Pokemon lose 1/8 of their max HP.",
    )
    IRONFIST = Ability(
        name="Iron Fist",
        description="This Pokemon's punch-based attacks have 1.2x power. Sucker Punch is not boosted.",
    )
    JUSTIFIED = Ability(
        name="Justified",
        description="This Pokemon's Attack is raised by 1 stage after it is damaged by a Dark-type move.",
    )
    KEENEYE = Ability(
        name="Keen Eye",
        description="This Pokemon's accuracy can't be lowered by others; ignores their evasiveness stat.",
    )
    KLUTZ = Ability(
        name="Klutz",
        description="This Pokemon's held item has no effect, except Macho Brace. Fling cannot be used.",
    )
    LEAFGUARD = Ability(
        name="Leaf Guard",
        description="If Sunny Day is active, this Pokemon cannot be statused and Rest will fail for it.",
    )
    LEVITATE = Ability(
        name="Levitate",
        description="This Pokemon is immune to Ground; Gravity/Ingrain/Smack Down/Iron Ball nullify it.",
    )
    LIBERO = Ability(
        name="Libero",
        description="This Pokemon's type changes to match the type of the move it is about to use.",
    )
    LIGHTMETAL = Ability(
        name="Light Metal", description="This Pokemon's weight is halved."
    )
    LIGHTNINGROD = Ability(
        name="Lightning Rod",
        description="This Pokemon draws Electric moves to itself to raise Sp. Atk by 1; Electric immunity.",
    )
    LIMBER = Ability(
        name="Limber",
        description="This Pokemon cannot be paralyzed. Gaining this Ability while paralyzed cures it.",
    )
    LIQUIDOOZE = Ability(
        name="Liquid Ooze",
        description="This Pokemon damages those draining HP from it for as much as they would heal.",
    )
    LIQUIDVOICE = Ability(
        name="Liquid Voice",
        description="This Pokemon's sound-based moves become Water type.",
    )
    LONGREACH = Ability(
        name="Long Reach",
        description="This Pokemon's attacks do not make contact with the target.",
    )
    MAGICBOUNCE = Ability(
        name="Magic Bounce",
        description="This Pokemon blocks certain status moves and bounces them back to the user.",
    )
    MAGICGUARD = Ability(
        name="Magic Guard",
        description="This Pokemon can only be damaged by direct attacks.",
    )
    MAGICIAN = Ability(
        name="Magician",
        description="If this Pokemon has no item, it steals the item off a Pokemon it hits with an attack.",
    )
    MAGMAARMOR = Ability(
        name="Magma Armor",
        description="This Pokemon cannot be frozen. Gaining this Ability while frozen cures it.",
    )
    MAGNETPULL = Ability(
        name="Magnet Pull",
        description="Prevents adjacent Steel-type foes from choosing to switch.",
    )
    MARVELSCALE = Ability(
        name="Marvel Scale",
        description="If this Pokemon is statused, its Defense is 1.5x.",
    )
    MEGALAUNCHER = Ability(
        name="Mega Launcher",
        description="This Pokemon's pulse moves have 1.5x power. Heal Pulse heals 3/4 target's max HP.",
    )
    MERCILESS = Ability(
        name="Merciless",
        description="This Pokemon's attacks are critical hits if the target is poisoned.",
    )
    MIMICRY = Ability(
        name="Mimicry",
        description="This Pokemon's type changes to match the Terrain. Type reverts when Terrain ends.",
    )
    MINUS = Ability(
        name="Minus",
        description="If an active ally has this Ability or the Plus Ability, this Pokemon's Sp. Atk is 1.5x.",
    )
    MIRRORARMOR = Ability(
        name="Mirror Armor",
        description="If this Pokemon's stat stages would be lowered, the attacker's are lowered instead.",
    )
    MISTYSURGE = Ability(
        name="Misty Surge",
        description="On switch-in, this Pokemon summons Misty Terrain.",
    )
    MOLDBREAKER = Ability(
        name="Mold Breaker",
        description="This Pokemon's moves and their effects ignore the Abilities of other Pokemon.",
    )
    MOODY = Ability(
        name="Moody",
        description="Boosts a random stat (except accuracy/evasion) +2 and another stat -1 every turn.",
    )
    MOTORDRIVE = Ability(
        name="Motor Drive",
        description="This Pokemon's Speed is raised 1 stage if hit by an Electric move; Electric immunity.",
    )
    MOXIE = Ability(
        name="Moxie",
        description="This Pokemon's Attack is raised by 1 stage if it attacks and KOes another Pokemon.",
    )
    MULTISCALE = Ability(
        name="Multiscale",
        description="If this Pokemon is at full HP, damage taken from attacks is halved.",
    )
    MULTITYPE = Ability(
        name="Multitype",
        description="If this Pokemon is an Arceus, its type changes to match its held Plate or Z-Crystal.",
    )
    MUMMY = Ability(
        name="Mummy",
        description="Pokemon making contact with this Pokemon have their Ability changed to Mummy.",
    )
    NATURALCURE = Ability(
        name="Natural Cure",
        description="This Pokemon has its non-volatile status condition cured when it switches out.",
    )
    NEUROFORCE = Ability(
        name="Neuroforce",
        description="This Pokemon's attacks that are super effective against the target do 1.25x damage.",
    )
    NEUTRALIZINGGAS = Ability(
        name="Neutralizing Gas",
        description="While this Pokemon is active, Abilities have no effect.",
    )
    NOGUARD = Ability(
        name="No Guard",
        description="Every move used by or against this Pokemon will always hit.",
    )
    NORMALIZE = Ability(
        name="Normalize",
        description="This Pokemon's moves are changed to be Normal type and have 1.2x power.",
    )
    OBLIVIOUS = Ability(
        name="Oblivious",
        description="This Pokemon cannot be infatuated or taunted. Immune to Intimidate.",
    )
    OVERCOAT = Ability(
        name="Overcoat",
        description="This Pokemon is immune to powder moves and damage from Sandstorm or Hail.",
    )
    OVERGROW = Ability(
        name="Overgrow",
        description="At 1/3 or less of its max HP, this Pokemon's attacking stat is 1.5x with Grass attacks.",
    )
    OWNTEMPO = Ability(
        name="Own Tempo",
        description="This Pokemon cannot be confused. Immune to Intimidate.",
    )
    PARENTALBOND = Ability(
        name="Parental Bond",
        description="This Pokemon's damaging moves hit twice. The second hit has its damage quartered.",
    )
    PASTELVEIL = Ability(
        name="Pastel Veil",
        description="This Pokemon and its allies cannot be poisoned. On switch-in, cures poisoned allies.",
    )
    PERISHBODY = Ability(
        name="Perish Body",
        description="Making contact with this Pokemon starts the Perish Song effect for it and the attacker.",
    )
    PICKPOCKET = Ability(
        name="Pickpocket",
        description="If this Pokemon has no item and is hit by a contact move, it steals the attacker's item.",
    )
    PICKUP = Ability(
        name="Pickup",
        description="If this Pokemon has no item, it finds one used by an adjacent Pokemon this turn.",
    )
    PIXILATE = Ability(
        name="Pixilate",
        description="This Pokemon's Normal-type moves become Fairy type and have 1.2x power.",
    )
    PLUS = Ability(
        name="Plus",
        description="If an active ally has this Ability or the Minus Ability, this Pokemon's Sp. Atk is 1.5x.",
    )
    POISONHEAL = Ability(
        name="Poison Heal",
        description="This Pokemon is healed by 1/8 of its max HP each turn when poisoned; no HP loss.",
    )
    POISONPOINT = Ability(
        name="Poison Point",
        description="30% chance a Pokemon making contact with this Pokemon will be poisoned.",
    )
    POISONTOUCH = Ability(
        name="Poison Touch",
        description="This Pokemon's contact moves have a 30% chance of poisoning.",
    )
    POWERCONSTRUCT = Ability(
        name="Power Construct",
        description="If Zygarde 10%/50%, changes to Complete if at 1/2 max HP or less at end of turn.",
    )
    POWEROFALCHEMY = Ability(
        name="Power of Alchemy",
        description="This Pokemon copies the Ability of an ally that faints.",
    )
    POWERSPOT = Ability(
        name="Power Spot",
        description="This Pokemon's allies have the power of their moves multiplied by 1.3.",
    )
    PRANKSTER = Ability(
        name="Prankster",
        description="This Pokemon's Status moves have priority raised by 1, but Dark types are immune.",
    )
    PRESSURE = Ability(
        name="Pressure",
        description="If this Pokemon is the target of a foe's move, that move loses one additional PP.",
    )
    PRIMORDIALSEA = Ability(
        name="Primordial Sea",
        description="On switch-in, heavy rain begins until this Ability is not active in battle.",
    )
    PRISMARMOR = Ability(
        name="Prism Armor",
        description="This Pokemon receives 3/4 damage from supereffective attacks.",
    )
    PROPELLERTAIL = Ability(
        name="Propeller Tail",
        description="This Pokemon's moves cannot be redirected to a different target by any effect.",
    )
    PROTEAN = Ability(
        name="Protean",
        description="This Pokemon's type changes to match the type of the move it is about to use.",
    )
    PSYCHICSURGE = Ability(
        name="Psychic Surge",
        description="On switch-in, this Pokemon summons Psychic Terrain.",
    )
    PUNKROCK = Ability(
        name="Punk Rock",
        description="This Pokemon receives 1/2 damage from sound moves. Its own have 1.3x power.",
    )
    PUREPOWER = Ability(
        name="Pure Power", description="This Pokemon's Attack is doubled."
    )
    QUEENLYMAJESTY = Ability(
        name="Queenly Majesty",
        description="While this Pokemon is active, allies are protected from opposing priority moves.",
    )
    QUICKDRAW = Ability(
        name="Quick Draw",
        description="This Pokemon has a 30% chance to move first in its priority bracket with attacking moves.",
    )
    QUICKFEET = Ability(
        name="Quick Feet",
        description="If this Pokemon is statused, its Speed is 1.5x; ignores Speed drop from paralysis.",
    )
    RAINDISH = Ability(
        name="Rain Dish",
        description="If Rain Dance is active, this Pokemon heals 1/16 of its max HP each turn.",
    )
    RATTLED = Ability(
        name="Rattled",
        description="Speed is raised 1 stage if hit by a Bug-, Dark-, or Ghost-type attack, or Intimidated.",
    )
    RECEIVER = Ability(
        name="Receiver",
        description="This Pokemon copies the Ability of an ally that faints.",
    )
    RECKLESS = Ability(
        name="Reckless",
        description="This Pokemon's attacks with recoil or crash damage have 1.2x power; not Struggle.",
    )
    REFRIGERATE = Ability(
        name="Refrigerate",
        description="This Pokemon's Normal-type moves become Ice type and have 1.2x power.",
    )
    REGENERATOR = Ability(
        name="Regenerator",
        description="This Pokemon restores 1/3 of its maximum HP, rounded down, when it switches out.",
    )
    RIPEN = Ability(
        name="Ripen",
        description="When this Pokemon eats a Berry, its effect is doubled.",
    )
    RIVALRY = Ability(
        name="Rivalry",
        description="This Pokemon's attacks do 1.25x on same gender targets; 0.75x on opposite gender.",
    )
    RKSSYSTEM = Ability(
        name="RKS System",
        description="If this Pokemon is a Silvally, its type changes to match its held Memory.",
    )
    ROCKHEAD = Ability(
        name="Rock Head",
        description="This Pokemon does not take recoil damage besides Struggle/Life Orb/crash damage.",
    )
    ROUGHSKIN = Ability(
        name="Rough Skin",
        description="Pokemon making contact with this Pokemon lose 1/8 of their max HP.",
    )
    RUNAWAY = Ability(name="Run Away", description="No competitive use.")
    SANDFORCE = Ability(
        name="Sand Force",
        description="This Pokemon's Ground/Rock/Steel attacks do 1.3x in Sandstorm; immunity to it.",
    )
    SANDRUSH = Ability(
        name="Sand Rush",
        description="If Sandstorm is active, this Pokemon's Speed is doubled; immunity to Sandstorm.",
    )
    SANDSPIT = Ability(
        name="Sand Spit",
        description="When this Pokemon is hit, Sandstorm begins.",
    )
    SANDSTREAM = Ability(
        name="Sand Stream",
        description="On switch-in, this Pokemon summons Sandstorm.",
    )
    SANDVEIL = Ability(
        name="Sand Veil",
        description="If Sandstorm is active, this Pokemon's evasiveness is 1.25x; immunity to Sandstorm.",
    )
    SAPSIPPER = Ability(
        name="Sap Sipper",
        description="This Pokemon's Attack is raised 1 stage if hit by a Grass move; Grass immunity.",
    )
    SCHOOLING = Ability(
        name="Schooling",
        description="If user is Wishiwashi, changes to School Form if it has > 1/4 max HP, else Solo Form.",
    )
    SCRAPPY = Ability(
        name="Scrappy",
        description="Fighting, Normal moves hit Ghost. Immune to Intimidate.",
    )
    SCREENCLEANER = Ability(
        name="Screen Cleaner",
        description="On switch-in, the effects of Aurora Veil, Light Screen, and Reflect end for both sides.",
    )
    SERENEGRACE = Ability(
        name="Serene Grace",
        description="This Pokemon's moves have their secondary effect chance doubled.",
    )
    SHADOWSHIELD = Ability(
        name="Shadow Shield",
        description="If this Pokemon is at full HP, damage taken from attacks is halved.",
    )
    SHADOWTAG = Ability(
        name="Shadow Tag",
        description="Prevents adjacent foes from choosing to switch unless they also have this Ability.",
    )
    SHEDSKIN = Ability(
        name="Shed Skin",
        description="This Pokemon has a 33% chance to have its status cured at the end of each turn.",
    )
    SHEERFORCE = Ability(
        name="Sheer Force",
        description="This Pokemon's attacks with secondary effects have 1.3x power; nullifies the effects.",
    )
    SHELLARMOR = Ability(
        name="Shell Armor",
        description="This Pokemon cannot be struck by a critical hit.",
    )
    SHIELDDUST = Ability(
        name="Shield Dust",
        description="This Pokemon is not affected by the secondary effect of another Pokemon's attack.",
    )
    SHIELDSDOWN = Ability(
        name="Shields Down",
        description="If Minior, switch-in/end of turn it changes to Core at 1/2 max HP or less, else Meteor.",
    )
    SIMPLE = Ability(
        name="Simple",
        description="When this Pokemon's stat stages are raised or lowered, the effect is doubled instead.",
    )
    SKILLLINK = Ability(
        name="Skill Link",
        description="This Pokemon's multi-hit attacks always hit the maximum number of times.",
    )
    SLOWSTART = Ability(
        name="Slow Start",
        description="On switch-in, this Pokemon's Attack and Speed are halved for 5 turns.",
    )
    SLUSHRUSH = Ability(
        name="Slush Rush",
        description="If Hail is active, this Pokemon's Speed is doubled.",
    )
    SNIPER = Ability(
        name="Sniper",
        description="If this Pokemon strikes with a critical hit, the damage is multiplied by 1.5.",
    )
    SNOWCLOAK = Ability(
        name="Snow Cloak",
        description="If Hail is active, this Pokemon's evasiveness is 1.25x; immunity to Hail.",
    )
    SNOWWARNING = Ability(
        name="Snow Warning",
        description="On switch-in, this Pokemon summons Hail.",
    )
    SOLARPOWER = Ability(
        name="Solar Power",
        description="If Sunny Day is active, this Pokemon's Sp. Atk is 1.5x; loses 1/8 max HP per turn.",
    )
    SOLIDROCK = Ability(
        name="Solid Rock",
        description="This Pokemon receives 3/4 damage from supereffective attacks.",
    )
    SOULHEART = Ability(
        name="Soul-Heart",
        description="This Pokemon's Sp. Atk is raised by 1 stage when another Pokemon faints.",
    )
    SOUNDPROOF = Ability(
        name="Soundproof",
        description="This Pokemon is immune to sound-based moves, including Heal Bell.",
    )
    SPEEDBOOST = Ability(
        name="Speed Boost",
        description="This Pokemon's Speed is raised 1 stage at the end of each full turn on the field.",
    )
    STAKEOUT = Ability(
        name="Stakeout",
        description="This Pokemon's attacking stat is doubled against a target that switched in this turn.",
    )
    STALL = Ability(
        name="Stall",
        description="This Pokemon moves last among Pokemon using the same or greater priority moves.",
    )
    STALWART = Ability(
        name="Stalwart",
        description="This Pokemon's moves cannot be redirected to a different target by any effect.",
    )
    STAMINA = Ability(
        name="Stamina",
        description="This Pokemon's Defense is raised by 1 stage after it is damaged by a move.",
    )
    STANCECHANGE = Ability(
        name="Stance Change",
        description="If Aegislash, changes Forme to Blade before attacks and Shield before King's Shield.",
    )
    STATIC = Ability(
        name="Static",
        description="30% chance a Pokemon making contact with this Pokemon will be paralyzed.",
    )
    STEADFAST = Ability(
        name="Steadfast",
        description="If this Pokemon flinches, its Speed is raised by 1 stage.",
    )
    STEAMENGINE = Ability(
        name="Steam Engine",
        description="This Pokemon's Speed is raised by 6 stages after it is damaged by Fire/Water moves.",
    )
    STEELWORKER = Ability(
        name="Steelworker",
        description="This Pokemon's attacking stat is multiplied by 1.5 while using a Steel-type attack.",
    )
    STEELYSPIRIT = Ability(
        name="Steely Spirit",
        description="This Pokemon and its allies' Steel-type moves have their power multiplied by 1.5.",
    )
    STENCH = Ability(
        name="Stench",
        description="This Pokemon's attacks without a chance to flinch gain a 10% chance to flinch.",
    )
    STICKYHOLD = Ability(
        name="Sticky Hold",
        description="This Pokemon cannot lose its held item due to another Pokemon's attack.",
    )
    STORMDRAIN = Ability(
        name="Storm Drain",
        description="This Pokemon draws Water moves to itself to raise Sp. Atk by 1; Water immunity.",
    )
    STRONGJAW = Ability(
        name="Strong Jaw",
        description="This Pokemon's bite-based attacks have 1.5x power. Bug Bite is not boosted.",
    )
    STURDY = Ability(
        name="Sturdy",
        description="If this Pokemon is at full HP, it survives one hit with at least 1 HP. Immune to OHKO.",
    )
    SUCTIONCUPS = Ability(
        name="Suction Cups",
        description="This Pokemon cannot be forced to switch out by another Pokemon's attack or item.",
    )
    SUPERLUCK = Ability(
        name="Super Luck",
        description="This Pokemon's critical hit ratio is raised by 1 stage.",
    )
    SURGESURFER = Ability(
        name="Surge Surfer",
        description="If Electric Terrain is active, this Pokemon's Speed is doubled.",
    )
    SWARM = Ability(
        name="Swarm",
        description="At 1/3 or less of its max HP, this Pokemon's attacking stat is 1.5x with Bug attacks.",
    )
    SWEETVEIL = Ability(
        name="Sweet Veil",
        description="This Pokemon and its allies cannot fall asleep.",
    )
    SWIFTSWIM = Ability(
        name="Swift Swim",
        description="If Rain Dance is active, this Pokemon's Speed is doubled.",
    )
    SYMBIOSIS = Ability(
        name="Symbiosis",
        description="If an ally uses its item, this Pokemon gives its item to that ally immediately.",
    )
    SYNCHRONIZE = Ability(
        name="Synchronize",
        description="If another Pokemon burns/poisons/paralyzes this Pokemon, it also gets that status.",
    )
    TANGLEDFEET = Ability(
        name="Tangled Feet",
        description="This Pokemon's evasiveness is doubled as long as it is confused.",
    )
    TANGLINGHAIR = Ability(
        name="Tangling Hair",
        description="Pokemon making contact with this Pokemon have their Speed lowered by 1 stage.",
    )
    TECHNICIAN = Ability(
        name="Technician",
        description="This Pokemon's moves of 60 power or less have 1.5x power. Includes Struggle.",
    )
    TELEPATHY = Ability(
        name="Telepathy",
        description="This Pokemon does not take damage from attacks made by its allies.",
    )
    TERAVOLT = Ability(
        name="Teravolt",
        description="This Pokemon's moves and their effects ignore the Abilities of other Pokemon.",
    )
    THICKFAT = Ability(
        name="Thick Fat",
        description="Fire/Ice-type moves against this Pokemon deal damage with a halved attacking stat.",
    )
    TINTEDLENS = Ability(
        name="Tinted Lens",
        description="This Pokemon's attacks that are not very effective on a target deal double damage.",
    )
    TORRENT = Ability(
        name="Torrent",
        description="At 1/3 or less of its max HP, this Pokemon's attacking stat is 1.5x with Water attacks.",
    )
    TOUGHCLAWS = Ability(
        name="Tough Claws",
        description="This Pokemon's contact moves have their power multiplied by 1.3.",
    )
    TOXICBOOST = Ability(
        name="Toxic Boost",
        description="While this Pokemon is poisoned, its physical attacks have 1.5x power.",
    )
    TRACE = Ability(
        name="Trace",
        description="On switch-in, or when it can, this Pokemon copies a random adjacent foe's Ability.",
    )
    TRANSISTOR = Ability(
        name="Transistor",
        description="This Pokemon's attacking stat is multiplied by 1.5 while using an Electric-type attack.",
    )
    TRIAGE = Ability(
        name="Triage",
        description="This Pokemon's healing moves have their priority increased by 3.",
    )
    TRUANT = Ability(
        name="Truant",
        description="This Pokemon skips every other turn instead of using a move.",
    )
    TURBOBLAZE = Ability(
        name="Turboblaze",
        description="This Pokemon's moves and their effects ignore the Abilities of other Pokemon.",
    )
    UNAWARE = Ability(
        name="Unaware",
        description="This Pokemon ignores other Pokemon's stat stages when taking or doing damage.",
    )
    UNBURDEN = Ability(
        name="Unburden",
        description="Speed is doubled on held item loss; boost is lost if it switches, gets new item/Ability.",
    )
    UNNERVE = Ability(
        name="Unnerve",
        description="While this Pokemon is active, it prevents opposing Pokemon from using their Berries.",
    )
    UNSEENFIST = Ability(
        name="Unseen Fist",
        description="All contact moves hit through protection.",
    )
    VICTORYSTAR = Ability(
        name="Victory Star",
        description="This Pokemon and its allies' moves have their accuracy multiplied by 1.1.",
    )
    VITALSPIRIT = Ability(
        name="Vital Spirit",
        description="This Pokemon cannot fall asleep. Gaining this Ability while asleep cures it.",
    )
    VOLTABSORB = Ability(
        name="Volt Absorb",
        description="This Pokemon heals 1/4 of its max HP when hit by Electric moves; Electric immunity.",
    )
    WANDERINGSPIRIT = Ability(
        name="Wandering Spirit",
        description="Pokemon making contact with this Pokemon have their Ability swapped with this one.",
    )
    WATERABSORB = Ability(
        name="Water Absorb",
        description="This Pokemon heals 1/4 of its max HP when hit by Water moves; Water immunity.",
    )
    WATERBUBBLE = Ability(
        name="Water Bubble",
        description="This Pokemon's Water power is 2x; it can't be burned; Fire power against it is halved.",
    )
    WATERCOMPACTION = Ability(
        name="Water Compaction",
        description="This Pokemon's Defense is raised 2 stages after it is damaged by a Water-type move.",
    )
    WATERVEIL = Ability(
        name="Water Veil",
        description="This Pokemon cannot be burned. Gaining this Ability while burned cures it.",
    )
    WEAKARMOR = Ability(
        name="Weak Armor",
        description="If a physical attack hits this Pokemon, Defense is lowered by 1, Speed is raised by 2.",
    )
    WHITESMOKE = Ability(
        name="White Smoke",
        description="Prevents other Pokemon from lowering this Pokemon's stat stages.",
    )
    WIMPOUT = Ability(
        name="Wimp Out",
        description="This Pokemon switches out when it reaches 1/2 or less of its maximum HP.",
    )
    WONDERGUARD = Ability(
        name="Wonder Guard",
        description="This Pokemon can only be damaged by supereffective moves and indirect damage.",
    )
    WONDERSKIN = Ability(
        name="Wonder Skin",
        description="Status moves with accuracy checks are 50% accurate when used on this Pokemon.",
    )
    ZENMODE = Ability(
        name="Zen Mode",
        description="If Darmanitan, at end of turn changes Mode to Standard if > 1/2 max HP, else Zen.",
    )
