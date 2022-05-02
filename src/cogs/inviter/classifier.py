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

from json import load

from discord import ButtonStyle, Interaction, InteractionResponse, Message, SelectOption
from discord.ui import Button, Select, button, select

from src.utils.etc import SETTING_EMOJI
from src.views.message_view import MessageView, msg_parser

__all__ = ("InviterView",)


with open("resources/hub_partners.json", mode="r") as f:
    DATA: dict[str, str] = load(f)


def inv_msg_parser(message: Message):
    info, desc = msg_parser(message)
    return info.split("partnered with ")[-1], desc


class InviterView(MessageView):
    def __init__(self, messages: list[Message]):
        super(InviterView, self).__init__(
            messages=messages,
            parser=inv_msg_parser,
            emoji="\N{HANDSHAKE}",
        )

    @select(
        placeholder="Select RP Hub",
        custom_id="hubs",
        options=[
            SelectOption(
                label=key,
                description="Click for more information",
                emoji="\N{HANDSHAKE}",
            )
            for key in DATA.keys()
            if key != "Parallel"
        ],
    )
    async def hubs(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        key = sct.values[0]
        if not (info := DATA.get(key)):
            info = f"Unknown info for {key}"
        await resp.send_message(content=info, ephemeral=True)

    @button(
        label="Read our Ad, send in your server before posting yours here.",
        custom_id="ad",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
        row=4,
    )
    async def server_ad(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message(content=DATA["Parallel"], ephemeral=True)
