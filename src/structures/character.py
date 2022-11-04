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

from dataclasses import asdict, dataclass, field
from enum import Enum
from random import sample
from re import match as re_match
from typing import Any, Iterable, Optional, Type

from asyncpg import Connection
from discord import Color, Embed, File, Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.utils import snowflake_time, utcnow
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.structures.ability import Ability, SpAbility
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import (
    Chimera,
    CustomMega,
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Pokemon,
    Species,
    UltraBeast,
    Variant,
)
from src.utils.functions import common_pop_get, fix, int_check
from src.utils.imagekit import Fonts, ImageKit

__all__ = ("Character", "CharacterArg", "Kind")


class AgeGroup(Enum):
    Unknown = None, None
    Child = None, 14
    Adolescent = 14, 25
    Adult = 25, 50
    Elderly = 50, 100
    Ancient = 100, None

    @property
    def key(self) -> tuple[int, int]:
        a, b = self.value
        return a or 0, b or 0

    @classmethod
    def parse(cls, item: AgeGroup | Optional[int] | str):
        if isinstance(item, AgeGroup):
            return item
        if isinstance(item, int) or item is None:
            return cls.from_number(item)
        if isinstance(item, str) and (
            foo := process.extractOne(
                item,
                cls,
                processor=lambda x: getattr(x, "name", x),
                score_cutoff=85,
            )
        ):
            return foo[0]
        return cls.Unknown

    @classmethod
    def from_number(cls, item: Optional[int]):
        data = cls.Unknown
        if item:
            for x in cls:
                a, b = x.value
                a = a or 0
                b = b or item

                if a <= item < b:
                    data = x
        return data

    @property
    def description(self):
        match self.value:
            case (None, None):
                return "The age is Unknown."
            case (a, None):
                return "Has lived for long enough."
            case (None, b):
                return "Considered a child."
            case (a, b):
                return f"{a} - {b - 1} (Rough equivalent in human years)"


class Kind(Enum):
    Common = Pokemon
    Legendary = Legendary
    Mythical = Mythical
    UltraBeast = UltraBeast
    Fakemon = Fakemon
    Variant = Variant
    Mega = Mega
    Fusion = Fusion
    CustomMega = CustomMega
    Chimera = Chimera

    @property
    def to_db(self) -> str:
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
            case self.Mega:
                return "MEGA"
            case self.Fusion:
                return "FUSION"
            case self.CustomMega:
                return "CUSTOM MEGA"
            case self.Chimera:
                return "CHIMERA"

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
            case "MEGA":
                return cls.Mega
            case "FUSION":
                return cls.Fusion
            case "CUSTOMMEGA":
                return cls.CustomMega
            case "CHIMERA":
                return cls.Chimera

    def all(self) -> frozenset[Species]:
        return self.value.all()

    @classmethod
    def from_class(cls, item: Type[Species]):
        for element in cls:
            if isinstance(item, element.value):
                return element
        return cls.Fakemon


@dataclass(slots=True)
class Character:
    species: Optional[Species] = None
    id: int = 0
    author: Optional[int] = None
    thread: Optional[int] = None
    server: int = 719343092963999804
    name: str = ""
    age: AgeGroup = AgeGroup.Unknown
    pronoun: Pronoun = Pronoun.Them
    backstory: Optional[str] = None
    personality: Optional[str] = None
    extra: Optional[str] = None
    abilities: frozenset[Ability] = field(default_factory=frozenset)
    moveset: frozenset[Move] = field(default_factory=frozenset)
    sp_ability: Optional[SpAbility] = None
    url: Optional[str] = None
    image: Optional[int] = None
    location: Optional[int] = None
    hidden_power: Optional[TypingEnum] = None

    @classmethod
    def from_dict(cls, kwargs: dict[str, Any]) -> Character:
        kwargs = {k.lower(): v for k, v in kwargs.items() if k.lower() in cls.__slots__}
        return Character(**kwargs)

    def to_mongo_dict(self):
        data = asdict(self)
        data["abilities"] = [x.id for x in self.abilities]
        if isinstance(self.species, (Fakemon, Variant, CustomMega, Chimera, Fusion)):
            aux = {"types": [x.name for x in self.types]}
            if isinstance(self.species, Chimera):
                aux |= {"chimera": [x.id for x in self.species.bases]}
            elif isinstance(self.species, CustomMega):
                aux |= {"mega": self.species.id}
            elif isinstance(self.species, Fusion):
                aux |= {"fusion": [x.id for x in self.species.bases]}
            else:
                aux |= {
                    "name": self.species.name,
                    "evolves_from": self.species.evolves_from,
                    "movepool": self.species.movepool.as_dict,
                }
                if isinstance(self.species, Variant):
                    aux["base"] = self.species.id

            data["species"] = aux
        elif self.species:
            data["species"] = self.species.id

        data["age"] = self.age.name
        data["pronoun"] = self.pronoun.name
        data["moveset"] = [x.id for x in self.moveset]
        data["hidden_power"] = str(self.hidden_power) if self.hidden_power else None
        if isinstance(self.sp_ability, SpAbility):
            data["sp_ability"] = asdict(self.sp_ability)
        if isinstance(self.image, File):
            data["image"] = None
        return data

    @classmethod
    def from_mongo_dict(cls, dct: dict[str, Any]):
        dct.pop("_id", None)
        species: Optional[dict[str, Any]] = dct.get("species", None)
        if isinstance(species, dict):
            if chimera := species.pop("chimera", []):
                species["bases"] = chimera
                dct["species"] = Chimera(**species)
            elif mega := species.pop("mega", ""):
                species["base"] = mega
                dct["species"] = CustomMega(**species)
            elif "base" in species:
                dct["species"] = Variant(**species)
            elif "fusion" in species:
                fusion = Fusion(*species.get("fusion"))
                if not fusion.types:
                    fusion.types = TypingEnum.deduce_many(*species.get("types", []))
                dct["species"] = fusion
            else:
                dct["species"] = Fakemon(**species)

        return Character(**dct)

    def __post_init__(self):
        self.image_url = self.image
        if isinstance(self.species, str):
            self.species = Species.from_ID(self.species)
        if not self.server:
            self.server = 719343092963999804
        if not self.can_have_special_abilities:
            self.sp_ability = None
        elif isinstance(self.sp_ability, dict):
            self.sp_ability = SpAbility(**self.sp_ability)
        if isinstance(self.abilities, str):
            self.abilities = [self.abilities]
        self.abilities = Ability.deduce_many(*self.abilities)
        if isinstance(self.moveset, str):
            self.moveset = [self.moveset]
        self.moveset = Move.deduce_many(*self.moveset)
        if isinstance(self.pronoun, str):
            self.pronoun = Pronoun.deduce(self.pronoun)
        self.age = AgeGroup.parse(self.age)
        if not self.can_have_special_abilities:
            self.sp_ability = None
        if self.hidden_power:
            self.hidden_power = TypingEnum.deduce(self.hidden_power)

    def __eq__(self, other: Character):
        return isinstance(other, Character) and self.id == other.id

    def __ne__(self, other: Character) -> bool:
        return isinstance(other, Character) and other.id != self.id

    def __hash__(self) -> int:
        return self.id >> 22

    @property
    def types(self) -> frozenset[TypingEnum]:
        if self.species:
            return frozenset(self.species.types)
        return frozenset()

    @property
    def possible_types(self) -> frozenset[frozenset[TypingEnum]]:
        if self.species:
            return self.species.possible_types
        return frozenset()

    @property
    def kind(self):
        return Kind.from_class(self.species)

    @property
    def image_url(self):
        if isinstance(self.image, int) and self.thread:
            return f"https://media.discordapp.net/attachments/{self.thread}/{self.image}/image.png"

    @image_url.setter
    def image_url(self, url: str):
        if isinstance(url, str) and self.thread:

            if find := re_match(
                rf"https:\/\/\w+\.discordapp\.\w+\/attachments\/{self.thread}\/(\d+)\/image\.png",
                string=url,
            ):
                url = int(find.group(1))

        self.image = url

    @image_url.deleter
    def image_url(self):
        self.image = None

    @property
    def created_at(self):
        return snowflake_time(self.id) if self.id else utcnow()

    @property
    def document_url(self):
        if self.url:
            return f"https://docs.google.com/document/d/{self.url}/edit?usp=sharing"

    @document_url.setter
    def document_url(self, url: str):
        url = url.removeprefix("https://docs.google.com/document/d/")
        url = url.removesuffix("/edit?usp=sharing")
        self.url = url

    @document_url.deleter
    def document_url(self):
        self.url = None

    @property
    def usable_abilities(self) -> frozenset[Ability]:
        if self.any_ability_at_first:
            return Ability.all()
        return self.species.abilities

    @property
    def randomize_abilities(self) -> frozenset[Ability]:
        if abilities := list(self.usable_abilities):
            amount = min(self.max_amount_abilities, len(abilities))
            items = sample(abilities, k=amount)
            return frozenset(items)
        return frozenset(self.abilities)

    @property
    def randomize_moveset(self) -> frozenset[Move]:
        if movepool := self.movepool:
            moves = list(movepool())
            amount = min(6, len(moves))
            return frozenset(sample(moves, k=amount))
        return self.moveset

    @property
    def evolves_from(self) -> Optional[Species]:
        if self.species:
            return self.species.species_evolves_from

    @property
    def evolves_to(self) -> list[Species]:
        if self.species:
            return self.species.species_evolves_to

    @property
    def emoji(self):
        return self.pronoun.emoji

    @property
    def movepool(self) -> Movepool:
        if self.species:
            return self.species.movepool
        return Movepool()

    @property
    def total_movepool(self) -> Movepool:
        if self.species:
            return self.species.total_movepool
        return Movepool()

    @property
    def can_have_special_abilities(self) -> bool:
        if self.species:
            return self.species.can_have_special_abilities
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return isinstance(self.species, (Variant, Fakemon))

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return isinstance(self.species, (Variant, Fakemon, CustomMega))

    @property
    def max_amount_abilities(self) -> int:
        if self.sp_ability:
            return 1
        return self.species.max_amount_abilities

    @property
    def place_mention(self) -> Optional[str]:
        if location := self.location:
            return f"<#{location}>"

    @property
    def jump_url(self) -> Optional[str]:
        """Message Link

        Returns
        -------
        Optional[str]
            URL
        """
        if self.server and self.thread and self.id:
            return f"https://discord.com/channels/{self.server}/{self.thread}/{self.id}"

    @property
    def default_image(self) -> Optional[str]:
        """This allows to obtain a default image for the character

        Returns
        -------
        Optional[str]
            Image it defaults to
        """
        if self.species and not self.species.requires_image:
            if self.pronoun == Pronoun.She:
                return self.species.female_image
            return self.species.base_image

    @property
    def embed(self) -> Embed:
        return self.embeds[0]

    @property
    def embeds(self) -> list[Embed]:
        """Discord embed out of the character

        Returns
        -------
        list[Embed]
            Embed with the character's information
        """
        c_embed = Embed(title=self.name.title(), color=Color.blurple(), timestamp=self.created_at)
        sp_embed = c_embed.copy()
        embeds = [c_embed]

        if url := self.document_url:
            c_embed.url = url
        if backstory := self.backstory:
            c_embed.description = backstory[:2000]
        c_embed.add_field(name="Pronoun", value=self.pronoun.name)
        c_embed.add_field(name="Age", value=self.age.name)

        if self.species and self.species.name:
            match self.kind:
                case Kind.Fusion | Kind.Chimera:
                    names = self.species.name.split("/")
                    if name := "\n".join(f"> **•** {name}" for name in names).title():
                        c_embed.add_field(name=f"{self.kind.name} Species", value=name[:1024])
                case Kind.Fakemon:
                    if evolves_from := self.evolves_from:
                        name = f"Fakemon Evolution - {evolves_from.name}"
                    else:
                        name = "Fakemon Species"
                    c_embed.add_field(name=name, value=self.species.name)
                case Kind.CustomMega | Kind.Variant:
                    c_embed.add_field(name=f"{self.kind.name} Species", value=self.species.name)
                case _:
                    c_embed.add_field(name="Species", value=self.species.name)

        for index, ability in enumerate(sorted(self.abilities, key=lambda x: x.name), start=1):
            c_embed.add_field(
                name=f"Ability {index} - {ability.name}",
                value=f"> {ability.description}",
                inline=False,
            )

        if (sp_ability := self.sp_ability) and sp_ability.valid:

            if name := sp_ability.name[:100]:
                sp_embed.title = name

            if value := sp_ability.description[:1024]:
                sp_embed.description = value

            if origin := sp_ability.origin[:600]:
                sp_embed.add_field(name="Sp.Ability - Origin", value=origin, inline=False)

            if pros := sp_ability.pros[:600]:
                sp_embed.add_field(name="Sp.Ability - Pros", value=pros, inline=False)

            if cons := sp_ability.cons[:600]:
                sp_embed.add_field(name="Sp.Ability - Cons", value=cons, inline=False)

            embeds.append(sp_embed)

        moves_text = "\n".join(f"> {item!r}" for item in sorted(self.moveset, key=lambda x: x.name))

        if hidden_power := self.hidden_power:
            embeds[0].color, embeds[-1].color = hidden_power.color, hidden_power.color
            moves_text = moves_text.replace("[Hidden Power] - Normal", f"[Hidden Power] - {hidden_power.name}")
            c_embed.set_footer(
                text=f"Hidden Power: {hidden_power.name}",
                icon_url=hidden_power.emoji.url,
            )

        if moves_text:
            c_embed.add_field(name="Moveset", value=moves_text, inline=False)

        if image := self.image_url:
            c_embed.set_image(url=image)
        elif isinstance(self.image, File):
            c_embed.set_image(url=f"attachment://{self.image.filename}")
        elif isinstance(self.image, str):
            c_embed.set_image(url=self.image)

        if self.personality:
            c_embed.add_field(name="Personality", value=self.personality[:200], inline=False)

        if self.extra:
            c_embed.add_field(name="Extra Information", value=self.extra[:256], inline=False)

        return embeds

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
                        width=330,
                        x=x,
                        y=y + 400,
                        background=0xFFFFFF,
                        background_transparency=70,
                        font=Fonts.Whitney_Black,
                        font_size=36,
                    )
                if oc.pronoun.image:
                    kit.add_image(image=oc.pronoun.image, height=120, width=120, x=x + 325, y=y + 325)
        return kit.url

    async def update(self, connection: Connection, idx: int = None, thread_id: int = None) -> None:
        """Method for updating data in database

        Parameters
        ----------
        connection : Connection
            asyncpg connection object
        idx : int, optional
            Index if it will be modified, by default None
        thread_id : int, Optional
            Thread to move if needed
        """
        new_index = idx or self.id
        if self.id != new_index:
            await connection.execute(
                """--sql
                UPDATE CHARACTER
                SET ID = $2, THREAD = $4
                WHERE ID = $1 AND SERVER = $3;
                """,
                self.id,
                new_index,
                self.server,
                thread_id or self.thread,
            )
        self.id = new_index
        await self.upsert(connection)

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """This should return a list of Characters

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Yields
        -------
        Character
        """
        async for item in connection.cursor(
            """--sql
            SELECT
                C.*,
                TO_JSONB(F.*) AS FAKEMON,
                TO_JSONB(S.*) AS SP_ABILITY,
                TO_JSON(M.*) AS MOVEPOOL
            FROM CHARACTER C
            LEFT JOIN FAKEMON F ON C.ID = F.ID
            LEFT JOIN SPECIAL_ABILITIES S ON C.ID = S.ID
            LEFT JOIN MOVEPOOL M ON C.ID = M.ID;
            """
        ):
            data = dict(item)
            kind = Kind.associated(data.pop("kind", "COMMON"))

            mon_type = TypingEnum.deduce_many(*data.pop("types"))

            if kind == Kind.Chimera:
                key = data.pop("species", "")
                species = Chimera(key.split("_"))
            else:
                species = Species.from_ID(data.pop("species", None))

            if fakemon_data := Fakemon.from_record(data.pop("fakemon")):
                if kind == Kind.Variant:
                    if not species:
                        print(fakemon_data)
                        continue
                    species = Variant(base=species, name=fakemon_data.name)
                elif kind == Kind.Fakemon:
                    species = fakemon_data

            if mon_type and isinstance(species, (Fakemon, Fusion, Variant, CustomMega, Chimera)):
                species.types = mon_type

            movepool = data.pop("movepool")

            if species:
                if kind == Kind.CustomMega:
                    species = CustomMega(species)
                elif movepool := Movepool.from_record(movepool):
                    if species.movepool != movepool and kind in [Kind.Variant, Kind.Fakemon]:
                        species.movepool = movepool
                    else:
                        await connection.execute("DELETE FROM MOVEPOOL WHERE ID = $1", data["id"])
                data["species"] = species
            else:
                await connection.execute("DELETE FROM FAKEMON WHERE ID = $1", data["id"])

            sp_data = data.pop("sp_ability", {})
            mon = Character(**data)
            if sp_data:
                sp_data.pop("id", None)
                sp_ability = SpAbility(**sp_data)
                if mon.can_have_special_abilities:
                    mon.sp_ability = sp_ability
                else:
                    sp_ability.clear()
                    await sp_ability.upsert(connection, mon.id)
            yield mon

    async def upsert(self, connection: Connection) -> None:
        """This is the standard upsert method which must be added
        in all character classes.

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await connection.execute(
            """--sql
            INSERT INTO CHARACTER(
                ID, NAME, AGE, PRONOUN, BACKSTORY, EXTRA,
                KIND, AUTHOR, SERVER, URL, IMAGE, LOCATION,
                THREAD, MOVESET, TYPES, ABILITIES, SPECIES, HIDDEN_POWER
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            )
            ON CONFLICT (ID) DO UPDATE
            SET
                ID = $1, NAME = $2, AGE = $3, PRONOUN = $4, BACKSTORY = $5,
                EXTRA = $6, KIND = $7, AUTHOR = $8, SERVER = $9, URL = $10,
                IMAGE = $11, LOCATION = $12, THREAD = $13, MOVESET = $14,
                TYPES = $15, ABILITIES = $16, SPECIES = $17, HIDDEN_POWER = $18;
            """,
            self.id,
            self.name,
            self.age.name,
            self.pronoun.name,
            self.backstory,
            self.extra,
            self.kind.to_db,
            self.author,
            self.server,
            self.url,
            self.image,
            self.location,
            self.thread,
            [x.id for x in self.moveset],
            [str(x) for x in self.types],
            [x.id for x in self.abilities],
            None if isinstance(self.species.id, int) else self.species.id,
            str(self.hidden_power) if self.hidden_power else None,
        )
        if (sp_ability := self.sp_ability) is None:
            sp_ability = SpAbility()
        await sp_ability.upsert(connection, idx=self.id)
        movepool = self.movepool.db_dict
        match self.kind:
            case Kind.Fakemon:
                await connection.execute(
                    """--sql
                    INSERT INTO FAKEMON(ID, NAME, EVOLVES_FROM)
                    VALUES ($1, $2, $3) ON CONFLICT (ID) DO UPDATE SET
                    NAME = $2, EVOLVES_FROM = $3;
                    """,
                    self.id,
                    self.species.name,
                    getattr(self.evolves_from, "id", None),
                )
                await connection.execute(
                    """--sql
                    INSERT INTO MOVEPOOL(ID, LEVEL, TM, EVENT, TUTOR, EGG, LEVELUP, OTHER)
                    VALUES ($1, $2::JSONB, $3, $4, $5, $6, $7, $8) ON CONFLICT (ID) DO UPDATE SET
                    LEVEL = $2::JSONB, TM = $3, EVENT = $4, TUTOR = $5, EGG = $6, LEVELUP = $7, OTHER = $8;
                    """,
                    self.id,
                    movepool["level"],
                    movepool["tm"],
                    movepool["event"],
                    movepool["tutor"],
                    movepool["egg"],
                    movepool["levelup"],
                    movepool["other"],
                )
            case Kind.Variant:
                if self.movepool == self.species.base.movepool:
                    await connection.execute("DELETE FROM MOVEPOOL WHERE ID = $1", self.id)
                else:
                    await connection.execute(
                        """--sql
                        INSERT INTO MOVEPOOL(ID, LEVEL, TM, EVENT, TUTOR, EGG, LEVELUP, OTHER)
                        VALUES ($1, $2::JSONB, $3, $4, $5, $6, $7, $8) ON CONFLICT (ID) DO UPDATE SET
                        LEVEL = $2::JSONB, TM = $3, EVENT = $4, TUTOR = $5, EGG = $6, LEVELUP = $7, OTHER = $8;
                        """,
                        self.id,
                        movepool["level"],
                        movepool["tm"],
                        movepool["event"],
                        movepool["tutor"],
                        movepool["egg"],
                        movepool["levelup"],
                        movepool["other"],
                    )
                await connection.execute(
                    """--sql
                    INSERT INTO FAKEMON(ID, NAME) VALUES ($1, $2)
                    ON CONFLICT (ID) DO UPDATE SET NAME = $2;
                    """,
                    self.id,
                    self.species.name,
                )

    async def delete(self, connection: Connection) -> None:
        """Delete in database

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        """
        if oc_id := self.id:
            await connection.execute(
                """--sql
                DELETE FROM CHARACTER
                WHERE ID = $1 AND SERVER = $2;
                """,
                oc_id,
                self.server,
            )

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
        )

    def __repr__(self) -> str:
        types = "/".join(i.name for i in self.types)
        name = self.kind.name if self.kind else "Error"
        species = self.species.name if self.species else "None"
        return f"{name}: {species}, Age: {self.age.name}, Types: {types}"

    @classmethod
    def process(cls, **kwargs) -> Character:
        """Function used for processing a dict, to a character
        Returns
        -------
        Character
            Character given the paraneters
        """
        data: dict[str, Any] = {k.lower(): v for k, v in kwargs.items()}

        if fakemon := data.pop("fakemon", ""):

            name: str = fakemon.title()

            if name.startswith("Mega "):
                species = CustomMega.deduce(name.removeprefix("Mega "))
            elif species := Fakemon.deduce(
                common_pop_get(
                    data,
                    "base",
                    "preevo",
                    "pre evo",
                    "pre_evo",
                )
            ):
                species.name = name
            else:
                species = Fakemon(name=name)

            data["species"] = species
        elif variant := data.pop("variant", ""):
            if species := Variant.deduce(common_pop_get(data, "base", "preevo", "pre evo", "pre_evo")):
                name = variant.title().replace(species.name, "").strip()
                species.name = f"{name} {species.name}".title()
            else:
                for item in variant.split(" "):
                    if species := Variant.deduce(item):
                        species.name = variant.title()
                        break

            data["species"] = species
        elif (
            (species := Fusion.deduce(",".join(data.pop("fusion", []))))
            or (species := Chimera.deduce(",".join(data.pop("chimera", []))))
            or (
                (aux := common_pop_get(data, "species", "pokemon"))
                and (species := Species.any_deduce(aux, chimera=True))
            )
        ):
            data["species"] = species

        if isinstance(age := common_pop_get(data, "age", "years"), str):
            if age.isdigit():
                age = int_check(age, 13, 100)
            data["age"] = AgeGroup.parse(age)

        if pronoun_info := common_pop_get(data, "pronoun", "gender", "pronouns"):
            data["pronoun"] = Pronoun.deduce(pronoun_info)

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
        data["sp_ability"] = common_pop_get(data, "spability", "sp_ability")

        if not species:
            data.pop("moveset", None)
        else:
            if type_info and (types := TypingEnum.deduce_many(*type_info)):
                if isinstance(species, (Fakemon, Fusion, Variant, CustomMega, Chimera)):
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

                if isinstance(species, (Fakemon, Fusion, Variant, CustomMega, Chimera)):
                    species.abilities = abilities
                elif abilities_txt := "/".join(x.name for x in abilities if x not in species.abilities):
                    species = Variant(base=species, name=f"{abilities_txt}-Granted {species.name}")
                    species.abilities = abilities
                    data["species"] = species

            if isinstance(species, (Fakemon, Variant)):
                species.movepool = movepool

            data = {k: v for k, v in data.items() if v}
            data["species"] = species

        return cls.from_dict(data)


class CharacterTransform(Transformer):
    async def transform(self, interaction: Interaction, value: str):
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        if not (member := interaction.namespace.member):
            member = interaction.user
        ocs = {oc.id: oc async for x in db.find({"author": member.id}) if (oc := Character.from_mongo_dict(x))}
        if value.isdigit() and (oc := ocs.get(int(value))):
            return oc
        elif options := process.extractOne(
            value,
            choices=ocs.values(),
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=60,
        ):
            return options[0]

    async def autocomplete(self, interaction: Interaction, value: str) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        if not (member := interaction.namespace.member):
            member = interaction.user
        ocs = {oc.id: oc async for x in db.find({"author": member.id}) if (oc := Character.from_mongo_dict(x))}
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
