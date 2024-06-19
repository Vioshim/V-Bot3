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


from datetime import datetime, timedelta

from dateparser import parse
from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    Interaction,
    Message,
    Thread,
    Webhook,
)
from discord.ui import Button, View, button
from discord.utils import MISSING, get, utcnow
from regex import IGNORECASE, MULTILINE, Pattern, compile

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.functions import safe_username

__all__ = ("BumpBot", "PingBump")


class BumpBot:
    id: int
    name: str
    cmd_id: int
    url: str
    hours: int
    format_date: Pattern[str]
    avatar: str = ""

    @classmethod
    def get(cls, **attrs):
        return get(cls.__subclasses__(), **attrs)

    @classmethod
    def on_message(cls, message: Message) -> bool:
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
        return message.author.id == cls.id

    @classmethod
    def on_message_edit(cls, before: Message, after: Message) -> bool:
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
        return after.author.id == cls.id

    @classmethod
    def adapt_embed(cls, ctx: Message) -> Embed:
        embed = ctx.embeds[0].copy()
        embed.timestamp = utcnow()
        if not embed.image:
            embed.set_image(url=WHITE_BAR)

        if interaction := ctx.interaction_metadata:
            user = interaction.user
            embed.set_author(name=user.display_name, icon_url=user.display_avatar)

        if url := cls.url:
            embed.url = url.format(server=ctx.guild.id)
            embed.add_field(
                name="Do you like the server?",
                value=f"> If you like the server, "
                f"feel free to let us know your opinion by rating/reviewing the server in {cls.name}.",
            )

        if guild := ctx.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        return embed


class Disboard(BumpBot):
    id = 302050872383242240
    name = "Disboard"
    cmd_id = 947088344167366698
    url = "https://disboard.org/server/{server}"
    hours = 2
    format_date = compile(r"(\d+ minutes)", IGNORECASE | MULTILINE)

    @classmethod
    def on_message(cls, message: Message) -> bool:
        return super().on_message(message) and message.embeds and "Bump done!" in message.embeds[0].description


class DiscordServer(BumpBot):
    id = 315926021457051650
    name = "Discord-Server"
    url = "https://discord-server.com/{server}#reviews"
    hours = 4.0
    cmd_id = 956435492398841858
    format_date = compile(r"(\d{2}:\d{2}:\d{2})", IGNORECASE | MULTILINE)

    @classmethod
    def on_message(cls, message: Message) -> bool:
        return super().on_message(message) and message.embeds and ":thumbsup:" in message.embeds[0].description


class ListIO(BumpBot):
    id = 212681528730189824
    name = "Discord List IO"
    url = "https://discordlist.io/leaderboard/Pokemon-Parallel-Yonder"
    hours = 7.0
    cmd_id = 999330004548735016
    format_date = compile(r"Please wait (\d+ hours \d+ minutes) more until next bump", IGNORECASE | MULTILINE)
    avatar = "https://cdn.discordapp.com/emojis/230815471299985408.webp"

    @classmethod
    def on_message(cls, message: Message) -> bool:
        return (
            super().on_message(message)
            and message.embeds
            and (
                "Your server has been bumped successfully!" in message.embeds[0].title
                or "Server bumped!" in message.embeds[0].description
            )
        )


class Disboost(BumpBot):
    id = 717015248170909726
    name = "Disboost"
    url = "https://disboost.com/server/{server}"
    hours = 1.0
    cmd_id = 924440973797380146
    format_date = compile(r"has already been bumped, try again (in \d+:\d+:\d+)", IGNORECASE | MULTILINE)

    @classmethod
    def on_message(cls, message: Message) -> bool:
        return super().on_message(message) and bool(
            message.embeds and "You have succesfully bumped" in message.embeds[0].description
        )


class PingBump(View):
    def __init__(
        self,
        *,
        before: Message = None,
        after: Message = None,
        data: BumpBot = None,
        webhook: Webhook = None,
    ):
        super(PingBump, self).__init__(timeout=None)
        self.embed = data.adapt_embed(after)
        self.webhook = webhook
        if url := self.embed.url:
            btn = Button(label="Click Here to Review us!", url=url)
            self.add_item(btn)
        self.before = before
        self.after = after
        self.data = data
        role = get(after.guild.roles, name="Bump Ping")
        if not role:
            self.remove_item(self.reminder)
        self.role = role

    @property
    def mention(self):
        return f"**{self.role and self.role.mention} (Slash Command is </bump:{self.data.cmd_id}>)**"

    @property
    def valid(self) -> bool:
        if before := self.before:
            self.data.on_message_edit(before, self.after)
        return self.data.on_message(self.after)

    @property
    def timedelta(self):
        return self.date.replace(tzinfo=None) - utcnow().replace(tzinfo=None)

    @property
    def date(self) -> datetime:
        if (embeds := self.after.embeds) and (data := self.data.format_date.search(embeds[0].description)):
            return parse(
                data.group(1),
                settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc"),
            )

        return self.after.created_at + timedelta(hours=self.data.hours)

    async def send(self, timeout: bool = False):
        if isinstance(self.after.channel, Thread):
            thread = self.after.channel
        else:
            thread = MISSING

        if timeout:
            embed, view = MISSING, MISSING
        else:
            embed, view = self.embed, self

        return await self.webhook.send(
            content=self.mention,
            embed=embed,
            view=view,
            wait=True,
            thread=thread,
            username=safe_username(self.after.author.display_name),
            avatar_url=self.data.avatar or self.after.author.display_avatar.url,
            allowed_mentions=AllowedMentions(users=True, roles=timeout),
        )

    @button(emoji="a:SZD_desk_bell:769116713639215124", style=ButtonStyle.blurple)
    async def reminder(self, itx: Interaction[CustomBot], _: Button) -> None:
        if self.role in itx.user.roles:
            await itx.user.remove_roles(self.role)
            msg = "Alright, you won't get notified"
        else:
            await itx.user.add_roles(self.role)
            msg = "Alright, you will get notified"

        await itx.response.send_message(msg, ephemeral=True)
