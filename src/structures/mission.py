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

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Union

from asyncpg import Connection
from discord import Color, Embed, User
from discord.utils import utcnow

from src.utils.etc import DICE_NUMBERS, WHITE_BAR

__all__ = ("Mission",)


@dataclass(repr=False, unsafe_hash=True)
class Mission:
    id: Optional[int] = None
    author: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    difficulty: Literal[1, 2, 3, 4, 5, 6] = 1
    place: Optional[int] = None
    target: Optional[str] = None
    client: Optional[str] = None
    reward: Optional[str] = None
    created_at: Optional[datetime] = None
    msg_id: Optional[int] = None
    claimed: Optional[int] = None
    concluded: bool = False

    def __post_init__(self):
        if not isinstance(self.created_at, datetime):
            self.created_at = utcnow()

    def __repr__(self):
        return f"Mission(id={self.id}, difficulty={self.difficulty})"

    async def upsert(self, connection: Connection) -> None:
        if isinstance(self.id, int):
            self.id = await connection.fetchval(
                "INSERT INTO MISSIONS("
                "ID, AUTHOR, TITLE, DESCRIPTION, DIFFICULTY, PLACE, TARGET, "
                "CLIENT, REWARD, CREATED_AT, MSG_ID, CLAIMED, CONCLUDED"
                ")VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)"
                "ON CONFLICT (ID) DO UPDATE SET "
                "AUTHOR = $2, "
                "TITLE = $3, "
                "DESCRIPTION = $4, "
                "DIFFICULTY = $5, "
                "PLACE = $6, "
                "TARGET = $7, "
                "CLIENT = $8, "
                "REWARD = $9, "
                "CREATED_AT = $10, "
                "MSG_ID = $11, "
                "CLAIMED = $12, "
                "CONCLUDED = $13 "
                "RETURNING ID;",
                self.id,
                self.author,
                self.title,
                self.description,
                self.difficulty,
                self.place,
                self.target,
                self.client,
                self.reward,
                self.created_at,
                self.msg_id,
                self.claimed,
                self.concluded,
            )
        else:
            self.id = await connection.fetchval(
                "INSERT INTO MISSIONS("
                "AUTHOR, TITLE, DESCRIPTION, DIFFICULTY, PLACE, TARGET, "
                "CLIENT, REWARD, CREATED_AT, MSG_ID, CLAIMED, CONCLUDED"
                ") VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12) "
                "RETURNING ID;",
                self.author,
                self.title,
                self.description,
                self.difficulty,
                self.place,
                self.target,
                self.client,
                self.reward,
                self.created_at,
                self.msg_id,
                self.claimed,
                self.concluded,
            )

    async def remove(self, connection: Connection) -> None:
        await connection.execute("DELETE FROM MISSIONS WHERE ID = $1", self.id)
        self.id = None

    @property
    def jump_url(self):
        if self.msg_id:
            return f"https://discord.com/channels/719343092963999804/908498210211909642/{self.msg_id}"

    @property
    def emoji(self):
        return DICE_NUMBERS[self.difficulty - 1]

    @property
    def embed(self):
        embed = Embed(
            title=(self.title or "").title(),
            description="> No description.",
            colour=Color.blurple(),
            timestamp=self.created_at,
        )
        embed.set_thumbnail(url=self.emoji.url)
        if description := self.description:
            if description[:2] == "> ":
                embed.description = f"> {description[2:]}"
            else:
                embed.description = f"> {description}"
        if target := self.target:
            embed.add_field(name="Target", value=target, inline=False)
        if client := self.client:
            embed.add_field(name="Client", value=client, inline=False)
        if reward := self.reward:
            embed.add_field(name="Reward", value=reward, inline=False)
        if place := self.place:
            embed.add_field(name="Place", value=f"<#{place}>", inline=False)

        embed.set_image(url=WHITE_BAR)
        return embed

    @classmethod
    async def fetch(cls, connection: Connection, mission_id: int) -> Optional[Mission]:
        if entry := await connection.fetchrow(
            "SELECT * FROM MISSIONS where id = $1", mission_id
        ):
            return Mission(**dict(entry))

    @classmethod
    async def fetch_all(cls, connection: Connection) -> list[Mission]:
        entries = []
        async for item in connection.cursor(
            query="SELECT * FROM MISSIONS order by created_at;"
        ):
            entries.append(Mission(**dict(item)))
        return entries

    @classmethod
    async def fetch_by_author(
        cls, connection: Connection, author: Union[User, int]
    ) -> list[Mission]:
        if not isinstance(author, int):
            author = author.id
        entries = []
        async for item in connection.cursor(
            "SELECT * FROM MISSIONS where author = $1 order by created_at;", author
        ):
            entries.append(Mission(**dict(item)))
        return entries
