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

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from os import urandom
from random import sample
from typing import Optional, Type

from asyncpg import Connection
from discord import Color, Embed
from discord.utils import utcnow

from src.enums.abilities import Abilities
from src.enums.mon_types import Types
from src.enums.moves import Moves
from src.enums.pronouns import Pronoun
from src.enums.species import Species
from src.structures.ability import SpAbility
from src.structures.movepool import Movepool
from src.structures.species import Species as SpeciesBase
from src.utils.imagekit import ImageKit

__all__ = ("Character",)


@dataclass(unsafe_hash=True, slots=True)
class Character(metaclass=ABCMeta):
    species: Type[SpeciesBase] | Species
    id: Optional[int] = None
    author_id: Optional[int] = None
    thread_id: Optional[int] = None
    server_id: int = 719343092963999804
    name: str = ""
    age: Optional[int] = None
    pronoun: Pronoun = Pronoun.Them
    backstory: Optional[str] = None
    extra: Optional[str] = None
    types: frozenset[Types] = field(default_factory=frozenset)
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
        if not self.created_at:
            self.created_at = utcnow()
        if types := self.species.types:
            self.types = types
        if not self.abilities:
            if abilities := list(self.species.abilities):
                amount = min(self.max_amount_abilities, len(abilities))
                items = sample(abilities, k=amount)
                self.abilities = frozenset(items)
        if not self.image:
            self.image = self.default_image

        if not self.moveset:
            if movepool := self.movepool:
                moves = list(movepool())
                amount = min(6, len(moves))
                items = sample(moves, k=amount)
                self.moveset = frozenset(items)

    @property
    def movepool(self) -> Movepool:
        return self.species.movepool

    # noinspection PyTypeChecker
    @property
    def can_have_special_abilities(self) -> bool:
        if len(self.abilities) == 2:
            return False
        return self.species.can_have_special_abilities

    # noinspection PyTypeChecker
    @property
    def max_amount_abilities(self) -> int:
        if self.sp_ability:
            return 1
        return self.species.max_amount_abilities

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
        return f"https://discord.com/channels/{self.server_id}/{self.thread_id}/{self.id}"

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
            else:
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
        c_embed.add_field(name="Pronoun", value=self.pronoun)
        c_embed.add_field(name="Age", value=self.age or "Unknown")
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
                value=sp_ability.method[:200],
                inline=False,
            )
            c_embed.add_field(name="Sp.Ability - Pros", value=sp_ability.pros[:200], inline=False)
            c_embed.add_field(name="Sp.Ability - Cons", value=sp_ability.cons[:200], inline=False)
        if moves_text := "\n".join(f"> {item!r}" for item in self.moveset):
            c_embed.add_field(name="Moveset", value=moves_text, inline=False)
        c_embed.set_image(url=self.generated_image)
        if entry := "/".join(i.name.title() for i in self.types):
            c_embed.set_footer(text=entry)

        if location := self.place_mention:
            c_embed.add_field(
                name="Last Location",
                value=location,
                inline=False,
            )

        if isinstance(self.extra, str):
            if extra := self.extra[: min(1000, len(c_embed) - 100)]:
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
            if image.startswith(f"https://cdn.discordapp.com/attachments/{self.thread_id}/"):
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

    async def change_id(self, connection: Connection, idx: int) -> None:
        if self.id:
            self.id = await connection.fetchval(
                """--sql
                UPDATE CHARACTER
                SET ID = $2
                WHERE ID = $1
                RETURNING ID;
                """,
                self.id,
                idx,
            )
        else:
            self.id = idx
            await self.upsert(connection)

    async def standard_upsert(self, connection: Connection, kind: str) -> None:
        """This is the standard upsert method for most of the kinds

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        kind : str
            kind to insert as
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
            self.pronoun,
            self.backstory,
            self.extra,
            kind,
            self.author_id,
            self.server_id,
            self.url,
            self.image,
            self.ping_button,
            self.delete_button,
            self.created_at,
            self.location,
            self.thread_id,
        )
        await connection.execute(
            """--sql
            DELETE FROM CHARACTER_TYPES
            WHERE CHARACTER = $1;
            """,
            self.id,
        )
        if entries := [(self.id, item.name, not main) for main, item in enumerate(self.types)]:
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
        if entries := [(self.id, item.id, bool(main)) for main, item in enumerate(self.abilities)]:
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
        if entries := [
            (self.id, value.id, key) for key, value in enumerate(self.moveset, start=1)
        ]:
            await connection.executemany(
                """--sql
                INSERT INTO MOVESET(CHARACTER, MOVE, SLOT)
                VALUES ($1, $2, $3);
                """,
                entries,
            )
        await connection.execute(
            """
            DELETE FROM SPECIAL_ABILITIES
            WHERE ID = $1;
            """,
            self.id,
        )
        if sp_ability := self.sp_ability:
            await sp_ability.upsert(connection, idx=self.id)

    @abstractmethod
    async def upsert(self, connection: Connection) -> None:
        """This is the standard upsert method which must be added
        in all character classes.

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
