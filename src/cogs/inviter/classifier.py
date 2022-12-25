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

from dataclasses import dataclass
from json import load
from typing import Optional

from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    InteractionResponse,
    Invite,
    Member,
    SelectOption,
    TextChannel,
)
from discord.abc import Messageable
from discord.ui import Button, Select, View, button, select
from discord.utils import remove_markdown
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.utils.etc import INVITE_EMOJI, LINK_EMOJI, SETTING_EMOJI

__all__ = ("InviteComplex", "InviteAdminComplex", "InviterView", "Partner", "PartnerComplex")


class InviteComplex(Complex[str]):
    def __init__(
        self,
        invite: Invite,
        member: Member,
        tags: dict[str, set[Partner]],
        target: TextChannel,
    ):
        super(InviteComplex, self).__init__(
            member=member,
            values=tags.keys(),
            max_values=len(tags),
            emoji_parser=LINK_EMOJI,
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
        tags: dict[str, set[Partner]],
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


@dataclass(slots=True)
class Partner:
    id: int
    msg_id: int
    url: str
    title: str
    content: str
    icon_url: str
    image_url: Optional[str]
    tags: list[str]

    @property
    def invite_url(self):
        return f"https://discord.gg/{self.url}"

    @property
    def data(self):
        return {
            "id": self.id,
            "msg_id": self.msg_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "icon_url": self.icon_url,
            "image_url": self.image_url,
            "tags": sorted(self.tags),
        }

    @classmethod
    def from_mongo_dict(self, kwargs: dict[str, str]):
        del kwargs["_id"]
        return Partner(**kwargs)

    def __eq__(self, o: Partner) -> bool:
        return isinstance(o, Partner) and o.id == self.id

    def __hash__(self) -> int:
        return self.id >> 22


class PartnerComplex(Complex[Partner]):
    def __init__(
        self,
        member: Member,
        items: set[Partner],
        target: Optional[Messageable] = None,
    ):
        super(PartnerComplex, self).__init__(
            member=member,
            target=target,
            values=items,
            timeout=None,
            parser=lambda x: (x.title, remove_markdown(x.content)),
            keep_working=True,
            sort_key=lambda x: x.title,
            silent_mode=True,
            auto_text_component=True,
        )
        self.embed.title = "Select Partner"

    @select(row=1, placeholder="Select Partners", custom_id="selector")
    async def select_choice(self, ctx: Interaction, sct: Select) -> None:
        if item := self.current_choice:
            embed = Embed(
                title=item.title,
                url=item.invite_url,
                color=ctx.user.color,
                description=item.content,
                timestamp=ctx.created_at,
            )
            embed.set_image(url=item.image_url)
            embed.set_thumbnail(url=item.icon_url)
            view = View()
            view.add_item(Button(label="Click here to join", url=item.invite_url))
            await ctx.response.send_message(
                content=item.invite_url,
                embed=embed,
                view=view,
                ephemeral=True,
            )

        await super(PartnerComplex, self).select_choice(ctx, sct)


class TagComplex(Complex[str]):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        data: dict[str, set[Partner]],
    ):
        super().__init__(
            member=member,
            target=target,
            values=[*data.keys()],
            max_values=len(data.keys()),
            emoji_parser=LINK_EMOJI,
            parser=lambda x: (x, f"{len(data[x])} servers."),
            auto_text_component=True,
            deselect_mode=True,
            auto_conclude=False,
            silent_mode=True,
            auto_choice_info=True,
        )
        self.data = data

    @button(
        label="Finish",
        custom_id="finish",
        style=ButtonStyle.blurple,
        row=4,
    )
    async def finish(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        if choices := sorted(self.choices):
            await ctx.response.defer(ephemeral=True, thinking=True)
            items = [self.data.get(x, set()) for x in choices]
            items = set[Partner].intersection(*items)
            view = PartnerComplex(member=ctx.user, target=ctx, items=items)
            await view.simple_send(title="Servers with tags: {}".format(", ".join(choices)), ephemeral=True)
        await self.delete(ctx)


class InviterView(View):
    @staticmethod
    def group_method(items: set[Partner]):
        items = sorted(items, key=lambda x: x.title)
        entries: dict[str, set[Partner]] = {}
        for item in items:
            for tag in item.tags:
                entries.setdefault(tag, set())
                entries[tag].add(item)
        return dict(sorted(entries.items(), key=lambda x: (-len(x[1]), x[0])))

    async def on_error(self, interaction: Interaction, error: Exception, item, /) -> None:
        interaction.client.logger.error("Ignoring exception in view %r for item %r", self, item, exc_info=error)

    @select(
        placeholder="Select RP Hub",
        custom_id="hubs",
        options=[
            SelectOption(
                label=k[:100],
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
        label="Parallel World's Ad",
        custom_id="Parallel",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
    )
    async def server_ad(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        embed = DATA[btn.custom_id].copy()
        embed.timestamp = ctx.created_at
        embed.color = ctx.user.color
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        await resp.send_message(content=embed.url, embed=embed, ephemeral=True)

    @button(
        label="Check Partners!",
        custom_id="Partner Tag System",
        style=ButtonStyle.blurple,
        emoji=LINK_EMOJI,
    )
    async def select_msg(self, ctx: Interaction, btn: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Partnerships")
        await ctx.response.defer(ephemeral=True, thinking=True)
        items = {Partner.from_mongo_dict(x) async for x in db.find()}
        data = self.group_method(items)
        view = TagComplex(member=ctx.user, target=ctx, data=data)
        await view.simple_send(
            title=btn.custom_id,
            description=f"Currently, we are partnered with {len(items)} servers!",
            ephemeral=True,
        )
