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

from typing import Any, Optional

from discord import Embed, Interaction
from discord.app_commands import Choice, Transform, Transformer

from src.structures.bot import CustomBot

__all__ = ("WikiEntry", "WikiTreeArg", "WikiNodeArg")


class WikiEntry:
    def __init__(
        self,
        path: str = None,
        content: Optional[str] = None,
        embeds: list[Embed] = None,
    ) -> None:

        if not embeds:
            embeds = []

        self.path = path or ""
        self.content = content
        self.embeds = [Embed.from_dict(x) if isinstance(x, dict) else x for x in embeds]
        self.children: dict[str, WikiEntry] = {}
        self.parent: Optional[WikiEntry] = None

    def __str__(self, level: int = 0) -> str:
        path = "/" + self.path
        ret = f"Wiki({path!r}, embeds={len(self.embeds)})\n"
        if level:
            ret = f"{'--' * level} {ret}"
        return ret + "".join(child.__str__(level + 1) for child in self.children.values())

    def __repr__(self) -> str:
        return f"WikiEntry(nodes={len(self.children)})"

    @property
    def route(self) -> str:
        entries = [self.path]
        aux = self
        while isinstance(aux.parent, WikiEntry):
            entries.append(aux.parent.path)
            aux = aux.parent
        return "/".join(entries[::-1])

    @property
    def simplified(self):
        return {
            "path": self.path,
            "content": self.content,
            "embeds": [x.to_dict() for x in self.embeds],
        }

    def printTree(
        self,
        root: Optional[WikiEntry] = None,
        markerStr="+-",
        levelMarkers: list[bool] = None,
    ):
        if not root:
            root = self
        levelMarkers = levelMarkers or []
        placeholder = " " * len(levelMarkers)
        connection = "|" + placeholder[:-1]
        level = len(levelMarkers)
        markers = "".join(map(lambda x: connection if x else placeholder, levelMarkers[:-1]))
        markers += markerStr if level > 0 else ""
        print(f"{markers}{root.path}")
        for i, child in enumerate(root.children):
            isLast = i == len(root.children) - 1
            self.printTree(child, markerStr, [*levelMarkers, not isLast])

    def lookup(self, foo: str, strict: bool = False) -> Optional[WikiEntry]:
        current = self
        for item in foo.split("/"):
            if item == "..":
                current = current.parent
            elif current and (value := current.children.get(item)):
                current = value
            elif strict:
                return None
            else:
                break
        return current or self

    def add_node_params(
        self,
        path: str = None,
        content: Optional[str] = None,
        embeds: list[Embed] = None,
    ):
        self.add_node(WikiEntry(path, content, embeds))

    def add_node(self, node: WikiEntry | list[str] | str | dict[str, Any]):
        if isinstance(node, list):
            node = "/".join(node)
        if isinstance(node, str):
            node = WikiEntry(path=node)
        if isinstance(node, dict):
            node.pop("_id", None)
            node = WikiEntry(**node)

        aux = self
        path = node.path.removeprefix("/")

        route = [x for x in node.path.split("/") if x]
        ref_route = dict(enumerate(route))

        for idx, item in enumerate(route):
            if item in aux.children:
                ref_route.pop(idx, None)
                aux = aux.children[item]
                path = path.removeprefix(item).removeprefix("/")

        route = list(ref_route.values())
        if elements := [x for x in path.removeprefix(aux.path).split("/") if x]:
            for index in range(len(elements)):
                if elements[: index + 1] == route:
                    ref = node
                else:
                    ref = WikiEntry()
                ref.path = elements[index]
                ref.parent = aux
                aux.children[elements[index]] = aux = ref
        else:
            aux.embeds = node.embeds

    def remove_node_params(self, path: str):
        aux = self
        for item in path.split("/"):
            if item in aux.children:
                aux = aux.children[item]
                path = path.removeprefix(item).removeprefix("/")

        if not [x for x in path.removeprefix(aux.path).split("/") if x]:
            del aux.parent.children[aux.path]

    def remove_node(self, node: WikiEntry | list[str] | str | dict[str, Any]):
        if isinstance(node, dict):
            node = node["path"]
        if isinstance(node, list):
            node = "/".join(node)
        if isinstance(node, WikiEntry):
            node = node.path

        self.remove_node_params(node)

    @classmethod
    def from_list(cls, nodes: list[WikiEntry]):
        result = cls()
        for item in nodes:
            result.add_node(item)
        return result

    def __getitem__(self, item: str) -> WikiEntry:
        return self.children[item]

    def __delitem__(self, item: str) -> None:
        del self.children[item]

    def __setitem__(self, key: str, value: WikiEntry):
        self.children[key] = value


class WikiTransformer(Transformer):
    @classmethod
    async def transform(cls, ctx: Interaction, value: str):
        bot: CustomBot = ctx.client
        entries = await bot.mongo_db("Wiki").find({}).to_list(length=None)
        tree = WikiEntry.from_list(entries)
        return tree.lookup(value.removeprefix("/"))


class WikiTreeTransformer(WikiTransformer):
    @classmethod
    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        bot: CustomBot = ctx.client
        entries = await bot.mongo_db("Wiki").find({}).to_list(length=None)
        tree = WikiEntry.from_list(entries)
        aux_tree = tree.lookup(value)
        items: list[WikiEntry] = [aux_tree]
        value = value.removeprefix(aux_tree.route.removeprefix("/"))
        items.extend(x for x in aux_tree.children.values() if x.children)
        return [
            Choice(name=name, value=x.route)
            for x in items
            if (name := f"{x.route}/".removeprefix("/")) and value in name
        ]


class WikiNodeTransformer(WikiTransformer):
    @classmethod
    async def autocomplete(cls, ctx: Interaction, value: str) -> list[Choice[str]]:
        bot: CustomBot = ctx.client
        entries = await bot.mongo_db("Wiki").find({}).to_list(length=None)
        tree = WikiEntry.from_list(entries)
        value = (ctx.namespace.group or "").removeprefix("/")
        aux_tree = tree.lookup(value)
        items: list[WikiEntry] = [aux_tree]
        value = value.removeprefix(aux_tree.route.removeprefix("/"))
        items.extend(aux_tree.children.values())
        return [
            Choice(name=name, value=x.route)
            for x in items
            if (name := x.route.removeprefix(aux_tree.route) or "/") and value in name
        ]


WikiTreeArg = Transform[WikiEntry, WikiTreeTransformer]
WikiNodeArg = Transform[WikiEntry, WikiNodeTransformer]
