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

from contextlib import asynccontextmanager, suppress
from difflib import get_close_matches
from types import TracebackType
from typing import Callable, Iterable, Optional, Sized, TypeVar, Union

from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    Emoji,
    File,
    GuildSticker,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    MessageReference,
    PartialEmoji,
    PartialMessage,
    StickerItem,
    User,
)
from discord.abc import Messageable, Snowflake
from discord.ui import Button, Select, button, select

from src.pagination.simple import Simple
from src.structures.bot import CustomBot
from src.utils.functions import embed_modifier, text_check

_T = TypeVar("_T", bound=Sized)
_M = TypeVar("_M", bound=Messageable)

__all__ = ("Complex", "ComplexInput")


def default_emoji_parser(item: _T) -> tuple[str, str]:
    """Standard parser for emoji out of elements

    Parameters
    ----------
    item : _T
        Element to parse as

    Returns
    -------
    str | PartialEmoji | EMoji
        Resulting emoji
    """
    if isinstance(item, (PartialEmoji, Emoji)):
        return item
    return getattr(item, "emoji", "\N{DIAMOND SHAPE WITH A DOT INSIDE}")


class Complex(Simple):
    def __init__(
        self,
        *,
        bot: CustomBot,
        member: Union[Member, User],
        values: Iterable[_T],
        target: _M = None,
        timeout: Optional[float] = 180.0,
        embed: Embed = None,
        max_values: int = 1,
        entries_per_page: int = 25,
        parser: Callable[[_T], tuple[str, str]] = None,
        emoji_parser: Union[
            str, Callable[[_T], Union[str, PartialEmoji, Emoji]]
        ] = None,
    ):
        self._choices: set[_T] = None
        self._max_values = max_values
        if isinstance(emoji_parser, str):
            self._emoji_parser = lambda x: emoji_parser
        else:
            self._emoji_parser = emoji_parser or default_emoji_parser
        super().__init__(
            bot=bot,
            timeout=timeout,
            member=member,
            target=target,
            values=values,
            embed=embed,
            entries_per_page=entries_per_page,
            parser=parser,
        )

    # noinspection PyMethodMayBeStatic
    def emoji_parser(self, item: _T) -> str:
        return self._emoji_parser(item)

    def set_emoji_parser(
        self, item: Callable[[_T], Union[str, PartialEmoji, Emoji]] = None
    ) -> None:
        """Function used for setting a parser

        Parameters
        ----------
        item : Callable[[_T], Union[str, PartialEmoji, Emoji]], optional
            Function to add, defaults to None
        """
        if item:
            self._emoji_parser = item
        else:
            self._emoji_parser = default_emoji_parser
        self.menu_format()

    async def __aenter__(self) -> set[_T]:
        await super(Complex, self).send()
        await self.wait()
        return self._choices

    async def __aexit__(
        self, exc_type: type, exc_val: Exception, exc_tb: TracebackType
    ) -> None:
        if exc_type:
            self.bot.logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=exc_val,
            )
        await self.delete()

    @property
    def choices(self) -> set[_T]:
        return self._choices

    @property
    def choice(self) -> Optional[_T]:
        if choices := self._choices:
            return choices.pop()

    @property
    def max_values(self):
        return self._max_values

    # noinspection PyTypeChecker,DuplicatedCode
    def menu_format(self) -> None:
        """Default Formatter"""
        self.buttons_format()
        # First, the current stored values in each option get cleared.
        # aside of changing the placeholder text

        foo: Select = self.select_choice
        pages: Select = self.navigate

        if not (choices := self.choices):
            choices = set()

        foo.placeholder = f"Picked:{len(choices)}, Max:{self.max_values}"

        foo.options.clear()
        pages.options.clear()

        # Then gets defined the amount of entries an user can pick

        foo.max_values = min(self.max_values - len(choices), self.entries_per_page)

        # Now we get the indexes that each page should start with

        indexes = self.values[:: self._entries_per_page]

        if total_pages := len(indexes):

            # We start to split the information in chunks

            elements: dict[int, list[_T]] = {}

            for index, _ in enumerate(indexes):
                # The chunks start to get loaded keeping in mind the length of the pages
                # the basis is pretty much the amount of elements multiplied by the page index.
                amount = index * self.entries_per_page
                items = self.values[amount : amount + self.entries_per_page]
                elements[index] = items

            # After loading the chunks, we proceed to determine the minimum and maximum range for the pagination
            # It needs to be done in such a way so that the current page becomes the one in the middle.
            #
            # Example: assuming there's 4 entries per page, 100 values and user is at the page 12 in this case,
            # the range of pages would be from page 10 to page 14

            amount = int(self.entries_per_page / 2)
            min_range = max(self._pos - amount, 0)
            max_range = min(self._pos + amount, len(elements))

            for index in range(min_range, max_range):
                item = elements[index]

                # Now that we got the pages, we proceed to parse the start and end of each chunk
                # that way, the page navigation can have the first and last name of the entries.

                firstname, _ = self.parser(item[0])
                lastname, _ = self.parser(item[-1])

                # If the page is the same, as the current, it will be default after editing.

                default = index == self._pos

                # The amount of digits required get determined for formatting purpose

                digits = max(len(f"{index + 1}"), len(f"{total_pages}"))
                page_text = f"Page {index + 1:0{digits}d}/{total_pages:0{digits}d}"
                pages.add_option(
                    label=page_text[:100],
                    value=f"{index}"[:100],
                    description=f"From {firstname} to {lastname}"[:100],
                    emoji="\N{PAGE FACING UP}",
                    default=default,
                )

            # Now we start to add the information of the current page in the paginator.

            for index, item in enumerate(elements[self._pos]):
                # In each cycle, we proceed to convert the name and value (as we use its index)
                # and determine the emoji, based on the current implementation of emoji_parser

                name, value = self.parser(item)
                emoji = self.emoji_parser(item)
                foo.add_option(
                    label=f"{name}"[:100],
                    value=f"{index}"[:100],
                    description=str(value).replace("\n", " ")[:100],
                    emoji=emoji,
                )
        else:

            # This is the outcome for no provided values.

            pages.add_option(
                label="Page 01/01",
                emoji="\N{PAGE FACING UP}",
                default=True,
            )
            foo.add_option(
                label="Empty List",
                default=True,
            )

    async def edit(self, page: Optional[int] = None) -> None:
        """
        Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        amount = len(self._choices or set())
        if amount < self._max_values:
            return await super(Complex, self).edit(page=page)
        await self.delete()

    @asynccontextmanager
    async def send(
        self,
        content: str = None,
        *,
        tts: bool = False,
        embed: Embed = None,
        embeds: list[Embed] = None,
        file: File = None,
        files: list[File] = None,
        stickers: list[Union[GuildSticker, StickerItem]] = None,
        delete_after: float = None,
        nonce: int = None,
        allowed_mentions: AllowedMentions = None,
        reference: Union[Message, MessageReference, PartialMessage] = None,
        mention_author: bool = False,
        username: str = None,
        avatar_url: str = None,
        ephemeral: bool = False,
        thread: Snowflake = None,
        single: bool = False,
        **kwargs,
    ):
        """Sends the paginator towards the defined destination

        Attributes
        ----------
        content : str, optional
            message's content
        tts : bool, optional
            message's tts, defaults to False
        embed : Embed, optional
            message's embed, defaults to None
            if set as None, no embed is generated.
        embeds : list[Embed], optional
            message's embeds, defaults to None
        file : File, optional
            message's file, defaults to None'
        files : list[File], optional
            message's file, defaults to None
        stickers : list[Union[GuildSticker, StickerItem]], optional
            message's stickers, defaults to None
        delete_after : float, optional
            defaults to None
        nonce : int, optional
            message's nonce, defaults to None
        allowed_mentions : AllowedMentions, optional
            message's allowed mentions, defaults MISSING
        reference : Union[Message, MessageReference, PartialMessage], optional
            message's reference, defaults to None
        mention_author : bool, optional
            if mentions the author of the message, defaults to MISSING
        username : str, Optional
            webhook username to send as, defaults to None
        avatar_url: str, optional
            webhook avatar_url to send as, defaults to None
        ephemeral: bool, optional
            if message is ephemeral, defaults to False
        thread: Snowflake, optional
            if message is sent to a thread, defaults to None
        single: bool, Optional
            If returning an object or a set of objects
        """
        try:
            embed = embed or self.embed
            self.embed = embed_modifier(embed, **kwargs)
            await super(Complex, self).send(
                content=content,
                tts=tts,
                embed=self.embed,
                embeds=embeds,
                file=file,
                files=files,
                stickers=stickers,
                delete_after=delete_after,
                nonce=nonce,
                allowed_mentions=allowed_mentions,
                reference=reference,
                mention_author=mention_author,
                username=username,
                avatar_url=avatar_url,
                ephemeral=ephemeral,
                thread=thread,
            )
            await self.wait()
            yield self.choice if single else self.choices
        finally:
            await self.delete()

    # noinspection PyTypeChecker
    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, sct: Select, interaction: Interaction) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        response: InteractionResponse = interaction.response
        if self._choices is None:
            self._choices = set()
        entries = []
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        for index in sct.values:
            item: _T = chunk[int(index)]
            name, _ = self.parser(item)
            entries.append(str(name))
            self._choices.add(item)
        await self.custom_choice(sct, interaction)
        if not response.is_done():
            text = ", ".join(entries)
            await response.send_message(
                content=f"Great! you have selected **{text}**.",
                ephemeral=True,
            )

        self.values = set(self.values) - self.choices
        if len(sct.values) == self.entries_per_page:
            self._pos -= 1
        await self.edit(page=self._pos)

    # noinspection PyTypeChecker
    @select(placeholder="Press to scroll pages", row=2, custom_id="navigate")
    async def navigate(self, sct: Select, interaction: Interaction) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        response: InteractionResponse = interaction.response
        await self.custom_navigate(sct, interaction)
        if not response.is_done():
            items: list[str] = interaction.data.get("values", [])
            if items[0].isdigit():
                return await self.edit(page=int(items[0]))

    async def custom_choice(self, sct: Select, interaction: Interaction) -> None:
        """
        Method used to reach next first of the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """

    async def custom_navigate(self, sct: Select, interaction: Interaction) -> None:
        """
        Method used to reach next first of the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """


class ComplexInput(Complex):
    """This class allows written input."""

    # noinspection PyTypeChecker
    @button(
        label="Click here to write down the choice instead.",
        emoji="\N{PENCIL}",
        custom_id="writer",
        disabled=False,
    )
    async def message_handler(self, btn: Button, ctx: Interaction):
        response: InteractionResponse = ctx.response
        await self.custom_message_handler(btn, ctx)
        if response.is_done():
            return
        btn.disabled = True
        if message := self.message:
            await message.edit(view=self)
        elif isinstance(target := self.target, Interaction):
            if message := await target.original_message():
                await message.edit(view=self)
        await response.send_message(
            content="Write down the choice in that case.", ephemeral=True
        )
        message: Message = await self.bot.wait_for(
            event="message",
            check=text_check(ctx),
        )
        aux = {}
        for item in self.values:
            key, _ = self.parser(item)
            aux[key] = item

        current = set()
        for elem in message.content.split(","):
            if len(self._choices or set()) < self.max_values - len(current):
                if entries := get_close_matches(
                    word=elem.strip(),
                    possibilities=aux,
                    n=1,
                ):
                    if self._choices is None:
                        self._choices = set()
                    item = aux[entries[0]]
                    current.add(item)

        with suppress(DiscordException):
            if current:
                self.choices.update(current)
                self.values = set(self.values) - self.choices
                await message.delete()
            else:
                await message.reply(
                    content="No close matches were found",
                    delete_after=5,
                )
                await message.delete(delay=5)

        return await self.edit(page=self._pos)

    async def custom_message_handler(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """
        Method used to reach next first of the pagination

        Parameters
        ----------
        btn: Button
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
