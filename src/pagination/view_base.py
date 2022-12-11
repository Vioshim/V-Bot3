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
from datetime import datetime
from typing import NamedTuple, Optional, Union

from discord import (
    AllowedMentions,
    ButtonStyle,
    DiscordException,
    Embed,
    File,
    GuildSticker,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    MessageReference,
    NotFound,
    PartialEmoji,
    PartialMessage,
    StickerItem,
    User,
    Webhook,
)
from discord.abc import Messageable, Snowflake
from discord.ext.commands import Context
from discord.ui import Button, View, button

from src.utils.etc import WHITE_BAR
from src.utils.functions import embed_modifier

__all__ = ("Basic",)


class ArrowEmotes(NamedTuple):
    START = PartialEmoji(name="DoubleArrowLeft", id=972196330808160296)
    BACK = PartialEmoji(name="ArrowLeft", id=972196330837528606)
    FORWARD = PartialEmoji(name="ArrowRight", id=972196330892058684)
    END = PartialEmoji(name="DoubleArrowRight", id=972196330942390372)
    CLOSE = PartialEmoji(name="Stop", id=972196330795585567)


class Basic(View):
    """A Paginator for View-only purposes"""

    def __init__(
        self,
        *,
        target: Optional[Messageable] = None,
        member: Union[Member, User] = None,
        timeout: Optional[float] = 180.0,
        embed: Optional[Embed] = None,
    ):
        """Init Method

        Parameters
        ----------
        member : Union[Member, User]
            Member
        target : Messageable
            Destination
        timeout : Float, optional
            Provided timeout, defaults to 180.0
        embed : Embed. optional
            Embed to display, defaults to None
        """
        super(Basic, self).__init__(timeout=timeout)
        if not embed:
            embed = Embed(
                colour=member.colour if member else None,
                timestamp=datetime.now(),
            )

        if not member:
            if isinstance(target, (Message, Context)):
                member = target.author
            elif isinstance(target, Interaction):
                member = target.user

        if isinstance(member, User) and (guilds := member.mutual_guilds):
            guild = guilds[0]
            member = guild.get_member(member.id)

        embed.set_image(url=WHITE_BAR)
        if isinstance(member, (User, Member)):
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        if isinstance(member, Member):
            guild = member.guild
            embed.set_footer(text=guild.name, icon_url=guild.icon)
        self.embed = embed
        self.member = member
        self.target = target
        self.message: Optional[Message] = None

    async def on_error(self, interaction: Interaction, error: Exception, item) -> None:
        """|coro|

        A callback that is called when an item's callback or :meth:`interaction_check`
        fails with an error.

        The default implementation logs to the library logger.

        Parameters
        -----------
        interaction: :class:`~discord.Interaction`
            The interaction that led to the failure.
        error: :class:`Exception`
            The exception that was raised.
        item: :class:`Item`
            The item that failed the dispatch.
        """
        interaction.client.logger.exception("Exception in view %r for item %r", self, item, exc_info=error)
        self.stop()

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        """Verification for the interaction user

        Returns
        -------
        bool
            If validation is successful
        """
        condition = self.member is None or interaction.user == self.member
        with suppress(KeyError):
            aux = interaction.client.supporting[interaction.user]
            condition |= self.member == aux

        if not condition:
            msg = f"This menu has been requested by {self.member}"
            await resp.send_message(msg, ephemeral=True)
        elif isinstance(self.target, Interaction):
            self.target = interaction

        return condition

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
        thinking: bool = False,
        thread: Snowflake = None,
        editing_original: bool = False,
        reply_to: Optional[Message] = None,
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
        thinking: bool, optional
            if message is thinking, defaults to False
        thread: Snowflake, optional
            if message is sent to a thread, defaults to None
        """
        target = self.target

        if not embeds:
            embed = embed or self.embed
            self.embed = embed_modifier(embed, **kwargs)
            embeds = [self.embed]

        if not target:
            target = await self.member.create_dm()

        data = dict(
            content=content,
            tts=tts,
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
            data["embed"] = self.embed

        data = {k: v for k, v in data.items() if v}

        if reply_to:
            self.message = await reply_to.reply(**data)
            return self.message

        if isinstance(target, Message):
            if editing_original:
                return await target.edit(**data)
            target = target.channel

        if isinstance(target, Interaction):
            resp: InteractionResponse = target.response
            if editing_original:
                if not resp.is_done():
                    await resp.edit_message(**data)
                else:
                    self.message = await target.edit_original_response(**data)
                return

            if not resp.is_done():
                with suppress(NotFound):
                    await resp.defer(ephemeral=ephemeral, thinking=thinking)
            try:
                self.message = await target.followup.send(**data, wait=True)
            except DiscordException as e:
                target.client.logger.exception("Exception", exc_info=e)
                data.pop("ephemeral", None)
                self.message = await target.channel.send(**data)
            if message := self.message:
                target.client.msg_cache.add(message.id)
        elif isinstance(target, Webhook):
            self.message = await target.send(**data, wait=True)
        else:
            self.message = await target.send(**data)

        return self.message

    async def delete(self, ctx: Optional[Interaction] = None) -> None:
        """This method deletes the view, and stops it."""
        try:
            if ctx and not ctx.response.is_done():
                resp: InteractionResponse = ctx.response
                if msg := self.message:
                    await resp.pong()
                    await msg.delete(delay=0)
                else:
                    await ctx.delete_original_response()
            elif msg := self.message:
                await msg.delete(delay=0)
        except HTTPException:
            if isinstance(self.target, Interaction):
                with suppress(HTTPException):
                    await self.target.delete_original_response()
        finally:
            self.stop()

    async def on_timeout(self) -> None:
        with suppress(DiscordException):
            await self.delete()


class BasicStop(Basic):
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
