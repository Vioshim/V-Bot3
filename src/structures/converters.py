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

from datetime import datetime
from typing import Union

from dateparser import parse
from discord import Member, Message, User
from discord.ext.commands import (
    Converter,
    MemberConverter,
    MemberNotFound,
    MessageConverter,
    MessageNotFound,
    PartialEmojiConversionFailure,
    PartialEmojiConverter,
    UserConverter,
)
from discord.file import File

from src.context.context import Context
from src.structures.exceptions import (
    NoDateFound,
    NoImageFound,
    NoMoveFound,
    NoSpeciesFound,
)
from src.structures.move import Move
from src.structures.species import Species
from src.utils.matches import REGEX_URL


class MovesCall(Converter[Move]):
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

        if data := Move.deduce(argument):
            return data

        raise NoMoveFound(argument)


class SpeciesCall(Converter[Species]):
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

        if data := Species.deduce(argument):
            return data

        raise NoSpeciesFound(argument)


class ImageURL(Converter[str]):
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

        converter = PartialEmojiConverter()
        try:
            emoji = await converter.convert(ctx, argument)
            return emoji.url
        except PartialEmojiConversionFailure:
            pass

        raise NoImageFound(argument)


class ImageFile(Converter[File]):
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


class AnyDateCall(Converter[datetime]):
    async def convert(self, ctx: Context, argument: str) -> datetime:
        """This method converts a string into a datetime

        Parameters
        ----------
        ctx : Context
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


class CurrentDateCall(Converter[datetime]):
    async def convert(self, ctx: Context, argument: str) -> datetime:
        """This method converts a string into a datetime

        Parameters
        ----------
        ctx : Context
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
        if date := parse(
            date_string=argument,
            settings=dict(PREFER_DATES_FROM="current_period", TIMEZONE="utc"),
        ):
            return date
        raise NoDateFound(argument)


class AfterDateCall(Converter[datetime]):
    async def convert(self, ctx: Context, argument: str):
        """This method converts a string into a datetime

        Parameters
        ----------
        ctx : Context
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
        if date := parse(
            argument, settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc")
        ):
            return date
        raise NoDateFound(argument)


class BeforeDateCall(Converter[datetime]):
    async def convert(self, ctx: Context, argument: str):
        """This method converts a string into a datetime

        Parameters
        ----------
        ctx : Context
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
        if date := parse(
            argument, settings=dict(PREFER_DATES_FROM="past", TIMEZONE="utc")
        ):
            return date
        raise NoDateFound(argument)


class MessageCaller(Converter[Message]):
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
            raise MessageNotFound("Message reference")
        converter = MessageConverter()
        return await converter.convert(ctx, argument)


class UserCaller(Converter[Union[Member, User]]):
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
            try:
                converter = MemberConverter()
                return await converter.convert(ctx=ctx, argument=argument)
            except MemberNotFound:
                pass
        converter = UserConverter()
        return await converter.convert(ctx=ctx, argument=argument)
