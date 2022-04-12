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

from typing import Any, Callable, Iterable, Optional, Sized, TypeVar, Union

from discord import Embed, Interaction, InteractionResponse, Member, User
from discord.abc import Messageable
from discord.ui import Button, button

from src.pagination.view_base import Basic

_T = TypeVar("_T", bound=Sized)
_M = TypeVar("_M", bound=Messageable)

__all__ = ("Simple",)


def default_parser(
    item: _T,
) -> tuple[str, str]:
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


class Simple(Basic):
    """A Paginator for View-only purposes"""

    def __init__(
        self,
        *,
        member: Union[Member, User],
        values: Iterable[_T],
        target: _M = None,
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
        target : _M
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
        super().__init__(
            member=member,
            target=target,
            timeout=timeout,
            embed=embed,
        )
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

    def sort(
        self,
        sort_key: Callable[[_T], Any] = None,
        reverse: bool = False,
    ) -> None:
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
        self.menu_format()

    @pos.deleter
    def pos(self):
        self._pos = 0
        self.menu_format()

    @property
    def parser(self):
        if self._parser:
            return self._parser
        return default_parser

    @parser.setter
    def parser(self, parser: Callable[[_T], tuple[str, str]]):
        self._parser = parser
        self.menu_format()

    @parser.deleter
    def parser(self):
        self._parser = None

    @property
    def values(self) -> list[_T]:
        return self._values

    @values.setter
    def values(
        self,
        values: Iterable[_T],
    ):
        if not isinstance(values, Iterable):
            name = values.__class__.__name__ if values is not None else "None"
            raise TypeError(f"{name} is not iterable.")
        items: list[_T] = list(values)
        self._values = items
        self.sort()
        self.menu_format()

    @property
    def entries_per_page(self) -> int:
        return self._entries_per_page

    @entries_per_page.setter
    def entries_per_page(self, entries_per_page: int):
        self._entries_per_page = entries_per_page
        self._pos = 0
        self.menu_format()

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
        self.embed.clear_fields()
        if chunks := len(self.values[:: self._entries_per_page]):
            self.embed.set_footer(
                text=f"Page {self._pos + 1} / {chunks}",
                icon_url=self.embed.footer.icon_url,
            )
            amount = self._entries_per_page * self._pos
            for item in self.values[amount : amount + self._entries_per_page]:
                name, value = self.parser(item)
                self.embed.add_field(
                    name=name[:256],
                    value=value[:1024],
                    inline=self.inline,
                )

    async def edit(
        self,
        interaction: Interaction,
        page: Optional[int] = None,
    ) -> None:
        """This method edits the pagination's page given an index.

        Parameters
        ----------
        page : int, optional
            page's index, defaults to None
        """
        data = {}

        if self.modifying_embed:
            data["embed"] = self.embed

        if isinstance(page, int):
            self.pos = page
            data["view"] = self

        resp: InteractionResponse = interaction.response

        if not resp.is_done():
            await resp.edit_message(**data)
        elif message := self.message:
            await message.edit(**data)

    @button(
        emoji=":lasttrack:952522808347467807",
        row=0,
        custom_id="first",
    )
    async def first(
        self,
        interaction: Interaction,
        _: Button,
    ) -> None:
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

    @button(
        emoji=":fastreverse:952522808599126056",
        row=0,
        custom_id="previous",
    )
    async def previous(
        self,
        interaction: Interaction,
        _: Button,
    ) -> None:
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

    @button(
        emoji=":stop:952522808573968454",
        row=0,
        custom_id="finish",
    )
    async def finish(
        self,
        interaction: Interaction,
        _: Button,
    ) -> None:
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
        if not resp.is_done():
            await resp.pong()
        await self.delete()

    @button(
        emoji=":fastforward:952522808347488326",
        row=0,
        custom_id="next",
    )
    async def next(
        self,
        interaction: Interaction,
        _: Button,
    ) -> None:
        """
        Method used to reach next page of the pagination

        Parameters
        ----------
        interaction: discord.Interaction
            Current interaction of the user
        _: discord.ui.Button
            Button which interacts with the User
        """
        return await self.edit(interaction=interaction, page=self._pos + 1)

    @button(
        emoji=":nexttrack:952522808355848292",
        row=0,
        custom_id="last",
    )
    async def last(
        self,
        interaction: Interaction,
        _: Button,
    ) -> None:
        """
        Method used to reach last page of the pagination

        Parameters
        ----------
        interaction: discord.Interaction
            Current interaction of the user
        _: discord.ui.Button
            Button which interacts with the User
        """
        return await self.edit(
            interaction=interaction,
            page=len(self.values[:: self._entries_per_page]) - 1,
        )
