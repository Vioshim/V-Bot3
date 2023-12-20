# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Vioshim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import dateparser
import discord
import webcolors
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ext import commands
from discord.utils import get, utcnow
from humanize import naturaltime
from rapidfuzz import process

from src.structures.bot import CustomBot as Client
from src.structures.mon_typing import TypingEnum
from src.structures.move import Category
from utils.imagekit import ImageKit

__all__ = ("DateConverter", "GuildArg")


class ColorConverter(commands.Converter[discord.Color]):
    async def convert(self, ctx: commands.Context[Client], argument: str, /) -> discord.Color:
        if argument.lower() == "d-proxy":
            argument = "#94939f"

        with suppress(ValueError):
            color = webcolors.name_to_rgb(argument)
            return discord.Color.from_rgb(color.red, color.green, color.blue)

        return await commands.ColourConverter().convert(ctx, argument)


@dataclass(slots=True)
class Context:
    bot: Client
    author: discord.Member
    guild: discord.Guild


class ImageURLConverter(commands.Converter[str]):
    @classmethod
    async def method(cls, ctx: commands.Context | discord.Interaction, argument: str, /) -> str:
        if not argument or argument.startswith("attachment://"):
            return argument or ""

        aux = Context(bot=ctx.client, author=ctx.user, guild=ctx.guild) if isinstance(ctx, discord.Interaction) else ctx

        name, *args = argument.strip().split()
        attachments: list[discord.Attachment] = []
        if ctx.message:
            attachments.extend(x for x in ctx.message.attachments if str(x.content_type).startswith("image/"))

        match [name.lower(), *args]:
            case ["default"]:
                return aux.author.default_avatar.url
            case ["default", index]:
                if index.isdigit():
                    return f"https://cdn.discordapp.com/embed/avatars/{index}.png"
            case ["event"]:
                events = [x for x in aux.guild.scheduled_events if x.cover_image]
                if data := sorted(events, key=lambda x: x.id, reverse=True):
                    return data[0].cover_image.url
            case ["sticker", *args]:
                try:
                    sticker = await commands.GuildStickerConverter().convert(aux, "".join(args))
                except commands.BadArgument as e:
                    if sticker := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.stickers,
                        score_cutoff=60,
                        processor=lambda x: x.name if isinstance(x, discord.Sticker) else x,
                    ):
                        sticker = sticker[0]
                    else:
                        raise commands.BadArgument(f"Invalid sticker: {argument}") from e
                return sticker.url
            case ["emoji", *args]:
                try:
                    emoji = await commands.EmojiConverter().convert(aux, "".join(args))
                except commands.BadArgument as e:
                    if emoji := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.emojis,
                        score_cutoff=60,
                        processor=lambda x: x.name if isinstance(x, discord.Emoji) else x,
                    ):
                        emoji = emoji[0]
                    else:
                        raise commands.BadArgument(f"Invalid emoji: {argument}") from e

                return emoji.url
            case ["event", *args]:
                try:
                    event = await commands.ScheduledEventConverter().convert(aux, "".join(args))
                except commands.BadArgument as e:
                    if event := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.scheduled_events,
                        score_cutoff=60,
                        processor=lambda x: x.name if isinstance(x, discord.ScheduledEvent) else x,
                    ):
                        event = event[0]
                    else:
                        raise commands.BadArgument(f"Invalid event: {argument}") from e

                return event.cover_image and event.cover_image.url
            case ["server" | "guild"]:
                return ctx.guild.icon and ctx.guild.icon.url
            case ["server" | "guild", *args]:
                try:
                    guild = await commands.GuildConverter().convert(aux, " ".join(args))
                except commands.BadArgument as e:
                    if guild := process.extractOne(
                        " ".join(args),
                        choices=ctx.author.mutual_guilds,
                        score_cutoff=60,
                        processor=lambda x: x.display_name if isinstance(x, discord.Member) else x,
                    ):
                        guild = guild[0]
                    else:
                        raise commands.BadArgument(f"Invalid server: {argument}") from e
                return guild.icon and guild.icon.url
            case ["user" | "member", *args, "default" | "Default"]:
                try:
                    user = await commands.MemberConverter().convert(aux, " ".join(args))
                except commands.BadArgument as e:
                    if user := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.members if ctx.guild else [aux.bot.user, ctx.author],
                        score_cutoff=60,
                        processor=lambda x: x.display_name if isinstance(x, discord.Member) else x,
                    ):
                        user = user[0]
                    else:
                        raise commands.BadArgument(f"Invalid user: {argument}") from e
                return user.default_avatar.url
            case ["banner", *args]:
                try:
                    user = await commands.MemberConverter().convert(aux, " ".join(args))
                except commands.BadArgument as e:
                    if user := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.members if ctx.guild else [aux.bot.user, ctx.author],
                        score_cutoff=60,
                        processor=lambda x: x.display_name if isinstance(x, discord.Member) else x,
                    ):
                        user = user[0]
                    else:
                        raise commands.BadArgument(f"Invalid user: {argument}") from e
                return user.banner and user.banner.url
            case ["user" | "member", *args]:
                try:
                    user = await commands.MemberConverter().convert(aux, " ".join(args))
                except commands.BadArgument as e:
                    if user := process.extractOne(
                        " ".join(args),
                        choices=ctx.guild.members if ctx.guild else [aux.bot.user, ctx.author],
                        score_cutoff=60,
                        processor=lambda x: x.display_name if isinstance(x, discord.Member) else x,
                    ):
                        user = user[0]
                    else:
                        raise commands.BadArgument(f"Invalid user: {argument}") from e
                icon = user.display_avatar
                if name.lower() == "user":
                    icon = user.avatar or icon
                return icon.url
            case ["attachment"]:
                if attachments:
                    return f"attachment://{attachments[0].filename}"
            case ["attachment", *args]:
                name_index = " ".join(args)
                if attachments and (
                    attachment := get(attachments, filename=name_index)
                    or (name_index.isdigit() and ctx.message.attachments[int(name_index)])
                ):
                    return f"attachment://{attachment.filename}"
            case ["bar" | "line"]:
                return "https://dummyimage.com/500x5/FFFFFF/000000&text=%20"
            case ["typing" | "type", *args]:
                if item := process.extractOne(
                    " ".join(args),
                    choices=TypingEnum,
                    score_cutoff=60,
                    processor=lambda x: x.name if isinstance(x, TypingEnum) else x,
                ):
                    return item[0].emoji.url
            case ["category", *args]:
                if item := process.extractOne(
                    " ".join(args),
                    choices=Category,
                    score_cutoff=60,
                    processor=lambda x: x.name if isinstance(x, Category) else x,
                ):
                    return item[0].url
        return argument

    async def convert(self, ctx: commands.Context[Client], argument: str, /) -> str:
        return await self.method(ctx, argument)

    @staticmethod
    def image_replacer(ctx: Optional[commands.Context[Client] | discord.Interaction[Client] | discord.Message] = None):
        def inner(url: str):
            url = (url and url.strip()) or ""

            BASE = "https://cdn.discordapp.com"

            attachments = []

            if isinstance(ctx, discord.Message):
                attachments = ctx.attachments
            elif ctx is not None and ctx.message:
                attachments = ctx.message.attachments

            if attachments and (
                item := get([x for x in attachments if str(x.content_type).startswith("image/")], url=url)
                or get(attachments, proxy_url=url)
            ):
                index = attachments.index(item)
                url = f"Attachment {index}"
            elif url == "https://dummyimage.com/500x5/FFFFFF/000000&text=%20":
                url = "Line"
            elif url.startswith(o := f"{BASE}/embed/avatars/"):
                url = f"Default {url.removeprefix(o).removesuffix('.png')}"
            elif o := get(TypingEnum, url=url):
                url = f"Type {o.name}"
            elif o := get(Category, url=url):
                url = f"Category {o.name}"
            elif getattr(ctx, "guild", None):
                if ctx.guild.icon and ctx.guild.icon.url == url:
                    url = "Server"
                elif url.startswith(o := f"{BASE}/avatars/"):
                    aux, data = url.removeprefix(o).split("/", 1)
                    if (
                        (member := ctx.guild.get_member(int(aux.strip())))
                        and member.avatar
                        and member.avatar.url == url
                    ):
                        url = f"User {member}"
                elif url.startswith(o := f"{BASE}/guilds/{ctx.guild.id}/users/"):
                    aux, data = url.removeprefix(o).split("/", 1)
                    if (member := ctx.guild.get_member(int(aux.strip()))) and member.display_avatar.url == url:
                        url = f"Member {member}"
                elif url.startswith(o := f"{BASE}/banners/"):
                    aux, data = url.removeprefix(o).split("/", 1)
                    if (
                        (member := ctx.guild.get_member(int(aux.strip())))
                        and member.banner
                        and member.banner.url == url
                    ):
                        url = f"Banner {member}"
                elif url.startswith(o := f"{BASE}/guild-events/"):
                    aux, data = url.removeprefix(o).split("/", 1)
                    if (
                        (event := ctx.guild.get_scheduled_event(int(aux.strip())))
                        and event.cover_image
                        and event.cover_image.url == url
                    ):
                        url = f"Event {event.name}"
                elif url.startswith(o := f"{BASE}/stickers/"):
                    aux, data = url.removeprefix(o).split(".", 1)
                    if (sticker := get(ctx.guild.stickers, id=int(aux.strip()))) and sticker.url == url:
                        url = f"Sticker {sticker.name}"
                elif url.startswith(o := f"{BASE}/emojis/"):
                    aux, data = url.removeprefix(o).split(".", 1)
                    if (emoji := get(ctx.guild.emojis, id=int(aux.strip()))) and emoji.url == url:
                        url = f"Emoji {emoji.name}"

            return url

        return inner


class DateConverter(commands.Converter[datetime]):
    async def convert(self, ctx: commands.Context[Client], argument: str, /) -> datetime:
        user_settings = await ctx.bot.fetch("UserSettings", id=ctx.author.id)
        tz = user_settings.tz or timezone.utc
        if date := dateparser.parse(
            argument,
            settings={
                "PREFER_DATES_FROM": "past",
                "TIMEZONE": str(tz),
                "RELATIVE_BASE": ctx.message.created_at.astimezone(tz),
            },
        ):
            return date.replace(tzinfo=tz)
        raise commands.BadArgument(f"Invalid_date: {argument}")


class EmbedFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    title: str = commands.flag(default="", aliases=["t"])
    description: str = commands.flag(default="", aliases=["d", "desc"])
    url: Optional[str] = None
    color: Optional[ColorConverter] = commands.flag(default=None, aliases=["colour"])
    image: Optional[ImageURLConverter] = None
    thumbnail: Optional[ImageURLConverter] = commands.flag(default=None, aliases=["th"])
    timestamp: Optional[DateConverter] = commands.flag(default=None, aliases=["date", "time"])
    author_name: Optional[str] = commands.flag(default=None, aliases=["an"])
    author_url: Optional[str] = commands.flag(default=None, aliases=["au"])
    author_icon: Optional[ImageURLConverter] = commands.flag(default=None, aliases=["ai"])
    footer_text: Optional[str] = commands.flag(default=None, aliases=["fo"])
    footer_icon: Optional[ImageURLConverter] = commands.flag(default=None, aliases=["foi"])
    field_name: list[str] = commands.flag(default=[], aliases=["fn"])
    field_value: list[str] = commands.flag(default=[], aliases=["fv"])
    field_inline: list[bool] = commands.flag(default=[], aliases=["fi"])

    @property
    def embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            url=self.url,
            color=self.color,
            timestamp=self.timestamp,
        )
        if self.image:
            embed.set_image(url=self.image)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        if self.author_name or self.author_url or self.author_icon:
            embed.set_author(
                name=self.author_name or "\u200b",
                url=self.author_url,
                icon_url=self.author_icon,
            )
        if self.footer_text or self.footer_icon:
            embed.set_footer(
                text=self.footer_text or "\u200b",
                icon_url=self.footer_icon,
            )

        items = [self.field_name, self.field_value, self.field_inline]

        max_size = max(items, key=len)
        for name, value, inline in zip(
            self.field_name + ["\u200b"] * (len(max_size) - len(self.field_name)),
            self.field_value + ["\u200b"] * (len(max_size) - len(self.field_value)),
            self.field_inline + [False] * (len(max_size) - len(self.field_inline)),
        ):
            embed.add_field(name=name, value=value, inline=inline)
        return embed

    @staticmethod
    def to_flags(
        ctx: Optional[commands.Context[Client] | discord.Interaction[Client] | discord.Message] = None,
        embed: discord.Embed = None,
    ):
        if embed is None:
            embed = discord.Embed()

        text = []
        image_replacer = ImageURLConverter.image_replacer(ctx)
        if embed.title:
            text.append(f"--title {embed.title}")
        if embed.description:
            text.append(f"--description {embed.description}")
        if embed.url:
            text.append(f"--url {embed.url}")
        if embed.color:
            try:
                color = webcolors.rgb_to_name(embed.color.to_rgb())
            except ValueError:
                color = str(embed.color)
                if color == "#94939f":
                    color = "D-Proxy"
            text.append(f"--color {color}")
        if embed.image:
            text.append(f"--image {image_replacer(embed.image.url)}")
        if embed.thumbnail:
            text.append(f"--thumbnail {image_replacer(embed.thumbnail.url)}")
        if embed.timestamp:
            text.append(f"--timestamp {naturaltime(embed.timestamp, when=utcnow())}")
        if embed.author:
            if embed.author.name != "\u200b":
                text.append(f"--author_name {embed.author.name}")
            if embed.author.url:
                text.append(f"--author_url {embed.author.url}")
            if embed.author.icon_url:
                text.append(f"--author_icon {image_replacer(embed.author.icon_url)}")
        if embed.footer:
            if embed.footer.text != "\u200b":
                text.append(f"--footer_text {embed.footer.text}")
            if embed.footer.icon_url:
                text.append(f"--footer_icon {image_replacer(embed.footer.icon_url)}")
        for field in embed.fields:
            text.extend(
                (
                    f"--fn {field.name}",
                    f"--fv {field.value}",
                    f"--fi {field.inline}",
                )
            )
        return "\n".join(text)


class ImageKitFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    base: str = commands.flag(aliases=["b"])
    height: Optional[int] = commands.flag(aliases=["h"], default=None)
    width: Optional[int] = commands.flag(aliases=["w"], default=None)
    img: list[ImageURLConverter] = commands.flag(aliases=["i"], default=[])
    img_height: list[int] = commands.flag(aliases=["ih"], default=[])
    img_width: list[int] = commands.flag(aliases=["iw"], default=[])
    img_pos_x: list[int] = commands.flag(aliases=["ix"], default=[])
    img_pos_y: list[int] = commands.flag(aliases=["iy"], default=[])

    @property
    def url(self) -> discord.Embed:
        base = ImageKit(base=self.base, height=self.height, width=self.width, format="png")
        img_pos_x = self.img_pos_x or [None] * len(self.img)
        img_pos_y = self.img_pos_y or [None] * len(self.img)
        img_height = self.img_height or [None] * len(self.img)
        img_width = self.img_width or [None] * len(self.img)
        for h, w, x, y, img in zip(
            img_height,
            img_width,
            img_pos_x,
            img_pos_y,
            self.img,
        ):
            base.add_image(
                img,
                height=h,
                width=w,
                x=x,
                y=y,
            )
        return base.url


class GuildTransformer(Transformer):
    async def transform(self, itx: discord.Interaction[Client], value: str, /):
        if value.isdigit() and (guild := itx.client.get_guild(int(value))):
            return guild

        if item := process.extractOne(
            value,
            choices=list(itx.user.mutual_guilds),
            score_cutoff=95,
            processor=lambda x: x.name if isinstance(x, discord.Guild) else x,
        ):
            return item[0]

        return itx.guild

    async def autocomplete(self, itx: discord.Interaction[Client], value: str, /) -> list[Choice[str]]:
        return [
            Choice(name=x[0].name[:100], value=str(x[0].id))
            for x in process.extract(
                value,
                choices=list(itx.user.mutual_guilds),
                limit=25,
                processor=lambda x: x.name if isinstance(x, discord.Guild) else x,
                score_cutoff=(60 if value else None),
            )
        ]


GuildArg = Transform[discord.Guild, GuildTransformer]
