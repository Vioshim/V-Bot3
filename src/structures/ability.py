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
from enum import Enum
from json import JSONEncoder, load
from re import split
from typing import Any, Callable, Optional

from asyncpg import Connection, Record
from discord import Embed
from discord.utils import find, get
from frozendict import frozendict
from rapidfuzz import process

from src.utils.functions import fix

__all__ = (
    "Ability",
    "AbilityEncoder",
    "SpAbility",
    "ALL_ABILITIES",
)

ALL_ABILITIES = frozendict()
ABILITIES_DEFINING = ["Beast Boost", "Protosynthesis", "Quark Drive"]


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
    def find(cls, predicate: Callable[[Ability], Any]):
        return find(predicate, cls.all())

    @classmethod
    def get(cls, **kwargs):
        return get(cls.all(), **kwargs)

    @classmethod
    def deduce_many(cls, *elems: str, limit_range: Optional[int] = None) -> frozenset[Ability]:
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
        items = {elem for elem in elems if isinstance(elem, cls)}
        if aux := ",".join(elem for elem in elems if isinstance(elem, str)):
            data = split(r"[^A-Za-z0-9 \.'-]", aux)
            items.update(x for elem in data if (x := cls.deduce(elem)))

        return frozenset(list(items)[:limit_range])

    @classmethod
    def deduce(cls, item: str):
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
        if isinstance(item, cls):
            return item
        if not (data := ALL_ABILITIES.get(fix(item))) and (
            items := process.extractOne(
                item,
                cls.all(),
                processor=lambda x: getattr(x, "name", x),
                score_cutoff=85,
            )
        ):
            data = items[0]
        if isinstance(data, Ability):
            return data

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

    @classmethod
    def hook(cls, data: dict[str, str]):
        if all(x in data for x in cls.__slots__):
            return cls(**data)


class UTraitKind(Enum):
    Birth_Gift = ("Unusual birth conditions.", "🐣")
    Bloodline = ("Runs through family's veins.", "👨‍👩‍👧‍👦")
    Hard_work = ("A power within that awakened by hard work.", "⚒️")
    Science = ("Unnatural modifications or applications.", "🔬")
    Technology = ("Tech-related improvements.", "⚙️")
    Survival = ("Instinctively awakened by adrenaline.", "🏕️")
    Event = ("Sudden, very rare yet it happened one day.", "☄️")
    Defect = ("Adaptation or unintended change.", "🧑‍⚕️")
    Curse = ("Harm or Punishment root", "☠️")
    Blessing = ("External favour and/or protection.", "🕯️")
    Magic = ("Spellcasting, rituals or new techniques", "🪄")
    Spite = ("Hatred, malice or sheer anger did this.", "💢")
    Item = ("Body synchronizes with it", "📦")
    Passed = ("Given from another creature", "🎁")

    @property
    def title(self):
        return self.name.replace("_", " ")

    @property
    def emoji(self) -> str:
        _, value = self.value
        return value

    @property
    def desc(self) -> str:
        value, _ = self.value
        return value

    @property
    def phrase(self):
        return f"{self.title}: {self.desc}"


@dataclass(unsafe_hash=True, slots=True)
class SpAbility:
    name: str = ""
    description: str = ""
    origin: str = ""
    pros: str = ""
    cons: str = ""
    kind: UTraitKind = UTraitKind.Hard_work

    def __post_init__(self):
        if isinstance(self.kind, str):
            try:
                self.kind = UTraitKind[self.kind]
            except KeyError:
                self.kind = UTraitKind.Hard_work

    def __repr__(self) -> str:
        return f"SPAbility(name={self.name})"

    def clear(self):
        self.name = ""
        self.description = ""
        self.origin = ""
        self.pros = ""
        self.cons = ""
        self.kind = UTraitKind.Hard_work

    @property
    def valid(self):
        return self.name and self.description and self.origin

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
        embed.set_footer(text=self.kind.phrase)
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

    def copy(self):
        return SpAbility(
            name=self.name,
            description=self.description,
            origin=self.origin,
            pros=self.pros,
            cons=self.cons,
            kind=self.kind,
        )

    @classmethod
    async def fetch(cls, connection: Connection, idx: int) -> Optional[SpAbility]:
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
        if not self or self == SpAbility():
            return await connection.execute(
                """--sql
                DELETE FROM SPECIAL_ABILITIES
                WHERE ID = $1;
                """,
                idx,
            )
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

    @classmethod
    def hook(cls, data: dict[str, str]):
        if all(x in data for x in cls.__slots__):
            return cls(**data)


class AbilityEncoder(JSONEncoder):
    """Ability encoder"""

    def default(self, o):
        if isinstance(o, (Ability, SpAbility)):
            return asdict(o)
        return super(AbilityEncoder, self).default(o)


with open("resources/abilities.json", mode="r", encoding="utf8") as f:
    abilities: list[Ability] = load(f, object_hook=lambda x: Ability.hook(x) or SpAbility.hook(x) or x)
    ALL_ABILITIES = frozendict({ab.id: ab for ab in abilities})
