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

from dataclasses import dataclass
from enum import Enum
from re import split
from typing import Iterable, Optional

from src.utils.functions import fix


@dataclass(unsafe_hash=True)
class PronounItem:
    """This is the basic information a pronoun has.

    Attributes
    -----------
    image: Optional[str]
        image stored at Imagekit, defaults to None
    emoji: Optional[str]
        emoji that represents the pronoun, defaults to None
    role_id: Optional[int]
        discord role that represents the pronoun, defaults to None
    """

    image: Optional[str]
    emoji: str
    role_id: int


class Pronoun(PronounItem, Enum):
    """This is an enum class representing Pronouns

    Methods
    -------
    deduce(item: str)
        deduces the Pronoun based on the given string.
    """

    He = ("male_n8DIlBU0M.png", "\N{MALE SIGN}", 1178871573701214268)
    She = ("female_bdjGCkuKH.png", "\N{FEMALE SIGN}", 1178871770590216313)
    Them = (None, "\N{BLACK SQUARE BUTTON}", 1178871778584571934)

    @classmethod
    def deduce(cls, item: str) -> Pronoun:
        """This is a function that determines the Pronoun out of a given string.

        Parameters
        ----------
        item : str
            Pronoun string to identify

        Returns
        -------
        Pronoun
            Identified Pronoun

        Raises
        ------
        TypeError
            Raises if item is not a string
        """
        if isinstance(item, Pronoun):
            return item

        if not isinstance(item, str):
            if not isinstance(item, Iterable):
                name = item.__class__.__name__
                raise TypeError(f"Expected str but received {name!r} instead.")

            item = "/".join(map(str, item))

        match fix(item):
            case x if "THEM" in x or "THEIR" in x:
                return Pronoun.Them
            case x if "FEMALE" in x or "SHE" in x or "HER" in x or "HERS" in x:
                return Pronoun.She
            case x if "MALE" in x or "HE" in x or "HIM" in x or "HIS" in x:
                return Pronoun.He
            case _:
                return Pronoun.Them

    @classmethod
    def deduce_many(cls, *elems: str) -> frozenset[Pronoun]:
        items = {elem for elem in elems if isinstance(elem, cls)}
        if aux := ",".join(elem for elem in elems if isinstance(elem, str)):
            data = split(r"[^A-Za-z0-9 \.'-]", aux)
            items.update(x for elem in data if (x := cls.deduce(elem)))

        return frozenset(items)
