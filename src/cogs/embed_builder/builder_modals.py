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
from colour import Color
from dateparser import parse
from discord import (
    ButtonStyle,
    Embed,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
    TextStyle,
)
from discord.ui import Button, Modal, TextInput, View, button

SETTING_EMOJI = PartialEmoji(
    name="setting",
    animated=True,
    id=962380600902320148,
)


class EmbedModal(Modal):
    def __init__(self, embed: Embed) -> None:
        super(EmbedModal, self).__init__(title="Embed's information", timeout=None)
        self.embed = embed
        self.reference = embed.copy()
        self.e_title = TextInput(label="Title", default=self.reference.title, max_length=256)
        self.e_url = TextInput(label="URL", default=self.reference.url)
        description = self.reference.description or ""
        self.e_description = TextInput(label="Description", style=TextStyle.paragraph, default=description[:4000])
        color = hex(self.reference.color.value).removeprefix("0x").upper() if self.reference.color else None
        self.e_color = TextInput(label="Color", default=color)
        timestamp = str(self.reference.timestamp or "")
        self.e_timestamp = TextInput(label="Timestamp", default=timestamp)
        self.add_item(self.e_title)
        self.add_item(self.e_url)
        self.add_item(self.e_description)
        self.add_item(self.e_color)
        self.add_item(self.e_timestamp)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        self.reference.title = self.e_title.value
        self.reference.url = self.e_url.value
        self.reference.description = self.e_description.value
        color = self.e_color.value or ""
        try:
            if not color.startswith("#"):
                color = Color(color)
                color = color.get_hex_l()
            color = color.removeprefix("#")
            color = int(color, base=16)
        except ValueError:
            color = self.reference.color
        finally:
            self.reference.color = color

        e_timestamp = self.e_timestamp.value or ""
        self.reference.timestamp = parse(e_timestamp, settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc"))
        try:
            await resp.edit_message(embed=self.reference)
        except HTTPException as e:
            await resp.send_message(str(e), ephemeral=True)
        else:
            self.embed = self.reference
        finally:
            self.stop()


class EmbedModificationView(View):
    def __init__(self, *, embed: Embed, author: Member):
        super(EmbedModificationView, self).__init__(timeout=None)
        self.embed = embed
        self.author = author

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if interaction.user != self.author:
            await resp.send_message(f"This embed is being modified by {self.author}", ephemeral=True)
            return False
        return True

    @button(label="Embed's Information".center(80, "\u2008"), style=ButtonStyle.blurple, emoji=SETTING_EMOJI, row=0)
    async def info(self, interaction: Interaction, btn: Button):
        resp: InteractionResponse = interaction.response
        modal = EmbedModal(self.embed)
        await resp.send_modal(modal)
        await modal.wait()
        self.embed = modal.embed

    @button(label="Conclude".center(80, "\u2008"), style=ButtonStyle.red, emoji=SETTING_EMOJI, row=2)
    async def conclude(self, interaction: Interaction, btn: Button):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(view=None)
        self.stop()
