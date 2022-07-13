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

from discord import Interaction, InteractionResponse, PartialEmoji, TextStyle
from discord.ui import Modal, Select, TextInput, button, select

from src.cogs.wiki.wiki import WikiEntry
from src.pagination.complex import Complex

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
        try:
            resp: InteractionResponse = interaction.response
            await resp.defer(ephemeral=True, thinking=True)
            tree = self.tree.lookup(self.folder.value) or self.tree
            view = WikiComplex(tree=tree, interaction=interaction)
            async with view.send(ephemeral=True, embeds=tree.embeds, content=tree.content):
                self.stop()
        except Exception as e:
            interaction.client.logger.exception("Detected exception", exc_info=e)


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
        self.embed.title = "This page has no information yet"
        self.embed.description = "Feel free to make suggestions to fill this page!"
        if not tree.parent:
            self.remove_item(self.parent_folder)

    async def selection(self, interaction: Interaction, tree: WikiEntry):
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        view = WikiComplex(tree=tree, target=interaction)
        interaction.client.logger.info("%s is reading %s", interaction.user.display_name, tree.route)
        content, embeds = tree.content, tree.embeds
        if not (content or embeds):
            embeds = [view.embed]
        await interaction.followup.send(ephemeral=True, embeds=embeds, content=content, view=view)

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        await self.selection(interaction, self.current_choice)
        await super(WikiComplex, self).select_choice(interaction, sct)

    @button(
        label="Parent Folder",
        emoji=PartialEmoji(name="IconReply", id=816772114639487057),
        custom_id="parent",
    )
    async def parent_folder(self, interaction: Interaction, _: Select) -> None:
        await self.selection(interaction, self.tree.parent)
