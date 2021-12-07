#  Copyright 2021 Vioshim
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Iterable, Optional, TypeVar

from discord import (  # TODO learn about AutocompleteContext
    AllowedMentions,
    DiscordException,
    Embed,
    File,
    GuildSticker,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    MessageReference,
    PartialMessage,
    StickerItem,
    User,
    Webhook,
)
from discord.abc import Messageable, Snowflake
from discord.ui import Button, View, button

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.functions import common_pop_get

_T = TypeVar("_T")
_M = TypeVar("_M", bound=Messageable)

__all__ = ("Simple",)


# noinspection DuplicatedCode,PyTypeChecker
class Simple(View):
    """A Paginator for View-only purposes"""

    def __init__(
            self,
            *,
            bot: CustomBot,
            member: Member | User,
            values: Iterable[_T],
            target: _M = None,
            timeout: Optional[float] = 180.0,
            embed: Embed = None,
            inline: bool = False,
            entries_per_page: int = 25,
    ):
        """Init Method

        Parameters
        ----------
        bot : CustomBot
            Bot
        member : Member
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
        entries_per_page : int
            The max amount of entries per page, defaults to 25
        """
        super().__init__(timeout=timeout)
        if not isinstance(values, Iterable):
            name = values.__class__.__name__ if values is not None else "None"
            raise TypeError(f"{name} is not iterable.")
        items: list[_T] = list(values)
        if not embed:
            embed = Embed(
                title="Displaying values", colour=member.colour, timestamp=datetime.now()
            )
            embed.set_image(url=WHITE_BAR)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            if guild := member.guild:
                embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        self.bot = bot
        self._embed = embed
        self._member = member
        self._values = items
        self._target = target
        self._message: Optional[Message] = None
        self._inline = inline
        self._pos = 0
        self._entries_per_page = entries_per_page
        self.sort()
        self.menu_format()

    def sort(self, key: Callable[[_T], Any] = None, reverse: bool = False) -> None:
        """Sort method used for the view's values

        Attributes
        ----------
        key : Callable[[_T], Any], optional
            key to use for sorting, defaults to None
        reverse : bool, optional
            sets the order to reverse, defaults to False
        """
        self.values.sort(key=key, reverse=reverse)

    # noinspection PyMethodMayBeStatic
    def parser(self, item: _T) -> tuple[str, str]:
        if isinstance(item, tuple):
            return item
        return str(item), repr(item)

    async def send(
            self,
            content: str = None,
            *,
            tts: bool = False,
            embed: Embed = None,
            embeds: list[Embed] = None,
            file: File = None,
            files: list[File] = None,
            stickers: list[GuildSticker | StickerItem] = None,
            delete_after: float = None,
            nonce: int = None,
            allowed_mentions: AllowedMentions = None,
            reference: Message | MessageReference | PartialMessage = None,
            mention_author: bool = False,
            username: str = None,
            avatar_url: str = None,
            ephemeral: bool = False,
            thread: Snowflake = None,
    ) -> bool:
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
        stickers : list[GuildSticker | StickerItem], optional
            message's stickers, defaults to None
        delete_after : float, optional
            defaults to None
        nonce : int, optional
            message's nonce, defaults to None
        allowed_mentions : AllowedMentions, optional
            message's allowed mentions, defaults MISSING
        reference : Message | MessageReference | PartialMessage, optional
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
        target = self._target

        if not target:
            target = await self.member.create_dm()

        data = dict(
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
            view=self,
        )

        webhook_elements = dict(
            username=username, avatar_url=avatar_url, thread=thread, ephemeral=ephemeral, wait=True
        )

        if not embeds and not embed:
            data["embed"] = self._embed

        data = {k: v for k, v in data.items() if v}

        if isinstance(target, Interaction):
            resp: InteractionResponse = target.response
            if not resp.is_done():
                common_pop_get(data, "stickers", "nonce", "reference", "mention_author")
                await resp.send_message(**data, ephemeral=ephemeral)
            else:
                data |= webhook_elements
                await target.followup.send(**data)
            if message := await target.original_message():
                await message.edit(embed=self._embed)
                self.message = message
        else:

            if isinstance(target, Webhook):
                data |= webhook_elements

            self.message = await target.send(**data)

        if message := self.message:
            self.bot.msg_cache.add(message.id)

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, target: _M):
        self._target = target

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, message: Optional[Message]):
        self._message = message

    @message.deleter
    def message(self):
        self._message = None

    @property
    def member(self) -> Member | User:
        return self._member

    @member.setter
    def member(self, member: Member | User):
        self._member = member

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
        self.menu_format()

    @property
    def entries_per_page(self) -> int:
        return self._entries_per_page

    @entries_per_page.setter
    def entries_per_page(self, entries_per_page: int):
        self._entries_per_page = entries_per_page
        self.menu_format()

    @property
    def embed(self):
        return self._embed

    @embed.setter
    def embed(self, embed: Embed):
        self._embed = embed

    async def delete(self) -> None:
        """This method deletes the view, and stops it."""
        try:
            if message := self.message:
                await message.delete()
            self.message = None
        except DiscordException as e:
            self.bot.logger.exception(
                "Exception occurred while deleting %s", self.message.jump_url, exc_info=e
            )
        finally:
            return self.stop()

    async def on_timeout(self) -> None:
        await self.delete()

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if self._member != interaction.user:
            return await resp.send_message("This isn't yours", ephemeral=True)
        return True

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
            for item in self.values[amount: amount + self._entries_per_page]:
                name, value = self.parser(item)
                self.embed.add_field(name=name, value=value, inline=self._inline)

    async def edit(self, page: int) -> None:
        """This method edits the pagination's page given an index.

        Parameters
        ----------
        page : int
            page's index
        """
        self._pos = page
        self.menu_format()
        try:
            if message := self.message:
                await message.edit(embed=self._embed, view=self)
        except DiscordException as e:
            self.bot.logger.exception(
                "Exception while editing view %s", self.message.jump_url, exc_info=e
            )

    @button(emoji=":lasttrack:861938354609717258", row=0, custom_id="first")
    async def first(self, btn: Button, interaction: Interaction) -> None:
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

    @button(emoji=":fastreverse:861938354136416277", row=0, custom_id="previous")
    async def previous(self, btn: Button, interaction: Interaction) -> None:
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

    @button(emoji=":stop:861938354244943913", row=0, custom_id="finish")
    async def finish(self, btn: Button, interaction: Interaction) -> None:
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
            await self.delete()

    @button(emoji=":fastforward:861938354085953557", row=0, custom_id="next")
    async def next(self, btn: Button, interaction: Interaction) -> None:
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

    @button(emoji=":nexttrack:861938354210603028", row=0, custom_id="last")
    async def last(self, btn: Button, interaction: Interaction) -> None:
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
            return await self.edit(page=len(self.values[:: self._entries_per_page]) - 1)

    async def custom_previous(self, btn: Button, interaction: Interaction):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_first(self, btn: Button, interaction: Interaction):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_finish(self, btn: Button, interaction: Interaction):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_next(self, btn: Button, interaction: Interaction):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """

    async def custom_last(self, btn: Button, interaction: Interaction):
        """Placeholder for custom defined operations

        Parameters
        ----------
        btn : Button
            button which interact with the User
        interaction : Interaction
            interaction that triggered the button
        """
