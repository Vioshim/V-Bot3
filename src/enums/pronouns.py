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

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass(unsafe_hash=True, slots=True)
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

    image: Optional[str] = None
    emoji: Optional[str] = None
    role_id: Optional[int] = None


class Pronoun(Enum):
    """This is an enum class representing Pronouns

    Attributes
    -----------
    image: Optional[str]
        image stored at Imagekit, defaults to None
    emoji: Optional[str]
        emoji that represents the pronoun, defaults to None
    role_id: Optional[int]
        discord role that represents the pronoun, defaults to None

    Methods
    -------
    deduce(item: str)
        deduces the Pronoun based on the given string.
    """

    He = PronounItem(image="male_n8DIlBU0M.png", emoji="\N{MALE SIGN}", role_id=738230651840626708)
    She = PronounItem(
        image="female_bdjGCkuKH.png", emoji="\N{FEMALE SIGN}", role_id=738230653916807199
    )
    Them = PronounItem(role_id=874721683381030973)

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
            name = item.__class__.__name__
            raise TypeError(f"Expected str but received {name} instead.")

        match item.lower():
            case x if "them" in x:
                return Pronoun.Them
            case x if "female" in x or "she" in x:
                return Pronoun.She
            case x if "male" in x or "he" in x:
                return Pronoun.He
            case _:
                return Pronoun.Them

    @property
    def emoji(self) -> Optional[str]:
        return self.value.emoji

    @property
    def image(self) -> Optional[str]:
        return self.value.image

    @property
    def role_id(self) -> Optional[int]:
        return self.value.role_id
