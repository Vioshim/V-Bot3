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

from datetime import datetime
from typing import Optional, Union

from discord import (
    AllowedMentions,
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
    PartialMessage,
    StickerItem,
    Thread,
    User,
    Webhook,
)
from discord.abc import Messageable, Snowflake
from discord.ext.commands import Context
from discord.ui import View

from src.utils.etc import WHITE_BAR
from src.utils.functions import embed_modifier

__all__ = ("Basic",)


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
            embed = Embed(colour=member.colour, timestamp=datetime.now())

        if not member:
            if isinstance(target, (Message, Context)):
                member = target.author
            elif isinstance(target, Interaction):
                member = target.user

        if isinstance(member, User) and (guilds := member.mutual_guilds):
            guild = guilds[0]
            member = guild.get_member(member.id)

        embed.set_image(url=WHITE_BAR)
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        if isinstance(member, Member):
            guild = member.guild
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        self.embed = embed
        self.member = member
        self.target = target
        self.message: Optional[Message] = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        """Verification for the interaction user

        Returns
        -------
        bool
            If validation is successful
        """
        if self.member != interaction.user:
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
            thinking=thinking,
        )

        if not embeds and not embed:
            data["embed"] = self.embed

        data = {k: v for k, v in data.items() if v}

        if reply_to:
            self.message = await reply_to.reply(**data)
            return self.message

        if isinstance(target, Message):
            target = target.channel

        if isinstance(target, Interaction):
            resp: InteractionResponse = target.response
            if editing_original:
                self.message = await target.edit_original_message(**data)
                return

            if not resp.is_done():
                if isinstance(target, Thread) and target.archived:
                    await target.edit(archived=True)
                await resp.defer(ephemeral=ephemeral, thinking=thinking)

            try:
                self.message = await target.followup.send(**data, wait=True)
            except DiscordException as e:
                target.client.logger.exception("Exception", exc_info=e)
                self.message = await target.channel.send(**data)
            if message := self.message:
                target.client.msg_cache.add(message.id)
        elif isinstance(target, Webhook):
            self.message = await target.send(**data, wait=True)
        else:
            self.message = await target.send(**data)

        return self.message

    async def delete(self) -> None:
        """This method deletes the view, and stops it."""

        try:
            if self.message:
                if self.message.flags.ephemeral:
                    await self.message.edit(view=None)
                else:
                    await self.message.delete()
        except HTTPException:
            try:
                if isinstance(self.target, Interaction):
                    message = await self.target.original_message()
                    await message.edit(view=None)
            except HTTPException:
                pass
        finally:
            self.message = None
            self.stop()

    async def on_timeout(self) -> None:
        await self.delete()
