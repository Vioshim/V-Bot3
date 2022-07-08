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

from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    InteractionResponse,
    Message,
    PartialEmoji,
    SelectOption,
)
from discord.ui import Button, Select, View, button, select

from src.utils.etc import SETTING_EMOJI
from src.views.message_view import MessagePaginator, msg_parser

__all__ = ("InviterView",)

IMAGE_URL = "https://cdn.discordapp.com/attachments/748384705098940426/909988411199348767/unknown.png"


with open("resources/hub_partners.json", mode="r") as f:
    DATA: dict[str, str] = load(f)


def inv_msg_parser(message: Message):
    info, desc = msg_parser(message)
    return info.split("partnered with ")[-1], desc


class InviterView(View):
    def __init__(self):
        super(InviterView, self).__init__(timeout=None)
        self._messages = []
        self.data: dict[str, set[Message]] = {}

    def group_method(self, messages: set[Message]):
        sct = self.select_msg
        sct.options.clear()
        self._messages = messages = sorted(
            filter(lambda x: x.webhook_id and x.embeds, messages),
            key=inv_msg_parser,
        )
        entries: dict[str, set[Message]] = {}
        for item in messages:
            for tag in item.embeds[0].footer.text.split(", "):
                entries.setdefault(tag, set())
                entries[tag].add(item)
        self.data = dict(sorted(entries.items(), key=lambda x: (len(x[1]), x[0]), reverse=True))
        for key, value in self.data.items():
            sct.add_option(
                label=key,
                value=key,
                description=f"{len(value)} servers.",
                emoji=PartialEmoji(name="MessageLink", id=778925231506587668),
            )
        if not sct.options:
            sct.append_option(SelectOption(label="Empty", value="Empty"))
            sct.disabled = True
        else:
            sct.disabled = False
        sct.max_values = len(sct.options)

    @property
    def messages(self):
        return self._messages

    @messages.setter
    def messages(self, messages: list[Message]):
        self.group_method(messages)

    @messages.deleter
    def messages(self):
        self.group_method([])

    @select(placeholder="Select Tags", row=3, custom_id="msg-filter")
    async def select_msg(self, ctx: Interaction, sct: Select):
        title = f"Servers with tags: {', '.join(sct.values)}"
        items = [self.data.get(x, set()) for x in sct.values]
        messages: set[Message] = set.intersection(*items)
        view = MessagePaginator(member=ctx.user, target=ctx, messages=messages, parser=inv_msg_parser)
        async with view.send(ephemeral=True, title=title):
            ctx.client.logger.info("User %s is reading %s", str(ctx.user), title)

    @select(
        placeholder="Select RP Hub",
        custom_id="hubs",
        options=[
            SelectOption(label=key, description="Click for more information", emoji="\N{HANDSHAKE}")
            for key in DATA.keys()
            if key != "Parallel"
        ],
    )
    async def hubs(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        key = sct.values[0]
        info = DATA.get(key, f"Unknown info for {key}")
        await resp.send_message(content=info, ephemeral=True)

    @button(
        label="Parallel Yonder's Ad",
        custom_id="ad",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
        row=4,
    )
    async def server_ad(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        text: str = DATA["Parallel"]
        url = text.split("\n\n")[-1]
        embed = Embed(
            title=f"{ctx.guild.name}'s Ad",
            color=ctx.user.color,
            description=text,
            url=url,
            timestamp=ctx.created_at,
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.add_field(name="Image", value=IMAGE_URL)
        embed.set_image(url=IMAGE_URL)
        await resp.send_message(content=url, embed=embed, ephemeral=True)
