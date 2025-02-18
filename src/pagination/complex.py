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

from contextlib import asynccontextmanager, suppress
from inspect import isfunction
from types import TracebackType
from typing import Any, Callable, Collection, Iterable, Optional, TypeVar

from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    Emoji,
    File,
    GuildSticker,
    Interaction,
    Member,
    Message,
    MessageReference,
    PartialEmoji,
    PartialMessage,
    StickerItem,
    TextStyle,
    User,
)
from discord.abc import Messageable, Snowflake
from discord.ui import Button, Modal, Select, TextInput, button, select
from rapidfuzz import process

from src.pagination.simple import Simple
from src.pagination.view_base import ArrowEmotes
from src.structures.bot import CustomBot
from src.utils.etc import CREATE_EMOJI, DELETE_EMOJI, LIST_EMOJI, PRESENCE_EMOJI

_T = TypeVar("_T", bound=Collection)

__all__ = ("Complex",)


class DefaultModal(Modal):
    def __init__(self, view: Complex[_T], title: str = "Fill the information") -> None:
        super(DefaultModal, self).__init__(title=title)
        self.text: Optional[str] = None
        self.view = view
        if item := view.text_component:
            self.item = item
            self.add_item(self.item)

    async def on_error(self, interaction: Interaction[CustomBot], error: Exception, /) -> None:
        await interaction.response.send_message("An error has occurred.", ephemeral=True)
        interaction.client.logger.error("Ignoring exception in modal %r:", self, exc_info=error)

    async def on_submit(self, interaction: Interaction[CustomBot], /) -> None:
        await interaction.response.pong()
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
        sort_key: Optional[tuple[Callable[[_T], Any], bool] | Callable[[_T], Any]] = None,
        text_component: Optional[TextInput | Modal] = None,
        auto_text_component: bool = False,
        real_max: Optional[int] = None,
        deselect_mode: bool = True,
        auto_conclude: bool = True,
        auto_choice_info: bool = False,
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
            modifying_embed=auto_choice_info,
        )
        self.auto_conclude = auto_conclude
        self.silent_mode = silent_mode
        self.keep_working = keep_working
        self.auto_choice_info = auto_choice_info
        self.choices: set[_T] = set()
        self.max_values = max_values
        self._emoji_parser = emoji_parser
        self.text_component = text_component
        self.auto_text_component = auto_text_component
        self.real_max = real_max
        self.real_values = self.values
        self.deselect_mode = deselect_mode

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
            sort_key, reverse = self.sort_pair
            self.sort(sort_key=sort_key, reverse=reverse)
        else:
            self._values = values
            self.real_values = values

    async def __aenter__(self) -> set[_T]:
        await super(Complex, self).send()
        await self.wait()
        return self.choices

    async def __aexit__(self, exc_type: type, exc_val: Exception, exc_tb: TracebackType) -> None:
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
        return getattr(item, "emoji", PRESENCE_EMOJI)

    @property
    def choice(self) -> Optional[_T]:
        return next(iter(self.choices), None)

    def menu_format(self) -> None:
        """Default Formatter"""
        # First, the current stored values in each option get cleared.
        # aside of changing the placeholder text
        foo = self.select_choice
        pages = self.navigate
        choices = self.choices
        text = (
            f"Picked: {len(choices)}, Max: {amount}, Options: {len(self.values)}"
            if (amount := self.real_max or self.max_values) > 1
            else f"Single Choice, Options: {len(self.values)}"
        )
        foo.placeholder = text
        if self.auto_text_component:
            self.text_component = TextInput(
                label=self.embed.title[:45] if self.embed and self.embed.title else "Input",
                placeholder=text[:100],
                style=TextStyle.paragraph,
            )
        if self.auto_choice_info and self.embed and 1 <= len(self.choices) <= 25:
            self.embed.clear_fields()
            key, reverse = self.sort_pair
            for k, v in map(self.parser, sorted(self.choices, key=key, reverse=reverse)):
                self.embed.add_field(name=k[:256], value=v[:1024], inline=False)

        if not (self.text_component and self.values):
            self.remove_item(self.message_handler)
        elif self.message_handler not in self.children:
            self.add_item(self.message_handler)
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
            if min_range > 20:
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

        pages.disabled = len(pages.options) <= 1
        foo.disabled = not foo.options
        foo.max_values = min(foo.max_values, len(foo.options) or 1)

        # This is the outcome for provided values.
        if len(pages.options) <= 1:
            self.remove_item(pages)
        elif pages not in self.children:
            self.add_item(pages)

        if not foo.options:
            foo.add_option(
                label="Placeholder",
                description="You shouldn't be seeing this",
                emoji=LIST_EMOJI,
            )

        if foo not in self.children:
            self.add_item(foo)

        if not self.choices:
            self.remove_item(self.element_remove)
        elif self.deselect_mode and self.element_remove not in self.children:
            self.add_item(self.element_remove)

    async def update(self, interaction: Interaction[CustomBot]) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        interaction : Interaction[CustomBot]
            Interaction[CustomBot] to use
        """
        await self.edit(interaction=interaction)

    async def edit(self, interaction: Interaction[CustomBot], page: Optional[int] = None) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        amount = self.max_values if self.real_max is None else self.real_max
        if self.keep_working or not self.auto_conclude or len(self.choices) < amount:
            return await super(Complex, self).edit(interaction=interaction, page=page)
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
        deleting: bool = True,
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
            if deleting:
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
    async def select_choice(self, interaction: Interaction[CustomBot], sct: Select) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        itx: Interaction[CustomBot]
            Current interaction of the user
        """
        items = self.current_choices
        if not interaction.response.is_done() and not self.silent_mode and all(x.isdigit() for x in sct.values):
            member: Member | User = interaction.user
            await interaction.response.defer(ephemeral=True, thinking=True)
            embed = Embed(description="\n".join(f"> **•** {x}" for x, _ in map(self.parser, items)), color=0x94939F)
            if embed.description:
                embed.title = "Great! you have selected"
            else:
                embed.title = "Nothing has been selected."

            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
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
    async def navigate(self, interaction: Interaction[CustomBot], sct: Select) -> None:
        """Method used to select values from the pagination

        Parameters
        ----------
        sct: Select
            Button which interacts with the User
        interaction: Interaction[CustomBot]
            Current interaction of the user
        """
        return await self.edit(interaction=interaction, page=int(sct.values[0]))

    @button(
        label="Write down the choice instead.",
        emoji=CREATE_EMOJI,
        custom_id="writer",
        style=ButtonStyle.blurple,
        disabled=False,
        row=4,
    )
    async def message_handler(self, interaction: Interaction[CustomBot], _: Button):
        component = self.text_component
        if isinstance(component, TextInput):
            component = DefaultModal(view=self)
        await interaction.response.send_modal(component)
        await component.wait()

    @button(label="Finish", custom_id="finish", style=ButtonStyle.blurple, row=4)
    async def finish(self, ctx: Interaction[CustomBot], btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await ctx.response.edit_message(view=self)
        await self.delete(ctx)

    @button(
        label="Deselect",
        emoji=DELETE_EMOJI,
        custom_id="remover",
        style=ButtonStyle.blurple,
        disabled=False,
        row=4,
    )
    async def element_remove(self, interaction: Interaction[CustomBot], _: Button):
        inner = InnerComplex(self, interaction)
        async with inner.send(editing_original=True, deleting=False) as choices:
            self.choices -= choices
            self.values.extend(choices)
            self.menu_format()
            interaction = inner.target or interaction
            original = self.modifying_embed
            self.modifying_embed = True
            await self.edit(interaction=interaction, page=self.pos)
            self.modifying_embed = original


class InnerComplex(Complex):
    def __init__(self, main: Complex, interaction: Interaction[CustomBot]):
        self.main = main
        super(InnerComplex, self).__init__(
            member=main.member,
            values=main.choices,
            target=interaction,
            timeout=None,
            embed=self.main.embed.copy(),
            max_values=len(main.choices),
            entries_per_page=main.entries_per_page,
            emoji_parser=main._emoji_parser,
            parser=main.parser,
            silent_mode=True,
            sort_key=main._sort_key,
            text_component=main.text_component,
            deselect_mode=False,
            auto_text_component=main.auto_text_component,
            auto_choice_info=True,
            auto_conclude=False,
        )
        self.embed.description = ""

    @button(label="Finish", custom_id="finish", style=ButtonStyle.blurple, row=4)
    async def finish(self, ctx: Interaction[CustomBot], btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await ctx.response.edit_message(view=self)
        self.stop()
