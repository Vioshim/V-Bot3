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
from io import BytesIO
from json import dumps
from random import sample
from typing import Any, Optional, Type

from asyncpg import Connection
from discord import Color, Embed, File, Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.utils import snowflake_time, utcnow
from docx.document import Document
from orjson import loads
from rapidfuzz import process

from src.structures.ability import Ability, SpAbility
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import (
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
from src.utils.functions import common_pop_get, int_check, multiple_pop, stats_check
from src.utils.imagekit import ImageKit
from src.utils.matches import DATA_FINDER

__all__ = (
    "Character",
    "CharacterArg",
    "oc_process",
)


class Kind(Enum):
    Common = "COMMON"
    Legendary = "LEGENDARY"
    Mythical = "MYTHICAL"
    UltraBeast = "ULTRA BEAST"
    Fakemon = "FAKEMON"
    Variant = "VARIANT"
    Mega = "MEGA"
    Fusion = "FUSION"
    CustomMega = "CUSTOM MEGA"

    @classmethod
    def from_class(cls, item: Type[Species]):
        match item:
            case x if isinstance(x, Pokemon):
                return cls.Common
            case x if isinstance(x, Legendary):
                return cls.Legendary
            case x if isinstance(x, Mythical):
                return cls.Mythical
            case x if isinstance(x, UltraBeast):
                return cls.UltraBeast
            case x if x is None or isinstance(x, Fakemon):
                return cls.Fakemon
            case x if isinstance(x, Variant):
                return cls.Variant
            case x if isinstance(x, Mega):
                return cls.Mega
            case x if isinstance(x, Fusion):
                return cls.Fusion
            case x if isinstance(x, CustomMega):
                return cls.CustomMega


@dataclass(unsafe_hash=True, slots=True)
class Character:
    species: Optional[Species] = None
    id: Optional[int] = None
    author: Optional[int] = None
    thread: Optional[int] = None
    server: int = 719343092963999804
    name: str = ""
    age: Optional[int] = None
    pronoun: Pronoun = Pronoun.Them
    backstory: Optional[str] = None
    extra: Optional[str] = None
    abilities: frozenset[Ability] = field(default_factory=frozenset)
    moveset: frozenset[Move] = field(default_factory=frozenset)
    types: frozenset[Typing] = field(default_factory=frozenset)
    sp_ability: Optional[SpAbility] = None
    url: Optional[str] = None
    image: Optional[int] = None
    location: Optional[int] = None

    def __post_init__(self):
        if not self.server:
            self.server = 719343092963999804
        if not self.can_have_special_abilities:
            self.sp_ability = None
        if isinstance(self.sp_ability, dict):
            self.sp_ability = SpAbility(**self.sp_ability)
        if isinstance(self.pronoun, str):
            self.pronoun = Pronoun[self.pronoun]
        if isinstance(self.age, int) and self.age >= 100:
            self.age = None
        if not self.types:
            self.types = self.species.types
        self.types = Typing.deduce_many(*self.types)
        self.moveset = Move.deduce_many(*self.moveset)
        self.abilities = Ability.deduce_many(*self.abilities)
        if self.kind == Kind.Fakemon:
            if evolves_from := self.evolves_from:
                self.species.movepool += evolves_from.movepool
            if not self.abilities:
                self.abilities = self.species.abilities
            elif not self.species.abilities:
                self.species.abilities = self.abilities
        if isinstance(self.species, (Pokemon, Legendary, Mythical, UltraBeast)):
            if extra_ab := ", ".join(x.name for x in self.abilities if x not in self.species.abilities):
                self.species = Variant(
                    base=self.species,
                    name=f"{extra_ab}-Granted {self.species.name}",
                )
            elif extra_mv := ", ".join(x.name for x in self.moveset if x not in self.species.total_movepool):
                self.species = Variant(
                    base=self.species,
                    name=f"{extra_mv}-Granted {self.species.name}",
                )
                self.species.movepool += Movepool(other=self.moveset)
            elif self.types != self.species.types:
                extra_tp = "/".join(x.name for x in self.types)
                self.species = Variant(
                    base=self.species,
                    name=f"{extra_tp}-Typed {self.species.name}",
                )
                self.species.types = self.types
        if isinstance(self.species, (Fakemon, Variant, CustomMega)):
            self.species.abilities = self.abilities

    def __eq__(self, other: Character):
        return self.id == other.id

    @property
    def possible_types(self):
        if isinstance(self.species, Fusion):
            return self.species.possible_types
        return frozenset({self.types})

    @property
    def kind(self):
        return Kind.from_class(self.species)

    @property
    def image_url(self):
        return f"https://cdn.discordapp.com/attachments/{self.thread}/{self.image}/image.png"

    @image_url.setter
    def image_url(self, url: str):
        self.image = int(url.split("/")[:-1][-1])

    @image_url.deleter
    def image_url(self):
        self.image = None

    @property
    def created_at(self):
        if self.id:
            return snowflake_time(self.id)
        return utcnow()

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
    def evolves_from(self) -> Optional[Type[Species]]:
        if self.species:
            return self.species.species_evolves_from

    @property
    def evolves_to(self) -> list[Type[Species]]:
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
    def jump_url(self) -> str:
        """Message Link

        Returns
        -------
        str
            URL
        """
        return f"https://discord.com/channels/{self.server}/{self.thread}/{self.id}"

    @property
    def default_image(self) -> Optional[str]:
        """This allows to obtain a default image for the character

        Returns
        -------
        Optional[str]
            Image it defaults to
        """
        if not self.species.requires_image:
            if self.pronoun == Pronoun.She:
                return self.species.female_image
            return self.species.base_image

    @property
    def embed(self) -> Embed:
        """Discord embed out of the character

        Returns
        -------
        Embed
            Embed with the character's information
        """
        c_embed = Embed(
            title=self.name.title(),
            color=Color.blurple(),
            timestamp=self.created_at,
            url=self.document_url,
        )
        if backstory := self.backstory:
            c_embed.description = backstory[:2000]
        c_embed.add_field(name="Pronoun", value=self.pronoun.name)
        c_embed.add_field(name="Age", value=self.age or "Unknown")
        if self.kind == Kind.Fusion:
            name1, name2 = self.species.name.split("/")
            c_embed.add_field(
                name="Fusion Species",
                value=f"> **•** {name1}\n> **•** {name2}".title(),
            )
        elif self.kind == Kind.Fakemon:
            if evolves_from := self.evolves_from:
                name = f"Fakemon Evolution - {evolves_from.name}"
            else:
                name = "Fakemon Species"
            c_embed.add_field(name=name, value=self.species.name)
            c_embed.add_field(
                name="HP ",
                value=("🔳" * self.species.HP).ljust(5, "⬜"),
            )
            c_embed.add_field(
                name="ATK",
                value=("🔳" * self.species.ATK).ljust(5, "⬜"),
            )
            c_embed.add_field(
                name="DEF",
                value=("🔳" * self.species.DEF).ljust(5, "⬜"),
            )
            c_embed.add_field(
                name="SPA",
                value=("🔳" * self.species.SPA).ljust(5, "⬜"),
            )
            c_embed.add_field(
                name="SPD",
                value=("🔳" * self.species.SPD).ljust(5, "⬜"),
            )
            c_embed.add_field(
                name="SPE",
                value=("🔳" * self.species.SPE).ljust(5, "⬜"),
            )
        elif self.kind in [Kind.CustomMega, Kind.Variant]:
            name = f"{self.kind.name} Species"
            c_embed.add_field(name=name, value=self.species.name)
        else:
            c_embed.add_field(name="Species", value=self.species.name)
        for index, ability in enumerate(self.abilities, start=1):
            c_embed.add_field(
                name=f"Ability {index} - {ability.name}",
                value=f"> {ability.description}",
                inline=False,
            )
        if sp_ability := self.sp_ability:
            c_embed.add_field(
                name=f'Sp.Ability - "{sp_ability.name[:100]}"',
                value=sp_ability.description[:200],
                inline=False,
            )
            c_embed.add_field(
                name="Sp.Ability - Origin",
                value=sp_ability.origin[:200],
                inline=False,
            )
            c_embed.add_field(
                name="Sp.Ability - Pros",
                value=sp_ability.pros[:200],
                inline=False,
            )
            c_embed.add_field(
                name="Sp.Ability - Cons",
                value=sp_ability.cons[:200],
                inline=False,
            )
        if moves_text := "\n".join(f"> {item!r}" for item in self.moveset):
            c_embed.add_field(name="Moveset", value=moves_text, inline=False)
        if image := self.image_url:
            c_embed.set_image(url=image)
        if entry := "/".join(i.name.title() for i in self.types):
            c_embed.set_footer(text=entry)

        if location := self.place_mention:
            c_embed.add_field(
                name="Last Location",
                value=location,
                inline=False,
            )
        extra = self.extra or ""
        if extra := extra[: min(1000, len(c_embed) - 100)]:
            c_embed.add_field(
                name="Extra Information",
                value=extra,
                inline=False,
            )

        return c_embed

    @property
    def generated_image(self) -> Optional[str]:
        """Generated Image

        Returns
        -------
        str
            URL
        """
        if isinstance(image := self.image, int):
            return self.image_url
        kit = ImageKit(base="background_Y8q8PAtEV.png", weight=900)
        kit.add_image(image=image, height=400)
        if icon := self.pronoun.image:
            kit.add_image(image=icon, x=-10, y=-10)
        for index, item in enumerate(self.types):
            kit.add_image(
                image=item.icon,
                weight=200,
                height=44,
                x=-10,
                y=44 * index + 10,
            )
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
                C.*, TO_JSON(F.*) AS FAKEMON,
                TO_JSON(V.*) AS VARIANT,
                TO_JSON(S.*) AS SP_ABILITY
            FROM CHARACTER C
            LEFT JOIN FAKEMON F ON C.ID = F.ID
            LEFT JOIN VARIANT_CHARACTER V ON C.ID = V.ID
            LEFT JOIN SPECIAL_ABILITIES S ON C.ID = S.ID;
            """
        ):
            data = dict(item)
            kind = Kind(data.pop("kind", "COMMON"))
            if species := Species.from_ID(data.pop("species", None)):
                data["species"] = species
            if variant_data := loads(data.pop("variant", None) or "{}"):
                if kind == Kind.Variant:
                    species = Species.from_ID(variant_data["species"])
                    species = Variant(base=species, name=variant_data["name"])
                    movepool_data = loads(data.pop("movepool", "{}"))
                    if movepool := Movepool.from_dict(**movepool_data):
                        species.movepool = movepool
                    data["species"] = species
                else:
                    await connection.execute(
                        "DELETE FROM VARIANT_CHARACTER WHERE ID = $1",
                        data["id"],
                    )
            if fakemon_data := loads(data.pop("fakemon", None) or "{}"):
                if kind == Kind.Fakemon:
                    evolves_from: Optional[str] = fakemon_data.pop("evolves_from", None)
                    stats = multiple_pop(fakemon_data, "hp", "atk", "def", "spa", "spd", "spe")
                    movepool_data = fakemon_data.pop("movepool", "{}")
                    movepool = Movepool.from_dict(**movepool_data)
                    stats = {k.upper(): v for k, v in stats.items()}
                    species = fakemon_data["name"]
                    data["species"] = Fakemon(
                        id=data["id"],
                        name=species,
                        movepool=movepool,
                        evolves_from=evolves_from,
                        **stats,
                    )
                else:
                    await connection.execute("DELETE FROM FAKEMON WHERE ID = $1", data["id"])
            sp_data = loads(data.pop("sp_ability", None) or "{}")
            mon = Character(**data)
            if sp_data:
                sp_ability = SpAbility.convert(sp_data)
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
                THREAD, MOVESET, TYPES, ABILITIES, SPECIES
            )
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
            )
            ON CONFLICT (ID) DO UPDATE
            SET
                ID = $1, NAME = $2, AGE = $3, PRONOUN = $4,
                BACKSTORY = $5, EXTRA = $6, KIND = $7, AUTHOR = $8,
                SERVER = $9, URL = $10, IMAGE = $11, LOCATION = $12,
                THREAD = $13, MOVESET = $14, TYPES = $15, ABILITIES = $16, SPECIES = $17;
            """,
            self.id,
            self.name,
            self.age,
            self.pronoun.name,
            self.backstory,
            self.extra,
            self.kind.value,
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
        )
        if (sp_ability := self.sp_ability) is None:
            sp_ability = SpAbility()
        await sp_ability.upsert(connection, idx=self.id)
        match self.kind:
            case Kind.Common | Kind.Mythical | Kind.Legendary:
                await connection.execute(
                    """--sql
                    INSERT INTO POKEMON_CHARACTER(ID, SPECIES)
                    VALUES ($1, $2) ON CONFLICT (ID)
                    DO UPDATE SET SPECIES = $2;
                    """,
                    self.id,
                    self.species.id,
                )
            case Kind.Fakemon:
                await connection.execute(
                    """--sql
                    INSERT INTO FAKEMON(ID, NAME, HP, ATK, DEF, SPA, SPD, SPE, EVOLVES_FROM, MOVEPOOL)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb) ON CONFLICT (ID) DO UPDATE SET
                    NAME = $2, HP = $3, ATK = $4, DEF = $5, SPA = $6, SPD = $7, SPE = $8, EVOLVES_FROM = $9, MOVEPOOL = $10::jsonb;
                    """,
                    self.id,
                    self.species.name,
                    self.species.HP,
                    self.species.ATK,
                    self.species.DEF,
                    self.species.SPA,
                    self.species.SPD,
                    self.species.SPE,
                    getattr(self.evolves_from, "id", None),
                    dumps(self.movepool.as_dict),
                )
            case Kind.Variant:
                if self.movepool == self.species.base.movepool:
                    movepool = Movepool()
                else:
                    movepool = self.movepool
                await connection.execute(
                    """--sql
                    INSERT INTO VARIANT_CHARACTER(ID, SPECIES, NAME, MOVEPOOL)
                    VALUES ($1, $2, $3, $4::JSONB) ON CONFLICT (ID)
                    DO UPDATE SET SPECIES = $2, NAME = $3, MOVEPOOL = $4::JSONB;
                    """,
                    self.id,
                    self.species.base.id,
                    self.species.name,
                    dumps(movepool.as_dict),
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

    def __repr__(self) -> str:
        types = "/".join(i.name for i in self.types)
        name = self.kind.name if self.kind else "Error"
        return f"{name}: {self.species.name}, Age: {self.age}, Types: {types}"


PLACEHOLDER_NAMES = {
    "Name": "name",
    "Age": "age",
    "Species": "species",
    "Gender": "gender",
    "Ability": "ability",
    "Pronoun": "pronoun",
    "Backstory": "backstory",
    "Additional Information": "extra",
    "F. Species": "fakemon",
    "F. Base": "base",
    "Variant": "variant",
    "Artist": "artist",
    "Website": "website",
}
PLACEHOLDER_DEFAULTS = {
    "name": "OC's Name",
    "age": "OC's Age",
    "species": "OC's Species",
    "gender": "OC's Gender",
    "ability": "OC's Ability",
    "pronoun": "OC's Preferred Pronoun",
    "backstory": "Character's backstory",
    "extra": "Character's extra information",
    "fakemon": "OC's Fakemon Species",
    "base": "OC's Base Species",
    "variant": "OC's Variant Species",
    "artist": "Artist's Name",
    "website": "Art's Website",
}
PLACEHOLDER_SP = {
    "What is it Called?": "name",
    "How is it Called?": "name",
    "How did they obtain it?": "origin",
    "What does the Special Ability do?": "description",
    "How does it make the character's life easier?": "pros",
    "How does it make the character's life harder?": "cons",
}
PLACEHOLDER_STATS = {
    "HP": "HP",
    "Attack": "ATK",
    "Defense": "DEF",
    "Special Attack": "SPA",
    "Special Defense": "SPD",
    "Speed": "SPE",
}


def oc_process(**kwargs) -> Character:
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

        if species is None:
            raise ValueError("Fakemon was not deduced by the bot.")

        data["species"] = species
    elif variant := data.pop("variant", ""):
        if species := Variant.deduce(
            common_pop_get(
                data,
                "base",
                "preevo",
                "pre evo",
                "pre_evo",
            )
        ):
            name = variant.title().replace(species.name, "").strip()
            species.name = f"{name} {species.name}".title()
        else:
            for item in variant.split(" "):
                if species := Variant.deduce(item):
                    species.name = variant.title()
                    break
            else:
                raise ValueError("Unable to determine the variant' species")

        data["species"] = species
    elif species := Fusion.deduce(data.pop("fusion", "")):
        data["species"] = species
    else:
        aux = common_pop_get(data, "species", "pokemon") or ""
        method = Species.any_deduce if "," in aux else Species.single_deduce
        if species := method(aux):
            data["species"] = species
        else:
            print(data)
            raise ValueError(
                f"Unable to determine the species, value: {species}, make sure you're using a recent template."
            )

    if species.banned:
        raise ValueError(f"The Species {species.name!r} is banned currently.")

    if pronoun_info := common_pop_get(data, "pronoun", "gender", "pronouns"):
        if pronoun := Pronoun.deduce(pronoun_info):
            data["pronoun"] = pronoun

    if age := common_pop_get(data, "age", "years"):
        data["age"] = int_check(age, 13, 99)

    if isinstance(species, Fakemon):
        if stats := data.pop("stats", {}):
            species.set_stats(**stats)

        if movepool := data.pop("movepool", dict(event=data.get("moveset", set()))):
            species.movepool = Movepool.from_dict(**movepool)

    data = {k: v for k, v in data.items() if v}
    data["species"] = species

    if isinstance(value := data.pop("spability", None), (SpAbility, dict)):
        data["sp_ability"] = value
    elif "false" not in (value := str(value).lower()) and ("true" in value or "yes" in value):
        data["sp_ability"] = SpAbility()

    return Character(**data)


def check(value: Optional[str]) -> bool:
    """A checker function to determine what is useful
    out of a character template

    Parameters
    ----------
    value : Optional[str]
        item to be inspected

    Returns
    -------
    bool
        If this item should be parsed or not
    """
    data = f"{value}".title().strip() not in ["None", "Move"]
    data &= value not in PLACEHOLDER_NAMES
    data &= value not in PLACEHOLDER_DEFAULTS.values()
    return data


def doc_convert(doc: Document) -> dict[str, Any]:
    """Google Convereter

    Parameters
    ----------
    doc : Document
        docx Document

    Returns
    -------
    dict[str, Any]
        Info
    """
    content_values: list[str] = [cell.text for table in doc.tables for row in table.rows for cell in row.cells]
    text = [x for item in content_values if (x := item.replace("\u2019", "'").strip())]
    raw_kwargs = dict(url=getattr(doc, "url", None))
    if stats := {
        PLACEHOLDER_STATS[item.strip()]: stats_check(*content_values[index + 1 :][:1])
        for index, item in enumerate(content_values)
        if item.strip() in PLACEHOLDER_STATS
        and len(content_values) > index
        and len(content_values[index + 1 :][:1]) == 1
    }:
        raw_kwargs["stats"] = stats

    for index, item in enumerate(text[:-1], start=1):
        if not check(next_value := text[index]):
            continue
        if argument := PLACEHOLDER_NAMES.get(item):
            raw_kwargs[argument] = next_value
        elif element := PLACEHOLDER_SP.get(item):
            raw_kwargs.setdefault("sp_ability", {})
            raw_kwargs["sp_ability"][element] = next_value
        elif element := DATA_FINDER.match(item):
            argument = next_value.title()
            match element.groups():
                case ["Level", y]:
                    idx = int(y)
                    raw_kwargs.setdefault("movepool", {})
                    raw_kwargs["movepool"].setdefault("level", {})
                    raw_kwargs["movepool"]["level"].setdefault(idx, set())
                    raw_kwargs["movepool"]["level"][idx].add(argument)
                case ["Move", _]:
                    raw_kwargs.setdefault("moveset", set())
                    raw_kwargs["moveset"].add(argument)
                case ["Ability", _]:
                    raw_kwargs.setdefault("abilities", set())
                    raw_kwargs["abilities"].add(next_value)
                case ["Species", _]:
                    raw_kwargs.setdefault("fusion", set())
                    raw_kwargs["fusion"].add(next_value)
                case ["Type", _]:
                    raw_kwargs.setdefault("types", set())
                    raw_kwargs["types"].add(next_value.upper())
                case [x, _]:
                    raw_kwargs.setdefault("movepool", {})
                    raw_kwargs["movepool"].setdefault(x.lower(), set())
                    raw_kwargs["movepool"][x.lower()].add(argument)

    try:
        if data := list(doc.inline_shapes):
            item = data[0]
            pic = item._inline.graphic.graphicData.pic
            blip = pic.blipFill.blip
            rid = blip.embed
            doc_part = doc.part
            image_part = doc_part.related_parts[rid]
            fp = BytesIO(image_part._blob)
            raw_kwargs["image"] = File(fp=fp, filename="image.png")
    except Exception:
        pass

    raw_kwargs.pop("artist", None)
    raw_kwargs.pop("website", None)

    return raw_kwargs


class CharacterTransform(Transformer):
    @classmethod
    async def transform(cls, interaction: Interaction, value: str):
        cog = interaction.client.get_cog("Submission")
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        return cog.ocs[value]

    @classmethod
    async def autocomplete(cls, interaction: Interaction, value: str) -> list[Choice[str]]:
        if not (member := interaction.namespace.member):
            member = interaction.user
        cog = interaction.client.get_cog("Submission")
        ocs: list[Character] = [oc for oc in cog.ocs.values() if oc.author == member.id]
        if options := process.extract(
            value,
            choices=ocs,
            limit=25,
            score_cutoff=60,
            processor=lambda x: getattr(x, "name", x),
        ):
            options = [x for x, _, _ in options]
        elif not value:
            options = ocs[:25]
        return [Choice(name=x.name, value=str(x.id)) for x in options]


CharacterArg = Transform[Character, CharacterTransform]
