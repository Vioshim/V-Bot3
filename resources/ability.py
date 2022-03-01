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

from dataclasses import asdict, dataclass
from difflib import get_close_matches
from json import JSONDecoder, JSONEncoder, load
from re import split
from typing import Any, Optional

from asyncpg import Connection, Record
from discord import Embed
from frozendict import frozendict


def fix(text: str) -> str:
    """This function removes special characters, and capitalizes an string

    Parameters
    ----------
    text : str
        string to be formatted

    Returns
    -------
    str
        formatted string
    """
    text: str = str(text).upper().strip()
    values = {"Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U"}
    return "".join(x for e in text if (x := values.get(e, e)).isalnum())


__all__ = (
    "Ability",
    "AbilityDecoder",
    "AbilityEncoder",
    "SpAbility",
    "ALL_ABILITIES",
)

ALL_ABILITIES = frozendict()


@dataclass(unsafe_hash=True, slots=True)
class Ability:
    """
    Ability class which represents the game provided ones.
    """

    id: str = ""
    name: str = ""
    description: str = ""
    battle: str = ""
    outside: str = ""
    random_fact: str = ""

    def __repr__(self) -> str:
        """Repr Method

        Returns
        -------
        str
            string representing the ability
        """
        return f"Ability(name={self.name!r})"

    @property
    def embed(self) -> Embed:
        """Generated Embed

        Returns
        -------
        Embed
            Embed
        """
        embed = Embed(title=self.name, description=self.description)
        if battle := self.battle:
            embed.add_field(name="In Battle", value=battle, inline=False)
        if outside := self.outside:
            embed.add_field(name="Out of Battle", value=outside, inline=False)
        if random_fact := self.random_fact:
            embed.add_field(name="Random Fact", value=random_fact, inline=False)
        return embed

    @classmethod
    def all(cls) -> frozenset[Ability]:
        return frozenset(ALL_ABILITIES.values())

    @classmethod
    def deduce_many(
        cls,
        *elems: str,
        limit_range: Optional[int] = None,
    ) -> frozenset[Ability]:
        """This is a method that determines the abilities out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        item : str
            String to search

        limit_range : int, optional
            max amount to deduce, defaults to None

        Returns
        -------
        frozenset[Ability]
            Obtained result
        """
        items: set[Ability] = set()
        aux: list[str] = []

        for elem in elems:
            if isinstance(elem, str):
                aux.append(elem)
            elif isinstance(elem, Ability):
                items.add(elem)

        for elem in split(r"[^A-Za-z0-9 \.'-]", ",".join(aux)):
            if data := ALL_ABILITIES.get(elem := fix(elem)):
                items.add(data)
            else:
                for data in get_close_matches(
                    word=elem,
                    possibilities=ALL_ABILITIES,
                    n=1,
                    cutoff=0.85,
                ):
                    items.add(ALL_ABILITIES[data])

        return frozenset(list(items)[:limit_range])

    @classmethod
    def deduce(cls, item: str) -> Optional[Ability]:
        """This is a method that determines the ability out of
        the existing entries, it has a 85% of precision.

        Parameters
        ----------
        item : str
            String to search

        Returns
        -------
        Optional[Ability]
            Obtained result
        """
        if isinstance(item, Ability):
            return item
        if isinstance(item, str):
            if data := ALL_ABILITIES.get(item := fix(item)):
                return data
            for elem in get_close_matches(
                item,
                possibilities=ALL_ABILITIES,
                n=1,
                cutoff=0.85,
            ):
                return ALL_ABILITIES[elem]

    @classmethod
    def from_ID(cls, item: str) -> Optional[Ability]:
        """This is a method that returns an ability given an exact ID.

        Parameters
        ----------
        item : str
            Ability ID to check

        Returns
        -------
        Optional[Ability]
            Obtained result
        """
        if isinstance(item, Ability):
            return item
        return ALL_ABILITIES.get(item)


@dataclass(unsafe_hash=True, slots=True)
class SpAbility:
    """
    Special Ability class which inherits from Ability
    """

    name: str = ""
    description: str = ""
    origin: str = ""
    pros: str = ""
    cons: str = ""

    def __repr__(self) -> str:
        return f"SPAbility(name={self.name})"

    @property
    def embed(self) -> Embed:
        """Generated Embed

        Returns
        -------
        Embed
            Embed
        """
        embed = Embed(title=self.name, description=self.description)
        if origin := self.origin:
            embed.add_field(name="Origin", value=origin[:1024], inline=False)
        if pros := self.pros:
            embed.add_field(name="Pros", value=pros[:1024], inline=False)
        if cons := self.cons:
            embed.add_field(name="Cons", value=cons[:1024], inline=False)
        if len(embed) >= 6000 and embed.description:
            embed.description = embed.description[:2000]
        return embed

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
        items = dict(record)
        items.pop("id", None)
        return SpAbility(**items)

    @classmethod
    async def fetch(
        cls,
        connection: Connection,
        idx: int,
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

    async def upsert(
        self,
        connection: Connection,
        idx: int,
    ) -> str:
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


class AbilityEncoder(JSONEncoder):
    """Ability encoder"""

    def default(self, o):
        if isinstance(o, (Ability, SpAbility)):
            return asdict(o)
        return super(AbilityEncoder, self).default(o)


class AbilityDecoder(JSONDecoder):
    """Ability decoder"""

    def __init__(self, *args, **kwargs):
        super(AbilityDecoder, self).__init__(
            object_hook=self.object_hook,
            *args,
            **kwargs,
        )

    def object_hook(self, dct: dict[str, Any]):
        """Decoder method for dicts

        Parameters
        ----------
        dct : dict[str, Any]
            Input

        Returns
        -------
        Any
            Result
        """
        if all(x in dct for x in SpAbility.__slots__):
            return SpAbility(**dct)
        if all(x in dct for x in Ability.__slots__):
            return Ability(**dct)
        return dct


with open("resources/abilities.json", mode="r") as f:
    abilities: list[Ability] = load(f, cls=AbilityDecoder)
    ALL_ABILITIES = frozendict({ab.id: ab for ab in abilities})
