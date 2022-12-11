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
    Invite,
    Member,
    Message,
    PartialEmoji,
    SelectOption,
    TextChannel,
)
from discord.ui import Button, Select, View, button, select

from src.pagination.complex import Complex
from src.utils.etc import INVITE_EMOJI, LINK_EMOJI, SETTING_EMOJI
from src.views.message_view import MessagePaginator, msg_parser

__all__ = ("InviteComplex", "InviteAdminComplex", "InviterView")


class InviteComplex(Complex[str]):
    def __init__(
        self,
        invite: Invite,
        member: Member,
        tags: dict[str, set[Message]],
        target: TextChannel,
    ):
        super(InviteComplex, self).__init__(
            member=member,
            values=tags.keys(),
            max_values=len(tags),
            emoji_parser=PartialEmoji(name="MessageLink", id=778925231506587668),
            target=target,
            parser=lambda x: (x, f"Adds {x} partnership"),
        )
        self.data = tags
        self.invite = invite


class InviteAdminComplex(InviteComplex):
    def __init__(
        self,
        invite: Invite,
        member: Member,
        tags: dict[str, set[Message]],
        target: TextChannel,
    ):
        super(InviteAdminComplex, self).__init__(
            invite=invite,
            member=member,
            tags=tags,
            target=target,
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        pm_manager_role = interaction.guild.get_role(788215077336514570)
        return interaction.user.guild_permissions.administrator or pm_manager_role in interaction.user.roles


DATA: dict[str, Embed] = {}

with open("resources/hub_partners.json", mode="r", encoding="utf8") as f:
    data = load(f)
    if isinstance(data, dict):
        DATA = {k: Embed.from_dict(v) for k, v in data.items()}


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
            filter(lambda x: x.author.bot and x.content and x.embeds, messages),
            key=inv_msg_parser,
        )
        entries: dict[str, set[Message]] = {}
        for item in messages:
            for tag in item.embeds[0].footer.text.split(", "):
                entries.setdefault(tag, set())
                entries[tag].add(item)
        self.data = dict(sorted(entries.items(), key=lambda x: (len(x[1]), x[0]), reverse=True))
        for key, value in self.data.items():
            sct.add_option(label=key, value=key, description=f"{len(value)} servers.", emoji=LINK_EMOJI)
        if not sct.options:
            sct.add_option(label="Empty")
            sct.disabled = True
        else:
            sct.disabled = False
        sct.max_values = len(sct.options)

    def append(self, message: Message):
        self._messages.append(message)
        self.group_method(self._messages)

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
            SelectOption(
                label=k,
                description=v.description.replace("\n", " ")[:100],
                emoji=INVITE_EMOJI,
            )
            for k, v in DATA.items()
            if k != "Parallel"
        ],
    )
    async def hubs(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        key = sct.values[0]
        info = DATA[key].copy()
        info.timestamp = ctx.created_at
        info.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        view = View()
        view.add_item(Button(label="Join Hub!", url=info.url, emoji=INVITE_EMOJI))
        await resp.send_message(content=info.url, embed=info, ephemeral=True, view=view)

    @button(
        label="Parallel Yonder's Ad",
        custom_id="ad",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
        row=4,
    )
    async def server_ad(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        embed = DATA["Parallel"].copy()
        embed.timestamp = ctx.created_at
        embed.color = ctx.user.color
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await resp.send_message(content=embed.url, embed=embed, ephemeral=True)
