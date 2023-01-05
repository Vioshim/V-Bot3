# Copyright 2023 Vioshim
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

import functools
import itertools
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from discord import Embed
from discord.utils import snowflake_time, utcnow

CLYDE = re.compile(r"(c)(lyde)", re.IGNORECASE)


@dataclass(slots=True)
class ProxyExtra:
    name: str = ""  # May not have name, therefore use same
    image: str = ""  # May not have image, therefore use same
    prefixes: frozenset[tuple[str, str]] = field(default_factory=frozenset)  # Specific prefixes

    def append_prefixes(self, *prefixes: tuple[str, str]):
        self.prefixes = self.prefixes.union(prefixes)

    def append_prefix(self, a: str, b: str):
        return self.append_prefixes((a, b))

    def remove_prefixes(self, *prefixes: tuple[str, str]):
        self.prefixes = self.prefixes.difference(prefixes)

    def remove_prefix(self, a: str, b: str):
        return self.remove_prefixes((a, b))

    def to_dict(self):
        return dict(
            name=self.name,
            image=self.image,
            prefixes=sorted(self.prefixes),
        )

    @classmethod
    def handle(cls, item: dict[str, Any] | ProxyExtra):
        if isinstance(item, cls):
            return item
        return cls(**item)

    def copy(self):
        return ProxyExtra(name=self.name, image=self.image, prefixes=self.prefixes.copy())

    @property
    def embed(self):
        embed = Embed(title=self.name)
        for index, (k, v) in enumerate(self.prefixes, start=1):
            embed.add_field(name=f"Prefix {index}", value=f"{k}text{v}")
        if self.image and isinstance(self.image, str):
            embed.set_image(url=self.image)
        return embed


@dataclass(slots=True)
class Proxy:
    id: int = 0
    author: int = 0
    server: int = 719343092963999804
    name: str = ""  # max 80 Characters
    image: Optional[str] = None
    extras: list[ProxyExtra] = field(default_factory=list)  # Specific Images
    prefixes: frozenset[tuple[str, str]] = field(default_factory=frozenset)  # Specific prefixes

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Proxy) and self.id == o.id

    def __ne__(self, o: object) -> bool:
        return isinstance(o, Proxy) and self.id != o.id

    def __hash__(self) -> int:
        return self.id >> 22

    def __post_init__(self):
        self.prefixes = frozenset(self.prefixes)
        self.extras = sorted(map(ProxyExtra.handle, self.extras), key=lambda x: x.name)

    def to_dict(self):
        return dict(
            id=self.id,
            author=self.author,
            server=self.server,
            name=self.name,
            image=self.image,
            extras=[x.to_dict() for x in sorted(self.extras, key=lambda x: x.name)],
            prefixes=sorted(self.prefixes),
        )

    def append_extra(self, name: str, image: Optional[str], prefixes: frozenset[tuple[str, str]] = None):
        if name != self.name:
            prefixes = prefixes or frozenset()
            image = image or self.image
            self.extras.append(ProxyExtra(name=name, image=image, prefixes=prefixes))

    def append_prefixes(self, *prefixes: tuple[str, str]):
        self.prefixes = self.prefixes.union(prefixes)

    def append_prefix(self, a: str, b: str):
        return self.append_prefixes((a, b))

    def remove_prefixes(self, *prefixes: tuple[str, str]):
        self.prefixes = self.prefixes.difference(prefixes)

    def remove_prefix(self, a: str, b: str):
        return self.remove_prefixes((a, b))

    @property
    def embed(self):
        embed = Embed(title=self.name, timestamp=self.created_at)
        for index, (k, v) in enumerate(self.prefixes, start=1):
            embed.add_field(name=f"Prefix {index}", value=f"{k}text{v}")
        if self.image and isinstance(self.image, str):
            embed.set_image(url=self.image)
        if self.extras:
            embed.set_footer(text=f"{len(self.extras)} Extras")
        return embed

    def copy(self):
        return Proxy(
            id=self.id,
            author=self.author,
            server=self.server,
            name=self.name,
            image=self.image,
            extras=map(ProxyExtra.copy, self.extras),
            prefixes=self.prefixes.copy(),
        )

    @staticmethod
    def prefix_handle(text: str = "", prefix_a: str = "", prefix_b: str = ""):
        if "text" in text:
            prefixes = text.split("text")
            prefix_a, prefix_b = (text, "") if len(prefixes) <= 1 else prefixes[0], prefixes[-1]
        return prefix_a, prefix_b

    def prefix_lookup(self, prefix_a: str = "", prefix_b: str = "") -> Optional[Proxy | ProxyExtra]:
        if not (prefix_a or prefix_b):
            return

        for k, v in self.prefixes:
            if k.startswith(prefix_a) and v.endswith(prefix_b):
                return self

        for item in self.extras:
            for k, v in item.prefixes:
                if k.startswith(prefix_a) and v.endswith(prefix_b):
                    return item

    def prefix_lookup_handle(self, text: str) -> Optional[Proxy | ProxyExtra]:
        return self.prefix_lookup(*self.prefix_handle(text))

    @classmethod
    def prefix_lookup_handle_many(cls, items: list[Proxy], text: str) -> Optional[Proxy | ProxyExtra]:
        a, b = cls.prefix_handle(text)
        for item in items:
            if aux := item.prefix_lookup(a, b):
                return aux

    def text_prefix_lookup(self, text: str, strip: bool = True) -> Optional[tuple[Proxy | ProxyExtra, str]]:
        if not text:
            return

        for k, v in self.prefixes:
            if text.startswith(k) and text.endswith(v):
                text = text.removeprefix(k).removesuffix(v)
                if strip:
                    text = text.strip()
                return self, text

        for item in self.extras:
            for k, v in item.prefixes:
                if text.startswith(k) and text.endswith(v):
                    if not item.name:
                        item.name = self.name
                    if not item.image:
                        item.image = self.image
                    text = text.removeprefix(k).removesuffix(v)
                    if strip:
                        text = text.strip()
                    return item, text

    @staticmethod
    def first_lookup(items: list[Proxy], text: str, strip: bool = True):
        for x in items:
            if aux := x.text_prefix_lookup(text, strip=strip):
                return aux

    @classmethod
    def lookup(cls, items: list[Proxy], text: str):
        current = None
        values: list[tuple[Proxy | ProxyExtra, str]] = []

        for paragraph in text.split("\n"):
            if aux := cls.first_lookup(items, paragraph, strip=False):
                proxy, paragraph = aux
                values.append(aux)
                current = proxy
            elif current:
                item = current, paragraph
                values.append(item)
            else:
                break

        proxy_msgs: list[tuple[Proxy | ProxyExtra, str]] = []
        for key, paragraphs in itertools.groupby(values, key=lambda x: x[0]):
            entry = functools.reduce(lambda x, y: f"{x}\n{y}", map(lambda z: z[1], paragraphs))
            proxy_msgs.append((key, entry.strip()))

        if not proxy_msgs and (aux := cls.first_lookup(items, text)):
            proxy_msgs.append(aux)

        return [
            aux if proxy is None and (aux := cls.first_lookup(items, paragraph)) else (proxy, paragraph)
            for proxy, paragraph in proxy_msgs
        ]

    @classmethod
    def from_mongo_dict(cls, dct: dict[str, Any]):
        dct.pop("_id", None)
        return cls(**dct)

    @staticmethod
    def clyde(text: str):
        return CLYDE.sub("\\1\u200a\\2", text)

    @property
    def display_name(self):
        return self.clyde(self.name)

    @staticmethod
    def alternate(text: str):
        a, b = text[:1], text[1:]
        return f"{a}\u200a{b}"

    @property
    def alternative_name(self):
        return self.alternate(self.display_name)

    @property
    def created_at(self):
        return snowflake_time(self.id) if self.id else utcnow()
