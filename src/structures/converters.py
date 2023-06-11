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


from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Union

import dateparser
import discord
import webcolors
from dateparser import parse
from discord import Member, Message, User
from discord.ext import commands
from discord.file import File
from discord.utils import get, utcnow
from humanize import naturaltime
from rapidfuzz import process

from src.structures.bot import CustomBot
from src.structures.exceptions import (
    NoDateFound,
    NoImageFound,
    NoMoveFound,
    NoSpeciesFound,
)
from src.structures.mon_typing import TypingEnum
from src.structures.move import Category, Move
from src.structures.species import Species
from src.utils.matches import REGEX_URL


class ColorConverter(commands.Converter[discord.Color]):
    async def convert(self, ctx: commands.Context[CustomBot], argument: str, /) -> discord.Color:
        with suppress(ValueError):
            color = webcolors.name_to_rgb(argument)
            return discord.Color.from_rgb(color.red, color.green, color.blue)

        return await commands.ColourConverter().convert(ctx, argument)


class DateConverter(commands.Converter[datetime]):
    async def convert(self, ctx: commands.Context[CustomBot], argument: str, /) -> datetime:
        db = ctx.bot.mongo_db("AFK")
        data: dict[str, int] = await db.find_one({"user": ctx.author.id})
        offset = data.get("offset", 0) if data else 0
        tz = timezone(offset=timedelta(hours=offset))
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


@dataclass(slots=True)
class Context:
    bot: CustomBot
    author: discord.Member
    guild: discord.Guild
    command: commands.Command | None = None


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

    async def convert(self, ctx: commands.Context[CustomBot], argument: str, /) -> str:
        return await self.method(ctx, argument)

    @staticmethod
    def image_replacer(
        ctx: Optional[commands.Context[CustomBot] | discord.Interaction[CustomBot] | discord.Message] = None,
    ):
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
                    aux, _ = url.removeprefix(o).split("/", 1)
                    if (
                        (member := ctx.guild.get_member(int(aux.strip())))
                        and member.avatar
                        and member.avatar.url == url
                    ):
                        url = f"User {member}"
                elif url.startswith(o := f"{BASE}/guilds/{ctx.guild.id}/users/"):
                    aux, _ = url.removeprefix(o).split("/", 1)
                    if (member := ctx.guild.get_member(int(aux.strip()))) and member.display_avatar.url == url:
                        url = f"Member {member}"
                elif url.startswith(o := f"{BASE}/banners/"):
                    aux, _ = url.removeprefix(o).split("/", 1)
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
                    aux, _ = url.removeprefix(o).split(".", 1)
                    if (sticker := get(ctx.guild.stickers, id=int(aux.strip()))) and sticker.url == url:
                        url = f"Sticker {sticker.name}"
                elif url.startswith(o := f"{BASE}/emojis/"):
                    aux, _ = url.removeprefix(o).split(".", 1)
                    if (emoji := get(ctx.guild.emojis, id=int(aux.strip()))) and emoji.url == url:
                        url = f"Emoji {emoji.name}"

            return url

        return inner


class MovesCall(commands.Converter[Move]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str) -> str:
        """Function which converts to image url if possible

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Parsing str argument

        Returns
        -------
        str
            Image's URL

        Raises
        ------
        NoImageFound
            If no image was found
        """

        if data := Move.deduce(argument):
            return data

        raise NoMoveFound(argument)


class SpeciesCall(commands.Converter[Species]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str) -> Species:
        """Function which converts to Species if possible

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Parsing str argument

        Returns
        -------
        Species
            Resulting Species

        Raises
        ------
        NoSpeciesFound
            If no image was found
        """

        if data := Species.single_deduce(argument):
            return data

        raise NoSpeciesFound(argument)


class ImageURL(commands.Converter[str]):
    # skipcq: PYL-R0201
    async def convert(self, ctx: Context, argument: str) -> str:
        """Function which converts to image url if possible

        Parameters
        ----------
        ctx : Context
            Context
        argument : str
            Parsing str argument

        Returns
        -------
        str
            Image's URL

        Raises
        ------
        NoImageFound
            If no image was found
        """
        message = ctx.message
        if reference := message.reference:
            message = reference.resolved

        if attachments := message.attachments:
            return attachments[0].proxy_url

        if REGEX_URL.search(message.content):
            return message.content

        converter = commands.PartialEmojiConverter()
        with suppress(commands.PartialEmojiConversionFailure):
            emoji = await converter.convert(ctx, argument)
            return emoji.url
        raise NoImageFound(argument)


class ImageFile(commands.Converter[File]):
    # skipcq: PYL-R0201
    async def convert(self, ctx: Context, argument: str) -> File:
        """Function which converts to file if possible

        Parameters
        ----------
        ctx : Context
            Context
        argument : str
            Parsing str argument

        Returns
        -------
        File
            Fetched File

        Raises
        ------
        NoImageFound
            If no file was fetched
        """
        message = ctx.message
        if reference := message.reference:
            message = reference.resolved

        if attachments := message.attachments:
            return await attachments[0].to_file()

        if file := await ctx.bot.get_file(message.content):
            return file

        raise NoImageFound(argument)


class AnyDateCall(commands.Converter[datetime]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str) -> datetime:
        """This method converts a string into a datetime

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Argument to be parsed by dataparser.parse

        Returns
        -------
        datetime
            Parsed date

        Raises
        ------
        NoDateFound
            If no date was found
        """
        if date := parse(argument, settings=dict(TIMEZONE="utc")):
            return date
        raise NoDateFound(argument)


class CurrentDateCall(commands.Converter[datetime]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str) -> datetime:
        """This method converts a string into a datetime

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Argument to be parsed by dataparser.parse

        Returns
        -------
        datetime
            Parsed date

        Raises
        ------
        NoDateFound
            If no date was found
        """
        if date := parse(date_string=argument, settings=dict(PREFER_DATES_FROM="current_period", TIMEZONE="utc")):
            return date
        raise NoDateFound(argument)


class AfterDateCall(commands.Converter[datetime]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str):
        """This method converts a string into a datetime

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Argument to be parsed by dataparser.parse

        Returns
        -------
        datetime
            Parsed date

        Raises
        ------
        NoDateFound
            If no date was found
        """
        if date := parse(argument, settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc")):
            return date
        raise NoDateFound(argument)


class BeforeDateCall(commands.Converter[datetime]):
    # skipcq: PYL-R0201
    async def convert(self, _: Context, argument: str):
        """This method converts a string into a datetime

        Parameters
        ----------
        _ : Context
            Context
        argument : str
            Argument to be parsed by dataparser.parse

        Returns
        -------
        datetime
            Parsed date

        Raises
        ------
        NoDateFound
            If no date was found
        """
        if date := parse(argument, settings=dict(PREFER_DATES_FROM="past", TIMEZONE="utc")):
            return date
        raise NoDateFound(argument)


class MessageCaller(commands.Converter[Message]):
    # skipcq: PYL-R0201
    async def convert(self, ctx: Context, argument: str) -> Message:
        """Message Converter

        Parameters
        ----------
        ctx : Context
            Context
        argument : str
            Argument

        Returns
        -------
        Message
            Fetched Message

        Raises
        ------
        MessageNotFound
            If no message was found
        """
        if reference := ctx.message.reference:
            if isinstance(reference.resolved, Message):
                return reference.resolved
            if cached := reference.cached_message:
                return cached
            raise commands.MessageNotFound("Message reference")
        converter = commands.MessageConverter()
        return await converter.convert(ctx, argument)


class UserCaller(commands.Converter[Union[Member, User]]):
    # skipcq: PYL-R0201
    async def convert(self, ctx: Context, argument: str) -> Union[Member, User]:
        """Method which obtains an user by it being a close match

        Parameters
        ----------
        ctx : Context
            Context
        argument : str
            Message's Content

        Returns
        -------
        Union[Member, User]
            Matching user
        """
        if guild := ctx.guild:
            argument = argument.lower()
            for user in guild.members:
                if argument in user.display_name.lower():
                    return user
                if argument in str(user).lower():
                    return user
            with suppress(commands.MemberNotFound):
                converter = commands.MemberConverter()
                return await converter.convert(ctx=ctx, argument=argument)
        converter = commands.UserConverter()
        return await converter.convert(ctx=ctx, argument=argument)


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
        ctx: Optional[commands.Context[CustomBot] | discord.Interaction[CustomBot] | discord.Message] = None,
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
