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


from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from discord import (
    Attachment,
    Colour,
    Embed,
    Interaction,
    InteractionResponse,
    Object,
    Role,
    Webhook,
)
from discord.ui import Modal, TextInput
from discord.utils import MISSING, get
from motor.motor_asyncio import AsyncIOMotorCollection

from src.utils.etc import WHITE_BAR

__all__ = ("CustomPerks",)


class Perk(ABC):
    @classmethod
    @abstractmethod
    async def method(cls, ctx: Interaction, msg: Optional[Attachment] = None):
        "Method that uses the interaction"


class CustomRoleModal(Modal, title="Custom Role"):
    name = TextInput(label="Name (Empty to Remove)", max_length=100, required=False)
    color = TextInput(label="Color", max_length=7, min_length=7, placeholder="#000000")

    def __init__(self, role: Optional[Role] = None, icon: Optional[Attachment] = None) -> None:
        super(CustomRoleModal, self).__init__(timeout=None)
        self.role, self.icon = role, icon
        if role:
            self.name.default = role.name
            self.color.default = str(role.color)
        else:
            self.color.default = str(Colour.random())

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        try:
            if self.color.value:
                Colour.from_str(self.color.value)
        except ValueError:
            await resp.send_message("Invalid Color", ephemeral=True)
            return False
        else:
            return True

    async def on_submit(self, ctx: Interaction) -> None:
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(title="Custom Role", timestamp=ctx.created_at)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        embed.set_image(url=WHITE_BAR)

        db: AsyncIOMotorCollection = ctx.client.mongo_db("Custom Role")
        if not self.name.value and self.role:
            await self.role.delete()
            embed.title = "Custom Role - Removed"
            embed.color = self.role.color
            embed.description = self.role.name
            embed.set_thumbnail(url=self.role.icon)
            await db.delete_one({"id": self.role.id})
        elif name := self.name.value:
            color = Colour.from_str(self.color.value) if self.color else Colour.default()

            if self.icon:
                icon_data = await self.icon.read()
            else:
                icon_data = None

            role = self.role

            if not role:
                icon_data = icon_data or MISSING
                AFK = get(ctx.guild.roles, name="AFK")
                role = await ctx.guild.create_role(name=name, colour=color, display_icon=icon_data)
                await role.edit(position=AFK.position - 1)
            else:
                await role.edit(name=name, color=color, display_icon=icon_data)

            embed.color = role.color
            embed.description = role.name
            embed.set_thumbnail(url=role.icon)

            if role not in ctx.user.roles:
                await ctx.user.add_roles(role)

            await db.replace_one(
                {"author": ctx.user.id},
                {"author": ctx.user.id, "id": role.id},
                upsert=True,
            )
            self.role = role

        w: Webhook = await ctx.client.webhook(1001125143071965204)

        await w.send(
            embed=embed,
            thread=Object(id=1001125679405993985),
            username=ctx.user.display_name,
            avatar_url=ctx.user.display_avatar.url,
        )

        await ctx.followup.send(embed=embed, ephemeral=True)
        self.stop()


class CustomRolePerk(Perk):
    @classmethod
    async def method(cls, ctx: Interaction, img: Optional[Attachment] = None):
        resp: InteractionResponse = ctx.response
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Custom Role")
        role: Optional[Role] = None

        if role_data := await db.find_one({"author": ctx.user.id}):
            role = ctx.guild.get_role(role_data["id"])
            if not role:
                await db.delete_one(role_data)
            elif role not in ctx.user.roles:
                await ctx.user.add_roles(role)

        modal = CustomRoleModal(role, img)
        await resp.send_modal(modal)


class RPSearchBannerPerk(Perk):
    @classmethod
    async def method(cls, ctx: Interaction, img: Optional[Attachment] = None):
        resp: InteractionResponse = ctx.response
        await resp.defer(thinking=True, ephemeral=True)
        db: AsyncIOMotorCollection = ctx.client.mongo_db("RP Search Banner")
        key = {"author": ctx.user.id}
        embed = Embed(title="RP Search Banner", color=ctx.user.color, timestamp=ctx.created_at)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        w: Webhook = await ctx.client.webhook(1001125143071965204)

        if img:
            url = f"attachment://{img.filename}"
            file = await img.to_file()
        else:
            url = "https://cdn.discordapp.com/attachments/748384705098940426/1004014765909229598/unknown.png"
            file = MISSING

        embed.set_image(url=url)
        m = await w.send(
            embed=embed,
            file=file,
            thread=Object(id=1001125679405993985),
            wait=True,
            username=ctx.user.display_name,
            avatar_url=ctx.user.display_avatar.url,
        )
        image = m.embeds[0].image.url
        embed.set_image(url=image)
        await db.replace_one(key, key | {"image": image}, upsert=True)
        await ctx.followup.send(embed=embed, ephemeral=True)


class OCBackgroundPerk(Perk):
    @classmethod
    async def method(cls, ctx: Interaction, img: Optional[Attachment] = None):
        resp: InteractionResponse = ctx.response
        await resp.defer(thinking=True, ephemeral=True)
        db: AsyncIOMotorCollection = ctx.client.mongo_db("OC Background")
        key = {"author": ctx.user.id}
        embed = Embed(title="OC Background", color=ctx.user.color, timestamp=ctx.created_at)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        w: Webhook = await ctx.client.webhook(1001125143071965204)

        if img:
            url = f"attachment://{img.filename}"
            file = await img.to_file()
        else:
            url = "https://cdn.discordapp.com/attachments/748384705098940426/1004016803317563402/unknown.png"
            file = MISSING

        embed.set_image(url=url)
        m = await w.send(
            embed=embed,
            file=file,
            thread=Object(id=1001125679405993985),
            wait=True,
            username=ctx.user.display_name,
            avatar_url=ctx.user.display_avatar.url,
        )
        image = m.embeds[0].image.url
        embed.set_image(url=image)
        await db.replace_one(key, key | {"image": image}, upsert=True)
        await ctx.followup.send(embed=embed, ephemeral=True)


class CustomPerks(Enum):
    Custom_Role = CustomRolePerk
    RP_Search_Banner = RPSearchBannerPerk
    OC_Background = OCBackgroundPerk

    async def method(self, ctx: Interaction, img: Optional[Attachment] = None):
        await self.value.method(ctx, img)
