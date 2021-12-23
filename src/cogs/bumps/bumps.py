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

from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Optional

from discord import (
    AllowedMentions,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    PartialEmoji,
    TextChannel,
)
from discord.ui import Button, View, button
from discord.utils import utcnow

from src.utils.etc import WHITE_BAR

__all__ = ("BumpsEnum",)


class Bump(metaclass=ABCMeta):
    def __init__(
        self,
        id: int,
        name: str,
        url: Optional[str] = None,
        prefix: str = "!bump",
        hours: float = 2.0,
    ):
        self.id: id
        self.name = name
        self.url = url
        self.prefix = prefix
        self.hours = hours

    @abstractmethod
    def on_message(self, message: Message) -> bool:
        """Trigger Message Event

        Parameters
        ----------
        message : Message
            Message

        Returns
        -------
        bool
            If applicable
        """
        return message.author.id == self.id

    @abstractmethod
    def on_message_edit(self, before: Message, after: Message) -> bool:
        """Trigger Event

        Parameters
        ----------
        before : Message
            previous message
        after : Message
            edited message

        Returns
        -------
            If applicable
        """
        return after.author.id == self.id

    def adapt_embed(self, ctx: Message):
        embed = ctx.embeds[0]
        embed.timestamp = utcnow()
        if not embed.image:
            embed.set_image(url=WHITE_BAR)
        if url := self.url:
            embed.url = url.format(server=ctx.guild.id)
            embed.add_field(
                name="Do you like the server?",
                value=f"> If you like the server, "
                f"feel free to let us know your opinion by rating/reviewing the server in {self.name}.",
            )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.avatar.url
        )
        if guild := ctx.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        return embed


class PingBump(View):
    def __init__(self, ctx: Message, data: Bump):
        super(PingBump, self).__init__(timeout=data.hours * 3600.0)
        self.mentions: set[Member] = set()
        self.embed = data.adapt_embed(ctx)
        self.prefix = data.prefix
        self.message: Optional[Message] = None
        self.data = data

    async def send(
        self,
    ):
        view = View()
        if url := self.embed.url:
            btn = Button(label="Click Here to Review us!", url=url)
            view.add_item(item=btn)
            self.message = await self.message.channel.send(
                embed=self.embed,
                view=view,
            )
        await self.wait()

    @button(
        emoji=PartialEmoji(
            name="SZD_desk_bell",
            animated=True,
            id=769116713639215124,
        )
    )
    async def reminder(self, _, inter: Interaction) -> None:
        resp: InteractionResponse = inter.response
        if inter.user in self.mentions:
            self.mentions.remove(inter.user)
            return await resp.send_message(
                "Alright, you won't get notified", ephemeral=True
            )
        self.mentions.add(inter.user)
        return await resp.send_message(
            "Alright, you will get notified", ephemeral=True
        )

    async def on_timeout(self) -> None:
        text = f"**Bump Reminder (Prefix is {self.prefix}):**\n"
        channel: TextChannel = self.message.channel
        if mentions := ", ".join(item.mention for item in self.mentions):
            text += f"Notifying: {mentions}"
        self.mentions.clear()
        self.reminder.disabled = True
        await self.message.edit(view=self)
        await channel.send(
            content=text,
            allowed_mentions=AllowedMentions(users=True),
        )
        self.stop()


class Disboard(Bump):
    def __init__(self):
        super(Disboard, self).__init__(
            id=302050872383242240,
            name="Disboard",
            url="https://disboard.org/server/{server}",
            prefix="!d bump",
        )

    def on_message(self, message: Message) -> bool:
        if super(Disboard, self).on_message(message):
            if embeds := message.embeds:
                return ":thumbsup:" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class DiscordServer(Bump):
    def __init__(self):
        super(DiscordServer, self).__init__(
            id=315926021457051650,
            name="Discord-Server",
            url="https://discord-server.com/{server}#reviews",
            hours=4.0,
        )

    def on_message(self, message: Message) -> bool:
        if super(DiscordServer, self).on_message(message):
            if embeds := message.embeds:
                return ":thumbsup:" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class ListIO(Bump):
    def __init__(self):
        super(ListIO, self).__init__(
            id=212681528730189824,
            name="Discord List IO",
            url="https://discordlist.io/leaderboard/Pokemon-Parallel-Yonder",
            hours=8.0,
            prefix="dlm!bump",
        )

    def on_message(self, message: Message) -> bool:
        if super(ListIO, self).on_message(message):
            if embeds := message.embeds:
                return "Server bumped!" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class ServerMate(Bump):
    def __init__(self):
        super(ServerMate, self).__init__(
            id=481810078031282176,
            name="Discord List IO",
            url="https://discordlist.io/leaderboard/Pokemon-Parallel-Yonder",
            hours=8.0,
            prefix="dlm!bump",
        )

    def on_message(self, message: Message) -> bool:
        return False

    def on_message_edit(self, before: Message, now: Message) -> bool:
        if super(ServerMate, self).on_message_edit(before, now):
            if embeds := now.embeds:
                return embeds[0].author.name == "Server Bumped"
        return False


class BumpsEnum(Enum):
    DISBOARD = Disboard()
    DISCORDSERVER = DiscordServer()
    LISTIO = ListIO()
    SERVERMATE = ServerMate()

    def on_message(self, message: Message) -> bool:
        return self.value.on_message(message)

    def on_message_edit(self, before: Message, now: Message) -> bool:
        return self.value.on_message_edit(before, now)
