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
from typing import Optional

from discord import (
    ButtonStyle,
    Embed,
    Interaction,
    InteractionResponse,
    Invite,
    Member,
    TextChannel,
)
from discord.abc import Messageable
from discord.ui import Button, Select, View, button, select
from discord.utils import get, remove_markdown
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.utils.etc import LINK_EMOJI, SETTING_EMOJI
from src.structures.bot import CustomBot

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

    async def interaction_check(self, itx: Interaction[CustomBot]) -> bool:
        pm_manager_role = get(itx.guild.roles, name="Recruiter")
        return itx.user.guild_permissions.administrator or pm_manager_role in itx.user.roles


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
    server: int

    @property
    def invite_url(self):
        return f"https://discord.gg/{self.url}"

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
            await view.simple_send(
                title=f"Servers with tags: {', '.join(choices)}",
                ephemeral=True,
            )
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

    async def on_error(self, interaction: Interaction[CustomBot], error: Exception, item, /) -> None:
        interaction.client.logger.error("Ignoring exception in view %r for item %r", self, item, exc_info=error)

    @button(
        label="Server's Ad",
        custom_id="partnerships.advertisement",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
    )
    async def server_ad(self, ctx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = ctx.response
        db = ctx.client.mongo_db("InfoData")

        if data := await db.find_one(
            {"server": ctx.guild_id, btn.custom_id: {"$exists": True, "$ne": None}},
            {"_id": 0, btn.custom_id: 1},
        ):
            embed = Embed.from_dict(data["partnerships"]["advertisement"])
        else:
            embed = Embed(
                title="Server's Ad",
                description="This server doesn't have an advertisement!",
            )

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
    async def select_msg(self, ctx: Interaction[CustomBot], btn: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Partnerships")
        await ctx.response.defer(ephemeral=True, thinking=True)
        items = {Partner(**item) async for item in db.find({"server": ctx.guild_id}, {"_id": 0})}
        data = self.group_method(items)
        view = TagComplex(member=ctx.user, target=ctx, data=data)
        await view.simple_send(
            title=btn.custom_id,
            description=f"Currently, we are partnered with {len(items)} servers!",
            ephemeral=True,
        )
