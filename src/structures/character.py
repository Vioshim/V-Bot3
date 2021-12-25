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

from abc import ABCMeta, abstractmethod
from asyncio import to_thread
from dataclasses import dataclass, field
from datetime import datetime
from os import urandom
from random import sample
from typing import Any, Optional, Type, Union

from asyncpg import Connection
from discord import Color, Embed
from discord.utils import utcnow
from frozendict import frozendict
from nested_lookup import nested_lookup

from src.enums.abilities import Abilities
from src.enums.mon_types import Types
from src.enums.moves import Moves
from src.enums.pronouns import Pronoun
from src.enums.species import Species
from src.structures.ability import SpAbility
from src.structures.movepool import Movepool
from src.structures.species import (
    CustomMega,
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Pokemon,
)
from src.structures.species import Species as SpeciesBase
from src.structures.species import UltraBeast, Variant
from src.utils.doc_reader import docs_reader
from src.utils.functions import common_pop_get, int_check, multiple_pop, stats_check
from src.utils.imagekit import ImageKit
from src.utils.matches import DATA_FINDER

__all__ = (
    "ASSOCIATIONS",
    "Character",
    "FakemonCharacter",
    "LegendaryCharacter",
    "FusionCharacter",
    "MegaCharacter",
    "PokemonCharacter",
    "fetch_all",
    "oc_process",
)


@dataclass(unsafe_hash=True)
class Character(metaclass=ABCMeta):
    species: Union[Type[SpeciesBase], Species] = None
    id: Optional[int] = None
    author: Optional[int] = None
    thread: Optional[int] = None
    server: int = 719343092963999804
    name: str = ""
    age: Optional[int] = None
    pronoun: Pronoun = Pronoun.Them
    backstory: Optional[str] = None
    extra: Optional[str] = None
    abilities: frozenset[Abilities] = field(default_factory=frozenset)
    moveset: frozenset[Moves] = field(default_factory=frozenset)
    sp_ability: Optional[SpAbility] = None
    url: Optional[str] = None
    image: Optional[str] = None
    ping_button: Optional[str] = None
    delete_button: Optional[str] = None
    location: Optional[int] = None
    created_at: datetime = None

    def __post_init__(self):
        if not self.ping_button:
            self.ping_button = urandom(32).hex()
        if not self.delete_button:
            self.delete_button = urandom(32).hex()
        if not self.server:
            self.server = 719343092963999804
        if not self.created_at:
            self.created_at = utcnow()
        if isinstance(self.pronoun, str):
            self.pronoun = Pronoun[self.pronoun]
        if isinstance(self.age, int):
            if self.age >= 100:
                self.age = None
            if self.age < 13:
                self.age = 13
        if not self.can_have_special_abilities:
            self.sp_ability = None

    def __eq__(self, other: Character):
        return self.id == other.id and self.thread == other.thread

    def randomize_abilities(self):
        if abilities := list(self.species.abilities):
            amount = min(self.max_amount_abilities, len(abilities))
            items = sample(abilities, k=amount)
            self.abilities = frozenset(items)

    def randomize_moveset(self):
        if movepool := self.movepool:
            moves = list(movepool())
            amount = min(6, len(moves))
            items = sample(moves, k=amount)
            self.moveset = frozenset(items)

    @property
    def emoji(self):
        return self.pronoun.emoji

    @property
    @abstractmethod
    def kind(self) -> str:
        """Kind in database

        Returns
        -------
        str
            kind
        """

    @property
    def types(self) -> frozenset[Types]:
        return self.species.types

    @property
    def movepool(self) -> Movepool:
        return self.species.movepool

    @property
    def can_have_special_abilities(self) -> bool:
        return self.species.can_have_special_abilities

    @property
    @abstractmethod
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """

    @property
    @abstractmethod
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """

    @property
    @abstractmethod
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """

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
        )
        c_embed.url = self.url or c_embed.Empty
        if backstory := self.backstory:
            c_embed.description = backstory[:2000]
        c_embed.add_field(name="Pronoun", value=self.pronoun.name)
        c_embed.add_field(name="Age", value=self.age or "Unknown")
        c_embed.add_field(name="Species", value=self.species.name)
        for index, ability in enumerate(self.abilities, start=1):
            c_embed.add_field(
                name=f"Ability {index} - {ability.value.name}",
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
                value=sp_ability.method[:200],
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
        if image := self.image:
            c_embed.set_image(url=image)
        if entry := "/".join(i.name.title() for i in self.types):
            c_embed.set_footer(text=entry)

        if location := self.place_mention:
            c_embed.add_field(
                name="Last Location",
                value=location,
                inline=False,
            )

        if isinstance(self.extra, str):
            if extra := self.extra[:min(1000, len(c_embed) - 100)]:
                index = len(c_embed.fields) - 1
                c_embed.insert_field_at(
                    index=index,
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
        Optional[str]
            URL
        """
        if image := self.image or self.default_image:
            if image.startswith(
                    f"https://cdn.discordapp.com/attachments/{self.thread}/"):
                return image

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

    async def update(self, connection: Connection, idx: int = None) -> None:
        """Method for updating data in database

        Parameters
        ----------
        connection : Connection
            asyncpg connection object
        idx : int, optional
            Index if it will be modified, by default None
        """
        new_index = idx or self.id
        if self.id:
            await connection.execute(
                """--sql
                UPDATE CHARACTER
                SET ID = $2
                WHERE ID = $1 AND SERVER = $3;
                """,
                self.id,
                new_index,
                self.server,
            )
        self.id = new_index
        await self.upsert(connection)

    def update_from_dict(self, data: dict[str, Any]):
        """Update the class' values given a dict

        Parameters
        ----------
        data : dict[str, Any]
            information to update
        """
        for k, v in data.items():
            if hasattr(self, item := k.lower()) and item != "kind":
                setattr(self, item, v)

    @classmethod
    @abstractmethod
    async def fetch_all(cls, connection: Connection) -> list[Character]:
        """This should return a list of Characters

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[Character]
            characters
        """

    async def retrieve(self, connection: Connection):
        """Updates the character's abilities and moves with the provided in database.

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        """
        if info := await connection.fetchrow(
                """--sql
            SELECT *
            FROM CHARACTER
            WHERE ID = $1;
            """,
                self.id,
        ):
            data = dict(info)
            if pronoun := data.get("pronoun"):
                data["pronoun"] = Pronoun[pronoun]
            self.update_from_dict(data)
            abilities: list[str] = await connection.fetch(
                """--sql
                SELECT ABILITY
                FROM CHARACTER_ABILITIES
                WHERE ID = $1
                ORDER BY SLOT;
                """,
                self.id,
            )
            self.abilities = frozenset(
                {Abilities[item["ability"]]
                 for item in abilities})

            if not self.has_default_types:
                mon_types = await connection.fetch(
                    """--sql
                    SELECT TYPE
                    FROM CHARACTER_TYPES
                    WHERE character = $1
                    ORDER BY MAIN;
                    """,
                    self.id,
                )
                self.species.types = frozenset(
                    {Types[item["type"]]
                     for item in mon_types})

            if self.kind in ["FAKEMON", "CUSTOM MEGA"]:
                self.species.abilities = self.abilities
            moveset: list[str] = await connection.fetch(
                """--sql
                SELECT MOVE
                FROM MOVESET
                WHERE CHARACTER = $1
                ORDER BY SLOT;
                """,
                self.id,
            )
            self.moveset = frozenset({Moves[item["move"]] for item in moveset})
            self.sp_ability = await SpAbility.fetch(connection, idx=self.id)

    @abstractmethod
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
                KIND, AUTHOR, SERVER, URL, IMAGE, PING_BUTTON,
                DELETE_BUTTON, CREATED_AT, LOCATION, THREAD)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            ON CONFLICT (ID) DO UPDATE
            SET
                ID = $1, NAME = $2, AGE = $3, PRONOUN = $4,
                BACKSTORY = $5, EXTRA = $6, KIND = $7, AUTHOR = $8,
                SERVER = $9, URL = $10, IMAGE = $11, ping_button = $12,
                DELETE_BUTTON = $13, CREATED_AT = $14,
                LOCATION = $15, THREAD = $16;
            """,
            self.id,
            self.name,
            self.age,
            self.pronoun.name,
            self.backstory,
            self.extra,
            self.kind,
            self.author,
            self.server,
            self.url,
            self.image,
            self.ping_button,
            self.delete_button,
            self.created_at,
            self.location,
            self.thread,
        )
        await connection.execute(
            """--sql
            DELETE FROM CHARACTER_TYPES
            WHERE CHARACTER = $1;
            """,
            self.id,
        )
        if entries := [(self.id, item.name, not main)
                       for main, item in enumerate(self.types)]:
            await connection.executemany(
                """--sql
                INSERT INTO CHARACTER_TYPES(CHARACTER, TYPE, MAIN)
                VALUES ($1, $2, $3);
                """,
                entries,
            )
        await connection.execute(
            """--sql
            DELETE FROM CHARACTER_ABILITIES
            WHERE ID = $1;
            """,
            self.id,
        )
        if entries := [(self.id, item.name, bool(main))
                       for main, item in enumerate(self.abilities)]:
            await connection.executemany(
                """--sql
                INSERT INTO CHARACTER_ABILITIES(ID, ABILITY, SLOT)
                VALUES ($1, $2, $3)
                ON CONFLICT (ID, SLOT) DO UPDATE SET ABILITY = $2;
                """,
                entries,
            )
        await connection.execute(
            """--sql
            DELETE FROM MOVESET
            WHERE CHARACTER = $1;
            """,
            self.id,
        )
        if entries := [(self.id, value.name, key)
                       for key, value in enumerate(self.moveset, start=1)]:
            await connection.executemany(
                """--sql
                INSERT INTO MOVESET(CHARACTER, MOVE, SLOT)
                VALUES ($1, $2, $3);
                """,
                entries,
            )
        await connection.execute(
            """--sql
            DELETE FROM SPECIAL_ABILITIES
            WHERE ID = $1;
            """,
            self.id,
        )
        if sp_ability := self.sp_ability:
            await sp_ability.upsert(connection, idx=self.id)

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


@dataclass(unsafe_hash=True)
class PokemonCharacter(Character):
    species: Pokemon = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Pokemon: {self.species.name}, Age: {self.age}, Types: {types}".title(
        )

    @property
    def kind(self) -> str:
        return "COMMON"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[PokemonCharacter]
            characters
        """
        characters: list[PokemonCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, PC.SPECIES
            FROM POKEMON_CHARACTER PC, CHARACTER C
            WHERE C.ID = PC.ID and C.kind = $1;
            """,
                "COMMON",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Species[species]
            mon = PokemonCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for PokemonCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await super(PokemonCharacter, self).upsert(connection)
        await connection.execute(
            """--sql
            INSERT INTO POKEMON_CHARACTER(ID, SPECIES)
            VALUES ($1, $2) ON CONFLICT (ID)
            DO UPDATE SET SPECIES = $2;
            """,
            self.id,
            self.species.id,
        )


@dataclass(unsafe_hash=True)
class LegendaryCharacter(Character):
    species: Legendary = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Legendary: {self.species.name}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "LEGENDARY"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[LegendaryCharacter]
            characters
        """
        characters: list[LegendaryCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, PC.SPECIES
            FROM POKEMON_CHARACTER PC, CHARACTER C
            WHERE C.ID = PC.ID and C.kind = $1;
            """,
                "LEGENDARY",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Species[species]
            mon = LegendaryCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for LegendaryCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        if oc_id := self.id:
            await super(LegendaryCharacter, self).upsert(connection)
            await connection.execute(
                """--sql
                INSERT INTO POKEMON_CHARACTER(ID, SPECIES)
                VALUES ($1, $2) ON CONFLICT (ID) DO UPDATE SET SPECIES = $2;
                """,
                oc_id,
                self.species.id,
            )


@dataclass(unsafe_hash=True)
class MythicalCharacter(Character):
    species: Mythical = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Mythical: {self.species.name}, Types: {types}".title()

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def kind(self) -> str:
        return "MYTHICAL"

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[MythicalCharacter]
            characters
        """
        characters: list[MythicalCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, PC.SPECIES
            FROM POKEMON_CHARACTER PC, CHARACTER C
            WHERE C.ID = PC.ID and C.kind = $1;
            """,
                "MYTHICAL",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Species[species]
            mon = MythicalCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for MythicalCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        if oc_id := self.id:
            await super(MythicalCharacter, self).upsert(connection)
            await connection.execute(
                "INSERT INTO POKEMON_CHARACTER(ID, SPECIES) "
                "VALUES ($1, $2) ON CONFLICT (ID) DO UPDATE SET SPECIES = $2;",
                oc_id,
                self.species.id,
            )


@dataclass(unsafe_hash=True)
class UltraBeastCharacter(Character):
    species: UltraBeast = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"UltraBeast: {self.species.name}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "ULTRA BEAST"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[MythicalCharacter]
            characters
        """
        characters: list[UltraBeastCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, PC.SPECIES
            FROM POKEMON_CHARACTER PC, CHARACTER C
            WHERE C.ID = PC.ID and C.kind = $1;
            """,
                "ULTRA BEAST",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Species[species]
            mon = UltraBeastCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for UltraBeastCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        if oc_id := self.id:
            await super(UltraBeastCharacter, self).upsert(connection)
            await connection.execute(
                """--sql
                INSERT INTO POKEMON_CHARACTER(ID, SPECIES)
                VALUES ($1, $2) ON CONFLICT (ID) DO
                UPDATE SET SPECIES = $2;
                """,
                oc_id,
                self.species.id,
            )


@dataclass(unsafe_hash=True)
class FakemonCharacter(Character):
    species: Fakemon = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Fakemon: {self.species.name}, Types: {types}".title()

    def __post_init__(self):
        super(FakemonCharacter, self).__post_init__()
        self.species.id = self.id
        self.abilities = self.abilities or self.species.abilities

    @property
    def kind(self) -> str:
        return "FAKEMON"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def embed(self) -> Embed:
        c_embed = super(FakemonCharacter, self).embed
        c_embed.set_field_at(
            index=2,
            name="Fakemon Species",
            value=self.species.name,
        )
        c_embed.insert_field_at(
            index=3,
            name="HP ",
            value=("🔳" * self.species.HP).ljust(5, "⬜"),
        )
        c_embed.insert_field_at(
            index=4,
            name="ATK",
            value=("🔳" * self.species.ATK).ljust(5, "⬜"),
        )
        c_embed.insert_field_at(
            index=5,
            name="DEF",
            value=("🔳" * self.species.DEF).ljust(5, "⬜"),
        )
        c_embed.insert_field_at(
            index=6,
            name="SPA",
            value=("🔳" * self.species.SPA).ljust(5, "⬜"),
        )
        c_embed.insert_field_at(
            index=7,
            name="SPD",
            value=("🔳" * self.species.SPD).ljust(5, "⬜"),
        )
        c_embed.insert_field_at(
            index=8,
            name="SPE",
            value=("🔳" * self.species.SPE).ljust(5, "⬜"),
        )
        return c_embed

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[FakemonCharacter]
            characters
        """
        characters: list[FakemonCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, F.NAME AS SPECIES,
            F.HP, F.ATK, F.DEF, F.SPA, F.SPD, F.SPE
            FROM FAKEMON F, CHARACTER C
            WHERE C.ID = F.ID and C.kind = $1;
            """,
                "FAKEMON",
        ):
            data: dict[str, int] = dict(item)
            data.pop("kind", None)
            fakemon_id = data["id"]
            stats = multiple_pop(data, "hp", "atk", "def", "spa", "spd", "spe")
            stats = {k.upper(): v for k, v in stats.items()}
            if species := data.get("species", None):
                movepool = await Movepool.fakemon_fetch(connection, fakemon_id)
                data["species"] = Fakemon(
                    id=fakemon_id,
                    name=species,
                    movepool=movepool,
                    **stats,
                )
            mon = FakemonCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for MegaCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        if oc_id := self.id:
            await super(FakemonCharacter, self).upsert(connection)
            await connection.execute(
                """--sql
                INSERT INTO FAKEMON(ID, NAME, HP, ATK, DEF, SPA, SPD, SPE)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (ID) DO UPDATE SET
                NAME = $2, HP = $3, ATK = $4, DEF = $5, SPA = $6, SPD = $7, SPE = $8;
                """,
                oc_id,
                self.name,
                self.species.HP,
                self.species.ATK,
                self.species.DEF,
                self.species.SPA,
                self.species.SPD,
                self.species.SPE,
            )
            await self.movepool.upsert(connection, oc_id)


@dataclass(unsafe_hash=True)
class CustomMegaCharacter(Character):
    species: CustomMega = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Custom: {self.species.name}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "CUSTOM MEGA"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def embed(self) -> Embed:
        c_embed = super(FusionCharacter, self).embed
        c_embed.set_field_at(
            index=2,
            name="Fakemon Species",
            value=f"> {self.species.name}".title(),
        )
        return c_embed

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[CustomMegaCharacter]
            characters
        """
        characters: list[CustomMegaCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, F.SPECIES AS SPECIES
            FROM CUSTOM_MEGA_CHARACTER F, CHARACTER C
            WHERE C.ID = F.ID and C.kind = $1;
            """,
                "CUSTOM MEGA",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = CustomMega(Species[species])
            mon = CustomMegaCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for CustomMegaCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await super(CustomMegaCharacter, self).upsert(connection)
        await connection.execute(
            """--sql
            INSERT INTO CUSTOM_MEGA_CHARACTER(ID, SPECIES)
            VALUES ($1, $2) ON CONFLICT (ID) DO
            UPDATE SET SPECIES = $2;
            """,
            self.id,
            self.species.id,
        )


@dataclass(unsafe_hash=True)
class VariantCharacter(Character):
    species: Variant = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Custom: {self.species.name}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "VARIANT"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def embed(self) -> Embed:
        c_embed = super(VariantCharacter, self).embed
        c_embed.set_field_at(
            index=2,
            name="Fakemon Species",
            value=f"> {self.species.name}".title(),
        )
        return c_embed

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[VariantCharacter]
            characters
        """
        characters: list[VariantCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, F.SPECIES AS SPECIES
            FROM VARIANT_CHARACTER F, CHARACTER C
            WHERE C.ID = F.ID and C.kind = $1;
            """,
                "VARIANT",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Variant(Species[species])
            mon = VariantCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters


@dataclass(unsafe_hash=True)
class FusionCharacter(Character):
    species: Fusion = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Fusion: {self.species.name}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "FUSION"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def possible_types(self) -> list[set[Types]]:
        return self.species.possible_types

    @property
    def embed(self) -> Embed:
        c_embed = super(FusionCharacter, self).embed
        name1, name2 = self.species.name.split("/")
        c_embed.set_field_at(
            index=2,
            name="Fusion Species",
            value=f"> **•** {name1}\n> **•** {name2}".title(),
        )
        return c_embed

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[FakemonCharacter]
            characters
        """
        characters: list[FusionCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, SPECIES1, SPECIES2
            FROM FUSION_CHARACTER F, CHARACTER C
            WHERE C.ID = F.ID and C.kind = $1;
            """,
                "FUSION",
        ):
            data: dict[str, int] = dict(item)
            data.pop("kind", None)
            mon1 = data.pop("species1", None)
            mon2 = data.pop("species2", None)
            data["species"] = Fusion(Species[mon1], Species[mon2])
            mon = FusionCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for FusionCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await super(FusionCharacter, self).upsert(connection)
        mon1, mon2 = self.species.id.split("_")
        await connection.execute(
            """--sql
            INSERT INTO FUSION_CHARACTER(ID, species1, species2)
            VALUES ($1, $2, $3) ON CONFLICT (ID) DO UPDATE SET
            SPECIES1 = $2, SPECIES2 = $3;
            """,
            self.id,
            mon1,
            mon2,
        )


@dataclass(unsafe_hash=True)
class MegaCharacter(Character):
    species: Mega = None

    def __repr__(self):
        types = "/".join(i.name for i in self.types)
        return f"Mega: {self.species.name[5:]}, Types: {types}".title()

    @property
    def kind(self) -> str:
        return "MEGA"

    @property
    def has_default_types(self) -> bool:
        """Wether if the species have a default type

        Returns
        -------
        bool
            answer
        """
        return True

    @property
    def any_move_at_first(self) -> bool:
        """Wether if the species can start with any move at first

        Returns
        -------
        bool
            answer
        """
        return False

    @property
    def any_ability_at_first(self) -> bool:
        """Wether if the species can start with any ability at first

        Returns
        -------
        bool
            answer
        """
        return False

    @classmethod
    async def fetch_all(cls, connection: Connection):
        """Obtains all Pokemon characters.

        Parameters
        ----------
        connection : Connection
            asyncpg connection

        Returns
        -------
        list[MegaCharacter]
            characters
        """
        characters: list[MegaCharacter] = []
        async for item in connection.cursor(
                """--sql
            SELECT C.*, PC.SPECIES
            FROM POKEMON_CHARACTER PC, CHARACTER C
            WHERE C.ID = PC.ID and C.kind = $1;
            """,
                "MEGA",
        ):
            data = dict(item)
            data.pop("kind", None)
            if species := data.pop("species", None):
                data["species"] = Species[species]
            mon = MegaCharacter(**data)
            await mon.retrieve(connection)
            characters.append(mon)

        return characters

    async def upsert(self, connection: Connection):
        """Upsert method for MegaCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await super().upsert(connection)
        await connection.execute(
            """--sql
            INSERT INTO POKEMON_CHARACTER(ID, SPECIES)
            VALUES ($1, $2) ON CONFLICT (ID) DO UPDATE SET SPECIES = $2;
            """,
            self.id,
            self.species.id,
        )


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
    "artist": "Artist's Name",
    "website": "Art's Website",
}
PLACEHOLDER_SP = {
    "What is it Called?": "name",
    "How is it Called?": "name",
    "How did they obtain it?": "method",
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

ASSOCIATIONS: frozendict[Type[SpeciesBase], Type[Character]] = frozendict({
    Pokemon:
    PokemonCharacter,
    Mega:
    MegaCharacter,
    Legendary:
    LegendaryCharacter,
    Mythical:
    MythicalCharacter,
    UltraBeast:
    UltraBeastCharacter,
    Fakemon:
    FakemonCharacter,
    Fusion:
    FusionCharacter,
    CustomMega:
    CustomMegaCharacter,
    Variant:
    VariantCharacter,
})


async def fetch_all(connection: Connection):
    """This method fetches all characters

    Parameters
    ----------
    connection : Connection
        asyncpg connection

    Returns
    -------
    list[Type[Character]]
        Characters
    """
    data: list[Type[Character]] = []

    for kind in ASSOCIATIONS.values():
        data.extend(await kind.fetch_all(connection))

    return data


def kind_deduce(item: Optional[SpeciesBase], *args, **kwargs):
    """This class returns the character class based on the given species

    Attributes
    ----------
    item : Optional[SpeciesBase]
        Species
    args : Any
        Args of the Character class
    kwargs : Any
        kwargs of the Character class

    Returns
    -------
    Optional[Character]
        Character instance
    """
    if instance := ASSOCIATIONS.get(type(item)):
        return instance(*args, **kwargs)


def oc_process(**kwargs):
    """Function used for processing a dict, to a character

    Returns
    -------
    Type[Character]
        Character given the paraneters
    """
    data: dict[str, Any] = {k.lower(): v for k, v in kwargs.items()}
    fakemon_mode: bool = "fakemon" in data
    if species_name := common_pop_get(
            data,
            "fakemon",
            "species",
            "fusion",
    ):
        if fakemon_mode:
            name: str = species_name.title()
            if name.startswith("Mega"):
                data["species"] = CustomMega(Species.deduce(name[5:]))
            elif name.startswith("Variant"):
                data["species"] = Variant(Species.deduce(name[8:]))
            else:
                data["species"] = Fakemon(name=name)
        elif species := Species.deduce(species_name):
            data["species"] = species

    if types := common_pop_get(data, "types", "type"):
        data["species"].types = frozenset(Types.deduce(types))

    if abilities := common_pop_get(data, "abilities", "ability"):
        data["abilities"] = frozenset(Abilities.deduce(abilities))

    if moveset := common_pop_get(data, "moveset", "moves"):
        data["moveset"] = frozenset(Moves.deduce(moveset))

    if pronoun := common_pop_get(data, "pronoun", "gender"):
        data["pronoun"] = Pronoun.deduce(pronoun)

    if isinstance(age := data.get("age"), str):
        data["age"] = int_check(age, 1, 99)

    if isinstance(species := data["species"], Fakemon):
        if stats := data.pop("stats", {}):
            species.set_stats(**stats)

        if movepool := data.pop("movepool",
                                {"event": data.get("moveset", set())}):
            species.movepool = Movepool.from_dict(**movepool)

    data = {k: v for k, v in data.items() if v}

    return kind_deduce(data.get("species"), **data)


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


async def doc_convert(url: str) -> dict[str, Any]:
    """Google Convereter

    Parameters
    ----------
    url : str
        Google Document

    Returns
    -------
    dict[str, Any]
        Info
    """
    if doc := await to_thread(docs_reader, url):
        tables = nested_lookup(key="table", document=doc["body"]["content"])
        contents = nested_lookup(key="textRun", document=tables)
        content_values: list[str] = nested_lookup(key="content",
                                                  document=contents)

        text = [
            strip.replace("\u2019", "'") for item in content_values
            if (strip := item.strip())
        ]

        movepool_typing = dict[str, Union[set[str], dict[int, set[str]]]]
        raw_kwargs: dict[str, Union[str, set[str], movepool_typing]] = dict(
            url=f"https://docs.google.com/document/d/{url}/edit?usp=sharing",
            moveset=set(),
            movepool={},
            abilities=set(),
            fusion=set(),
            types=set(),
            stats={
                stat: stats_check(*value)
                for index, item in enumerate(content_values) if all((
                    stat := PLACEHOLDER_STATS.get(item.strip()),
                    len(content_values) > index,
                    len(value := content_values[index + 1:][:1]) == 1,
                ))
            },
        )

        for index, item in enumerate(text[:-1], start=1):
            if not check(next_value := text[index]):
                continue
            if argument := PLACEHOLDER_NAMES.get(item):
                raw_kwargs[argument] = next_value
            elif element := DATA_FINDER.match(item):
                argument = next_value.title()
                x, y = element.groups()
                if x == "Level":
                    idx = int(y)
                    raw_kwargs["movepool"].setdefault("level", {})
                    raw_kwargs["movepool"]["level"].setdefault(idx, set())
                    raw_kwargs["movepool"]["level"][idx].add(argument)
                elif x == "Move":
                    raw_kwargs["moveset"].add(argument)
                elif x == "Ability":
                    raw_kwargs["abilities"].add(next_value)
                elif x == "Species":
                    raw_kwargs["fusion"].add(next_value)
                elif x == "Type":
                    raw_kwargs["types"].add(next_value.upper())
                else:
                    raw_kwargs["movepool"].setdefault(x.lower(), set())
                    raw_kwargs["movepool"][x.lower()].add(argument)

        raw_kwargs.pop("artist", None)
        raw_kwargs.pop("website", None)

        if inline := doc.get("inlineObjects"):
            if images := nested_lookup(key="contentUri", document=inline):
                raw_kwargs["image"] = images[0]

        return raw_kwargs
