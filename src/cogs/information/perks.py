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

from discord import Attachment, Colour, Embed, Interaction, Object, Role
from discord.ui import Modal, TextInput
from discord.utils import MISSING, find

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.functions import safe_username

__all__ = ("CustomPerks",)


class Perk(ABC):
    @classmethod
    @abstractmethod
    async def method(cls, itx: Interaction[CustomBot], msg: Optional[Attachment] = None):
        "Method that uses the interaction"


class CustomRoleModal(Modal, title="Custom Role"):
    def __init__(self, role: Optional[Role] = None, icon: Optional[Attachment] = None) -> None:
        super(CustomRoleModal, self).__init__(timeout=None)
        self.role, self.icon = role, icon
        self.name = TextInput(
            label="Name (Empty to Remove)",
            max_length=100,
            required=False,
        )
        self.color = TextInput(
            label="Color",
            max_length=7,
            min_length=7,
            placeholder="#000000",
            required=False,
        )
        if role:
            self.name.default = role.name
            self.color.default = str(role.color)
        else:
            self.color.default = str(Colour.random())
        self.add_item(self.name)
        self.add_item(self.color)

    async def on_error(self, itx: Interaction[CustomBot], error: Exception, /) -> None:
        itx.client.logger.error("Ignoring exception in Modal %r", self, exc_info=error)

    async def interaction_check(self, interaction: Interaction[CustomBot]) -> bool:
        try:
            if self.color.value:
                Colour.from_str(self.color.value)
        except ValueError:
            await interaction.response.send_message("Invalid Color", ephemeral=True)
            return False
        return True

    async def on_submit(self, itx: Interaction[CustomBot]) -> None:
        await itx.response.defer(ephemeral=True, thinking=True)

        embed = Embed(title="Custom Role", timestamp=itx.created_at)
        embed.set_footer(text=itx.guild.name, icon_url=itx.guild.icon)
        embed.set_image(url=WHITE_BAR)

        db = itx.client.mongo_db("Custom Role")
        if not self.name.value and self.role:
            await self.role.delete()
            embed.title = "Custom Role - Removed"
            embed.color = self.role.color
            embed.description = self.role.name
            embed.set_thumbnail(url=self.role.icon)
            await db.delete_one({"id": self.role.id, "server": itx.guild_id})
        elif name := self.name.value:
            color = Colour.from_str(self.color.value) if self.color else Colour.default()

            icon_data = await self.icon.read() if self.icon else None
            role = self.role

            if not role:
                icon_data = icon_data or MISSING
                booster = find(lambda x: x.is_premium_subscriber(), itx.guild.roles)
                role = await itx.guild.create_role(name=name, colour=color, display_icon=icon_data)
                await role.edit(position=booster.position + 1)
            else:
                await role.edit(name=name, color=color, display_icon=icon_data)

            embed.color = role.color
            embed.description = role.name
            embed.set_thumbnail(url=role.icon)

            if role not in itx.user.roles:
                await itx.user.add_roles(role)

            await db.replace_one(
                {"author": itx.user.id, "server": itx.guild_id},
                {"author": itx.user.id, "id": role.id, "server": itx.guild_id},
                upsert=True,
            )
            self.role = role

        db = itx.client.mongo_db("Server")
        data = await db.find_one({"id": itx.guild_id})
        data = data or {}

        if info := data.get("member_boost"):
            channel_id = info.get("channel")
            if thread_id := info.get("thread"):
                thread = Object(id=thread_id)
            else:
                thread = MISSING

            w = await itx.client.webhook(channel_id)
            await w.send(
                embed=embed,
                thread=thread,
                username=safe_username(itx.user.display_name),
                avatar_url=itx.user.display_avatar.url,
            )

        await itx.followup.send(embed=embed, ephemeral=True)
        self.stop()


class CustomRolePerk(Perk):
    @classmethod
    async def method(cls, itx: Interaction[CustomBot], img: Optional[Attachment] = None):
        db = itx.client.mongo_db("Custom Role")
        role: Optional[Role] = None
        if role_data := await db.find_one({"author": itx.user.id, "server": itx.guild_id}):
            role = itx.guild.get_role(role_data["id"])
            if not role:
                await db.delete_one(role_data)
            elif role not in itx.user.roles:
                await itx.user.add_roles(role)
        modal = CustomRoleModal(role=role, icon=img)
        await itx.response.send_modal(modal)


class RPSearchBannerPerk(Perk):
    @classmethod
    async def method(cls, itx: Interaction[CustomBot], img: Optional[Attachment] = None):
        await itx.response.defer(thinking=True, ephemeral=True)
        db = itx.client.mongo_db("RP Search Banner")
        key = {"author": itx.user.id, "server": itx.guild_id}
        embed = Embed(title="RP Search Banner", color=itx.user.color, timestamp=itx.created_at)
        embed.set_footer(text=itx.guild.name, icon_url=itx.guild.icon)

        if img:
            url = f"attachment://{img.filename}"
            file = await img.to_file()
        else:
            url = "https://cdn.discordapp.com/attachments/823629617629495386/1020175863037317150/unknown.png"
            file = MISSING

        embed.set_image(url=url)

        db = itx.client.mongo_db("Server")
        data = await db.find_one({"id": itx.guild_id})
        data = data or {}

        if info := data.get("member_boost"):
            channel_id = info.get("channel")
            if thread_id := info.get("thread"):
                thread = Object(id=thread_id)
            else:
                thread = MISSING

            w = await itx.client.webhook(channel_id)
            m = await w.send(
                embed=embed,
                file=file,
                thread=thread,
                wait=True,
                username=safe_username(itx.user.display_name),
                avatar_url=itx.user.display_avatar.url,
            )
            image = m.embeds[0].image.url
            embed.set_image(url=image)
            await db.replace_one(key, key | {"image": image}, upsert=True)

        await itx.followup.send(embed=embed, ephemeral=True)


class OCBackgroundPerk(Perk):
    @classmethod
    async def method(cls, itx: Interaction[CustomBot], img: Optional[Attachment] = None):
        await itx.response.defer(thinking=True, ephemeral=True)
        db = itx.client.mongo_db("OC Background")
        key = {"author": itx.user.id, "server": itx.guild_id}
        embed = Embed(title="OC Background", color=itx.user.color, timestamp=itx.created_at)
        embed.set_footer(text=itx.guild.name, icon_url=itx.guild.icon)

        if img:
            embed.set_image(url=f"attachment://{img.filename}")
            file = await img.to_file()
        else:
            embed.set_image(
                url="https://cdn.discordapp.com/attachments/823629617629495386/1020182375256313856/unknown.png"
            )
            file = MISSING

        db = itx.client.mongo_db("Server")
        data = await db.find_one({"id": itx.guild_id})
        data = data or {}

        if info := data.get("member_boost"):
            channel_id = info.get("channel")
            if thread_id := info.get("thread"):
                thread = Object(id=thread_id)
            else:
                thread = MISSING

            w = await itx.client.webhook(channel_id)
            m = await w.send(
                embed=embed,
                file=file,
                thread=thread,
                wait=True,
                username=safe_username(itx.user.display_name),
                avatar_url=itx.user.display_avatar.url,
            )
            image = m.embeds[0].image.url
            embed.set_image(url=image)
            await db.replace_one(key, key | {"image": image}, upsert=True)
            await itx.followup.send(embed=embed, ephemeral=True)


class CustomPerks(Enum):
    Custom_Role = CustomRolePerk
    RP_Search_Banner = RPSearchBannerPerk
    OC_Background = OCBackgroundPerk

    async def method(self, itx: Interaction[CustomBot], img: Optional[Attachment] = None):
        await self.value.method(itx, img)
