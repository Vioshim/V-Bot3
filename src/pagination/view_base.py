# Copyright 2021 Vioshim
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

from datetime import datetime
from typing import Generic, Optional, TypeVar, Union

from discord import (
    AllowedMentions,
    ApplicationContext,
    DiscordException,
    Embed,
    File,
    GuildSticker,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    MessageReference,
    NotFound,
    PartialMessage,
    StickerItem,
    User,
    Webhook,
)
from discord.abc import Messageable, Snowflake
from discord.ext.commands import Context
from discord.ui import View

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR

_M = TypeVar("_M", bound=Messageable)

__all__ = ("Basic",)


# noinspection DuplicatedCode,PyTypeChecker
class Basic(Generic[_M], View):
    """A Paginator for View-only purposes"""

    def __init__(
        self,
        *,
        bot: CustomBot,
        target: _M = None,
        member: Union[Member, User] = None,
        timeout: Optional[float] = 180.0,
        embed: Embed = None,
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
        timeout : Float, optional
            Provided timeout, defaults to 180.0
        embed : Embed. optional
            Embed to display, defaults to None
        """
        super().__init__(timeout=timeout)
        if not embed:
            embed = Embed(
                colour=member.colour,
                timestamp=datetime.now(),
            )

        if not member:
            if isinstance(target, (Message, Context, ApplicationContext)):
                member = target.author
            elif isinstance(target, Interaction):
                member = target.user

        embed.set_image(url=WHITE_BAR)
        embed.set_author(
            name=member.display_name,
            icon_url=member.display_avatar.url,
        )
        if isinstance(member, Member):
            guild = member.guild
            embed.set_footer(
                text=guild.name,
                icon_url=guild.icon.url,
            )
        self.bot = bot
        self._embed = embed
        self._member = member
        self._target = target
        self._message: Optional[Message] = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        """Verification for the interaction user

        Returns
        -------
        bool
            If validation is successful
        """
        if self._member != interaction.user:
            msg = f"This menu has been requested by {self.member}"
            await resp.send_message(msg, ephemeral=True)
            return False
        return True

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
            username=username,
            avatar_url=avatar_url,
            thread=thread,
            ephemeral=ephemeral,
        )

        if not embeds and not embed:
            data["embed"] = self._embed

        data = {k: v for k, v in data.items() if v}

        if isinstance(target, Message):
            target = target.channel

        if isinstance(target, Interaction):
            resp: InteractionResponse = target.response
            if not resp.is_done():
                await resp.send_message(**data)
                self.bot.logger.info("Test 1")
            else:
                await target.followup.send(**data)
                self.bot.logger.info("Test 2")
            if message := await target.original_message():
                await message.edit(embed=self._embed, view=self)
                self.message = message
                self.bot.logger.info("Test 3")
        elif isinstance(target, Webhook):
            self.message = await target.send(**data, wait=True)
            self.bot.logger.info("Test 4")
        else:
            self.message = await target.send(**data)
            self.bot.logger.info("Test 5")

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
    def member(self) -> Union[Member, User]:
        return self._member

    @member.setter
    def member(self, member: Union[Member, User]):
        self._member = member

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
        except NotFound:
            return
        except DiscordException as e:
            self.bot.logger.exception(
                "Exception occurred while deleting %s",
                self.message.jump_url,
                exc_info=e,
            )
        finally:
            return self.stop()

    async def on_timeout(self) -> None:
        await self.delete()
