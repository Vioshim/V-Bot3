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

from dataclasses import asdict, astuple, dataclass, field
from typing import Callable, Union

from asyncpg.connection import Connection
from frozendict import frozendict

from src.enums.moves import Moves

__all__ = ("Movepool", )


# noinspection PyArgumentList
@dataclass(unsafe_hash=True, repr=False)
class Movepool:
    """
    Class which represents a movepool
    """

    level: frozendict[int,
                      frozenset[Moves]] = field(default_factory=frozendict)
    tm: frozenset[Moves] = field(default_factory=frozenset)
    event: frozenset[Moves] = field(default_factory=frozenset)
    tutor: frozenset[Moves] = field(default_factory=frozenset)
    egg: frozenset[Moves] = field(default_factory=frozenset)
    levelup: frozenset[Moves] = field(default_factory=frozenset)
    other: frozenset[Moves] = field(default_factory=frozenset)

    def __post_init__(self):
        self.level = frozendict(
            {k: frozenset(v)
             for k, v in self.level.items()})
        self.tm = frozenset(self.tm)
        self.event = frozenset(self.event)
        self.tutor = frozenset(self.tutor)
        self.egg = frozenset(self.egg)
        self.levelup = frozenset(self.levelup)
        self.other = frozenset(self.other)

    def __repr__(self) -> str:
        """Repr Method

        Returns
        -------
        str
            repr
        """
        elements: list[str] = []
        for key, value in asdict(self).items():
            if isinstance(value, dict):
                count = sum(len(item) for item in value.values())
            else:
                count = len(value)
            if count:
                elements.append(f"{key}={count}")
        data = ", ".join(elements)
        return f"Movepool({data})"

    def __len__(self) -> int:
        """Returns the total of individual moves in the movepool

        Returns
        -------
        int
            total of moves
        """
        return len(self())

    def __bool__(self):
        return any(astuple(self))

    def __lt__(self, other: Movepool):
        return len(self) < len(other)

    def __gt__(self, other: Movepool):
        return len(self) > len(other)

    def operator(
        self,
        other: Movepool,
        method: Callable[[frozenset[Moves], frozenset[Moves]],
                         frozenset[Moves]],
    ) -> Movepool:
        """This method allows to perform operations on the movepool

        Parameters
        ----------
        other : Movepool
            Movepool to apply operations against
        method : Callable[ [frozenset[Moves], frozenset[Moves]], frozenset[Moves] ]
            Method to be used

        Returns
        -------
        Movepool
            Resulting movepool
        """
        level: dict[int, frozenset] = {}

        for index in set(self.level) | set(other.level):
            first = self.level.get(index, set())
            last = other.level.get(index, set())
            if data := method(first, last):
                level[index] = frozenset(data)

        return Movepool(
            level=frozendict(level),
            tm=method(self.tm, other.tm),
            egg=method(self.egg, other.egg),
            event=method(self.event, other.event),
            tutor=method(self.tutor, other.tutor),
            levelup=method(self.levelup, other.levelup),
            other=method(self.other, other.other),
        )

    def __add__(self, other: Movepool) -> Movepool:
        """Add method

        Parameters
        ----------
        other : Movepool
            Movepool to operate against

        Returns
        -------
        Movepool
            resulting movepool
        """
        return self.operator(other, method=lambda x, y: x | y)

    def __sub__(self, other: Movepool) -> Movepool:
        """Sub method

        Parameters
        ----------
        other : Movepool
            Movepool to operate against

        Returns
        -------
        Movepool
            resulting movepool
        """
        return self.operator(other, method=lambda x, y: x - y)

    def __xor__(self, other: Movepool) -> Movepool:
        """Xor method

        Parameters
        ----------
        other : Movepool
            Movepool to operate against

        Returns
        -------
        Movepool
            resulting movepool
        """
        return self.operator(other, method=lambda x, y: x ^ y)

    def __and__(self, other: Movepool) -> Movepool:
        """And method

        Parameters
        ----------
        other : Movepool
            Movepool to operate against

        Returns
        -------
        Movepool
            resulting movepool
        """
        return self.operator(other, method=lambda x, y: x & y)

    def __call__(self) -> list[Moves]:
        """Returns all moves that belong to this instance in alphabetical order.

        Returns
        -------
        list[Moves]
            List of moves that belong to this instance.
        """
        moves = set()
        for item in astuple(self):
            if isinstance(item, frozenset):
                moves.update(item)
            elif isinstance(item, frozendict):
                for level in item.values():
                    moves.update(level)
        moves = list(moves)
        moves.sort(key=lambda move: move.name)
        return moves

    def __contains__(self, item: Moves) -> bool:
        """Check if movepool contains a move.

        Parameters
        ----------
        item : Moves
            Moves to check

        Returns
        -------
        bool
            Wether included or not
        """
        return bool(item in self.__call__())

    def __setitem__(
        self,
        key: str,
        value: Union[set[Moves], dict[int, set[Moves]]],
    ):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : Union[frozenset[Moves], frozendict[int, frozenset[Moves]]]
            Values to set
        """
        if key == "level":
            if isinstance(value, dict):
                level = {}
                for key, value in value.items():
                    moves = set()
                    for item in value:
                        if data := Moves.fetch_by_name(item):
                            if not data.banned:
                                moves.add(item)
                    level[key] = frozenset(moves)
                self.level = frozendict(level)
        else:
            moves = set()
            for item in value:
                if data := Moves.fetch_by_name(item):
                    if not data.banned:
                        moves.add(item)

            moves = frozenset(moves)

            item = key.lower()

            if item == "tm":
                self.tm = moves
            elif item == "event":
                self.event = moves
            elif item == "tutor":
                self.tutor = moves
            elif item == "egg":
                self.egg = moves
            elif item in ["levelup", "level-up"]:
                self.levelup = moves
            else:
                self.other = moves

    def __getitem__(self, key: str):
        """Get method for movepool

        Parameters
        ----------
        key : str
            Parameter to obtain

        Returns
        -------
        Union[frozenset[Moves], frozendict[int, frozenset[Moves]]]
            Values that belong to the movepool

        Raises
        ------
        KeyError
            If the provided key is not found
        """
        item = key.lower()
        if item == "tm":
            return self.tm
        if item == "event":
            return self.event
        if item == "tutor":
            return self.tutor
        if item == "egg":
            return self.egg
        if item in ["levelup", "level-up"]:
            return self.levelup
        if item == "other":
            return self.other
        raise KeyError(key)

    @classmethod
    def from_dict(cls, **kwargs) -> Movepool:
        """Returns a Movepool which corresponds to the kwargs provided

        Returns
        -------
        Movepool
            Generated movepool
        """

        level = {k: frozenset(v) for k, v in kwargs.get("level", {}).items()}

        movepool = Movepool(level=frozendict(level))
        for item in ["tm", "event", "tutor", "egg", "levelup", "other"]:
            movepool[item] = frozenset(kwargs.get(item, set()))
        return movepool

    @property
    def level_moves(self) -> frozenset[Moves]:
        """Moves the pokemon can learn through level

        Returns
        -------
        frozenset[Moves]
            Frozenset out of level moves
        """
        moves: set[Moves] = set()
        for level in self.level.values():
            moves.update(level)
        return frozenset(moves)

    @classmethod
    async def fakemon_fetch(cls, connection: Connection, id: int) -> Movepool:
        """Obtains movepool out of a Fakemon ID

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        id : int
            fakemon's ID

        Returns
        -------
        Movepool
            resulting movepool
        """
        items: dict[str, Union[set[Moves], dict[int,
                                                set[Moves]]]] = dict(level={})
        async for item in connection.cursor(
                """--sql
                SELECT MOVE, METHOD
                FROM FAKEMON_MOVEPOOL
                WHERE FAKEMON = $1 AND METHOD != 'LEVEL';
                """,
                id,
        ):
            move, method = item["move"], item["method"]
            items.setdefault(method, set())
            items[method].add(Moves[move])

        async for item in connection.cursor(
                """--sql
                SELECT MOVE, LEVEL
                FROM FAKEMON_LEARNSET
                WHERE FAKEMON = $1;
                """,
                id,
        ):
            move, level = item["move"], item["level"]
            items["level"].setdefault(level, set())
            items["level"][level].add(Moves[move])

        return cls.from_dict(**items)

    async def upsert(self, connection: Connection, id: int) -> None:
        """Fakemon Upsert Method for Fakemons

        Parameters
        ----------
        connection : Connection
            asyncpg connection
        id : int
            Fakemon's ID
        """
        await connection.execute(
            """--sql
            DELETE FROM FAKEMON_MOVEPOOL
            WHERE FAKEMON = $1;
            """,
            id,
        )
        await connection.execute(
            """--sql
            DELETE FROM FAKEMON_LEARNSET
            WHERE FAKEMON = $1;
            """,
            id,
        )

        movepool_elements = []
        learnset_elements = []

        move_set = frozenset[Moves]
        data: dict[str, Union[move_set, frozendict[int, move_set]]] = {
            "LEVEL": self.level,
            "TM": self.tm,
            "EVENT": self.event,
            "TUTOR": self.tutor,
            "EGG": self.egg,
            "LEVEL-UP": self.levelup,
            "OTHER": self.other,
        }

        for key, value in data.items():

            if isinstance(value, frozendict):
                for level, values in value.items():
                    entries = ((id, m.name, level) for m in values
                               if not m.banned)
                    learnset_elements.extend(entries)
                    movepool_elements.extend(
                        (x, y, "LEVEL") for x, y, _ in entries)
            elif isinstance(value, frozenset):
                movepool_elements.extend(
                    (id, m.name, key) for m in value if not m.banned)

        if movepool_elements:
            await connection.executemany(
                """
                --sql
                INSERT INTO FAKEMON_MOVEPOOL(FAKEMON, MOVE, METHOD)
                VALUES ($1, $2, $3);
                """,
                movepool_elements,
            )
        if learnset_elements:
            await connection.executemany(
                """
                --sql
                INSERT INTO FAKEMON_LEARNSET(FAKEMON, MOVE, LEVEL)
                VALUES ($1, $2, $3);
                """,
                learnset_elements,
            )
