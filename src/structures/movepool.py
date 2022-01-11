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

from dataclasses import asdict, astuple, dataclass, field
from json import JSONDecoder, JSONEncoder
from typing import Any, Callable, Iterable, Union

from asyncpg.connection import Connection
from frozendict import frozendict

from src.structures.move import Move

__all__ = (
    "Movepool",
    "MovepoolEncoder",
    "MovepoolDecoder",
)

move_set = frozenset[Move]


@dataclass(unsafe_hash=True, repr=False, slots=True)
class Movepool:
    """
    Class which represents a movepool
    """

    level: frozendict[int, move_set] = field(default_factory=frozendict)
    tm: move_set = field(default_factory=frozenset)
    event: move_set = field(default_factory=frozenset)
    tutor: move_set = field(default_factory=frozenset)
    egg: move_set = field(default_factory=frozenset)
    levelup: move_set = field(default_factory=frozenset)
    other: move_set = field(default_factory=frozenset)

    def __post_init__(self):
        self.level = frozendict(
            {k: frozenset(v) for k, v in self.level.items()}
        )
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
        method: Callable[[move_set, move_set], move_set],
    ) -> Movepool:
        """This method allows to perform operations on the movepool

        Parameters
        ----------
        other : Movepool
            Movepool to apply operations against
        method : Callable[ [move_set, move_set], move_set ]
            Method to be used

        Returns
        -------
        Movepool
            Resulting movepool
        """
        level: dict[int, frozenset] = {}

        level_indexes: list[int] = list(self.level | other.level)
        level_indexes.sort()

        for index in level_indexes:
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
        if key == "level":
            if isinstance(value, dict):
                level = {}
                for key, value in value.items():
                    key = str(key)
                    if not key.isdigit():
                        continue

                    moves = set()
                    for item in value:
                        if data := Move.deduce(item):
                            if not data.banned:
                                moves.add(data)
                    level[int(key)] = frozenset(moves)
                self.level = frozendict(level)
        else:
            moves = set()
            for item in value:
                if data := Move.deduce(item):
                    if not data.banned:
                        moves.add(data)

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
        Union[move_set, frozendict[int, move_set]]
            Values that belong to the movepool

        Raises
        ------
        KeyError
            If the provided key is not found
        """
        match key.lower():
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

        return Movepool(
            level=frozendict(
                {
                    k: entry
                    for k, v in self.level.items()
                    if (
                        entry := frozenset(
                            {x for x in v if x not in total_remove}
                        )
                    )
                }
            ),
            tm=frozenset({x for x in self.tm if x not in total_remove}),
            event=frozenset({x for x in self.event if x not in total_remove}),
            tutor=frozenset({x for x in self.tutor if x not in total_remove}),
            egg=frozenset({x for x in self.egg if x not in total_remove}),
            other=frozenset({x for x in self.other if x not in total_remove}),
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
            default = {} if item == "level" else set()
            movepool[item] = kwargs.get(item, default)
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
            return [move.id for move in moves]

        return dict(
            level={k: foo(v) for k, v in self.level.items()},
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
        items = dict(level={})
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

        data = {
            "TM": self.tm,
            "EVENT": self.event,
            "TUTOR": self.tutor,
            "EGG": self.egg,
            "LEVEL-UP": self.levelup,
            "OTHER": self.other,
        }

        for level, values in self.level.items():
            learnset_elements.extend(
                (
                    id,
                    m.name,
                    level,
                )
                for m in values
                if not m.banned
            )

        for key, value in data.items():
            movepool_elements.extend(
                (
                    id,
                    m.name,
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
