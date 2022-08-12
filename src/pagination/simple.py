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

from math import ceil
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    NamedTuple,
    Optional,
    Sized,
    TypeVar,
    Union,
)

from discord import (
    AllowedMentions,
    ButtonStyle,
    DiscordException,
    Embed,
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
from discord.ui import Button, button

from src.pagination.view_base import Basic

_T = TypeVar("_T", bound=Sized)

__all__ = ("Simple",)


class ArrowEmotes(NamedTuple):
    START = PartialEmoji(name="DoubleArrowLeft", id=972196330808160296)
    BACK = PartialEmoji(name="ArrowLeft", id=972196330837528606)
    FORWARD = PartialEmoji(name="ArrowRight", id=972196330892058684)
    END = PartialEmoji(name="DoubleArrowRight", id=972196330942390372)
    CLOSE = PartialEmoji(name="Stop", id=972196330795585567)


def default_parser(item: _T) -> tuple[str, str]:
    """Standard parser for elements

    Parameters
    ----------
    item : _T
        Element to parse as

    Returns
    -------
    tuple[str, str]
        Resulting pair
    """

    if isinstance(item, tuple):
        return item
    if not (name := getattr(item, "name", None)):
        name = str(item)
    if not (description := getattr(item, "description", None)):
        description = repr(item)
    return name, description


class Simple(Generic[_T], Basic):
    """A Paginator for View-only purposes"""

    def __init__(
        self,
        *,
        member: Union[Member, User],
        values: Iterable[_T],
        target: Optional[Messageable] = None,
        timeout: Optional[float] = 180.0,
        embed: Embed = None,
        inline: bool = False,
        entries_per_page: int = 25,
        parser: Callable[[_T], tuple[str, str]] = None,
        sort_key: Callable[[_T], Any] = None,
        modifying_embed: bool = True,
    ):
        """Init Method

        Parameters
        ----------
        member : Union[Member, User]
            Member
        target : Optional[Messageable]
            Destination
        values : Iterable[T], optional
            Provided Values, defaults to frozenset()
        timeout : Float, optional
            Provided timeout, defaults to 180.0
        embed : Embed. optional
            Embed to display, defaults to None
        inline : bool, optional
            If the values need to be inline or not, defaults to False
        entries_per_page : int, optional
            The max amount of entries per page, defaults to 25
        parser : Callable[[_T], tuple[str, str]]
            Parser method, defaults to lambda x: str(x), repr(x)
        sort_key : Callable[[_T], Any], optional
            key used for sorting
        """
        super(Simple, self).__init__(member=member, target=target, timeout=timeout, embed=embed)
        self.modifying_embed = modifying_embed
        if not isinstance(values, Iterable):
            name = values.__class__.__name__ if values is not None else "None"
            raise TypeError(f"{name} is not iterable.")
        items: list[_T] = list(values)
        self._sort_key = sort_key
        self._values = items
        self.inline = inline
        self._pos = 0
        self._parser = parser
        self._entries_per_page = entries_per_page
        if not isinstance(values, list) or sort_key:
            self.sort(sort_key=sort_key)

    def sort(self, sort_key: Callable[[_T], Any] = None, reverse: bool = False) -> None:
        """Sort method used for the view's values

        Attributes
        ----------
        key : Callable[[_T], Any], optional
            key to use for sorting, defaults to None
        reverse : bool, optional
            sets the order to reverse, defaults to False
        """
        try:
            self._sort_key = sort_key
            self.values.sort(key=sort_key, reverse=reverse)
        except TypeError:
            self._sort_key = str
            self.values.sort(key=str, reverse=reverse)

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos: int):
        self._pos = pos

    @pos.deleter
    def pos(self):
        self._pos = 0

    @property
    def parser(self):
        if self._parser:
            return self._parser
        return default_parser

    @parser.setter
    def parser(self, parser: Callable[[_T], tuple[str, str]]):
        self._parser = parser

    @parser.deleter
    def parser(self):
        self._parser = None

    @property
    def values(self) -> list[_T]:
        return self._values

    @values.setter
    def values(self, values: Iterable[_T]):
        if not isinstance(values, Iterable):
            name = values.__class__.__name__ if values is not None else "None"
            raise TypeError(f"{name} is not iterable.")
        items: list[_T] = list(values)
        self._values = items
        self.sort()

    @property
    def entries_per_page(self) -> int:
        return self._entries_per_page

    @entries_per_page.setter
    def entries_per_page(self, entries_per_page: int):
        self._entries_per_page = entries_per_page
        self._pos = 0

    @entries_per_page.deleter
    def entries_per_page(self):
        self._entries_per_page = 25
        self._pos = 0

    def to_components(self) -> list[dict[str, Any]]:
        self.menu_format()
        return super(Simple, self).to_components()

    @entries_per_page.deleter
    def entries_per_page(self):
        self._entries_per_page = 25
        self._pos = 0
        self.menu_format()

    def buttons_format(self) -> None:
        """This method formats the first buttons based on the
        current page that is being viewed..
        """
        self.first.disabled = self._pos == 0
        self.previous.disabled = self._pos == 0
        if chunks := len(self.values[:: self._entries_per_page]):
            self.next.disabled = self._pos == chunks - 1
            self.last.disabled = self._pos == chunks - 1
        else:
            self.next.disabled = True
            self.last.disabled = True

    def menu_format(self):
        """Default Formatter"""
        self.buttons_format()
        if self.entries_per_page != 1:
            self.embed.clear_fields()
        chunks = len(self.values[:: self.entries_per_page]) or (self.pos + 1)
        self.embed.set_footer(text=f"Page {self.pos + 1} / {chunks}", icon_url=self.embed.footer.icon_url)
        amount = self.entries_per_page * self.pos
        for item in map(self.parser, self.values[amount : amount + self.entries_per_page]):
            name, value = map(str, item)
            if self.entries_per_page == 1:
                self.embed.title = name[:256]
                self.embed.description = value[:4096]
            else:
                self.embed.add_field(name=name[:256], value=value[:1024], inline=self.inline)

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
        editing_original: bool = False,
        **kwargs,
    ) -> None:
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
        """
        self.menu_format()
        return await super(Simple, self).send(
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

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        data = {}

        if self.modifying_embed:
            data["embed"] = self.embed

        if isinstance(page, int):
            self.pos = min(max(0, page), self.max_pages)
            self.menu_format()
            data["view"] = self

        return data

    @property
    def max_pages(self):
        return ceil(len(self.values) / self.entries_per_page)

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        """This method edits the pagination's page given an index.

        Parameters
        ----------
        page : int, optional
            page's index, defaults to None
        """
        resp: InteractionResponse = interaction.response

        if self.is_finished():
            return

        data = self.default_params(page=page)
        try:
            if not resp.is_done():
                await resp.edit_message(**data)
            elif self.message:
                self.message = await self.message.edit(**data)
            else:
                self.message = await interaction.edit_original_response(**data)
        except DiscordException as e:
            interaction.client.logger.exception(
                "Error in Simple View - Page %s - Author: %s - Info: %s",
                str(page),
                str(self.member),
                str(self.embed.to_dict()),
                exc_info=e,
            )
            self.stop()

    @button(emoji=ArrowEmotes.START, row=0, custom_id="first", style=ButtonStyle.blurple)
    async def first(self, interaction: Interaction, _: Button) -> None:
        """
        Method used to reach next first of the pagination

        Parameters
        ----------
        interaction: Interaction
            Current interaction of the user
        _: Button
            Button which interacts with the User
        """
        return await self.edit(interaction=interaction, page=0)

    @button(emoji=ArrowEmotes.BACK, row=0, custom_id="previous", style=ButtonStyle.blurple)
    async def previous(self, interaction: Interaction, _: Button) -> None:
        """
        Method used to reach previous page of the pagination

        Parameters
        ----------
        interaction: Interaction
            Current interaction of the user
        _: Button
            Button which interacts with the User
        """
        return await self.edit(interaction=interaction, page=self._pos - 1)

    @button(emoji=ArrowEmotes.CLOSE, row=0, custom_id="finish", style=ButtonStyle.blurple)
    async def finish(self, interaction: Interaction, _: Button) -> None:
        """
        Method used to conclude the pagination

        Parameters
        ----------
        interaction: discord.Interaction
            Current interaction of the user
        _: discord.ui.Button
            Button which interacts with the User
        """
        resp: InteractionResponse = interaction.response
        if interaction.message.flags.ephemeral:
            await resp.edit_message(view=None)
        else:
            await interaction.message.delete(delay=0)
        self.stop()

    @button(emoji=ArrowEmotes.FORWARD, row=0, custom_id="next", style=ButtonStyle.blurple)
    async def next(self, interaction: Interaction, _: Button) -> None:
        """
        Method used to reach next page of the pagination

        Parameters
        ----------
        interaction: discord.Interaction
            Current interaction of the user
        _: discord.ui.Button
            Button which interacts with the User
        """
        await self.edit(interaction=interaction, page=self._pos + 1)

    @button(emoji=ArrowEmotes.END, row=0, custom_id="last", style=ButtonStyle.blurple)
    async def last(self, interaction: Interaction, _: Button) -> None:
        """
        Method used to reach last page of the pagination

        Parameters
        ----------
        interaction: discord.Interaction
            Current interaction of the user
        _: discord.ui.Button
            Button which interacts with the User
        """
        await self.edit(interaction=interaction, page=len(self.values[:: self._entries_per_page]) - 1)
