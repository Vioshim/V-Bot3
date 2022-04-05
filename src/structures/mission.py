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
from datetime import datetime
from typing import Literal, Optional

from asyncpg import Connection
from discord import Color, Embed
from discord.utils import utcnow

from src.utils.etc import DICE_NUMBERS, WHITE_BAR

__all__ = ("Mission",)


@dataclass(repr=False, unsafe_hash=True, slots=True)
class Mission:
    id: Optional[int] = None
    author: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    place: Optional[int] = None
    target: Optional[str] = None
    client: Optional[str] = None
    reward: Optional[str] = None
    created_at: Optional[datetime] = None
    msg_id: Optional[int] = None
    max_amount: Optional[int] = None
    difficulty: Literal[1, 2, 3, 4, 5, 6] = 1
    ocs: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self):
        if not isinstance(self.created_at, datetime):
            self.created_at = utcnow()

    def __repr__(self):
        return (
            f"Mission(id={self.id}, difficulty={self.difficulty}, ocs={len(self.ocs)})"
        )

    async def upsert(self, connection: Connection) -> None:
        if isinstance(self.id, int):
            self.id = await connection.fetchval(
                """--sql
                INSERT INTO MISSIONS(ID, AUTHOR, TITLE, DESCRIPTION, DIFFICULTY, PLACE, TARGET, CLIENT, REWARD, CREATED_AT, MSG_ID, MAX_AMOUNT)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (ID) DO UPDATE SET
                    AUTHOR = $2,
                    TITLE = $3,
                    DESCRIPTION = $4,
                    DIFFICULTY = $5,
                    PLACE = $6,
                    TARGET = $7,
                    CLIENT = $8,
                    REWARD = $9,
                    CREATED_AT = $10,
                    MSG_ID = $11,
                    MAX_AMOUNT = $12
                RETURNING ID;
                """,
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
                self.max_amount,
            )
        else:
            self.id = await connection.fetchval(
                """--sql
                INSERT INTO MISSIONS(AUTHOR, TITLE, DESCRIPTION, DIFFICULTY, PLACE, TARGET, CLIENT, REWARD, CREATED_AT, MSG_ID, MAX_AMOUNT)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING ID;
                """,
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
                self.max_amount,
            )
        if ocs := self.ocs:
            await connection.execute(
                "DELETE FROM mission_assignment WHERE mission = $1",
                self.id,
            )
            await connection.executemany(
                "INSERT INTO mission_assignment(character, mission) VALUES ($1, $2)",
                [(i, self.id) for i in ocs],
            )

    async def upsert_oc(self, connection: Connection, oc_id: int) -> datetime:
        self.ocs |= {oc_id}
        return await connection.fetchval(
            "INSERT INTO mission_assignment(character, mission) VALUES ($1, $2) RETURNING ASSIGNED_AT",
            oc_id,
            self.id,
        )

    async def remove(self, connection: Connection) -> None:
        await connection.execute("DELETE FROM MISSIONS WHERE ID = $1", self.id)
        self.id = None

    @property
    def jump_url(self):
        return f"https://discord.com/channels/719343092963999804/908498210211909642/{self.msg_id}"

    @property
    def thread_url(self):
        return f"https://discord.com/channels/719343092963999804/{self.msg_id}"

    @property
    def emoji(self):
        return DICE_NUMBERS[self.difficulty - 1]

    @property
    def embed(self) -> Embed:
        """Returns the Mission as Embed

        Returns
        -------
        Embed
            Embed
        """
        embed = Embed(
            title=(self.title or "").title(),
            description="> No description.",
            colour=Color.blurple(),
            timestamp=self.created_at,
        )
        embed.set_thumbnail(url=self.emoji.url)
        if description := self.description:
            embed.description = description
        if target := self.target:
            embed.add_field(name="Target", value=target, inline=False)
        if client := self.client:
            embed.add_field(name="Client", value=client, inline=False)
        if reward := self.reward:
            embed.add_field(name="Reward", value=reward, inline=False)
        if place := self.place:
            embed.add_field(name="Place", value=f"<#{place}>", inline=False)

        if limit := self.max_amount:
            text = f"{len(self.ocs):02d}/{limit:02d}"
        else:
            text = f"{len(self.ocs):02d}"
        embed.set_footer(text=f"{text} OCs have accepted this mission.")
        embed.set_image(url=WHITE_BAR)
        return embed
