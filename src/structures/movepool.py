#  Copyright 2021 Vioshim
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import annotations

from dataclasses import asdict, astuple, dataclass, field
from typing import Callable

from asyncpg.connection import Connection
from frozendict import frozendict

from src.enums.moves import Moves

__all__ = ("Movepool",)


# noinspection PyArgumentList
@dataclass(unsafe_hash=True, repr=False, slots=True)
class Movepool:
    """
    Class which represents a movepool
    """

    level: frozendict[int, frozenset[Moves]] = field(default_factory=frozendict)
    tm: frozenset[Moves] = field(default_factory=frozenset)
    event: frozenset[Moves] = field(default_factory=frozenset)
    tutor: frozenset[Moves] = field(default_factory=frozenset)
    egg: frozenset[Moves] = field(default_factory=frozenset)
    levelup: frozenset[Moves] = field(default_factory=frozenset)
    other: frozenset[Moves] = field(default_factory=frozenset)

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
            method: Callable[[frozenset[Moves], frozenset[Moves]], frozenset[Moves]],
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
        level: dict[int, frozenset] = dict()

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
            value: set[Moves] | dict[int, set[Moves]],
    ):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : frozenset[Moves] | frozendict[int, frozenset[Moves]]
            Values to set
        """
        if key == "level":
            if isinstance(value, dict):
                level = dict()
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

            match key.lower():
                case "tm":
                    self.tm = moves
                case "event":
                    self.event = moves
                case "tutor":
                    self.tutor = moves
                case "egg":
                    self.egg = moves
                case "levelup" | "level-up":
                    self.levelup = moves
                case _:
                    self.other = moves

    def __getitem__(self, key: str):
        """Get method for movepool

        Parameters
        ----------
        key : str
            Parameter to obtain

        Returns
        -------
        frozenset[Moves] | frozendict[int, frozenset[Moves]]
            Values that belong to the movepool

        Raises
        ------
        KeyError
            If the provided key is not found
        """
        match key.lower():
            case "level":
                return self.level
            case "tm":
                return self.tm
            case "event":
                return self.event
            case "tutor":
                return self.tutor
            case "egg":
                return self.egg
            case "levelup" | "level-up":
                return self.levelup
            case "other":
                return self.other
            case _:
                raise KeyError(key)

    @classmethod
    def from_dict(cls, **kwargs) -> Movepool:
        """Returns a Movepool which corresponds to the kwargs provided

        Returns
        -------
        Movepool
            Generated movepool
        """

        movepool = Movepool()
        for item in cls.__slots__:
            movepool[item] = kwargs.get(item, set())
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
        items: dict[str, set[Moves] | dict[int, set[Moves]]] = dict(level={})
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

        for key, value in asdict(self).items():

            if key == "levelup":
                key = "level-up"

            movepool_elements.extend((id, key, m.id) for m in value if not m.banned)

            if isinstance(value, dict):
                for level, values in self.level.items():
                    learnset_elements.extend((id, m.id, level) for m in values if not m.banned)

        if learnset_elements:
            await connection.executemany(
                """
                --sql
                INSERT INTO FAKEMON_LEARNSET(FAKEMON, MOVE, LEVEL)
                VALUES ($1, $2, $3);
                """,
                learnset_elements,
            )
        if movepool_elements:
            await connection.executemany(
                """
                --sql
                INSERT INTO FAKEMON_MOVEPOOL(FAKEMON, METHOD, MOVE)
                VALUES ($1, $2, $3);
                """,
                movepool_elements,
            )
