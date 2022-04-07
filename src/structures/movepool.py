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
move_dict = dict[int, set[Move]]
frozen_dict = frozendict[int, frozenset[Move]]


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
        self.level = frozen_dict({k: frozen_set(v) for k, v in self.level.items()})
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

    def methods_for(self, move: Move):
        elements = dict(
            level=move in self.level_moves,
            tm=move in self.tm,
            event=move in self.event,
            tutor=move in self.tutor,
            egg=move in self.egg,
            levelup=move in self.levelup,
            other=move in self.other,
        )
        return [k for k, v in elements.items() if v]

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

    def __eq__(self, other: Movepool) -> bool:
        if isinstance(other, Movepool):
            return astuple(self) == astuple(other)
        return NotImplemented

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

    def __radd__(self, other: Movepool) -> Movepool:
        """Recursive Add method

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

    def assign(
        self,
        key: str,
        value: Union[str, set[Move], dict[int, set[Move]]] = None,
    ):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : Union[str, move_set, frozendict[int, move_set]]
            Values to set
        """
        key = fix(key)

        if isinstance(value, str):
            if key == "LEVEL":
                aux = {}
                for part in value.split("\n"):
                    try:
                        index, items = part.split(": ")
                        aux[index] = items.split(",")
                    except ValueError:
                        continue
                value = aux
            else:
                value = value.split(",")

        if key == "LEVEL":
            if isinstance(value := value or {}, dict):
                level: move_dict = {}
                for key, value in value.items():
                    key = str(key)
                    if not key.isdigit():
                        continue

                    moves = move_set()
                    for item in value:
                        if data := Move.deduce(item):
                            moves.add(data)
                    if (key := int(key)) != 0:
                        level[key] = frozen_set(moves)
                    else:
                        self.levelup |= frozen_set(moves)
                self.level = frozen_dict(level)
        elif isinstance(value := value or set(), Iterable):
            moves = move_set()
            for item in value:
                if data := Move.deduce(item):
                    moves.add(data)

            moves = frozen_set(moves)

            match key:
                case "TM":
                    self.tm |= moves
                case "EVENT":
                    self.event |= moves
                case "TUTOR":
                    self.tutor |= moves
                case "EGG":
                    self.egg |= moves
                case "LEVELUP":
                    self.levelup |= moves
                case _:
                    self.other |= moves

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
        self.assign(key, value)

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
            data = filter(lambda x: x not in total_remove, moves)
            items = sorted(data, key=lambda x: x.name)
            return frozen_set(items)

        return Movepool(
            level=frozen_dict(
                {k: entry for k, v in sorted(self.level.items()) if (entry := foo(v))}
            ),
            tm=foo(self.tm),
            event=foo(self.event),
            tutor=foo(self.event),
            egg=foo(self.egg),
            other=foo(self.other),
        )

    def add_level_moves(self, level: int, *moves: Move):
        aux = self.level.setdefault(level, frozen_set())
        aux = dict(aux) | {level: frozen_set(moves)}
        self.level = frozen_dict(aux)

    def remove_level_moves(self, level: int, *moves: Move):
        if total := self.level.get(level, set()) - frozenset(moves):
            self.level[level] = total
        else:
            self.level.pop(level, None)

    @classmethod
    def from_dict(cls, **kwargs) -> Movepool:
        """Returns a Movepool which corresponds to the kwargs provided

        Returns
        -------
        Movepool
            Generated movepool
        """
        movepool = cls()
        for item in movepool.__slots__:
            if value := kwargs.get(item):
                movepool.assign(key=item, value=value)
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

        elements = dict(
            level={k: foo(v) for k, v in sorted(self.level.items()) if v},
            egg=foo(self.egg),
            event=foo(self.event),
            tm=foo(self.tm),
            tutor=foo(self.tutor),
            levelup=foo(self.levelup),
            other=foo(self.other),
        )

        return {k: v for k, v in elements.items() if v}

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

        elements = dict(
            level={k: foo(v) for k, v in sorted(self.level.items()) if v},
            egg=foo(self.egg),
            event=foo(self.event),
            tm=foo(self.tm),
            tutor=foo(self.tutor),
            levelup=foo(self.levelup),
            other=foo(self.other),
        )

        return {k: v for k, v in elements.items() if v}

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


class MovepoolEncoder(JSONEncoder):
    """Movepool encoder"""

    def default(self, o):
        if isinstance(o, Movepool):
            return o.as_dict
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
        if set(dct).issubsset(Movepool.__slots__):
            return Movepool.from_dict(**dct)
        return dct
