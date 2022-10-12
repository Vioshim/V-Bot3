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

from os import urandom
from typing import Mapping

from frozendict import frozendict


class Item:
    def __init__(
        self,
        name: str = "",
        description: str = "",
        weight: float = 0.0,
        crafting: Mapping["Item", int] = None,
        contents: Mapping["Item", int] = None,
    ) -> None:
        self.id = urandom(16).hex()
        self.name = name or "Unknown"
        self.description = description
        self.weight = weight
        self.crafting: frozendict[Item, int] = frozendict(crafting or {})
        self.contents: frozendict[Item, int] = frozendict(contents or {})

    def __hash__(self) -> int:
        return hash(self.id or "")

    def __eq__(self, item: Item) -> bool:
        return isinstance(item, Item) and self.id == item.id
