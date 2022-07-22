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
from typing import Any, Callable, Iterable, Optional

from frozendict import frozendict

from src.structures.move import Move
from src.utils.functions import fix

__all__ = ("Movepool", "MovepoolEncoder", "MovepoolDecoder")


@dataclass(unsafe_hash=True, repr=False, slots=True)
class Movepool:
    """
    Class which represents a movepool
    """

    level: frozendict[int, frozenset[Move]] = field(default_factory=frozendict)
    tm: frozenset[Move] = field(default_factory=frozenset)
    event: frozenset[Move] = field(default_factory=frozenset)
    tutor: frozenset[Move] = field(default_factory=frozenset)
    egg: frozenset[Move] = field(default_factory=frozenset)
    levelup: frozenset[Move] = field(default_factory=frozenset)
    other: frozenset[Move] = field(default_factory=frozenset)

    def __post_init__(self):
        self.level = frozendict({int(k): x for k, v in self.level.items() if (x := frozenset(v))})
        self.tm = frozenset(self.tm)
        self.event = frozenset(self.event)
        self.tutor = frozenset(self.tutor)
        self.egg = frozenset(self.egg)
        self.levelup = frozenset(self.levelup)
        self.other = frozenset(self.other)

    @classmethod
    def from_record(cls, item) -> Optional[Movepool]:
        if not item:
            return
        return cls.from_dict(
            level=item["level"],
            tm=item["tm"],
            event=item["event"],
            tutor=item["tutor"],
            egg=item["egg"],
            levelup=item["levelup"],
            other=item["other"],
        )

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
        method: Callable[[frozenset[Move], frozenset[Move]], frozenset[Move]],
    ) -> Movepool:
        """This method allows to perform operations on the movepool

        Parameters
        ----------
        other : Movepool
            Movepool to apply operations against
        method : Callable[[frozenset[Move], frozenset[Move]], frozenset[Move]]
            Method to be used

        Returns
        -------
        Movepool
            Resulting movepool
        """
        level: dict[int, frozenset[Move]] = {}

        for index in sorted(self.level | other.level):
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
        moves: set[Move] = set()
        for item in astuple(self):
            if isinstance(item, frozenset):
                moves.update(item)
            elif isinstance(item, frozendict):
                moves.update(*item.values())
        return sorted(moves, key=lambda x: x.name)

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

    def assign(self, key: str, value: Optional[str | set[Move] | dict[int, set[Move]]] = None):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : Optional[str | set[Move] | dict[int, set[Move]]]
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

        if key == "LEVEL" and isinstance(value := value or {}, dict):
            level: dict[int, set[Move]] = {}
            for key, value in value.items():
                key = str(key)
                if not key.isdigit():
                    continue

                moves = frozenset({data for item in value if (data := Move.deduce(item))})
                if (key := int(key)) != 0:
                    level[key] = moves
                else:
                    self.levelup |= moves
            self.level = frozendict(level)
        elif isinstance(value := value or set(), Iterable):
            moves = frozenset({data for item in value if (data := Move.deduce(item))})
            match key:
                case "LEVEL":
                    self.level.setdefault(1, frozenset())
                    self.level[1] |= moves
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

    def __setitem__(self, key: str, value: set[Move] | dict[int, set[Move]]):
        """Assigning method for movepool

        Parameters
        ----------
        key : str
            Element in specific to set
        value : set[Move] | frozendict[int, set[Move]]
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
        set[Move] | frozendict[int, set[Move]]
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
            return frozenset(items)

        level = {k: foo(v) for k, v in sorted(self.level.items())}

        level = {k: foo(v) for k, v in sorted(self.level.items())}

        return Movepool(
            level=frozendict(level),
            tm=foo(self.tm),
            event=foo(self.event),
            tutor=foo(self.event),
            egg=foo(self.egg),
            other=foo(self.other),
        )

    def add_level_moves(self, level: int, *moves: Move):
        aux = dict(self.level.setdefault(level, frozenset()))
        aux[level] |= frozenset(moves)
        self.level = frozendict(aux)

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
    def db_dict(self) -> dict[str, list[str] | dict[str, list[str]]]:
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
            level={str(k): foo(v) for k, v in sorted(self.level.items()) if v},
            egg=foo(self.egg),
            event=foo(self.event),
            tm=foo(self.tm),
            tutor=foo(self.tutor),
            levelup=foo(self.levelup),
            other=foo(self.other),
        )

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
    def level_moves(self):
        """Moves the pokemon can learn through level

        Returns
        -------
        frozenset[Move]
            Frozenset out of level moves
        """
        moves: set[Move] = set()
        moves.update(*self.level.values())
        return frozenset(moves)

    def copy(self):
        return Movepool() + self


class MovepoolEncoder(JSONEncoder):
    """Movepool encoder"""

    def default(self, o):
        if isinstance(o, Movepool):
            return o.as_dict
        return super(MovepoolEncoder, self).default(o)


class MovepoolDecoder(JSONDecoder):
    """Movepool decoder"""

    def __init__(self, *args, **kwargs):
        super(MovepoolDecoder, self).__init__(object_hook=self.object_hook, *args, **kwargs)

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
