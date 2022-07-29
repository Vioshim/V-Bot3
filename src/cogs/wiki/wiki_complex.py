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

from typing import Optional

from discord import (
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    PartialEmoji,
    TextStyle,
)
from discord.ui import Modal, Select, TextInput, button, select
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.wiki.wiki import WikiEntry
from src.pagination.complex import Complex
from src.utils.etc import WHITE_BAR

__all__ = ("WikiModal", "WikiComplex")


def wiki_parser(item: WikiEntry):
    key = f"Entry has {len(item.children)} pages." if item.children else None
    if not key and item.embeds:
        key = item.embeds[0].title or None
    return (f"/{item.path}", key)


class WikiModal(Modal, title="Wiki Route"):
    def __init__(self, tree: WikiEntry) -> None:
        super(WikiModal, self).__init__(timeout=None)
        self.tree = tree
        self.folder = TextInput(label="Wiki Folder", style=TextStyle.paragraph, required=True, default=tree.route)
        self.add_item(self.folder)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Wiki")
        entries = await db.find({}).to_list(length=None)
        tree = WikiEntry.from_list(entries)
        view = WikiComplex(tree=tree, target=interaction)
        content, embeds = tree.content, tree.embeds
        if not (content or embeds):
            embeds = [view.embed]
        view.message = await interaction.followup.send(
            ephemeral=True,
            embeds=embeds,
            content=content,
            wait=True,
            view=view,
        )
        self.stop()


class WikiComplex(Complex[WikiEntry]):
    def __init__(self, *, tree: WikiEntry, target: Interaction):
        super(WikiComplex, self).__init__(
            member=target.user,
            values=list(tree.children.values()),
            target=target,
            timeout=None,
            parser=wiki_parser,
            emoji_parser=lambda x: "\N{BLUE BOOK}" if x.children else "\N{PAGE FACING UP}",
            silent_mode=True,
            text_component=WikiModal(tree),
        )
        self.tree = tree
        self.parent_folder.disabled = not tree.parent

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        if self.keep_working or len(self.choices) < self.max_values:
            resp: InteractionResponse = interaction.response
            content, embeds = self.tree.content, self.tree.embeds
            if not (content or embeds):
                embed = Embed(
                    title="This page has no information yet",
                    description="Feel free to make suggestions to fill this page!",
                    color=self.member.color,
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(
                    text=self.member.guild.name,
                    icon_url=self.member.guild.icon,
                )
                embeds = [embed]

            self.parent_folder.disabled = not self.tree.parent
            data = dict(content=content, embeds=embeds)

            if isinstance(page, int):
                self.pos = page
                self.menu_format()
                data["view"] = self

            resp: InteractionResponse = interaction.response

            if not resp.is_done():
                return await resp.edit_message(**data)
            try:
                if message := self.message or interaction.message:
                    await message.edit(**data)
                else:
                    self.message = await interaction.edit_original_message(**data)
            except DiscordException as e:
                interaction.client.logger.exception("View Error", exc_info=e)
                self.stop()
        else:
            await self.delete(interaction)

    async def selection(self, interaction: Interaction, tree: WikiEntry):
        interaction.client.logger.info("%s is reading %s", interaction.user.display_name, tree.route)
        content, embeds = tree.content, tree.embeds
        if not (content or embeds):
            embeds = [self.embed]
        self.tree = tree
        self._values = list(tree.children.values())
        await self.edit(interaction=interaction, page=0)

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        await self.selection(interaction, self.current_choice)

    @button(
        label="Parent Folder",
        emoji=PartialEmoji(name="IconReply", id=816772114639487057),
        custom_id="parent",
    )
    async def parent_folder(self, interaction: Interaction, _: Select) -> None:
        await self.selection(interaction, self.tree.parent)
