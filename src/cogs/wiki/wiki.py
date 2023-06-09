# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Vioshim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import annotations

from contextlib import suppress
from typing import Any, Optional

from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    Message,
    PartialEmoji,
    SelectOption,
    TextStyle,
)
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, button, select

from src.pagination.complex import Complex
from src.structures.bot import CustomBot as Client
from src.structures.converters import Context, EmbedFlags
from src.utils.etc import REPLY_EMOJI, ArrowEmotes

__all__ = (
    "WikiComplex",
    "WikiEntry",
)

TREE_ICON, LEVEL_ICON = (
    "\N{BOX DRAWINGS DOUBLE UP AND RIGHT}",
    "\N{BOX DRAWINGS DOUBLE HORIZONTAL}",
)


class WikiEntry:
    def __init__(
        self,
        title: str = "",
        desc: str = "",
        path: list[str] | str = "",
        content: str = "",
        embeds: list[Embed] = None,
        order: int = 0,
        emoji: Optional[PartialEmoji | str] = None,
        parent: Optional[WikiEntry] = None,
        children: dict[str, WikiEntry] = None,
    ) -> None:
        embeds = embeds or []
        self.content = content or ""
        self.title = title or ""
        self.desc = desc or ""
        self.path = "/".join(path) if isinstance(path, list) else path
        self.embeds = [Embed.from_dict(x) if isinstance(x, dict) else x for x in embeds]
        self.children = children or {}
        self.parent = parent
        self.order = order
        if isinstance(emoji, str):
            emoji = PartialEmoji.from_str(emoji)
        self._emoji = emoji

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return isinstance(other, WikiEntry) and self.path == other.path

    def __ne__(self, other):
        return isinstance(other, WikiEntry) and self.path != other.path

    def contains(self, text: str):
        text = text.lower()
        return any(
            (
                self.title and text in self.title.lower(),
                self.desc and text in self.desc.lower(),
                self.content and text in self.content.lower(),
                any(x.title and text in x.title.lower() for x in self.embeds),
                any(x.description and text in x.description.lower() for x in self.embeds),
                any(x.footer.text and text in x.footer.text.lower() for x in self.embeds),
                any(x.author.name and text in x.author.name.lower() for x in self.embeds),
                any(text in f.name or text in f.value for x in self.embeds for f in x.fields),
            )
        )

    def delete(self):
        return self.parent and self.parent.children.pop(self.path, None)

    def copy(self):
        return WikiEntry(
            title=self.title,
            desc=self.desc,
            path=self.path,
            content=self.content,
            embeds=[embed.copy() for embed in self.embeds],
            order=self.order,
            emoji=self.emoji,
            children=self.children.copy(),
            parent=self.parent,
        )

    @property
    def key(self):
        return {"path": self.path.split("/")}

    @property
    def ordered_children(self):
        return sorted(
            self.children.values(),
            key=lambda x: (x.order, -len(x.children), x.path),
        )

    @property
    def emoji(self) -> PartialEmoji:
        if self._emoji:
            return self._emoji
        emoji = "\N{LEDGER}" if self.children else "\N{PAGE FACING UP}"
        return PartialEmoji.from_str(emoji)

    @emoji.setter
    def emoji(self, value: Optional[PartialEmoji | str]):
        if isinstance(value, str):
            value = PartialEmoji.from_str(value)
        self._emoji = value

    @emoji.deleter
    def emoji(self):
        self._emoji = None

    def __str__(self, level: int = 0) -> str:
        ret = f"{TREE_ICON}{LEVEL_ICON * (level * 2)} /{self.path}\n"
        items = sorted(self.children.values(), key=lambda x: x.order)
        return ret + "".join(child.__str__(level + 1) for child in items)

    def __repr__(self) -> str:
        return f"WikiEntry({len(self.children)})"

    @property
    def route(self) -> str:
        entries = [self.path] if self.path else []
        aux = self
        while isinstance(aux.parent, WikiEntry):
            entries.append(aux.parent.path)
            aux = aux.parent
        return "/".join(entries[::-1]).strip("/")

    @property
    def simplified(self):
        route = self.route.strip("/")
        return {
            "path": route.split("/") if route else [],
            "title": self.title,
            "desc": self.desc,
            "content": self.content,
            "embeds": [x.to_dict() for x in self.embeds if x],
            "order": self.order,
            "emoji": str(self._emoji) if self._emoji else None,
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
        connection = f"|{placeholder[:-1]}"
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
        path: str = "",
        title: str = "",
        content: str = "",
        desc: str = "",
        embeds: list[Embed] = None,
        order: int = 0,
        emoji: str = None,
    ):
        self.add_node(
            item := WikiEntry(
                path=path,
                title=title,
                desc=desc,
                content=content,
                embeds=embeds,
                order=order,
                emoji=emoji,
            )
        )
        return item

    @classmethod
    def from_data(cls, node: WikiEntry | list[str] | str | dict[str, Any]):
        if isinstance(node, list):
            node = "/".join(node)
        if isinstance(node, str):
            node = WikiEntry(path=node)
        if isinstance(node, dict):
            node.pop("_id", None)
            node = WikiEntry(**node)
        return node

    def add_node(self, node: WikiEntry | list[str] | str | dict[str, Any]):
        if not isinstance(node, WikiEntry):
            node = self.from_data(node)
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
            for index, _ in enumerate(elements):
                ref = node if elements[: index + 1] == route else WikiEntry()
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
    def from_list(cls, nodes: list[WikiEntry], **kwargs):
        result = cls(**kwargs)
        for item in sorted(map(cls.from_data, nodes), key=lambda x: (x.path.count("/"), x.order)):
            result.add_node(item)
        return result

    def __getitem__(self, item: str) -> WikiEntry:
        return self.children[item]

    def __delitem__(self, item: str) -> None:
        del self.children[item]

    def __setitem__(self, key: str, value: WikiEntry):
        self.children[key] = value

    @property
    def flatten(self):
        return self.to_list(self)

    @classmethod
    def to_list(cls, parent: WikiEntry):
        yield parent
        for child in parent.children.values():
            yield from cls.to_list(child)


class WikiPathModal(Modal, title="Wiki Path"):
    def __init__(self, node: WikiEntry, message: Message, context: commands.Context[Client]) -> None:
        super(WikiPathModal, self).__init__(timeout=None)
        embed = (
            message.embeds[0]
            if message.embeds
            else Embed(color=context.author.color, timestamp=context.message.created_at)
        )
        embed_text = EmbedFlags.to_flags(message, embed)
        self.title_data = TextInput(label="Title", required=False, default=node.title)
        self.desc_data = TextInput(label="Description", required=False, default=node.desc)
        self.order_data = TextInput(label="Order", required=False, default=str(node.order))
        self.embed_data = TextInput(label="Embed", style=TextStyle.paragraph, default=embed_text[:4000])
        self.path_data = TextInput(label="Path")
        self.node = node
        self.context = context
        self.add_item(self.title_data)
        self.add_item(self.desc_data)
        self.add_item(self.order_data)
        self.add_item(self.embed_data)
        if path := node.path:
            self.path_data.default = path
            self.add_item(self.path_data)

    async def on_submit(self, interaction: Interaction[Client]) -> None:
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            db = interaction.client.mongo_db("Wiki")
            payload = await EmbedFlags().convert(self.context, self.embed_data.value)
            embed = payload.embed
            order = int(self.order_data.value)
            msg = await interaction.followup.send(embed=embed, wait=True)
            await msg.delete(delay=3)
        except Exception as e:
            interaction.client.logger.exception(
                "Wiki(%s) had exception: %s",
                self.node.path,
                interaction.user.display_name,
                exc_info=e,
            )
            embed = Embed(
                title=e.__class__.__name__,
                description=f"```py\n{e}\n```",
                color=0x94939F,
            )
            await interaction.followup.send(embed=embed)
        else:
            self.node.embeds = [embed] if embed else []
            self.node.title = self.title_data.value
            self.node.desc = self.desc_data.value
            self.node.order = order

            if self.node.parent:
                self.node.parent.children[self.node.path] = self.node

            if (
                self.path_data.value
                and self.path_data.value != self.node.path
                and (node := self.node.delete())
                and (query := {f"path.{index}": value for index, value in enumerate(node.route.split("/"))})
            ):
                self.node.path = self.path_data.value
                route = self.node.route.strip()
                new_info = {f"path.{index}": value for index, value in enumerate(route.split("/"))}
                await db.update_many(query, {"$set": new_info})
            else:
                route = self.node.route.strip()

            if parent := self.node.parent:
                parent.children[self.node.path] = self.node

            await db.replace_one({"path": route.split("/") if route else []}, self.node.simplified, upsert=True)
            interaction.client.logger.info("Wiki(%s) modified by %s", route or "/", interaction.user.display_name)
        finally:
            self.stop()


class WikiContentModal(Modal, title="Wiki Content"):
    text = TextInput(
        label="Content",
        style=TextStyle.paragraph,
        required=False,
        max_length=2000,
        default="",
    )


def wiki_parser(item: WikiEntry):
    key = item.desc or (f"Entry has {len(item.children)} pages." if item.children else "")
    if not key and item.embeds:
        key = item.embeds[0].title or None
    return (item.title or f"/{item.path}", key)


class WikiComplex(Complex[WikiEntry]):
    def __init__(
        self,
        *,
        tree: WikiEntry,
        context: commands.Context[Client] | Interaction[Client],
    ):
        if isinstance(context, Interaction):
            member, target = context.user, context
            context = Context(context.client, context.user, context.guild)
        else:
            member, target = context.author, context.interaction or context.channel

        edit_mode = context.author.guild_permissions.administrator
        super(WikiComplex, self).__init__(
            member=member,
            values=tree.ordered_children,
            target=target,
            timeout=None if edit_mode else 180,
            parser=wiki_parser,
            silent_mode=True,
        )
        self.context = context
        self.edit_mode = edit_mode
        self.real_max = self.max_values
        self.tree = tree
        self.remove_item(self.finish)
        if not self.edit_mode:
            self.remove_item(self.edit_options)

    @property
    def children_entries(self):
        if self.tree.parent and self.tree in (
            items := sorted(
                self.tree.parent.children.values(),
                key=lambda x: x.order,
            )
        ):
            return items
        return []

    def menu_format(self) -> None:
        super(WikiComplex, self).menu_format()
        items = self.children_entries
        try:
            index = items.index(self.tree)
            self.parent_folder.label = f"{index + 1}/{len(items)}"
            self.parent_folder.style = ButtonStyle.grey
        except ValueError:
            index = 0
            self.parent_folder.label = ""
            self.parent_folder.style = ButtonStyle.blurple

        self.first_child.disabled = index <= 0
        self.previous_child.disabled = index <= 0
        self.next_child.disabled = index >= len(items) - 1
        self.last_child.disabled = index >= len(items) - 1

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        text, embeds = self.tree.content, self.tree.embeds
        if not (embeds or text):
            embed = Embed(
                title="This page has no information yet",
                description="Feel free to make suggestions to fill this page!",
                color=0x94939F,
            )
            embeds.append(embed)

        data = dict(embeds=embeds, content=text)

        if isinstance(page, int):
            self.pos = page
            self.menu_format()
            data["view"] = self

        return data

    async def selection(self, interaction: Interaction[Client], tree: Optional[WikiEntry] = None):
        tree = tree or self.tree
        interaction.client.logger.info("%s is reading %s", interaction.user.display_name, tree.route)
        self.tree = tree
        self._values = tree.ordered_children
        await self.edit(interaction=interaction, page=0)

    @button(emoji=ArrowEmotes.START, custom_id="START", row=0)
    async def first_child(self, interaction: Interaction[Client], _: Button) -> None:
        items = sorted(self.tree.parent.children.values(), key=lambda x: x.order)
        await self.selection(interaction, items[0])

    @button(emoji=ArrowEmotes.BACK, custom_id="BACK", row=0)
    async def previous_child(self, interaction: Interaction[Client], _: Button) -> None:
        items = sorted(self.tree.parent.children.values(), key=lambda x: x.order)
        index = 0
        with suppress(ValueError):
            index = max(items.index(self.tree) - 1, index)
        await self.selection(interaction, items[index])

    @button(emoji=REPLY_EMOJI, label="1 / 1", custom_id="parent", row=0)
    async def parent_folder(self, interaction: Interaction[Client], _: Button) -> None:
        if self.tree.parent:
            return await self.selection(interaction, self.tree.parent)
        await self.delete(interaction)

    @button(emoji=ArrowEmotes.FORWARD, custom_id="FORWARD", row=0)
    async def next_child(self, interaction: Interaction[Client], _: Button) -> None:
        items = sorted(self.tree.parent.children.values(), key=lambda x: x.order)
        index = len(items) - 1
        with suppress(ValueError):
            index = min(items.index(self.tree) + 1, index)
        await self.selection(interaction, items[index])

    @button(emoji=ArrowEmotes.END, custom_id="END", row=0)
    async def last_child(self, interaction: Interaction[Client], _: Button) -> None:
        items = sorted(self.tree.parent.children.values(), key=lambda x: x.order)
        await self.selection(interaction, items[-1])

    @select(placeholder="Select the elements", custom_id="selector", row=1)
    async def select_choice(self, interaction: Interaction[Client], _: Select) -> None:
        await self.selection(interaction, self.current_choice)

    @select(
        placeholder="Edit options",
        custom_id="edit-options",
        row=3,
        options=[
            SelectOption(
                label="Edit content",
                emoji="📝",
                description="Edit the content of the page",
            ),
            SelectOption(
                label="Edit page",
                emoji="📝",
                description="Edit the page's embed'",
            ),
            SelectOption(
                label="Delete page",
                emoji="🗑️",
                description="Delete the page",
            ),
            SelectOption(
                label="New page",
                emoji="📄",
                description="Create a new page",
            ),
            SelectOption(
                label="Refresh page",
                emoji="🔄",
                description="Refresh the pages",
            ),
        ],
    )
    async def edit_options(self, interaction: Interaction[Client], sct: Select) -> None:
        if not (self.edit_mode or interaction.permissions.administrator):
            return await interaction.response.send_message(
                "You don't have the permission to do that",
                ephemeral=True,
            )

        match sct.values[0]:
            case "Edit content":
                modal = WikiContentModal()
                modal.text.default = self.tree.content
                await interaction.response.send_modal(modal)
                await modal.wait()
                self.tree.content = modal.text
                await self.selection(interaction, self.tree)
            case "Edit page":
                modal = WikiPathModal(self.tree, interaction.message, self.context)
                await interaction.response.send_modal(modal)
                await modal.wait()
                await self.selection(interaction, modal.node)
            case "Delete page":
                if current := self.tree.delete():
                    db = interaction.client.mongo_db("Wiki")
                    route = current.route
                    await db.delete_many({f"path.{index}": path for index, path in enumerate(route.split("/"))})
                    if parent := current.parent:
                        tree = parent
                    else:
                        entries = await db.find({}).to_list(length=None)
                        tree = WikiEntry.from_list(entries)
                await self.selection(interaction, tree)
            case "New page":
                items = self.tree.children.values() if self.tree.children else [self.tree]
                if self.tree.path.startswith("Changelog"):
                    order = min(items, key=lambda x: x.order).order - 1
                else:
                    order = max(items, key=lambda x: x.order).order + 1
                node = WikiEntry(order=order, parent=self.tree, path="New page")
                modal = WikiPathModal(node, interaction.message, self.context)
                await interaction.response.send_modal(modal)
                await modal.wait()
                await self.selection(interaction, modal.node)
            case "Refresh page":
                entries = await interaction.client.mongo_db("Wiki").find({}).to_list(length=None)
                await self.selection(interaction, WikiEntry.from_list(entries))
