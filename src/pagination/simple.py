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

from contextlib import suppress
from typing import Any, Callable, Iterable, Optional, Sized, TypeVar, Union

from discord import (
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    User,
)
from discord.abc import Messageable
from discord.ui import Button, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot

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
        bot: CustomBot,
        member: Union[Member, User],
        values: Iterable[_T],
        target: _M = None,
        timeout: Optional[float] = 180.0,
        embed: Embed = None,
        inline: bool = False,
        entries_per_page: int = 25,
        parser: Callable[[_T], tuple[str, str]] = default_parser,
        sort_key: Callable[[_T], Any] = None,
        modifying_embed: bool = True,
    ):
        """Init Method

        Parameters
        ----------
        bot : CustomBot
            Bot
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
            bot=bot,
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
        self._inline = inline
        self._pos = 0
        self._parser = parser or default_parser
        self._entries_per_page = entries_per_page
        if not isinstance(values, list) or sort_key:
            self.sort(sort_key=sort_key)
        self.menu_format()

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

    def set_parser(
        self,
        item: Callable[[_T], tuple[str, str]] = None,
    ) -> None:
        """Function used for setting a parser

        Parameters
        ----------
        item : Callable[[_T], tuple[str, str]], optional
            Function to add, defaults to None
        """
        if item:
            self._parser = item
        else:
            self._parser = default_parser
        self.menu_format()

    def parser(
        self,
        item: _T,
    ) -> tuple[str, str]:
        """This method parses an item and returns a tuple which will set
        values and description for the select choices

        Parameters
        ----------
        item : _T
            Independant element

        Returns
        -------
        tuple[str, str]
            generated name and description for the item
        """
        return self._parser(item)

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
        """Default Formatter

        Returns
        -------

        """
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
                    name=name, value=value, inline=self._inline
                )

    async def edit(
        self,
        page: Optional[int] = None,
    ) -> None:
        """This method edits the pagination's page given an index.

        Parameters
        ----------
        page : int, optional
            page's index, defaults to None
        """
        if isinstance(page, int):
            self._pos = page
            self.menu_format()
            data = dict(view=self)
        else:
            data = dict(view=None)

        if self.modifying_embed:
            data["embed"] = self._embed

        with suppress(DiscordException):
            if message := self.message:
                await message.edit(**data)
            elif isinstance(target := self.target, Interaction):
                await target.edit_original_message(**data)

    @button(
        emoji=":lasttrack:952522808347467807",
        row=0,
        custom_id="first",
    )
    async def first(
        self,
        btn: Button,
        interaction: Interaction,
    ) -> None:
        """
        Method used to reach next first of the pagination

        Parameters
        ----------
        btn: Button
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        resp: InteractionResponse = interaction.response
        await self.custom_first(btn, interaction)
        if not resp.is_done():
            return await self.edit(page=0)

    @button(
        emoji=":fastreverse:952522808599126056",
        row=0,
        custom_id="previous",
    )
    async def previous(
        self,
        btn: Button,
        interaction: Interaction,
    ) -> None:
        """
        Method used to reach previous page of the pagination

        Parameters
        ----------
        btn: Button
            Button which interacts with the User
        interaction: Interaction
            Current interaction of the user
        """
        resp: InteractionResponse = interaction.response
        await self.custom_previous(btn, interaction)
        if not resp.is_done():
            return await self.edit(page=self._pos - 1)

    @button(
        emoji=":stop:952522808573968454",
        row=0,
        custom_id="finish",
    )
    async def finish(
        self,
        btn: Button,
        interaction: Interaction,
    ) -> None:
        """
        Method used to conclude the pagination

        Parameters
        ----------
        btn: discord.ui.Button
            Button which interacts with the User
        interaction: discord.Interaction
            Current interaction of the user
        """
        resp: InteractionResponse = interaction.response
        await self.custom_finish(btn, interaction)
        if not resp.is_done():
            await self.delete(force=True)

    @button(
        emoji=":fastforward:952522808347488326",
        row=0,
        custom_id="next",
    )
    async def next(
        self,
        btn: Button,
        interaction: Interaction,
    ) -> None:
        """
        Method used to reach next page of the pagination

        Parameters
        ----------
        btn: discord.ui.Button
            Button which interacts with the User
        interaction: discord.Interaction
            Current interaction of the user
        """
        resp: InteractionResponse = interaction.response
        await self.custom_next(btn, interaction)
        if not resp.is_done():
            return await self.edit(page=self._pos + 1)

    @button(
        emoji=":nexttrack:952522808355848292",
        row=0,
        custom_id="last",
    )
    async def last(
        self,
        btn: Button,
        interaction: Interaction,
    ) -> None:
        """
        Method used to reach last page of the pagination

        Parameters
        ----------
        btn: discord.ui.Button
            Button which interacts with the User
        interaction: discord.Interaction
            Current interaction of the user
        """
        resp: InteractionResponse = interaction.response
        await self.custom_last(btn, interaction)
        if not resp.is_done():
            return await self.edit(
                page=len(self.values[:: self._entries_per_page]) - 1
            )

    async def custom_previous(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_first(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_finish(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_next(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_last(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """
