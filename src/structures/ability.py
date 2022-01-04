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

from dataclasses import dataclass, field
from typing import Optional

from asyncpg import Connection, Record

__all__ = ("Ability", "SpAbility")


@dataclass(unsafe_hash=True, slots=True)
class Ability:
    """
    Ability class which represents the game provided ones.
    """

    name: str = field(default_factory=str)  # Name of the ability
    description: str = field(default_factory=str)  # Description of the ability

    def __repr__(self) -> str:
        """Repr Method

        Returns
        -------
        str
            string representing the ability
        """
        return f"Ability({self.name!r})"


@dataclass(unsafe_hash=True, slots=True)
class SpAbility(Ability):
    """
    Special Ability class which inherits from Ability
    """

    name: str = field(default_factory=str)  # Name of the special ability
    description: str = field(
        default_factory=str
    )  # Description of the special ability
    origin: str = field(
        default_factory=str
    )  # Method to obtain the special ability
    pros: str = field(default_factory=str)  # Pros of the special ability
    cons: str = field(default_factory=str)  # Cons of the special ability

    def __repr__(self) -> str:
        return f"SPAbility(name={self.name})"

    @classmethod
    def convert(cls, record: Record) -> SpAbility:
        """Method that converts a record into a SpAbility instance

        Parameters
        ----------
        record : Record
            record to convert

        Returns
        -------
        SpAbility
            converted element
        """
        name, description, origin, pros, cons = (
            record["name"],
            record["description"],
            record["origin"],
            record["pros"],
            record["cons"],
        )
        return SpAbility(
            name=name,
            description=description,
            origin=origin,
            pros=pros,
            cons=cons,
        )

    @classmethod
    async def fetch(
        cls, connection: Connection, idx: int
    ) -> Optional[SpAbility]:
        """This method calls database to obtain information

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        idx : int
            ID to look for

        Returns
        -------
        Optional[SpAbility]
            Fetched element
        """
        if entry := await connection.fetchrow(
            """--sql
                    SELECT *
                    FROM SPECIAL_ABILITIES
                    WHERE ID = $1;
                    """,
            idx,
        ):
            return cls.convert(entry)

    async def upsert(self, connection: Connection, idx: int) -> str:
        """This method calls database to set information

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        idx : int
            id of the special ability

        Returns
        -------
        str
            Result of the query
        """
        return await connection.execute(
            """--sql
            INSERT INTO SPECIAL_ABILITIES(ID, NAME, DESCRIPTION, ORIGIN, PROS, CONS)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (ID) DO UPDATE
            SET NAME = $2, DESCRIPTION = $3, ORIGIN = $4, PROS = $5, CONS = $6;
            """,
            idx,
            self.name,
            self.description,
            self.origin,
            self.pros,
            self.cons,
        )
