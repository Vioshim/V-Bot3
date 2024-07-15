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

import math
import re
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from io import BytesIO
from typing import Any, Iterable, Optional, Type

from discord import Color, Embed, File, Interaction, PartialEmoji
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.utils import snowflake_time, utcnow
from docx import Document as document
from docx.document import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pokeball import Pokeball
from src.structures.pronouns import Pronoun
from src.structures.species import (
    CustomGMax,
    CustomMega,
    CustomParadox,
    CustomSpecies,
    CustomUltraBeast,
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Paradox,
    Pokemon,
    Species,
    UltraBeast,
    Variant,
)
from src.utils.functions import common_pop_get, fix, int_check
from src.utils.imagekit import Fonts, ImageKit

__all__ = ("Character", "CharacterArg", "Kind", "Size")


class AgeGroup(Enum):
    Unknown = 0, "The age is Unknown."
    Egg = 1, "Newly hatched Pokémon."
    Baby = 5, "Recently evolved from an egg, still in early stages"
    Toddler = 10, "Learning and developing, but not quite a child."
    Child = 15, "Considered a child in their species."
    Adolescent = 18, "15 - 17 (Rough equivalent in human years)"
    Young_Adult = 26, "18 - 25 (Rough equivalent in human years)"
    Adult = 40, "26 - 39 (Rough equivalent in human years)"
    Middle_Aged = 55, "40 - 54 (Rough equivalent in human years)"
    Senior = 70, "55 - 69 (Rough equivalent in human years)"
    Elderly = 85, "70 - 84 (Rough equivalent in human years)"
    Ancient = 100, "85 - 99 (Rough equivalent in human years)"
    Timeless = 125, "Magic, pokeball from past, or lived long enough."

    @classmethod
    def parse(cls, item: AgeGroup | Optional[int] | str):
        if isinstance(item, AgeGroup):
            return item

        item = item or 0
        if isinstance(item, str):
            if item.isdigit():
                item = int(item)
            elif foo := process.extractOne(
                item,
                cls,
                processor=lambda x: x.name if isinstance(x, cls) else x,
                score_cutoff=85,
            ):
                return foo[0]

        return cls.from_number(item) if isinstance(item, int) else cls.Unknown

    @classmethod
    def from_number(cls, item: Optional[int]):
        base = item or 0
        return next((x for x in cls if x.value[0] >= base), cls.Ancient)

    @property
    def title(self):
        return self.name.replace("_", " ")

    @property
    def key(self):
        value, _ = self.value
        return value

    @property
    def description(self):
        _, desc = self.value
        return desc


class Kind(Enum):
    Common = Pokemon
    Legendary = Legendary
    Mythical = Mythical
    UltraBeast = UltraBeast
    Fakemon = Fakemon
    Variant = Variant
    Mega = Mega
    Fusion = Fusion
    Paradox = Paradox
    CustomMega = CustomMega
    CustomParadox = CustomParadox
    CustomUltraBeast = CustomUltraBeast
    CustomGMax = CustomGMax

    @property
    def title(self):
        name = self.name
        if name.startswith("Custom"):
            name = name.removeprefix("Custom") + " (Custom)"
        return name.replace("Common", "Pokemon")

    @property
    def to_db(self):
        match self:
            case self.Common:
                return "COMMON"
            case self.Legendary:
                return "LEGENDARY"
            case self.Mythical:
                return "MYTHICAL"
            case self.UltraBeast:
                return "ULTRA BEAST"
            case self.Fakemon:
                return "FAKEMON"
            case self.Variant:
                return "VARIANT"
            case self.Paradox:
                return "PARADOX"
            case self.Mega:
                return "MEGA"
            case self.Fusion:
                return "FUSION"
            case self.CustomMega:
                return "CUSTOM MEGA"
            case self.CustomUltraBeast:
                return "CUSTOM ULTRA BEAST"
            case self.CustomParadox:
                return "CUSTOM PARADOX"
            case self.CustomGMax:
                return "CUSTOM GMAX"

    @classmethod
    def associated(cls, name: str) -> Optional[Kind]:
        match fix(name):
            case "COMMON":
                return cls.Common
            case "LEGENDARY":
                return cls.Legendary
            case "MYTHICAL":
                return cls.Mythical
            case "ULTRABEAST":
                return cls.UltraBeast
            case "FAKEMON":
                return cls.Fakemon
            case "VARIANT":
                return cls.Variant
            case "PARADOX":
                return cls.Paradox
            case "MEGA":
                return cls.Mega
            case "FUSION":
                return cls.Fusion
            case "CUSTOMMEGA":
                return cls.CustomMega
            case "CUSTOMULTRABEAST":
                return cls.CustomUltraBeast
            case "CUSTOMPARADOX":
                return cls.CustomParadox
            case "CUSTOMGMAX":
                return cls.CustomGMax

    def all(self) -> frozenset[Species]:
        return self.value.all()

    @classmethod
    def from_class(cls, item: Type[Species]):
        return next(
            (element for element in cls if isinstance(item, element.value)),
            cls.Fakemon,
        )


class Size(float, Enum):
    Maximum = 1.5
    Very_Large = 1.375
    Large = 1.25
    Above_Average = 1.125
    Average = 1.0
    Below_Average = 0.875
    Small = 0.75
    Very_Small = 0.625
    Minimum = 0.5

    @property
    def emoji(self):
        if self.value > 1:
            return "🟧"
        if self.value < 1:
            return "🟦"
        return "🟩"

    @property
    def reference_name(self):
        return "Default" if self == Size.Average else self.name.replace("_", " ")

    def height_value(self, value: float = 0):
        if value:
            return round(value * self, 2)
        return round(0.825 * self.value**2, 2)

    def weight_value(self, value: float = 0):
        if value:
            return round(value * self.value, 2)
        return round(10 * ((self.value - 0.25) / 0.6) ** 3, 2)

    @staticmethod
    def meters_to_ft_inches(value: float = 0):
        return int(value / 0.3048), int(value / 0.3048 % 1 * 12)

    @staticmethod
    def kg_to_lbs(value: float = 0):
        return math.ceil(value * 220.462) / 100

    @staticmethod
    def ft_inches_to_meters(feet: float = 0, inches: float = 0):
        return math.ceil(feet * 30.48 + inches * 2.54) / 100

    @staticmethod
    def lbs_to_kgs(value: float = 0):
        return math.ceil(value * 45.359) / 100

    def height_info(self, value: float = 0):
        value = self.height_value(value)
        feet, inches = self.meters_to_ft_inches(value)
        if (feet, inches) <= (1, 0):
            inches += 12 * feet
            return f"{value*100:.2f} cm / {inches:02d} in"
        return f"{value:.2f} m / {feet}' {inches:02d}\" ft"

    def weight_info(self, value: float = 0):
        value = self.weight_value(value)
        lbs = self.kg_to_lbs(value)

        if value < 1:
            return f"{value*1000:.2f} g / {lbs*16:.2f} oz"

        return f"{value:.2f} kg / {lbs:.2f} lbs"


class Stats(StrEnum):
    HP = "HP"
    ATK = "Attack"
    DEF = "Defense"
    SPA = "Sp. Attack"
    SPD = "Sp. Defense"
    SPE = "Speed"


class Nature(Enum):
    def __init__(self, high: Stats, low: Stats):
        self.description = f"⬆ {high.value} | ⬇ {low.value}"

    # fmt: off
    Composed   = (Stats.HP,  Stats.HP )  # noqa: E202,E221
    Cuddly     = (Stats.HP,  Stats.ATK)  # noqa: E221
    Distracted = (Stats.HP,  Stats.DEF)  # noqa: E221
    Proud      = (Stats.HP,  Stats.SPA)  # noqa: E221
    Decisive   = (Stats.HP,  Stats.SPD)  # noqa: E221
    Patient    = (Stats.HP,  Stats.SPE)  # noqa: E221
    Desperate  = (Stats.ATK, Stats.HP )  # noqa: E202,E221
    Hardy      = (Stats.ATK, Stats.ATK)  # noqa: E221
    Lonely     = (Stats.ATK, Stats.DEF)  # noqa: E221
    Adamant    = (Stats.ATK, Stats.SPA)  # noqa: E221
    Naughty    = (Stats.ATK, Stats.SPD)  # noqa: E221
    Brave      = (Stats.ATK, Stats.SPE)  # noqa: E221
    Stark      = (Stats.DEF, Stats.HP )  # noqa: E202,E221
    Bold       = (Stats.DEF, Stats.ATK)  # noqa: E221
    Docile     = (Stats.DEF, Stats.DEF)  # noqa: E221
    Impish     = (Stats.DEF, Stats.SPA)  # noqa: E221
    Lax        = (Stats.DEF, Stats.SPD)  # noqa: E221
    Relaxed    = (Stats.DEF, Stats.SPE)  # noqa: E221
    Curious    = (Stats.SPA, Stats.HP )  # noqa: E202,E221
    Modest     = (Stats.SPA, Stats.ATK)  # noqa: E221
    Mild       = (Stats.SPA, Stats.DEF)  # noqa: E221
    Bashful    = (Stats.SPA, Stats.SPA)  # noqa: E221
    Rash       = (Stats.SPA, Stats.SPD)  # noqa: E221
    Quiet      = (Stats.SPA, Stats.SPE)  # noqa: E221
    Dreamy     = (Stats.SPD, Stats.HP )  # noqa: E202,E221
    Calm       = (Stats.SPD, Stats.ATK)  # noqa: E221
    Gentle     = (Stats.SPD, Stats.DEF)  # noqa: E221
    Careful    = (Stats.SPD, Stats.SPA)  # noqa: E221
    Quirky     = (Stats.SPD, Stats.SPD)  # noqa: E221
    Sassy      = (Stats.SPD, Stats.SPE)  # noqa: E221
    Skittish   = (Stats.SPE, Stats.HP )  # noqa: E202,E221
    Timid      = (Stats.SPE, Stats.ATK)  # noqa: E221
    Hasty      = (Stats.SPE, Stats.DEF)  # noqa: E221
    Jolly      = (Stats.SPE, Stats.SPA)  # noqa: E221
    Naive      = (Stats.SPE, Stats.SPD)  # noqa: E221
    Serious    = (Stats.SPE, Stats.SPE)  # noqa: E221
    # fmt: on


class Trope(Enum):
    Common = "Common character."
    Bartender = "Alcoholic drink maker."
    Drifter = "Comes from another world."
    Feral = "Feral character."
    Pack_Leader = "Feral pack leader."
    Great_Feral = "Kaiju or giant feral."
    Reploid = "Sentient robot or android."
    Tribal = "Live like people and ferals."
    Ditto = "Shape-shifter, can transform into anything."
    Illusionist = "Illusionist, can create illusions."
    Spirit = "Good, neutral or evil spirit."
    Alchemist = "Master of potions and transmutations."
    Chef = "Master of cooking."
    Inventor = "Creates gadgets and machines."
    Naturalist = "Loves nature and animals."
    Guard = "Protects others."
    Healer = "Heals others."
    Weaponry = "Master of weapons."
    Armory = "Master of armor."
    Prime = "Cosmic guardians of the universe."
    Player = "Player character, external to the story."
    GM = "Game Master character."
    Monk = "Handles spiritual matters."
    Gambler = "Risk-taker, loves games of chance."
    Librarian = "Loves books and knowledge."
    Researcher = "Writes and researches."
    Antagonist = "Villain or rival character."
    Asshole = "Rude and mean character."
    Aura_Bot = "Redwood network reploid assistant."
    Adopt_Care = "Seeking adoption, foster or care."
    Caretaker = "Cares for others, like a parent."
    Tailor = "Makes clothes and accessories."
    Fashion_Model = "Poses for art and fashion."
    Fighter = "Fights for fun or sport."
    Brawler = "Fights for survival."
    Warrior = "Fights for honor."
    Gladiator = "Fights for entertainment."
    Orb_Launcher = "Orb launcher, uses orbs."
    Lorekeeper = "Dungeon researcher and historian."
    Miner = "Digs and mines for resources."
    Blacksmith = "Makes weapons and armor."
    Enchanter = "Enchants items and weapons."
    Merchant = "Sells goods and services."
    Vigilante = "Fights crime and corruption."
    Mercenary = "Hired for missions and tasks."
    Entertainer = "Performs for others."
    Musician = "Plays or composes music."
    Thief = "Steals for profit or fun."
    Politician = "Affiliated with politics."
    Clairvoyant = "Reads past, predicts behavior."
    Carpenter = "Builds and repairs structures."
    Engineer = "Designs and builds machines."
    Mechanic = "Repairs and maintains machines."
    Driver = "Drives and operates ground vehicles."
    Pilot = "Flies and operates air vehicles."
    Sailor = "Navigates and operates water/lava vehicles."
    Fisherman = "Catches fish and seafood."
    Hunter = "Hunts animals for food or sport."
    Farmer = "Grows crops and raises animals."
    Gardener = "Cares for plants and flowers."
    Herbalist = "Uses plants for medicine."
    Doctor = "Heals and treats injuries."
    Nurse = "Assists doctors and patients."
    Surgeon = "Performs surgeries and operations."
    Therapist = "Counsels and treats mental health."
    Mage = "Uses magic and spells."
    Sorcerer = "Uses dark magic and curses."
    Wizard = "Uses arcane magic and rituals."
    Warlock = "Uses demonic magic and pacts."
    Witch = "Uses nature magic and potions."
    Shaman = "Uses spirit magic and rituals."
    Bomber = "Uses explosives and bombs."


class SizeCategory(float, Enum):
    Mini = 0.1
    Small = 0.2
    Below_Average = 0.5
    Average = 1.0
    Above_Average = 1.25
    Large = 1.5
    Alpha = Large
    Kaiju = 12


@dataclass(slots=True)
class Character:
    species: Optional[Species] = None
    id: int = 0
    author: Optional[int] = None
    thread: Optional[int] = None
    server: int = 1196879060173852702
    name: str = ""
    age: AgeGroup = AgeGroup.Unknown
    pronoun: frozenset[Pronoun] = field(default_factory=frozenset)
    backstory: Optional[str] = None
    personality: Optional[str] = None
    extra: Optional[str] = None
    abilities: frozenset[Ability] = field(default_factory=frozenset)
    moveset: frozenset[Move] = field(default_factory=frozenset)
    sp_ability: Optional[SpAbility] = None
    url: str = ""
    image: Optional[int | str | File] = None
    location: Optional[int] = None
    hidden_power: Optional[TypingEnum] = None
    size: Size | float = Size.Average
    size_category: SizeCategory = SizeCategory.Average
    weight: Size | float = Size.Average
    last_used: Optional[int] = None
    nature: Optional[Nature] = None
    hidden_info: Optional[str] = None
    tropes: frozenset[Trope] = field(default_factory=frozenset)
    emoji: Optional[PartialEmoji] = None
    pokeball: Optional[Pokeball] = None

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Character:
        kwargs = {k.lower(): v for k, v in kwargs.items() if k.lower() in cls.__slots__}
        return Character(**kwargs)

    def to_mongo_dict(self):
        data = asdict(self)
        data["abilities"] = [x.id for x in self.abilities]
        data["pokeball"] = self.pokeball and self.pokeball.name
        data["species"] = self.species and self.species.as_data()
        data["age"] = self.age.name
        data["size"] = self.size.name if isinstance(self.size, Size) else self.size
        data["weight"] = self.weight.name if isinstance(self.weight, Size) else self.weight
        data["size_category"] = self.size_category.name
        data["pronoun"] = [x.name for x in self.pronoun]
        data["moveset"] = [x.id for x in self.moveset]
        data["hidden_power"] = self.hidden_power.name if self.hidden_power else None
        data["tropes"] = [x.name for x in self.tropes]
        data["nature"] = self.nature.name if self.nature else None
        data["emoji"] = self.emoji and str(self.emoji)
        if isinstance(self.sp_ability, SpAbility):
            aux = asdict(self.sp_ability)
            aux["kind"] = self.sp_ability.kind.name
            data["sp_ability"] = aux
        if isinstance(self.image, File):
            data["image"] = None
        return data

    @classmethod
    def from_mongo_dict(cls, dct: dict[str, Any]):
        dct.pop("_id", None)
        species = dct.pop("species", None)
        dct["tropes"] = dct.get("trope", [])
        dct["species"] = species and Species.from_data(species)
        return Character.from_dict(dct)

    def __post_init__(self):
        self.image_url = self.image
        self.url = self.url or ""
        if isinstance(self.species, str):
            self.species = Species.from_ID(self.species)
        if not self.server:
            self.server = 1196879060173852702
        if isinstance(self.sp_ability, dict):
            self.sp_ability = SpAbility(**self.sp_ability)
        if isinstance(self.abilities, str):
            self.abilities = [self.abilities]
        self.abilities = Ability.deduce_many(*self.abilities)
        if isinstance(self.moveset, str):
            self.moveset = [self.moveset]
        self.moveset = Move.deduce_many(*self.moveset)
        if isinstance(self.size, str):
            try:
                self.size = Size[self.size.removesuffix("_")]
            except KeyError:
                self.size = Size.Average
        if isinstance(self.weight, str):
            try:
                self.weight = Size[self.weight]
            except KeyError:
                self.weight = Size.Average
        if isinstance(self.pokeball, str):
            try:
                self.pokeball = Pokeball[self.pokeball]
            except KeyError:
                self.pokeball = None

        if isinstance(self.nature, str):
            try:
                self.nature = Nature[self.nature]
            except KeyError:
                self.nature = None
        if isinstance(self.pronoun, str):
            self.pronoun = [self.pronoun]
        self.pronoun = Pronoun.deduce_many(*self.pronoun)
        self.age = AgeGroup.parse(self.age)
        if self.hidden_power:
            self.hidden_power = TypingEnum.deduce(self.hidden_power)

        if isinstance(self.tropes, str):
            self.tropes = [self.tropes]

        if isinstance(self.tropes, list):
            try:
                self.tropes = frozenset({Trope[x] for x in self.tropes})
            except KeyError:
                self.tropes = frozenset()

        if isinstance(self.size_category, str):
            try:
                self.size_category = SizeCategory[self.size_category]
            except KeyError:
                self.size_category = SizeCategory.Average
        if isinstance(self.emoji, str):
            try:
                self.emoji = PartialEmoji.from_str(self.emoji)
            except ValueError:
                self.emoji = None

    def __eq__(self, other: Character):
        return isinstance(other, Character) and self.id == other.id

    def __ne__(self, other: Character) -> bool:
        return isinstance(other, Character) and other.id != self.id

    def __hash__(self) -> int:
        return self.id >> 22

    @property
    def min_amount_species(self):
        return 2 if isinstance(self.species, Fusion) else 1

    @property
    def max_amount_species(self):
        return 3 if isinstance(self.species, Fusion) else 1

    @property
    def last_used_at(self):
        data = max(self.id or 0, self.location or 0, self.last_used or 0)
        return snowflake_time(data) if data else utcnow()

    @property
    def types(self) -> frozenset[TypingEnum]:
        return frozenset(self.species.types) if self.species else frozenset()

    @property
    def possible_types(self) -> frozenset[frozenset[TypingEnum]]:
        return self.species.possible_types if self.species else frozenset()

    @property
    def kind(self):
        return Kind.from_class(self.species)

    @property
    def image_url(self):
        if isinstance(self.image, int) and self.thread:
            return f"https://media.discordapp.net/attachments/{self.thread}/{self.image}/image.png"
        if isinstance(self.image, str) and self.image.startswith(
            "https://media.discordapp.net/attachments/1196967811034132581/"
        ):
            return self.image

    @image_url.setter
    def image_url(self, url: str):
        if isinstance(url, str) and self.thread:
            if find := re.match(
                rf"https:\/\/\w+\.discordapp\.\w+\/attachments\/{self.thread}\/(\d+)\/image\.png",
                string=url,
            ):
                url = int(find[1])

        self.image = url or None

    @image_url.deleter
    def image_url(self):
        self.image = None

    @property
    def created_at(self):
        return snowflake_time(self.id) if self.id else utcnow()

    @property
    def document_url(self):
        return f"https://docs.google.com/document/d/{self.url}/edit?usp=sharing" if self.url else ""

    @document_url.setter
    def document_url(self, url: str):
        url = url.removeprefix("https://docs.google.com/document/d/")
        url = url.removesuffix("/edit?usp=sharing")
        self.url = url

    @document_url.deleter
    def document_url(self):
        self.url = ""

    @property
    def evolves_from(self):
        return self.species and self.species.species_evolves_from

    @property
    def evolves_to(self):
        return self.species and self.species.species_evolves_to

    @property
    def pronoun_emoji(self):
        match self.pronoun:
            case x if Pronoun.He in x and Pronoun.She not in x:
                return Pronoun.He.emoji
            case x if Pronoun.She in x and Pronoun.He not in x:
                return Pronoun.She.emoji
            case _:
                return Pronoun.Them.emoji

    @property
    def default_emoji(self):
        return self.emoji or self.pronoun_emoji

    @property
    def pronoun_text(self):
        return ", ".join(sorted(x.name for x in self.pronoun))

    @property
    def movepool(self) -> Movepool:
        return self.species.movepool if self.species else Movepool()

    @property
    def total_movepool(self) -> Movepool:
        movepool = Movepool()
        if self.species:
            movepool += self.species.total_movepool
        return movepool

    @property
    def place_mention(self):
        if self.location:
            return f"<#{self.location}>"

    @property
    def jump_url(self):
        if self.server and self.thread and self.id:
            return f"https://discord.com/channels/{self.server}/{self.thread}/{self.id}"

    @property
    def location_url(self):
        url = f"https://discord.com/channels/{self.server}/"
        url += f"{self.location}" if self.location else ""
        return f"{url}/{self.last_used}" if self.last_used else url

    @property
    def height_text(self):
        return Size.Average.height_info(self.height_value)

    @property
    def height_value(self):
        if isinstance(self.size, Size):
            height = self.species.height if self.species else 0
            value = self.size.height_value(height)
        else:
            value = self.size
        return round(value, 2)

    @property
    def weight_text(self):
        return Size.Average.weight_info(self.weight_value)

    @property
    def weight_value(self):
        if isinstance(self.weight, Size):
            weight = self.species.weight if self.species else 0
            value = self.weight.weight_value(weight)
        else:
            value = self.weight
        return round(value, 2)

    @property
    def default_image(self):
        """This allows to obtain a default image for the character

        Returns
        -------
        Optional[str]
            Image it defaults to
        """
        return self.species and self.species.base_image

    @property
    def species_data(self):
        match self.species:
            case mon if isinstance(mon, Fusion):
                return "Fusion", "\n".join(f"* {x.name}" for x in mon.bases)[:1024]
            case mon if isinstance(mon, Fakemon):
                a1 = Ability.get(name="Beast Boost")
                if a1 in self.abilities:
                    name = "Fakemon Ultra Beast"
                elif evolves_from := mon.species_evolves_from:
                    name = "Fakemon Evo" if evolves_from.name == mon.name else f"{evolves_from.name} Evo"
                else:
                    name = "Fakemon Species"
                return name, mon.name
            case mon if isinstance(mon, CustomMega):
                return "Mega", mon.name
            case mon if isinstance(mon, (CustomParadox, CustomUltraBeast, Variant)):
                a1 = Ability.get(name="Protosynthesis")
                a2 = Ability.get(name="Quark Drive")

                if a1 in self.abilities:
                    phrase = "Past"
                elif a2 in self.abilities:
                    phrase = "Future"
                elif TypingEnum.Typeless in mon.types:
                    phrase = "Typeless"
                else:
                    phrase = mon.__class__.__name__.removeprefix("Custom")

                if mon.base and mon.base.name != mon.name:
                    phrase = {"UltraBeast": "UB"}.get(phrase, phrase)
                    phrase = f"{phrase} {mon.base.name}"

                return phrase, mon.name
            case mon if isinstance(mon, Species):
                phrase = mon.__class__.__name__.removeprefix("Custom")
                return phrase, mon.name

    @property
    def embed(self) -> Embed:
        return self.embeds[0]

    @property
    def color(self) -> Color:
        if hidden_power := self.hidden_power:
            return Color(hidden_power.color)
        return Color.blurple()

    @property
    def embeds(self) -> list[Embed]:
        """Discord embed out of the character

        Returns
        -------
        list[Embed]
            Embed with the character's information
        """
        c_embed = Embed(title=self.name[:256].title(), url=self.document_url, timestamp=self.created_at)
        embeds = [c_embed]

        if backstory := self.backstory:
            c_embed.description = backstory[:2000]

        if pronoun := self.pronoun_text:
            c_embed.add_field(name="Pronoun", value=pronoun)

        c_embed.add_field(name="Age", value=self.age.title)

        if species_data := self.species_data:
            name1, name2 = species_data
            types_text = "".join(str(x.emoji) for x in self.types)
            c_embed.add_field(name=f"{name1}\n{types_text}", value=name2)

        for ability in sorted(self.abilities, key=lambda x: x.name):
            c_embed.add_field(
                name=f"Ability: {ability.name}",
                value=f"> {ability.description}",
                inline=False,
            )

        if tropes := self.tropes:
            c_embed.add_field(
                name="Tropes",
                value="\n".join(
                    f"* {x.name.replace('_', ' ')}: {x.value}" for x in sorted(tropes, key=lambda x: x.name)
                ),
                inline=False,
            )

        if (sp_ability := self.sp_ability) and sp_ability.valid:
            sp_embed = Embed(
                title=name if (name := sp_ability.name[:100]) else f"{self.name[:92]}'s Trait",
                description=sp_ability.description[:1024],
                timestamp=self.created_at,
            )

            if origin := sp_ability.origin[:600]:
                sp_embed.add_field(name="Origin", value=origin, inline=False)

            if pros := sp_ability.pros[:600]:
                sp_embed.add_field(name="Pros", value=pros, inline=False)

            if cons := sp_ability.cons[:600]:
                sp_embed.add_field(name="Cons", value=cons, inline=False)

            sp_embed.set_footer(text=sp_ability.kind.phrase)

            embeds.append(sp_embed)

        if hidden_power := self.hidden_power:
            color = Color(hidden_power.color)
            moveset_title = f"{hidden_power.emoji} Moveset"
        else:
            color = Color.blurple()
            moveset_title = "Moveset"

        if self.pokeball:
            embeds[-1].set_thumbnail(url=self.pokeball.url)

        embeds[0].color, embeds[-1].color = color, color
        footer_elements: list[str] = []

        if self.nature:
            footer_elements.append(f"Nature: {self.nature.name}")

        if self.species:
            footer_elements.append(self.height_text)
            footer_elements.append(self.weight_text)

        footer_text = "\n".join(footer_elements) or "No additional information."
        c_embed.set_footer(text=footer_text, icon_url=self.emoji and self.emoji.url)

        def move_parser(x: Move):
            item = self.hidden_power if x.move_id in {237, 851} and self.hidden_power else x.type
            item = TypingEnum.Typeless if TypingEnum.Typeless in self.types else item
            return f"* [{x.name}] - {item.name} ({x.category.name})".title()

        moves_text = "\n".join(map(move_parser, sorted(self.moveset, key=lambda x: x.name)))
        c_embed.add_field(name=moveset_title, value=moves_text or "> No information.", inline=False)

        if image := self.image_url:
            c_embed.set_image(url=image)
        elif isinstance(self.image, File):
            c_embed.set_image(url=f"attachment://{self.image.filename}")
        elif isinstance(self.image, str) and self.image:
            c_embed.set_image(url=self.image)
        else:
            c_embed.set_image(url="attachment://image.png")

        if self.personality:
            c_embed.add_field(name="Personality", value=self.personality[:512], inline=False)

        if self.extra:
            c_embed.add_field(name="Extra", value=self.extra[:512], inline=False)

        return embeds

    @property
    def params_header(self):
        data = {
            "Age": self.age.title,
            "Hidden Power": self.hidden_power.name if self.hidden_power else "Unknown",
            "Nature": self.nature.name if self.nature else None,
        }

        data["Measure"] = "\n".join([*self.height_text.split(" / "), *self.weight_text.split(" / ")])

        if species_data := self.species_data:
            data[species_data[0]] = species_data[1]

        return data

    async def to_docx(self, bot: CustomBot):
        doc: Document = document()

        params_header = self.params_header

        doc.add_heading(f"{self.pronoun_emoji}〛{self.name}", 0)

        table = doc.add_table(rows=1, cols=len(params_header))
        hdr_cells = table.rows[0].cells
        for text, row in zip(params_header, hdr_cells):
            row.text = text

        row_cells = table.add_row().cells
        for index, item in enumerate(params_header.values()):
            row_cells[index].text = str(item)

        if img_file := await bot.get_file(self.image_url):
            doc.add_picture(img_file.fp, width=Inches(6))

        if self.abilities:
            doc.add_heading("Abilities", level=1)
            table = doc.add_table(rows=0, cols=2)
            for item in sorted(self.abilities, key=lambda x: x.name):
                row_cells = table.add_row().cells
                row_cells[0].text = item.name
                row_cells[1].text = item.description

        if self.moveset:
            doc.add_heading("Favorite Moves", level=1)
            items = sorted(self.moveset, key=lambda x: x.name)
            table = doc.add_table(rows=1, cols=2)
            hdr_cells = table.rows[0].cells
            for index, values in enumerate((items[:2], items[2:])):
                move_args = []

                for item in values:
                    item_type = item.type
                    if item.name in ["Hidden Power", "Tera Blast"] and self.hidden_power:
                        item_type = self.hidden_power
                    item_type = TypingEnum.Typeless if TypingEnum.Typeless in self.types else item_type
                    move_args.append(f"• {item.name} - {item.category.name} - {item_type.name}".title())

                hdr_cells[index].text = "\n".join(move_args)

        if self.backstory or self.extra or self.personality:
            doc.add_page_break()

        if self.backstory:
            doc.add_heading("Bio", 1)
            doc.add_paragraph(self.backstory).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if self.personality:
            doc.add_heading("Personality", 1)
            doc.add_paragraph(self.personality).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if self.extra:
            doc.add_heading("Extra Information", 1)
            doc.add_paragraph(self.extra).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if sp_ability := self.sp_ability:
            doc.add_page_break()
            doc.add_heading(f"Unique Trait: {sp_ability.name}", 1)
            doc.add_heading(sp_ability.kind.phrase, 2)
            if sp_ability.description:
                doc.add_paragraph(sp_ability.description).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if origin := sp_ability.origin:
                doc.add_heading("How was it obtained?", 2)
                doc.add_paragraph(origin).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if pros := sp_ability.pros:
                doc.add_heading("How does it make the character's life easier?", 2)
                doc.add_paragraph(pros).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if cons := sp_ability.cons:
                doc.add_heading("How does it make the character's life harder?", 2)
                doc.add_paragraph(cons).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if (
            isinstance(self.species, CustomSpecies)
            and self.species.can_change_movepool()
            and (movepool := self.species.movepool)
        ):

            doc.add_page_break()
            doc.add_heading("Movepool", level=1)
            if movepool.level:
                doc.add_heading("Level Moves", level=2)
                for k, v in movepool.level.items():
                    if o := ", ".join(x.name for x in sorted(v, key=lambda x: x.name)):
                        p = doc.add_paragraph(style="List Bullet")
                        p.add_run(f"Level {k:02d}: ").bold = True
                        p.add_run(o)

            if tm := ", ".join(x.name for x in sorted(movepool.tm, key=lambda x: x.name)):
                doc.add_heading("TM Moves", level=2)
                doc.add_paragraph(tm).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if tutor := ", ".join(x.name for x in sorted(movepool.tutor, key=lambda x: x.name)):
                doc.add_heading("Tutor Moves", level=2)
                doc.add_paragraph(tutor).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if egg := ", ".join(x.name for x in sorted(movepool.egg, key=lambda x: x.name)):
                doc.add_heading("Egg Moves", level=2)
                doc.add_paragraph(egg).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

            if other := ", ".join(x.name for x in sorted(movepool.other, key=lambda x: x.name)):
                doc.add_heading("Other Moves", level=2)
                doc.add_paragraph(other).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        doc.save(fp := BytesIO())
        fp.seek(0)
        return File(fp=fp, filename=f"{self.id or 'Character'}.docx")

    async def to_pdf(self, bot: CustomBot) -> File:
        """To PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()

        content = [
            Table(
                [[k, v] for k, v in self.params_header.items()],
                colWidths=[100, 300],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                        ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                    ]
                ),
            )
        ]

        # Add heading
        content.append(Paragraph(f"<strong>{self.pronoun_emoji}〛{self.name}</strong>", styles["Heading1"]))

        # Add an image
        if img_file := await bot.get_file(self.image_url):
            img_stream = BytesIO(img_file.fp.read())
            content.append(Image(img_stream))

        # Add abilities and moveset sections
        if self.abilities:
            content.append(Paragraph("Abilities", styles["Heading2"]))
            for item in self.abilities:
                content.append(Paragraph(f"<strong>{item.name}</strong> - {item.description}", styles["Normal"]))

        if self.moveset:
            content.append(Paragraph("Favorite Moves", styles["Heading2"]))
            for item in self.moveset:
                content.append(Paragraph(f"• {item.name} - {item.category.name} - {item.type.name}", styles["Normal"]))

        if self.backstory or self.extra or self.personality:
            content.append(PageBreak())

        if self.backstory:
            content.extend(
                (
                    Spacer(1, 12),
                    Paragraph("Bio", styles["Heading2"]),
                    Paragraph(self.backstory, styles["Normal"]),
                )
            )

        if self.personality:
            content.extend(
                (
                    Spacer(1, 12),
                    Paragraph("Personality", styles["Heading2"]),
                    Paragraph(self.personality, styles["Normal"]),
                )
            )

        if self.extra:
            content.extend(
                (
                    Spacer(1, 12),
                    Paragraph("Extra Information", styles["Heading2"]),
                    Paragraph(self.extra, styles["Normal"]),
                )
            )

        if sp_ability := self.sp_ability:
            content.append(PageBreak())
            content.append(Paragraph(f"Unique Trait: {sp_ability.name}", styles["Heading1"]))
            content.append(Paragraph(sp_ability.kind.phrase, styles["Heading2"]))

            if sp_ability.description:
                content.append(Paragraph(sp_ability.description, styles["Normal"]))

            if sp_ability.pros:
                content.append(Paragraph("How does it make the character's life easier?", styles["Heading3"]))
                content.append(Paragraph(sp_ability.pros, styles["Normal"]))

            if sp_ability.cons:
                content.append(Paragraph("How does it make the character's life harder?", styles["Heading3"]))
                content.append(Paragraph(sp_ability.cons, styles["Normal"]))

            if sp_ability.origin:
                content.append(Paragraph("How was it obtained?", styles["Heading3"]))
                content.append(Paragraph(sp_ability.origin, styles["Normal"]))

        if isinstance(
            self.species,
            (
                Variant,
                CustomParadox,
                CustomUltraBeast,
                Fakemon,
            ),
        ) and (movepool := self.species.movepool):
            content.extend(
                (
                    PageBreak(),
                    Paragraph("Movepool", styles["Heading1"]),
                )
            )

            if movepool.level:
                content.append(Paragraph("Level Moves", styles["Heading2"]))
                content.append(
                    Table(
                        [
                            [f"{k:03d}", ", ".join(x.name for x in sorted(v, key=lambda x: x.name))]
                            for k, v in movepool.level.items()
                            if v
                        ],
                        colWidths=[50, 350],
                        style=TableStyle(
                            [
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                            ]
                        ),
                    )
                )

            if movepool.tm:
                content.extend(
                    (
                        Paragraph("TM Moves", styles["Heading2"]),
                        Paragraph(
                            ", ".join(x.name for x in sorted(movepool.tm, key=lambda x: x.name)),
                            styles["Normal"],
                        ),
                    )
                )

            if movepool.tutor:
                content.extend(
                    (
                        Paragraph("Tutor Moves", styles["Heading2"]),
                        Paragraph(
                            ", ".join(x.name for x in sorted(movepool.tutor, key=lambda x: x.name)),
                            styles["Normal"],
                        ),
                    )
                )

            if movepool.egg:
                content.extend(
                    (
                        Paragraph("Egg Moves", styles["Heading2"]),
                        Paragraph(
                            ", ".join(x.name for x in sorted(movepool.egg, key=lambda x: x.name)),
                            styles["Normal"],
                        ),
                    )
                )

            if movepool.event:
                content.extend(
                    (
                        Paragraph("Event Moves", styles["Heading2"]),
                        Paragraph(
                            ", ".join(x.name for x in sorted(movepool.event, key=lambda x: x.name)),
                            styles["Normal"],
                        ),
                    )
                )

            if movepool.other:
                content.extend(
                    (
                        Paragraph("Other Moves", styles["Heading2"]),
                        Paragraph(
                            ", ".join(x.name for x in sorted(movepool.other, key=lambda x: x.name)),
                            styles["Normal"],
                        ),
                    )
                )

        # Build the PDF document
        doc.build(content)
        buffer.seek(0)

        return File(fp=buffer, filename=f"{self.id or 'Character'}.pdf")

    def generated_image(self, background: Optional[str] = None) -> Optional[str]:
        """Generated Image

        Returns
        -------
        str
            URL
        """
        if isinstance(image := self.image, int):
            return self.image_url
        if image := image or self.default_image:
            if not background:
                background = "background_Y8q8PAtEV.png"
            kit = ImageKit(base=background, width=900, height=450, format="png")
            kit.add_image(image=image, height=450)
            for index, item in enumerate(self.types):
                kit.add_image(image=item.icon, width=200, height=44, x=-10, y=44 * index + 10)
            return kit.url

    @classmethod
    def collage(cls, ocs: Iterable[Character], background: Optional[str] = None, font: bool = True):
        items: list[Character | None] = list(ocs)[:6]

        if background and (amount := 6 - len(items)):
            items.extend([None] * amount)

        kit = ImageKit(base=background or "OC_list_9a1DZPDet.png", width=1500, height=1000, format="png")
        for index, oc in enumerate(items):
            x = 500 * (index % 3) + 25
            y = 500 * (index // 3) + 25
            if oc is None:
                kit.add_image(image="placeholder_uSDglnt-E.png", height=450, width=450, x=x, y=y)
            elif isinstance(oc, Character):
                kit.add_image(image=oc.image_url, height=450, width=450, x=x, y=y)
                for idx, item in enumerate(oc.types):
                    kit.add_image(image=item.icon, width=200, height=44, x=250 + x, y=y + 44 * idx)
                if font:
                    kit.add_text(
                        text=oc.name,
                        width=450,
                        x=x,
                        y=y + 400,
                        background=0xFFFFFF,
                        background_transparency=70,
                        font=Fonts.Whitney_Black,
                        font_size=36,
                        padding=15,
                    )
        return kit.url

    @classmethod
    def rack(cls, ocs: Iterable[Character], font: bool = True):
        items: list[Character | None] = list(ocs)[:4]
        kit = ImageKit(base="Rack_FgmVfIYZs.png", width=2000, height=500, format="png")
        for index, oc in enumerate(items):
            x, y = 500 * index + 25, 25
            if oc is None:
                kit.add_image(image="placeholder_uSDglnt-E.png", height=450, width=450, x=x, y=y)
            elif isinstance(oc, Character):
                kit.add_image(image=oc.image_url, height=450, width=450, x=x, y=y)
                for idx, item in enumerate(oc.types):
                    kit.add_image(image=item.icon, width=200, height=44, x=250 + x, y=y + 44 * idx)
                if font:
                    kit.add_text(
                        text=oc.name,
                        width=450,
                        x=x,
                        y=y + 400,
                        background=0xFFFFFF,
                        background_transparency=70,
                        font=Fonts.Whitney_Black,
                        font_size=36,
                        padding=15,
                    )
        return kit.url

    @classmethod
    def rack2(cls, ocs: Iterable[Character], font: bool = True):
        items: list[Character | None] = list(ocs)[:4]

        kit = ImageKit(base="Rack2_tAEzwkZUI.png", width=1000, height=1000, format="png")
        for index, oc in enumerate(items):
            x = 500 * (index % 2) + 25
            y = 500 * (index // 2) + 25
            if oc is None:
                kit.add_image(image="placeholder_uSDglnt-E.png", height=450, width=450, x=x, y=y)
            elif isinstance(oc, Character):
                kit.add_image(image=oc.image_url, height=450, width=450, x=x, y=y)
                for idx, item in enumerate(oc.types):
                    kit.add_image(image=item.icon, width=200, height=44, x=250 + x, y=y + 44 * idx)
                if font:
                    kit.add_text(
                        text=oc.name,
                        width=450,
                        x=x,
                        y=y + 400,
                        background=0xFFFFFF,
                        background_transparency=70,
                        font=Fonts.Whitney_Black,
                        font_size=36,
                        padding=15,
                    )
        return kit.url

    def copy(self):
        sp_ability = self.sp_ability.copy() if self.sp_ability else None
        return Character(
            species=self.species,
            id=self.id,
            author=self.author,
            thread=self.thread,
            server=self.server,
            name=self.name,
            age=self.age,
            pronoun=self.pronoun,
            backstory=self.backstory,
            personality=self.personality,
            extra=self.extra,
            abilities=self.abilities.copy(),
            moveset=self.moveset.copy(),
            sp_ability=sp_ability,
            url=self.url,
            image=self.image,
            location=self.location,
            hidden_power=self.hidden_power,
            size=self.size,
            weight=self.weight,
            last_used=self.last_used,
            nature=self.nature,
            tropes=self.tropes,
            size_category=self.size_category,
            emoji=self.emoji,
            pokeball=self.pokeball,
        )

    def __repr__(self) -> str:
        species = self.species.name if self.species else None
        return f"{self.age.title} - {species}"

    @classmethod
    def process(cls, **kwargs) -> Character:
        """Function used for processing a dict, to a character
        Returns
        -------
        Character
            Character given the paraneters
        """
        data: dict[str, Any] = {k.lower(): v for k, v in kwargs.items()}

        base = common_pop_get(
            data,
            "base",
            "preevo",
            "pre evo",
            "pre_evo",
        )

        if mega := data.pop("mega", ""):
            species = CustomMega.single_deduce(mega.removeprefix("Mega "))
            data["species"] = species
        elif (paradox := data.pop("paradox", "")) and base:
            species = CustomParadox.single_deduce(base)
            species.name = paradox
            data["species"] = species
        elif (ub := common_pop_get(data, "ultrabeast", "ub")) and base:
            species = CustomUltraBeast.single_deduce(base)
            species.name = ub
            data["species"] = species
        elif fakemon := data.pop("fakemon", ""):
            name: str = fakemon.title()
            if species := Fakemon.single_deduce(base):
                species.name = name
            else:
                species = Fakemon(name=name)

            data["species"] = species
        elif variant := data.pop("variant", ""):
            if species := Variant.single_deduce(base):
                species.name = variant
            else:
                for item in variant.split(" "):
                    if species := Variant.single_deduce(item):
                        species.name = variant.title()
                        break

            data["species"] = species
        elif (species := Fusion.single_deduce(",".join(data.pop("fusion", [])))) or (
            (aux := common_pop_get(data, "species", "pokemon")) and (species := Species.any_deduce(aux))
        ):
            data["species"] = species

        if isinstance(age := common_pop_get(data, "age", "years"), str):
            data["age"] = AgeGroup.parse(int_check(age))

        if pronoun_info := common_pop_get(data, "pronoun", "gender", "pronouns"):
            data["pronoun"] = Pronoun.deduce_many(pronoun_info)

        data.pop("stats", {})

        if move_info := common_pop_get(data, "moveset", "moves"):
            if isinstance(move_info, str):
                move_info = move_info.split(",")
            move_info = [x for x in move_info if x.lower() != "move"]
            if moveset := Move.deduce_many(*move_info):
                data["moveset"] = moveset

        type_info = common_pop_get(data, "types", "type")
        ability_info = common_pop_get(data, "abilities", "ability")
        movepool = Movepool.from_dict(**data.pop("movepool", dict(event=data.get("moveset", set()))))
        data["sp_ability"] = common_pop_get(data, "spability", "sp_ability", "unique_trait")

        if not species:
            data.pop("moveset", None)
        else:
            if type_info and (types := TypingEnum.deduce_many(*type_info)):
                if isinstance(species, (Fusion, CustomSpecies)):
                    species.types = types
                elif species.types != types:
                    types_txt = "/".join(i.name for i in types)
                    species = Variant(base=species, name=f"{types_txt}-Typed {species.name}")
                    species.types = types

            if ability_info:
                if isinstance(ability_info, str):
                    ability_info = [ability_info]
                if abilities := Ability.deduce_many(*ability_info):
                    data["abilities"] = abilities

                if isinstance(species, (Fusion, CustomSpecies)):
                    species.abilities = abilities
                elif abilities_txt := "/".join(x.name for x in abilities if x not in species.abilities):
                    species = Variant(base=species, name=f"{abilities_txt}-Granted {species.name}")
                    species.abilities = abilities
                    data["species"] = species

            if isinstance(species, CustomSpecies) and (species.base is None or species.base.movepool != movepool):
                species.movepool = movepool

            data = {k: v for k, v in data.items() if v}
            data["species"] = species

        return cls.from_dict(data)


class CharacterTransform(Transformer):
    async def transform(self, interaction: Interaction[CustomBot], value: str, /):
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        if not (member := interaction.namespace.member):
            member = interaction.client.supporting.get(interaction.user, interaction.user)
        ocs = {
            oc.id: oc
            async for x in db.find({"author": member.id, "server": interaction.guild_id})
            if (oc := Character.from_mongo_dict(x))
        }
        if value.isdigit() and (oc := ocs.get(int(value))):
            return oc
        if options := process.extractOne(
            value,
            choices=ocs.values(),
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=60,
        ):
            return options[0]

    async def autocomplete(self, interaction: Interaction[CustomBot], value: str, /) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        if not (member := interaction.namespace.member):
            member = interaction.client.supporting.get(interaction.user, interaction.user)
        ocs = {
            oc.id: oc
            async for x in db.find({"author": member.id, "server": interaction.guild_id})
            if (oc := Character.from_mongo_dict(x))
        }
        if value.isdigit() and (oc := ocs.get(int(value))):
            options = [oc]
        elif options := process.extract(
            value,
            choices=ocs.values(),
            limit=25,
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=60,
        ):
            options = [x[0] for x in options]
        elif not value:
            options = list(ocs.values())[:25]
        return [Choice(name=x.name, value=str(x.id)) for x in options]


CharacterArg = Transform[Character, CharacterTransform]
