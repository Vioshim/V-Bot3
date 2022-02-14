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

from dataclasses import astuple, dataclass, field
from json import JSONDecoder, JSONEncoder
from typing import Any, Callable, Iterable, Union

from asyncpg.connection import Connection
from frozendict import frozendict

from src.structures.move import Move
from src.utils.functions import fix

__all__ = (
    "Movepool",
    "MovepoolEncoder",
    "MovepoolDecoder",
)

move_set = set[Move]
frozen_set = frozenset[Move]
move_dict = dict[int, move_set]
frozen_dict = frozendict[int, frozen_set]


@dataclass(unsafe_hash=True, repr=False, slots=True)
class Movepool:
    """
    Class which represents a movepool
    """

    level: frozen_dict = field(default_factory=frozen_dict)
    tm: frozen_set = field(default_factory=frozen_set)
    event: frozen_set = field(default_factory=frozen_set)
    tutor: frozen_set = field(default_factory=frozen_set)
    egg: frozen_set = field(default_factory=frozen_set)
    levelup: frozen_set = field(default_factory=frozen_set)
    other: frozen_set = field(default_factory=frozen_set)

    def __post_init__(self):
        self.level = frozen_dict(
            {k: frozen_set(v) for k, v in self.level.items()}
        )
        self.tm = frozen_set(self.tm)
        self.event = frozen_set(self.event)
        self.tutor = frozen_set(self.tutor)
        self.egg = frozen_set(self.egg)
        self.levelup = frozen_set(self.levelup)
        self.other = frozen_set(self.other)

    def __repr__(self) -> str:
        """Repr Method

        Returns
        -------
        str
            repr
        """
        elements = dict(
            level=len(self.level_moves),
            tm=len(self.tm),
            event=len(self.event),
            tutor=len(self.tutor),
            egg=len(self.egg),
            levelup=len(self.levelup),
            other=len(self.other),
        )
        data = ", ".join(f"{k}={v}" for k, v in elements.items() if v)
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
        method: Callable[[frozen_set, frozen_set], frozen_set],
    ) -> Movepool:
        """This method allows to perform operations on the movepool

        Parameters
        ----------
        other : Movepool
            Movepool to apply operations against
        method : Callable[ [frozen_set, frozen_set], frozen_set ]
            Method to be used

        Returns
        -------
        Movepool
            Resulting movepool
        """
        level: frozen_dict = {}

        level_indexes: list[int] = list(self.level | other.level)
        level_indexes.sort()

        for index in level_indexes:
            first = self.level.get(index, set())
            last = other.level.get(index, set())
            if data := method(first, last):
                level[index] = frozen_set(data)

        return Movepool(
            level=frozen_dict(level),
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

    def __call__(self) -> list[Move]:
        """Returns all moves that belong to this instance in alphabetical order.

        Returns
        -------
        list[Move]
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
        moves.sort(key=str)
        return moves

    def __contains__(self, item: Move) -> bool:
        """Check if movepool contains a move.

        Parameters
        ----------
        item : Move
            Move to check

        Returns
        -------
        bool
            Wether included or not
        """
        return bool(item in self.__call__())

    def __setitem__(
        self,
        key: str,
        value: Union[set[Move], dict[int, set[Move]]],
    ):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : Union[move_set, frozendict[int, move_set]]
            Values to set
        """
        key = fix(key)

        if key == "LEVEL":
            if isinstance(value, dict):
                level: move_dict = {}
                for key, value in value.items():
                    key = str(key)
                    if not key.isdigit():
                        continue

                    moves = move_set()
                    for item in value:
                        if data := Move.deduce(item):
                            if not data.banned:
                                moves.add(data)
                    level[int(key)] = frozen_set(moves)
                self.level = frozen_dict(level)
        else:
            moves = move_set()
            for item in value:
                if data := Move.deduce(item):
                    if not data.banned:
                        moves.add(data)

            moves = frozen_set(moves)

            match key:
                case "TM":
                    self.tm = moves
                case "EVENT":
                    self.event = moves
                case "TUTOR":
                    self.tutor = moves
                case "EGG":
                    self.egg = moves
                case "LEVELUP":
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
        Union[move_set, frozendict[int, move_set]]
            Values that belong to the movepool

        Raises
        ------
        KeyError
            If the provided key is not found
        """
        match fix(key):
            case "LEVEL":
                return self.level_moves
            case "TM":
                return self.tm
            case "EVENT":
                return self.event
            case "TUTOR":
                return self.tutor
            case "EGG":
                return self.egg
            case "LEVELUP":
                return self.levelup
            case "OTHER":
                return self.other
            case _:
                raise KeyError(key)

    def without_moves(self, to_remove: Iterable[Move] | Movepool) -> Movepool:
        """This function returns a copy of the movepool without specific moves

        Parameters
        ----------
        to_remove : Iterable[Move] | Movepool
            moves to remove

        Returns
        -------
        Movepool
            resulting movepool
        """

        total_remove = to_remove

        if isinstance(to_remove, Movepool):
            total_remove = total_remove()

        def foo(moves: Iterable[Move]):
            items = sorted(move for move in moves if move not in total_remove)
            return frozen_set(items)

        return Movepool(
            level=frozen_dict(
                {
                    k: entry
                    for k, v in sorted(self.level.items())
                    if (entry := foo(v))
                }
            ),
            tm=foo(self.tm),
            event=foo(self.event),
            tutor=foo(self.event),
            egg=foo(self.egg),
            other=foo(self.other),
        )

    @classmethod
    def from_dict(cls, **kwargs) -> Movepool:
        """Returns a Movepool which corresponds to the kwargs provided

        Returns
        -------
        Movepool
            Generated movepool
        """
        movepool = Movepool()
        for item in movepool.__slots__:
            movepool[item] = kwargs.get(item, {} if item == "level" else set())
        return movepool

    @property
    def as_dict(self) -> dict[str, list[str] | dict[int, list[str]]]:
        """Returns a Movepool as dict with moves as strings

        Returns
        -------
        dict[str, list[str] | dict[int, list[str]]]
            generated values
        """

        def foo(moves: frozenset[Move]) -> list[str]:
            """Inner method for conversion

            Parameters
            ----------
            moves : frozenset[Move]
                moves to convert

            Returns
            -------
            list[str]
                List of move IDs
            """
            return sorted(move.id for move in moves)

        return dict(
            level={k: foo(v) for k, v in sorted(self.level.items())},
            egg=foo(self.egg),
            event=foo(self.event),
            tm=foo(self.tm),
            tutor=foo(self.tutor),
            levelup=foo(self.levelup),
            other=foo(self.other),
        )

    @property
    def as_display_dict(self) -> dict[str, list[str] | dict[int, list[str]]]:
        """Returns a Movepool as dict with moves as strings

        Returns
        -------
        dict[str, list[str] | dict[int, list[str]]]
            generated values
        """

        def foo(moves: frozenset[Move]) -> list[str]:
            """Inner method for conversion

            Parameters
            ----------
            moves : frozenset[Move]
                moves to convert

            Returns
            -------
            list[str]
                List of move Names
            """
            return sorted(move.name for move in moves)

        return dict(
            level={k: foo(v) for k, v in sorted(self.level.items())},
            egg=foo(self.egg),
            event=foo(self.event),
            tm=foo(self.tm),
            tutor=foo(self.tutor),
            levelup=foo(self.levelup),
            other=foo(self.other),
        )

    @property
    def level_moves(self) -> move_set:
        """Moves the pokemon can learn through level

        Returns
        -------
        move_set
            Frozenset out of level moves
        """
        moves: set[Move] = set()
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
        item_set = set[Move]
        level_set = dict[str, item_set]
        items = dict(
            level=level_set(),
            egg=item_set(),
            event=item_set(),
            tm=item_set(),
            tutor=item_set(),
            levelup=item_set(),
            other=item_set(),
        )
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
            items[method].add(Move.from_ID(move))

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
            items["level"][level].add(Move.from_ID(move))

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

        data = dict(
            TM=self.tm,
            EVENT=self.event,
            TUTOR=self.tutor,
            EGG=self.egg,
            LEVELUP=self.levelup,
            OTHER=self.other,
        )

        for level, values in self.level.items():
            learnset_elements.extend(
                (
                    id,
                    m.id,
                    level,
                )
                for m in values
                if not m.banned
            )

        for key, value in data.items():
            movepool_elements.extend(
                (
                    id,
                    m.id,
                    key,
                )
                for m in value
                if not m.banned
            )

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


class MovepoolEncoder(JSONEncoder):
    """Movepool encoder"""

    def default(self, o):
        if isinstance(o, Movepool):
            data = {}
            for item in o.__slots__:
                if isinstance(element := o[item], frozendict):
                    data[item] = {
                        k: sorted(map(lambda x: x.id, v))
                        for k, v in element.items()
                    }
                elif isinstance(element, frozenset):
                    data[item] = sorted(map(lambda x: x.id, element))
            return data
        return super(MovepoolEncoder, self).default(o)


class MovepoolDecoder(JSONDecoder):
    """Movepool decoder"""

    def __init__(self, *args, **kwargs):
        super(MovepoolDecoder, self).__init__(
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
        if any(i in dct for i in Movepool.__slots__):
            return Movepool.from_dict(**dct)
        return dct
