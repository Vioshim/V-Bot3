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

from contextlib import asynccontextmanager, suppress
from inspect import isfunction
from logging import getLogger, setLoggerClass
from types import TracebackType
from typing import Any, Callable, Iterable, Optional, Sized, TypeVar

from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
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
from discord.ui import Button, Modal, Select, TextInput, button, select
from rapidfuzz import process

from src.pagination.simple import Simple
from src.pagination.view_base import ArrowEmotes
from src.structures.logger import ColoredLogger
from src.utils.etc import LIST_EMOJI, WHITE_BAR

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

_T = TypeVar("_T", bound=Sized)

__all__ = ("Complex",)


class DefaultModal(Modal):
    def __init__(self, view: Complex[_T], title: str = "Fill the information") -> None:
        super(DefaultModal, self).__init__(title=title)
        self.text: Optional[str] = None
        self.view = view
        if item := view.text_component:
            self.item = item
            self.add_item(self.item)

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        resp: InteractionResponse = interaction.response
        await resp.send_message("An error has occurred.", ephemeral=True)
        logger.error("Ignoring exception in modal %r:", self, exc_info=error)

    async def on_submit(self, interaction: Interaction) -> None:
        current = set()
        elements = [o for x in str(self.item.value or "").split(",") if (o := x.strip())]
        choices = self.view.choices
        total = set(self.view.real_values) - choices

        def processor(item: _T):
            if isinstance(item, str):
                return item
            x, _ = self.view.parser(item)
            return x

        for elem in elements:
            if entry := process.extractOne(elem, total, processor=processor, score_cutoff=85):
                max_amount = self.view.real_max or self.view.max_values
                if len(choices) < max_amount - len(current):
                    current.add(entry[0])

        if current:
            self.view.choices |= current

        await self.view.edit(interaction=interaction, page=self.view.pos)
        self.stop()


class Complex(Simple[_T]):
    def __init__(
        self,
        *,
        member: Member | User,
        values: Iterable[_T],
        target: Optional[Messageable] = None,
        timeout: Optional[float] = 180.0,
        embed: Embed = None,
        max_values: int = 1,
        entries_per_page: int = 25,
        parser: Callable[[_T], tuple[str, str]] = None,
        emoji_parser: str | PartialEmoji | Emoji | Callable[[_T], str | PartialEmoji | Emoji] = None,
        silent_mode: bool = False,
        keep_working: bool = False,
        sort_key: Optional[Callable[[_T], Any]] = None,
        text_component: Optional[TextInput | Modal] = None,
        real_max: Optional[int] = None,
    ):
        super(Complex, self).__init__(
            timeout=timeout,
            member=member,
            target=target,
            values=values,
            embed=embed,
            entries_per_page=entries_per_page,
            parser=parser,
            sort_key=sort_key,
            modifying_embed=False,
        )
        self.silent_mode = silent_mode
        self.keep_working = keep_working
        self.choices: set[_T] = set()
        self.max_values = max_values
        self._emoji_parser = emoji_parser
        self.text_component = text_component
        self.real_max = real_max
        self.real_values = self.values

    @property
    def values(self) -> list[_T]:
        return self._values

    @values.setter
    def values(self, values: Iterable[_T]):
        if not isinstance(values, Iterable):
            name = values.__class__.__name__ if values is not None else "None"
            raise TypeError(f"{name} is not iterable.")

        if not isinstance(values, list) or self._sort_key:
            items = list(values)
            self._values = items
            self.real_values = items
            self.sort()
        else:
            self._values = values
            self.real_values = values

    async def __aenter__(self) -> set[_T]:
        await super(Complex, self).send()
        await self.wait()
        return self.choices

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: TracebackType) -> None:
        if exc_type:
            logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=exc_val,
            )
        await self.delete()

    def chunk(self, index: int):
        amount = self.entries_per_page * index
        return self.values[amount : amount + self.entries_per_page]

    @property
    def current_chunk(self):
        return self.chunk(self.pos)

    def emoji_parser(self, item: _T) -> Optional[PartialEmoji | Emoji | str]:
        if isinstance(self._emoji_parser, (PartialEmoji, Emoji, str)):
            return self._emoji_parser
        if isfunction(self._emoji_parser):
            return self._emoji_parser(item)
        return getattr(item, "emoji", PartialEmoji(name="StatusRichPresence", id=842328614883295232))

    @property
    def choice(self) -> Optional[_T]:
        return next(iter(self.choices), None)

    def menu_format(self) -> None:
        """Default Formatter"""
        # First, the current stored values in each option get cleared.
        # aside of changing the placeholder text
        if not self.text_component:
            self.remove_item(self.message_handler)
        elif self.message_handler not in self.children:
            self.add_item(self.message_handler)

        foo: Select = self.select_choice
        pages: Select = self.navigate
        choices = self.choices
        amount = self.real_max or self.max_values
        foo.placeholder = f"Picked: {len(choices)}, Max: {amount}, Total: {len(self.values)}"
        foo.options.clear()
        pages.options.clear()
        # Then gets defined the amount of entries an user can pick
        foo.max_values = min(max(amount - len(choices), 1), self.entries_per_page)
        # Now we get the indexes that each page should start with
        indexes = self.values[:: self.entries_per_page]
        total_pages = len(indexes)

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

        amount = self.pos // 20
        min_range = max(amount, 0) * 20
        max_range = min(min_range + 20, len(elements))

        if max_range < len(elements):
            if max_range + 1 < len(elements):
                pages.add_option(label="Next Pages", value=str(max_range), emoji=ArrowEmotes.FORWARD)
            pages.add_option(label="Last Pages", value=str(len(elements) - 1), emoji=ArrowEmotes.END)

        if min_range > 0:
            if min_range - 20 > 0:
                pages.add_option(label="Previous Pages", value=str(max_range - 20), emoji=ArrowEmotes.BACK)
            pages.add_option(label="First Pages", value="0", emoji=ArrowEmotes.START)

        pages.options.sort(key=lambda x: int(x.value))

        for index in range(min_range, max_range):
            item = elements[index]

            # Now that we got the pages, we proceed to parse the start and end of each chunk
            # that way, the page navigation can have the first and last name of the entries.

            firstname, _ = self.parser(item[0])
            lastname, _ = self.parser(item[-1])

            # If the page is the same, as the current, it will be default after editing.

            default = index == self.pos

            # The amount of digits required get determined for formatting purpose
            page_text = f"Page {index + 1}/{total_pages}"
            if len(page_text) > 100:
                page_text = f"Page {index + 1}"

            pages.add_option(
                label=page_text,
                value=f"{index}",
                description=f"From {firstname} to {lastname}"[:100],
                emoji=LIST_EMOJI,
                default=default,
            )

        # Now we start to add the information of the current page in the paginator.
        for index, item in enumerate(elements.get(self.pos, [])):
            # In each cycle, we proceed to convert the name and value (as we use its index)
            # and determine the emoji, based on the current implementation of emoji_parser
            name, value = map(lambda x: str(x).replace("\n", " ").strip()[:100] if x else None, self.parser(item))
            emoji = self.emoji_parser(item)
            foo.add_option(label=name, value=str(index), description=value, emoji=emoji)

        pages.disabled = len(pages.options) == 1
        foo.max_values = min(foo.max_values, len(foo.options))

        # This is the outcome for provided values.
        if not pages.options:
            self.remove_item(pages)
        elif pages not in self.children:
            self.add_item(pages)

        if not foo.options:
            self.remove_item(foo)
        elif foo not in self.children:
            self.add_item(foo)

    async def update(self, interaction: Interaction) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        interaction : Interaction
            Interaction to use
        """
        await self.edit(interaction=interaction)

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        amount = self.max_values if self.real_max is None else self.real_max
        if self.keep_working or len(self.choices) < amount:
            await super(Complex, self).edit(interaction=interaction, page=page)
        else:
            await self.delete(interaction)

    @asynccontextmanager
    async def send(
        self,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embed: Optional[Embed] = None,
        embeds: Optional[list[Embed]] = None,
        file: Optional[File] = None,
        files: Optional[list[File]] = None,
        stickers: Optional[list[GuildSticker | StickerItem]] = None,
        delete_after: Optional[float] = None,
        nonce: Optional[int] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        reference: Optional[Message | MessageReference | PartialMessage] = None,
        mention_author: bool = False,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        ephemeral: bool = False,
        thread: Optional[Snowflake] = None,
        single: bool = False,
        editing_original: bool = False,
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
        editing_original: bool, optional
            If the message is gonna be edited, defaults to False
        """
        try:
            await super(Complex, self).send(
                content=content,
                tts=tts,
                embed=embed,
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
                editing_original=editing_original,
                **kwargs,
            )
            await self.wait()
            if single:
                yield self.choice
            else:
                yield self.choices
        finally:
            await self.delete()

    async def simple_send(
        self,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embed: Optional[Embed] = None,
        embeds: Optional[list[Embed]] = None,
        file: Optional[File] = None,
        files: Optional[list[File]] = None,
        stickers: Optional[list[GuildSticker | StickerItem]] = None,
        delete_after: Optional[float] = None,
        nonce: Optional[int] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        reference: Optional[Message | MessageReference | PartialMessage] = None,
        mention_author: bool = False,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        ephemeral: bool = False,
        thread: Optional[Snowflake] = None,
        editing_original: bool = False,
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
        editing_original: bool, optional
            If the message is gonna be edited, defaults to False
        """
        await super(Complex, self).send(
            content=content,
            tts=tts,
            embed=embed,
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
            editing_original=editing_original,
            **kwargs,
        )

    @property
    def current_choices(self) -> set[_T]:
        sct, chunk, data = self.select_choice, self.current_chunk, set()
        for index in [int(x) for x in sct.values if x.isdigit()]:
            with suppress(IndexError):
                data.add(chunk[index])
        return data

    @property
    def current_choice(self) -> Optional[_T]:
        return next(iter(self.current_choices), None)

    @select(placeholder="Select the elements", row=1, custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        response: InteractionResponse = interaction.response

        items = self.current_choices
        if not response.is_done() and not self.silent_mode and all(x.isdigit() for x in sct.values):
            member: Member | User = interaction.user
            await response.defer(ephemeral=True, thinking=True)
            embed = Embed(
                description="\n".join(f"> **•** {x}" for x, _ in map(self.parser, items)),
                color=Color.blurple(),
            )
            if embed.description:
                embed.title = "Great! you have selected"
            else:
                embed.title = "Nothing has been selected."

            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            embed.set_image(url=WHITE_BAR)
            if guild := interaction.guild:
                embed.set_footer(text=guild.name, icon_url=guild.icon)
            await interaction.followup.send(embed=embed, ephemeral=True)

        if not self.keep_working:
            self.choices |= items
            self.values = set(self.values) - self.choices

        max_pages = len(self.values[:: self.entries_per_page]) - 1

        if "first" in sct.values:
            self.pos = 0
        elif "last" in sct.values:
            self.pos = max_pages
        elif "next" in sct.values:
            self.pos = min(self.pos + 1, max_pages)
        elif "back" in sct.values or (len([x for x in sct.values if x.isdigit()]) == self.entries_per_page):
            self.pos = max(self.pos - 1, 0)

        await self.edit(interaction=interaction, page=self.pos)

    @select(placeholder="Press to scroll pages", row=2, custom_id="navigate")
    async def navigate(self, interaction: Interaction, sct: Select) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        return await self.edit(interaction=interaction, page=int(sct.values[0]))

    @button(
        label="Write down the choice instead.",
        emoji=PartialEmoji(name="channelcreate", id=432986578781077514),
        custom_id="writer",
        style=ButtonStyle.blurple,
        disabled=False,
        row=4,
    )
    async def message_handler(self, interaction: Interaction, _: Button):
        response: InteractionResponse = interaction.response
        component = self.text_component
        if isinstance(component, TextInput):
            component = DefaultModal(view=self)
        await response.send_modal(component)
        await component.wait()

    @button(
        label="Finish",
        custom_id="finish",
        style=ButtonStyle.blurple,
        row=4,
    )
    async def finish(self, ctx: Interaction, btn: Button):
        await self.delete(ctx)
