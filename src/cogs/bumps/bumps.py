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


from datetime import datetime
from re import IGNORECASE, MULTILINE, Pattern, compile
from typing import Optional

from dateparser import parse
from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    Interaction,
    InteractionResponse,
    Message,
    Thread,
    Webhook,
    WebhookMessage,
)
from discord.ui import Button, View, button
from discord.utils import MISSING, get, utcnow

from src.utils.etc import WHITE_BAR

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

    @classmethod
    def adapt_embed(cls, ctx: Message) -> Embed:
        embed = ctx.embeds[0]
        embed.timestamp = utcnow()
        if not embed.image:
            embed.set_image(url=WHITE_BAR)

        if interaction := ctx.interaction:
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
        return message.embeds and "Bump done!" in message.embeds[0].description


class DiscordServer(BumpBot):
    id = 315926021457051650
    name = "Discord-Server"
    url = "https://discord-server.com/{server}#reviews"
    hours = 4.0
    cmd_id = 956435492398841858
    format_date = compile(r"(\d{2}:\d{2}:\d{2})", IGNORECASE | MULTILINE)

    @classmethod
    def on_message(cls, message: Message) -> bool:
        return message.embeds and ":thumbsup:" in message.embeds[0].description


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
        return message.embeds and (
            "Your server has been bumped successfully!" in message.embeds[0].title
            or "Server bumped!" in message.embeds[0].description
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
        return bool(message.embeds and "You have succesfully bumped" in message.embeds[0].description)


class PingBump(View):
    def __init__(
        self,
        *,
        before: Message = None,
        after: Message = None,
        data: BumpBot = None,
        webhook: Webhook = None,
    ):
        super(PingBump, self).__init__(timeout=data.hours * 3600.0)
        self.embed = data.adapt_embed(after)
        self.webhook = webhook
        if url := self.embed.url:
            btn = Button(label="Click Here to Review us!", url=url)
            self.add_item(btn)
        self.before = before
        self.after = after
        self.data = data
        self.message: Optional[WebhookMessage] = None

    @property
    def valid(self) -> bool:
        if before := self.before:
            self.data.on_message_edit(before, self.after)
        return self.data.on_message(self.after)

    @property
    def timedelta(self):
        if date := self.date:
            return date.replace(tzinfo=None) - utcnow().replace(tzinfo=None)

    @property
    def date(self) -> datetime:
        if (embeds := self.after.embeds) and (
            data := self.data.format_date.search(
                embeds[0].description,
            )
        ):
            return parse(
                data.group(1),
                settings=dict(
                    PREFER_DATES_FROM="future",
                    TIMEZONE="utc",
                ),
            )

    async def send(self, timeout: bool = False):
        if isinstance(self.after.channel, Thread):
            thread = self.after.channel
        else:
            thread = MISSING

        mention = f"</bump:{self.data.cmd_id}>"
        if timeout:
            mention = f"**<@&1008443584594325554> (Slash Command is {mention}):**"
            embed, view, wait = MISSING, MISSING, False
        else:
            embed, view, wait = self.embed, self, True

        if not (avatar_url := self.data.avatar):
            avatar_url = self.after.author.display_avatar.url

        self.message = await self.webhook.send(
            content=mention,
            embed=embed,
            view=view,
            wait=wait,
            thread=thread,
            username=self.after.author.display_name,
            avatar_url=avatar_url,
            allowed_mentions=AllowedMentions(users=True, roles=True),
        )

    @button(emoji="a:SZD_desk_bell:769116713639215124", style=ButtonStyle.blurple)
    async def reminder(self, inter: Interaction, _: Button) -> None:
        resp: InteractionResponse = inter.response
        role = inter.guild.get_role(1008443584594325554)
        if role in inter.user.roles:
            await inter.user.remove_roles(role)
            msg = "Alright, you won't get notified"
        else:
            await inter.user.add_roles(role)
            msg = "Alright, you will get notified"
        await resp.send_message(msg, ephemeral=True)

    async def on_timeout(self) -> None:
        self.reminder.disabled = True
        if message := self.message:
            await message.edit(view=self)
        await self.send(timeout=True)
        self.stop()
