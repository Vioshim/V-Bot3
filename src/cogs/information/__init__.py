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


import asyncio
from contextlib import suppress
from datetime import timedelta
from os import getenv
from typing import Optional

import discord
from aiohttp import ClientResponseError
from discord import app_commands
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View, select
from discord.utils import MISSING, format_dt, get, utcnow
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import fuzz
from yaml import dump

from src.cogs.information.perks import CustomPerks
from src.cogs.information.poll import PollView
from src.structures.bot import CustomBot
from src.utils.etc import DEFAULT_TIMEZONE, LINK_EMOJI, WHITE_BAR
from src.utils.functions import message_line, name_emoji_from_channel, safe_username
from src.utils.matches import TUPPER_REPLY_PATTERN

__all__ = ("Information", "setup")


TENOR_URL = "https://g.tenor.com/v1/gifs"
GIPHY_URL = "https://api.giphy.com/v1/gifs"

TENOR_API = getenv("TENOR_API")
GIPHY_API = getenv("GIPHY_API")
WEATHER_API = getenv("WEATHER_API")

ICON_VALUES = {
    True: "\N{WHITE HEAVY CHECK MARK}",
    False: "\N{CROSS MARK}",
    None: "\N{BLACK SQUARE BUTTON}",
}


class AnnouncementModal(Modal):
    def __init__(self, *, word: str, name: str, **kwargs):
        super(AnnouncementModal, self).__init__(title=word, timeout=None)
        self.word = word

        self.kwargs = kwargs
        self.thread_name = TextInput(
            label="Title",
            placeholder=word,
            default=name,
            required=True,
            max_length=100,
        )
        self.add_item(self.thread_name)

        self.poll_data = TextInput(
            label="Poll Data",
            style=discord.TextStyle.paragraph,
            placeholder="Value, Value, Value",
            required=True,
        )
        self.poll_range = TextInput(
            label="Poll min-max values (e.g. 1-2 or 4)",
            placeholder="1 - 25",
            default="1",
            required=True,
        )
        self.required = TextInput(
            label="Required Roles",
            placeholder="True/False",
            default="True",
            required=False,
        )

        self.thread_mode = kwargs.pop("thread", False)
        self.poll_mode = kwargs.pop("poll", word == "Poll")

        if self.poll_mode:
            self.add_item(self.poll_data)
            self.add_item(self.poll_range)

    async def on_submit(self, itx: discord.Interaction[CustomBot]):
        embeds: list[discord.Embed] = self.kwargs.get("embeds", [])
        await itx.response.defer(ephemeral=True, thinking=True)
        webhook = await itx.client.webhook(itx.channel)

        if embeds:
            embeds[0].title = self.thread_name.value
            embeds[0].set_author(
                name=itx.user.display_name,
                icon_url=itx.user.avatar,
                url="https://ko-fi.com/Vioshim" if await itx.client.is_owner(itx.user) else None,
            )

        msg = await webhook.send(
            **self.kwargs,
            allowed_mentions=discord.AllowedMentions(everyone=True, roles=True),
            wait=True,
        )

        if self.poll_mode:
            db: AsyncIOMotorCollection = itx.client.mongo_db("Poll")
            if not (answers := [int(o) for x in self.poll_range.value.split("-") if (o := x.strip()) and o.isdigit()]):
                answers = [1]
            view = PollView(
                options={o: [] for x in self.poll_data.value.split(",") if (o := x.strip())},
                min_values=int(answers[0]),
                max_values=int(answers[-1]),
                required=self.required.value.lower() == "true",
            )
            await msg.edit(view=view)
            await db.insert_one({"id": msg.id} | view.data)

        if self.thread_mode:
            thread = await msg.create_thread(name=self.thread_name.value)
            await thread.add_user(itx.user)
            match self.word:
                case "OC Question" | "Story" | "Storyline" | "Mission":
                    if dproxy := itx.guild.get_member(1061328084307034212):
                        await thread.add_user(dproxy)
                    if tupper := itx.guild.get_member(431544605209788416):
                        await thread.add_user(tupper)

        await itx.followup.send("Thread created successfully", ephemeral=True)
        self.stop()


class AnnouncementView(View):
    def __init__(
        self,
        *,
        member: discord.Member,
        ping_roles: dict[str, int],
        word_channels: dict[int, str],
        **kwargs,
    ):
        super(AnnouncementView, self).__init__()
        self.member = member
        self.kwargs = kwargs
        self.ping_roles = ping_roles
        self.word_channels = word_channels
        self.format()

    async def interaction_check(self, interaction: discord.Interaction[CustomBot]) -> bool:
        if interaction.user != self.member:
            await interaction.response.send_message(f"Message requested by {self.member.mention}", ephemeral=True)
            return False
        return True

    def format(self):
        self.features.options.clear()
        self.features.add_option(
            label="Add a thread",
            value="thread",
            emoji=discord.PartialEmoji(name="messageupdate", id=432986578927747073),
        )
        self.features.add_option(
            label="Add a poll",
            value="poll",
            emoji=discord.PartialEmoji(name="channelcreate", id=432986578781077514),
        )
        self.features.add_option(
            label="Cancel Process",
            value="cancel",
            emoji="\N{CROSS MARK}",
        )
        if self.member.guild_permissions.administrator:
            for k, v in self.ping_roles.items():
                self.features.add_option(
                    label=f"{k} Role",
                    value=f"{v}",
                    description=f"Pings the {k} role",
                    emoji="\N{CHEERING MEGAPHONE}",
                )

    @select(placeholder="Select Features", max_values=3)
    async def features(self, itx: discord.Interaction[CustomBot], sct: Select):
        if str(itx.guild_id) in sct.values:
            self.kwargs["content"] = "@everyone"
        elif roles := " ".join(o.mention for x in sct.values if x.isdigit() and (o := itx.guild.get_role(int(x)))):
            self.kwargs["content"] = roles
        else:
            self.kwargs["content"] = None

        self.kwargs["poll"] = "poll" in sct.values
        self.kwargs["thread"] = "thread" in sct.values

        if "cancel" in sct.values:
            await itx.response.pong()
        else:
            word = self.word_channels.get(itx.channel_id)
            data = itx.created_at.astimezone(tz=DEFAULT_TIMEZONE)
            name = f"{word} {itx.user.display_name} {data.strftime('%B %d')}"
            modal = AnnouncementModal(word=word, name=name, **self.kwargs)
            await itx.response.send_modal(modal)
            await modal.wait()

        await itx.message.delete(delay=0)
        self.stop()


class Information(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready = False
        self.message: Optional[discord.Message] = None
        self.bot.tree.on_error = self.on_error
        self.info_data: dict[int, dict[str, dict[str, int] | int | list[int]]] = {}

    @commands.Cog.listener()
    async def on_ready(self):
        """Loads the program in the scheduler"""
        if self.ready:
            return

        db = self.bot.mongo_db("Poll")
        async for item in db.find({}, {"_id": 0}):
            item_id = item.pop("id", None)
            self.bot.add_view(PollView(**item), message_id=item_id)

        db = self.bot.mongo_db("InfoData")
        async for item in db.find({}, {"_id": 0}):
            server_id = item.pop("server", None)

            word_channels = item.pop("word_channels", {})
            item["word_channels"] = {v: k for k, v in word_channels.items()}

            self.info_data[server_id] = item

        self.ready = True

    @app_commands.command()
    @app_commands.guilds(1065784144417787994, 952518750748438549, 1196879060173852702)
    @app_commands.checks.has_any_role("Booster", "Supporter")
    async def perks(
        self,
        itx: discord.Interaction[CustomBot],
        perk: CustomPerks,
        icon: Optional[discord.Attachment] = None,
    ):
        """Custom Functions for Supporters!

        Parameters
        ----------
        ctx : Interaction
            Interaction
        perk : Perks
            Perk to Use
        icon : Attachment
            Image File
        """
        if not icon or str(icon.content_type).startswith("image"):
            try:
                await perk.method(itx, icon)
            except Exception as e:
                self.bot.logger.exception("Exception in perks", exc_info=e)
                await itx.response.send_message(str(e), ephemeral=True)
        else:
            await itx.response.send_message("Valid File Format: image/png", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        data = self.info_data.get(member.guild.id, {})
        if not (info := data.get("member_remove", {})):
            return

        guild = member.guild
        embed = discord.Embed(
            title="Member Left - Roles",
            description="The user did not have any roles.",
            color=discord.Colour.red(),
            timestamp=utcnow(),
        )
        if roles := member.roles[:0:-1]:
            embed.description = "\n".join(f"> **•** {role.mention}" for role in roles)
        if icon := guild.icon:
            embed.set_footer(text=f"ID: {member.id}", icon_url=icon.url)
        else:
            embed.set_footer(text=f"ID: {member.id}")

        embed.set_image(url=WHITE_BAR)
        view = View()

        db1 = self.bot.mongo_db("Roleplayers")
        if item := await db1.find_one({"user": member.id, "server": member.guild.id}):
            url = f"https://discord.com/channels/{guild.id}/{item['id']}"
            view.add_item(Button(label="Characters", url=url))

        db = self.bot.mongo_db("Custom Role")
        if data := await db.find_one({"author": member.id, "server": member.guild.id}):
            if role := get(member.guild.roles, id=data["id"]):
                with suppress(discord.DiscordException):
                    await role.delete(reason="User left")

            await db.delete_one(data)

        asset = member.display_avatar.replace(format="png", size=4096)
        file = await asset.to_file()
        embed.set_thumbnail(url=f"attachment://{file.filename}")

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Join Logging")
        await log.send(
            content=member.mention,
            file=file,
            embed=embed,
            view=view,
            username=safe_username(member.display_name),
            thread=thread,
            avatar_url=member.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        data = self.info_data.get(member.guild.id, {})
        if not (info := data.get("member_join", {})):
            return

        date = utcnow()
        embed = discord.Embed(description=f"{member.mention} - {member}", timestamp=date)
        if member.created_at >= date - timedelta(days=30):
            embed.title = "Member Joined - Account Created Recently"
            embed.color = discord.Colour.orange()
            await member.timeout(timedelta(days=7), reason="Account created less than 30 days ago.")
        else:
            embed.title = "Member Joined"
            embed.color = discord.Colour.green()

        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {member.id}")
        asset = member.display_avatar.replace(format="png", size=512)

        file = await asset.to_file()
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.add_field(name="Account Age", value=format_dt(member.created_at, style="R"))
        view = View()
        db1 = self.bot.mongo_db("Roleplayers")
        if item := await db1.find_one({"user": member.id, "server": member.guild.id}):
            url = f"https://discord.com/channels/{member.guild.id}/{item['id']}"
            view.add_item(Button(label="Characters", url=url))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Join Logging")
        await log.send(
            content=member.mention,
            embed=embed,
            file=file,
            view=view,
            thread=thread,
            username=safe_username(member.display_name),
            avatar_url=member.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_member_update(self, past: discord.Member, now: discord.Member):
        data = self.info_data.get(now.guild.id, {})
        info = {}
        embeds: list[discord.Embed] = []
        files: list[discord.File] = []

        if past.premium_since != now.premium_since:

            if not (info := data.get("member_boost", {})):
                return

            if past.premium_since and not now.premium_since:
                embed = discord.Embed(title="Has un-boosted the Server!", colour=discord.Colour.red())
                db = self.bot.mongo_db("Custom Role")
                if (data := await db.find_one_and_delete({"author": now.id, "server": now.guild.id})) and (
                    role := get(now.guild.roles, id=data["id"])
                ):
                    if role.icon:
                        file = await role.icon.to_file()
                        embed.set_thumbnail(url=f"attachment://{file.filename}")
                        files.append(file)
                    embed.add_field(name="Name", value=role.name)
                    embed.add_field(name="Color", value=role.color)

                    with suppress(discord.DiscordException):
                        await role.delete(reason="User unboosted")
            else:
                embed = discord.Embed(title="Has boosted the Server!", colour=discord.Colour.brand_green())
            embeds.append(embed)

        elif (past.display_name, past.display_avatar) != (now.display_name, now.display_avatar):

            if not (info := data.get("member_update", {})):
                return

            embed1 = discord.Embed(title=past.display_name, colour=discord.Colour.red())
            embed2 = discord.Embed(title=now.display_name, colour=discord.Colour.brand_green())

            if past.display_avatar != now.display_avatar:
                file = await now.display_avatar.with_size(4096).to_file()
                embed1.set_thumbnail(url=past.display_avatar)
                embed2.set_thumbnail(url=f"attachment://{file.filename}")
                files.append(file)

            embeds.extend([embed1, embed2])

        if embeds:
            embeds[0].set_author(name=now.display_name, icon_url=now.display_avatar)
            embeds[-1].set_footer(text=now.guild.name, icon_url=now.guild.icon)
            for embed in embeds:
                embed.set_image(url=WHITE_BAR)

        if info and now.guild.me.guild_permissions.manage_webhooks:
            channel_id = info["id"]
            if thread_id := info.get("thread"):
                thread = discord.Object(id=thread_id)
            else:
                thread = MISSING

            log = await self.bot.webhook(channel_id, reason="Logging")
            await log.send(
                content=now.mention,
                embed=embed,
                files=files,
                thread=thread,
                username=safe_username(now.display_name),
                avatar_url=now.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.Member | discord.User):
        data = self.info_data.get(guild.id, {})
        if not (info := data.get("member_ban", {})):
            return

        embed = discord.Embed(
            title="Member Banned",
            colour=discord.Colour.red(),
            description=f"{user.mention} - {user}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {user.id}")
        asset = user.display_avatar.replace(format="png", size=512)

        file = await asset.to_file()
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.add_field(name="Account Age", value=format_dt(user.created_at, style="R"))
        view = View()
        db1 = self.bot.mongo_db("Roleplayers")
        if item := await db1.find_one({"user": user.id, "server": guild.id}):
            url = f"https://discord.com/channels/{guild.id}/{item['id']}"
            view.add_item(Button(label="Characters", url=url))
        else:
            view.add_item(Button(label="Account Link", url=f"https://discord.com/users/{user.id}"))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Join Logging")
        await log.send(
            content=user.mention,
            embed=embed,
            file=file,
            view=view,
            thread=thread,
            username=safe_username(user.display_name),
            avatar_url=user.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_role_create(self, role: discord.Role):
        """Role Create Event

        Parameters
        ----------
        role : Role
            Added role
        """
        data = self.info_data.get(role.guild.id, {})
        if not (info := data.get("server_changes", {})) or "role_create" not in data.get("features", []):
            return

        embed = discord.Embed(
            title="Role Created",
            description=role.name,
            color=role.color,
            timestamp=role.created_at,
        )
        if isinstance(icon := role.display_icon, discord.Asset):
            embed.set_thumbnail(url=icon)
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=role.guild.name, icon_url=role.guild.icon)

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Join Logging")
        await log.send(embed=embed, thread=thread)

    @commands.Cog.listener()
    async def on_role_delete(self, role: discord.Role):
        """Role Delete Event

        Parameters
        ----------
        role : Role
            Added role
        """
        data = self.info_data.get(role.guild.id, {})
        if not (info := data.get("server_changes", {})) or "role_delete" not in data.get("features", []):
            return

        embed = discord.Embed(
            title="Role Deleted",
            description=role.name,
            color=role.color,
            timestamp=role.created_at,
        )
        files = []
        if isinstance(icon := role.display_icon, discord.Asset):
            files.append(file := await icon.to_file())
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=role.guild.name, icon_url=role.guild.icon)

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Role delete")
        await log.send(embed=embed, files=files, thread=thread)

    @commands.Cog.listener()
    async def on_role_update(self, before: discord.Role, after: discord.Role):
        """Role Update Event

        Parameters
        ----------
        before : Role
            Role before editing
        after : Role
            Role after editing
        """

        data = self.info_data.get(after.guild.id, {})
        if not (info := data.get("server_changes", {})) or "role_update" not in data.get("features", []):
            return

        embed1 = discord.Embed(title=f"Role Update: {after.name}", colour=before.color, timestamp=before.created_at)
        embed1.set_image(url=WHITE_BAR)

        embed2 = discord.Embed(colour=after.color, timestamp=utcnow())
        embed2.set_image(url=WHITE_BAR)

        embeds, files = [embed1, embed2], []

        if condition := before.name != after.name:
            embed1.title = f"Role Before: {before.name}"
            embed2.title = f"Role Afterwards: {after.name}"

        condition |= before.color != after.color

        if before.display_icon != after.display_icon:
            condition = True
            for aux1, aux2 in zip([embed1, embed2], [before.display_icon, after.display_icon]):
                if isinstance(aux2, discord.Asset):
                    aux1.url = WHITE_BAR
                    files.append(file := await aux2.to_file())
                    aux1.set_image(url=f"attachment://{file.filename}")
                else:
                    aux1.description = f"Icon: {aux2}"

        if before.permissions != after.permissions:
            condition = True
            embeds.append(
                discord.Embed(
                    title="Updated Permissions",
                    description="\n".join(
                        f"• {ICON_VALUES[v1]} -> {ICON_VALUES[v2]}: {k1.replace('_', ' ').title()}"
                        for ((k1, v1), (k2, v2)) in zip(before.permissions, after.permissions)
                        if k1 == k2 and v1 != v2
                    ),
                    color=discord.Colour.blurple(),
                    timestamp=utcnow(),
                ).set_image(url=WHITE_BAR)
            )

        if not condition:
            return

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(embeds=embeds, files=files, thread=thread)

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: discord.Guild,
        before: list[discord.Emoji],
        after: list[discord.Emoji],
    ):
        """Guild Emoji Update

        Parameters
        ----------
        guild : Guild
            Guild
        before : list[Emoji]
            Cached Emojis
        after : list[Emoji]
            New Emojis
        """
        data = self.info_data.get(guild.id, {})
        if not (info := data.get("server_changes", {})) or "guild_emojis_update" not in data.get("features", []):
            return

        aux_before, aux_after = set[discord.Emoji](before), set[discord.Emoji](after)
        description = "\n".join(f"+ {x} - {x!r}" for x in (aux_after - aux_before))
        embed = discord.Embed(
            title="Emoji Changes",
            description=description,
            color=discord.Colour.blurple(),
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)

        embeds, files = [embed], []

        for item in aux_before - aux_after:
            files.append(file := await item.to_file())
            e = discord.Embed(title=item.name)
            e.set_thumbnail(url=f"attachment://{file.filename}")
            e.set_image(url=WHITE_BAR)
            e.set_footer(text=f"ID: {item.id}")

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(embeds=embeds, thread=thread)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        """Channel Create Event

        Parameters
        ----------
        channel : GuildChannel
            Channel Deleted
        after : GuildChannel
            Channel after editing
        """
        data = self.info_data.get(channel.guild.id, {})
        if not (info := data.get("server_changes", {})) or "guild_channel_create" not in data.get("features", []):
            return

        if not isinstance(channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title=f"Channel Create: {channel.name}",
            description=channel.topic,
            colour=discord.Colour.green(),
            timestamp=channel.created_at,
        )

        for item, perms in channel.overwrites.items():
            if len(embed.fields) >= 25:
                break

            name = getattr(item, "name", str(item))

            text = "\n".join(
                f"{ICON_VALUES[value]}: {key.replace('_', ' ').title()}" for key, value in perms if value is not None
            )
            if text:
                embed.add_field(name=name, value=text[:1024])

        view = View()
        cat_name = getattr(channel.category, "name", "No Category")
        embed.set_footer(text=f"Category: {cat_name}")
        name, emoji = name_emoji_from_channel(channel)
        view.add_item(Button(emoji=emoji, label=name, url=channel.jump_url))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(embed=embed, view=view, thread=thread)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        """Channel Update Event

        Parameters
        ----------
        channel : GuildChannel
            Channel Deleted
        after : GuildChannel
            Channel after editing
        """

        data = self.info_data.get(channel.guild.id, {})
        if not (info := data.get("server_changes", {})) or "guild_channel_delete" not in data.get("features", []):
            return

        embed = discord.Embed(
            title=f"Channel Delete: {channel.name}",
            description=getattr(channel, "topic", None),
            colour=discord.Colour.red(),
            timestamp=channel.created_at,
        )

        for item, perms in channel.overwrites.items():
            if len(embed.fields) >= 25:
                break

            name = getattr(item, "name", str(item))

            text = "\n".join(
                f"{ICON_VALUES[value]}: {key.replace('_', ' ').title()}" for key, value in perms if value is not None
            )
            if text:
                embed.add_field(name=name, value=text[:1024])

        if threads := "\n".join(f"• {x.name}" for x in getattr(channel, "threads", [])):
            embed.title = f"{embed.title} - Deleted Threads"
            embed.description = threads[:4096]

        view = View()
        name, emoji = name_emoji_from_channel(channel)
        if category := channel.category:
            embed.set_footer(text=f"Category: {category.name}")
            view.add_item(Button(emoji=emoji, label=name, url=category.jump_url))
        else:
            embed.set_footer(text="No Category")
            view.add_item(Button(emoji=emoji, label=name, url=channel.jump_url))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(embed=embed, view=view, thread=thread)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: GuildChannel,
        after: GuildChannel,
    ):
        """Channel Update Event

        Parameters
        ----------
        before : GuildChannel
            Channel before editing
        after : GuildChannel
            Channel after editing
        """
        data = self.info_data.get(after.guild.id, {})
        if not (info := data.get("server_changes", {})) or "guild_channel_update" not in data.get("features", []):
            return

        embed1 = discord.Embed(
            title=f"Channel Update: {after.name}",
            colour=discord.Colour.red(),
            timestamp=before.created_at,
        )
        embed1.set_image(url=WHITE_BAR)
        embed2 = discord.Embed(
            colour=discord.Colour.green(),
            timestamp=utcnow(),
        )
        embed2.set_image(url=WHITE_BAR)

        embeds = [embed1]

        topic1 = getattr(before, "topic", None)
        topic2 = getattr(after, "topic", None)
        if condition := before.name != after.name or topic1 != topic2:
            embed1.title = f"Channel Before: {before.name}"
            embed2.title = f"Channel Afterwards: {after.name}"
            if topic1 != topic2:
                embed1.description, embed2.description = topic1, topic2

        if not any(
            (
                after.category and after.category.overwrites == after.overwrites,
                before.overwrites == after.overwrites,
            )
        ):
            condition = True

            differences = discord.Embed(
                title="Permissions Overwritten",
                description="",
                colour=discord.Colour.blurple(),
                timestamp=utcnow(),
            )
            items = []

            for item in before.overwrites | after.overwrites:
                if len(differences.fields) >= 25:
                    break

                if item not in before.overwrites:
                    items.append(f"+ {item}")
                elif item not in after.overwrites:
                    items.append(f"- {item}")
                value1 = dict(before.overwrites.get(item, discord.PermissionOverwrite()))
                value2 = dict(after.overwrites.get(item, discord.PermissionOverwrite()))

                if text := "\n".join(
                    f"{icon1} -> {icon2}: {key.replace('_', ' ').title()}"
                    for key in value1
                    if value1[key] != value2[key]
                    and (icon1 := ICON_VALUES[value1[key]])
                    and (icon2 := ICON_VALUES[value2[key]])
                ):
                    differences.add_field(name=str(item), value=text[:1024])

            differences.description = "\n".join(items)

            embeds.append(differences)

        if not condition:
            return

        view = View()
        name, emoji = name_emoji_from_channel(after)
        view.add_item(Button(emoji=emoji, label=name, url=after.jump_url))

        if embed2.title or embed2.description:
            embeds.append(embed2)

        if before.category != after.category:
            condition = True
            cat_name1 = getattr(before.category, "name", "No Category")
            cat_name2 = getattr(after.category, "name", "No Category")
            embeds[-1].set_footer(text=f"Category: {cat_name1} -> {cat_name2}")

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(embeds=embeds, view=view, thread=thread)

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        data = self.info_data.get(guild.id, {})
        if not (info := data.get("member_unban", {})):
            return

        embed = discord.Embed(
            title="Member Unbanned",
            colour=discord.Colour.green(),
            description=f"{user.mention} - {user}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {user.id}")
        asset = user.display_avatar.replace(format="png", size=512)

        file = await asset.to_file()
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.add_field(name="Account Age", value=format_dt(user.created_at, style="R"))
        db1 = self.bot.mongo_db("Roleplayers")
        view = View()
        if item := await db1.find_one({"user": user.id, "server": guild.id}):
            url = f"https://discord.com/channels/{guild.id}/{item['id']}"
            view.add_item(Button(label="Characters", url=url))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Join Logging")
        await log.send(
            content=user.mention,
            embed=embed,
            file=file,
            view=view,
            thread=thread,
            username=safe_username(user.display_name),
            avatar_url=user.display_avatar.url,
        )

    async def on_message(self, message: discord.Message):
        if not message.guild:
            return

        data = self.info_data.get(message.guild.id, {})
        if not (info := data.get("word_channels", {})) or message.mention_everyone or message.role_mentions:
            return

        channel = message.channel
        context = await self.bot.get_context(message)

        if context.command:
            return

        if word := info.get(channel.id):
            if message.author.bot:
                return

            webhook = await self.bot.webhook(channel)

            if message.webhook_id and webhook.id != message.webhook_id:
                await message.delete(delay=0)
                return

            self.bot.msg_cache_add(message)
            kwargs = await self.embed_info(message)
            if embeds := kwargs.get("embeds", []):
                embeds[0].title = word
            del kwargs["view"]

            view = AnnouncementView(
                member=message.author,
                ping_roles=data.get("ping_roles", {}),
                word_channels=data.get("word_channels", {}),
                **kwargs,
            )
            conf_embed = discord.Embed(title=word, color=discord.Colour.blurple(), timestamp=utcnow())
            conf_embed.set_image(url=WHITE_BAR)
            conf_embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
            await message.reply(embed=conf_embed, view=view)
            await view.wait()
            await message.delete(delay=0)

        elif "tupper_logging" not in data.get("features", []):
            messages: list[discord.Message] = []

            def checker(m: discord.Message):
                if m.webhook_id and message.channel == m.channel:
                    messages.append(m)
                return False

            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(
                        self.bot.wait_for("message", check=checker, timeout=2),
                        name="Message",
                    ),
                    asyncio.create_task(
                        self.bot.wait_for("message_edit", check=lambda x, _: x == message),
                        name="Edit",
                    ),
                    asyncio.create_task(
                        self.bot.wait_for("message_delete", check=lambda x: x == message),
                        name="Delete",
                    ),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for future in pending:
                future.cancel()

            for future in done:
                future.exception()

            if any(future.get_name() == "Edit" for future in done):
                return

            attachments = message.attachments
            for msg in sorted(messages, key=lambda x: x.id):
                if data := TUPPER_REPLY_PATTERN.search(msg.content):
                    text = str(data.group("content") or msg.content)
                else:
                    text = msg.content

                if (
                    text in message.content
                    or fuzz.WRatio(text, message.content, score_cutoff=95)
                    or (
                        attachments
                        and len(attachments) == len(msg.attachments)
                        and all(x.filename == y.filename for x, y in zip(attachments, msg.attachments))
                    )
                ):
                    self.bot.msg_cache_add(message)
                    break

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Bump handler for message editing bots

        Parameters
        ----------
        before : Message
            Message before editing
        after : Message
            Message after editing
        """
        if not isinstance(member := after.author, discord.Member):
            return

        data = self.info_data.get(member.guild.id, {})
        if not (info := data.get("message_edit", {})) or member.bot:
            return

        embed1 = discord.Embed(
            title="Previous Message",
            colour=discord.Colour.red(),
            description="",
            timestamp=before.edited_at or before.created_at,
        )
        embed1.set_image(url=WHITE_BAR)
        embed2 = discord.Embed(
            title="Message Afterwards",
            colour=discord.Colour.green(),
            description="",
            timestamp=after.edited_at or utcnow(),
        )
        embed2.set_image(url=WHITE_BAR)

        embeds, files = [embed1, embed2], []

        if condition := before.content != after.content:
            embed1.description, embed2.description = before.content, after.content

        if before.attachments and not after.attachments:
            embed2.description += "Removed Attachments. "
            files = [await x.to_file(use_cached=True) for x in before.attachments]
            condition = True

        if before.pinned != after.pinned:
            condition = True
            if before.pinned:
                embed2.set_author(name="Unpinned Message")
            elif after.pinned:
                embed2.set_author(name="Pinned Message")

        if before.embeds and not after.embeds:
            condition = True
            embed2.description += "Removed Embeds. "
            embeds.extend(before.embeds)

        if not condition:
            return

        view = View()
        name, emoji = name_emoji_from_channel(after.channel)
        view.add_item(Button(emoji=emoji, label=name, url=after.jump_url))

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Edit Logging")
        await log.send(
            username=safe_username(member.display_name),
            avatar_url=member.display_avatar,
            files=files,
            embeds=embeds,
            view=view,
            thread=thread,
        )

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        """Cached Message deleted detection

        Parameters
        ----------
        message: Message
            Cached Message
        """
        if not msg.guild:
            return

        data = self.info_data.get(msg.guild.id, {})
        if not (info := data.get("message_delete", {})):
            return

        if (
            (msg.application_id == self.bot.user.id and msg.webhook_id)
            or self.bot.user == msg.author
            or msg.channel.name.endswith("-logs")
        ):
            return

        await asyncio.sleep(1)
        if msg.id in self.bot.msg_cache:
            return

        kwargs = await self.embed_info(msg)

        if not msg.webhook_id:
            kwargs["content"] = msg.author.mention

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        log = await self.bot.webhook(channel_id, reason="Message delete logging")
        await log.send(
            **kwargs,
            thread=thread,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Message deleted detection

        Parameters
        ----------
        payload: RawMessageDeleteEvent
            Deleted Message Event
        """
        with suppress(KeyError):
            self.bot.msg_cache.remove(payload.message_id)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[discord.Message]):
        """This coroutine triggers upon cached bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        if not (messages and messages[0].guild):
            return

        msg = messages[0]
        data = self.info_data.get(msg.guild.id, {})
        if not (info := data.get("bulk_message_delete", {})):
            return

        channel_id = info["id"]
        if thread_id := info.get("thread"):
            thread = discord.Object(id=thread_id)
        else:
            thread = MISSING

        w = await self.bot.webhook(channel_id, reason="Bulk delete logging")
        if (
            messages := [message_line(x) for x in messages if x.id not in self.bot.msg_cache and x.webhook_id != w.id]
        ) and (
            paste := await self.bot.m_bin.create_paste(
                filename=f"{utcnow().strftime('%x')} - {msg.channel}.yaml",
                content=dump(
                    data=messages,
                    allow_unicode=True,
                    sort_keys=False,
                ),
            )
        ):
            embed = discord.Embed(
                title="Bulk Message Delete",
                url=paste,
                description=f"Deleted {len(messages)} messages",
                timestamp=utcnow(),
            )
            embed.set_image(url=WHITE_BAR)
            embed.set_footer(text=msg.guild.name, icon_url=msg.guild.icon)

            view = View()
            name, emoji = name_emoji_from_channel(msg.channel)
            view.add_item(Button(emoji=emoji, label=name, url=msg.jump_url))
            view.add_item(Button(emoji=LINK_EMOJI, label="See Logs", url=str(paste)))

            await w.send(embed=embed, view=view, thread=thread)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """This coroutine triggers upon raw bulk message deletions.

        Parameters
        ----------
        payload: RawBulkMessageDeleteEvent
            Messages that were deleted.
        """
        self.bot.msg_cache -= payload.message_ids

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return

        try:
            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            if not (channel := guild.get_channel_or_thread(payload.channel_id)):
                channel = await guild.fetch_channel(payload.channel_id)

            message = await channel.fetch_message(payload.message_id)
            everyone = guild.get_role(guild.id)
            data = self.info_data.get(guild.id, {}).get("star_reactions", {})
            disabled_categories = data.get("disabled_categories", [])
            max_amount = data.get("max_amount", 3)

            reactions = [x for x in message.reactions if str(x.emoji) == str(payload.emoji)]
            reaction = reactions[0]

            if (
                not message.is_system()
                and channel.category_id is not None
                and message.author != self.bot.user
                and message.author != payload.member
                and bool(channel.permissions_for(everyone).add_reactions)
                and channel.category_id not in disabled_categories
                and all(x.type != "rich" for x in message.embeds)
                and (not message.author.bot or message.webhook_id)
            ):
                if reaction.count >= max_amount and not message.pinned:
                    await message.pin()
            else:
                await reaction.remove(payload.member)
        except discord.DiscordException as e:
            self.bot.logger.exception("Error on Star System", exc_info=e)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return

        try:
            guild: discord.Guild = self.bot.get_guild(payload.guild_id)
            if not (channel := guild.get_channel_or_thread(payload.channel_id)):
                channel = await guild.fetch_channel(payload.channel_id)

            if not (message := get(self.bot.cached_messages, id=payload.message_id)):
                message = await channel.fetch_message(payload.message_id)

            data = self.info_data.get(guild.id, {}).get("star_reactions", {})
            disabled_categories = data.get("disabled_categories", [])
            max_amount = data.get("max_amount", 3)

            if (
                (reactions := {x for x in message.reactions if str(x.emoji) == str(payload.emoji)})
                and not message.is_system()
                and channel.category_id is not None
                and message.author != self.bot.user
                and message.author != payload.member
                and bool(channel.permissions_for(guild.default_role).add_reactions)
                and channel.category_id not in disabled_categories
                and all(x.type != "rich" for x in message.embeds)
                and (not message.author.bot or message.webhook_id)
                and reactions.pop().count < max_amount
                and message.pinned
            ):
                await message.unpin()
        except discord.DiscordException as e:
            self.bot.logger.exception("Error on Star System", exc_info=e)

    async def tenor_fetch(self, image_id: str):
        try:
            params = {"ids": image_id, "key": TENOR_API}
            async with self.bot.session.get(url=TENOR_URL, params=params) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["results"][0]
                    media = result["media"][0]
                    title: str = result["title"] or result["content_description"]
                    url: str = result["itemurl"]
                    image: str = media["gif"]["url"]
                    return title, url, image
        except (ClientResponseError, IndexError, KeyError):
            return None

    async def giphy_fetch(self, image_id: str):
        URL = f"{GIPHY_URL}/{image_id}"
        try:
            params = {"api_key": GIPHY_API}
            async with self.bot.session.get(url=URL, params=params) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["data"]
                    title: str = result["title"]
                    url: str = result["url"]
                    image: str = result["images"]["original"]["url"]
                    return title, url, image
        except (ClientResponseError, KeyError):
            return None

    async def gif_fetch(self, url: str):
        image_id = url.split("-")[-1]
        if url.startswith("https://tenor.com/"):
            return await self.tenor_fetch(image_id)
        if url.startswith("https://giphy.com/"):
            return await self.giphy_fetch(image_id)

    async def embed_info(self, message: discord.Message):
        embeds: list[discord.Embed] = []
        if content := message.content:
            embed = discord.Embed(
                title="Message",
                description=content,
                color=discord.Colour.blurple(),
            )
            embed.set_image(url=WHITE_BAR)
        else:
            embed = discord.Embed()
        embeds.append(embed)
        for sticker in message.stickers:
            if embed.title == "Sticker":
                aux = discord.Embed(color=discord.Colour.blurple())
                embeds.append(aux)
            else:
                aux = embed
                aux.description = None

            aux.title = "Sticker"
            aux.set_image(url=sticker.url)
            aux.add_field(name="Sticker Name", value=sticker.name)

        for e in message.embeds:
            match e.type:
                case "gifv":
                    if data := await self.gif_fetch(e.url):
                        gif_title, gif_url, gif_image = data
                        if embed.title == "GIF":
                            aux = discord.Embed(color=discord.Colour.blurple())
                            embeds.append(aux)
                        else:
                            aux = embed
                            aux.description = None

                        aux.title = "GIF"
                        aux.url = gif_url
                        aux.set_image(url=gif_image)
                        aux.add_field(name="GIF Title", value=gif_title)
                case "image":
                    if embed.description == e.url:
                        aux = embed
                    else:
                        aux = discord.Embed(color=discord.Colour.blurple())
                        embeds.append(aux)
                    aux.set_image(url=e.url)
                case "article" | "link":
                    if message.content == e.url:
                        aux = embed
                        aux.title = e.title
                        aux.description = e.description
                        aux.url = e.url
                    else:
                        aux = e
                    if provider := e.provider:
                        aux.set_author(name=provider.name, url=provider.url or e.url)
                    if thumbnail := e.thumbnail:
                        aux.set_image(url=thumbnail.url)
                        aux.set_thumbnail(url=None)
                    if aux != embed:
                        embeds.append(aux)
                case _:
                    embeds.append(e)

        files = [await x.to_file() for x in message.attachments]
        view = View()
        name, emoji = name_emoji_from_channel(message.channel)
        view.add_item(Button(emoji=emoji, label=name, url=message.jump_url))

        username: str = message.author.display_name
        if message.author.bot and "〕" not in username:
            username = f"Bot〕{username}"

        if embeds := embeds[1:11] if embeds[0] == discord.Embed() else embeds[:10]:
            last_embed = embeds[-1]
            last_embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
            last_embed.timestamp = utcnow()

        return dict(
            embeds=embeds,
            files=files,
            view=view,
            username=safe_username(username),
            avatar_url=message.author.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context[CustomBot]):
        """This allows me to check when commands are being used.

        Parameters
        ----------
        ctx: Context
            Context
        """
        name: str = ctx.guild.name if ctx.guild else "Private Message"
        self.bot.logger.info("%s > %s > %s", name, ctx.author, ctx.command.qualified_name)

    async def on_error(self, itx: discord.Interaction[CustomBot], error: app_commands.AppCommandError):
        error: Exception | app_commands.AppCommandError = getattr(error, "original", error)
        command = itx.command
        if command and command._has_any_error_handlers():  # skipcq: PYL-W0212
            return

        self.bot.logger.error(
            "Interaction Error(%s, %s)",
            getattr(command, "name", "Unknown"),
            ", ".join(f"{k}={v}" for k, v in itx.data.items()),
            exc_info=error,
        )

        with suppress(discord.NotFound):
            if not itx.response.is_done():
                await itx.response.defer(thinking=True, ephemeral=True)

        embed = discord.Embed(
            color=discord.Colour.red(),
            timestamp=itx.created_at,
        )
        embed.set_image(url=WHITE_BAR)

        if not isinstance(error, app_commands.AppCommandError):
            embed.title = f"Error - {type(error := error.__cause__ or error).__name__}"
            embed.description = f"```py\n{error}\n```"
        else:
            embed.title = f"Error - {type(error).__name__}"
            embed.description = str(error)

        with suppress(discord.NotFound):
            await itx.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context[CustomBot], error: commands.CommandError):
        """Command error handler

        Parameters
        ----------
        ctx: Context
            Context
        error: CommandError
            Error
        """
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
                commands.DisabledCommand,
            ),
        ):
            await ctx.send(
                embed=discord.Embed(
                    color=discord.Colour.red(),
                    title=f"Error - {ctx.command.qualified_name}",
                    description=str(error),
                )
            )
            return

        if hasattr(ctx.command, "on_error"):
            return

        # skipcq: PYL-W0212
        if (cog := ctx.cog) and cog._get_overridden_method(cog.cog_command_error):
            return

        error_cause = error.__cause__ or error
        await ctx.send(
            embed=discord.Embed(
                color=discord.Colour.red(),
                title=f"Unexpected error - {ctx.command.qualified_name}",
                description=f"```py\n{type(error_cause).__name__}: {error_cause}\n```",
            )
        )

        self.bot.logger.error(
            "Command Error(%s, %s)",
            ctx.command.qualified_name,
            ", ".join(f"{k}={v!r}" for k, v in ctx.kwargs.items()),
            exc_info=error,
        )


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Information(bot))
