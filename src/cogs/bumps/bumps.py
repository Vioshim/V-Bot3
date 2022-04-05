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

from abc import ABCMeta, abstractmethod
from datetime import datetime
from re import IGNORECASE, MULTILINE, compile
from typing import Optional

from dateparser import parse
from discord import (
    AllowedMentions,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    TextChannel,
)
from discord.ui import Button, View, button
from discord.utils import utcnow

from src.utils.etc import WHITE_BAR

__all__ = ("BUMPS",)


class Bump(metaclass=ABCMeta):
    def __init__(
        self,
        name: str,
        prefix: str,
        url: Optional[str] = None,
        hours: float = 2.0,
        format_date: str = "",
    ):
        self.name = name
        self.prefix = prefix
        self.url = url
        self.hours = hours
        self.format_date = compile(format_date, IGNORECASE | MULTILINE)

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

    def adapt_embed(self, ctx: Message) -> Embed:
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
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )
        if guild := ctx.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        return embed


class PingBump(View):
    def __init__(
        self,
        *,
        before: Message = None,
        after: Message = None,
        data: Bump = None,
    ):
        super(PingBump, self).__init__(timeout=data.hours * 3600.0)
        self.mentions: set[Member] = set()
        self.embed = data.adapt_embed(after)
        if url := self.embed.url:
            btn = Button(label="Click Here to Review us!", url=url)
            self.add_item(btn)
        self.before = before
        self.after = after
        self.data = data
        self.message: Optional[Message] = None

    @property
    def valid(self) -> bool:
        if before := self.before:
            self.data.on_message_edit(before, self.after)
        return self.data.on_message(self.after)

    @property
    def timedelta(self):
        if date := self.date:
            return date - utcnow()

    @property
    def date(self) -> datetime:
        if (embeds := self.after.embeds) and (
            data := self.data.format_date.search(embeds[0].description)
        ):
            return parse(
                data.group(1),
                settings=dict(
                    PREFER_DATES_FROM="future",
                    TIMEZONE="utc",
                ),
            )

    async def send(self):
        self.message = await self.after.channel.send(
            embed=self.embed,
            view=self,
        )

    @button(emoji="a:SZD_desk_bell:769116713639215124")
    async def reminder(self, _: Button, inter: Interaction) -> None:
        resp: InteractionResponse = inter.response
        if inter.user in self.mentions:
            self.mentions.remove(inter.user)
            return await resp.send_message(
                "Alright, you won't get notified", ephemeral=True
            )
        self.mentions.add(inter.user)
        return await resp.send_message("Alright, you will get notified", ephemeral=True)

    async def on_timeout(self) -> None:
        text = f"**Bump Reminder (Prefix is {self.data.prefix}):**\n"
        channel: TextChannel = self.message.channel
        if mentions := ", ".join(item.mention for item in self.mentions):
            text += f"Notifying: {mentions}"
        self.mentions.clear()
        self.reminder.disabled = True
        if message := self.message:
            await message.edit(view=self)
        await channel.send(
            content=text,
            allowed_mentions=AllowedMentions(users=True),
        )
        self.stop()


class Disboard(Bump):
    def __init__(self):
        super(Disboard, self).__init__(
            name="Disboard",
            url="https://disboard.org/server/{server}",
            prefix="!d bump",
            format_date=r"(\d+ minutes)",
        )

    def on_message(self, message: Message) -> bool:
        if embeds := message.embeds:
            return "Bump done!" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class DiscordServer(Bump):
    def __init__(self):
        super(DiscordServer, self).__init__(
            name="Discord-Server",
            url="https://discord-server.com/{server}#reviews",
            hours=4.0,
            prefix="!bump",
            format_date=r"(\d{2}:\d{2}:\d{2})",
        )

    def on_message(self, message: Message) -> bool:
        if embeds := message.embeds:
            return ":thumbsup:" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class ListIO(Bump):
    def __init__(self):
        super(ListIO, self).__init__(
            name="Discord List IO",
            url="https://discordlist.io/leaderboard/Pokemon-Parallel-Yonder",
            hours=8.0,
            prefix="dlm!bump",
            format_date=r"Available in: (\d+ hours \d+ minutes)",
        )

    def on_message(self, message: Message) -> bool:
        if embeds := message.embeds:
            return "Server bumped!" in embeds[0].description
        return False

    def on_message_edit(self, _before: Message, _now: Message) -> bool:
        return False


class ServerMate(Bump):
    def __init__(self):
        super(ServerMate, self).__init__(
            name="Discord List IO",
            url="https://discordlist.io/leaderboard/Pokemon-Parallel-Yonder",
            hours=8.0,
            prefix="!bump",
            format_date=r"Available in: (\d+ hours \d+ minutes)",
        )

    def on_message(self, message: Message) -> bool:
        return False

    def on_message_edit(self, before: Message, now: Message) -> bool:
        if embeds := now.embeds:
            return embeds[0].author.name == "Server Bumped"
        return False


BUMPS: dict[int, Bump] = {
    302050872383242240: Disboard(),
    315926021457051650: DiscordServer(),
    212681528730189824: ListIO(),
    481810078031282176: ServerMate(),
}
