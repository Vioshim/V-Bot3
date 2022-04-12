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

from contextlib import suppress
from itertools import groupby
from logging import getLogger, setLoggerClass
from typing import Callable

from discord import (
    Embed,
    Forbidden,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    SelectOption,
    TextChannel,
    Webhook,
)
from discord.ui import Select, View, select
from discord.utils import remove_markdown
from humanize import naturaltime

from src.pagination.complex import Complex
from src.structures.logger import ColoredLogger

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


__all__ = ("MessagePaginator", "get_title", "get_date", "msg_parser")


def get_title(message: Message):
    if embeds := message.embeds:
        value = embeds[0].title or embeds[0].description
    else:
        value = message.content
    if len(attachments := message.attachments) > 1:
        value = value or f"{len(attachments)} Attachments"
    elif attachments:
        value = value or attachments[0].filename
    if len(stickers := message.stickers) > 1:
        value = value or f"{len(stickers)} Stickers"
    elif stickers:
        value = value or f"Sticker: {stickers[0].name}"
    return remove_markdown(value or "Unknown").removeprefix("> ")


def get_date(message: Message):
    return naturaltime(message.created_at.replace(tzinfo=None)).title()


def msg_parser(msg: Message):
    description = get_date(msg)
    if msg.embeds:
        description = msg.embeds[0].description or description
    return get_title(msg), description


class MessagePaginator(Complex):
    def __init__(
        self,
        member: Member,
        target: Interaction | Webhook | TextChannel,
        messages: set[Message],
        parser: Callable[[Message], tuple[str, str]] = msg_parser,
    ):
        super(MessagePaginator, self).__init__(
            member=member,
            target=target,
            values=messages,
            timeout=None,
            parser=parser,
            keep_working=True,
            sort_key=get_title,
        )
        self.embed.title = "Select Message"

    @select(
        row=1,
        placeholder="Select the messages",
        custom_id="selector",
    )
    async def select_choice(
        self,
        ctx: Interaction,
        sct: Select,
    ) -> None:
        response: InteractionResponse = ctx.response
        item: Message = self.current_choice
        view = View.from_message(item)
        await response.defer(ephemeral=True)
        files = []
        embeds = item.embeds
        if not (item.content or embeds):
            for attach in item.attachments:
                with suppress(HTTPException, NotFound, Forbidden):
                    file = await attach.to_file(use_cached=True)
                    files.append(file)
            embeds = [
                Embed(title=sticker.name).set_image(url=sticker.url)
                for sticker in item.stickers
            ]

        if not (files or embeds or item.content):
            await ctx.followup.send(
                "Message information is unknown.",
                ephemeral=True,
            )
            with suppress(HTTPException, NotFound, Forbidden):
                await item.delete()
        else:
            await ctx.followup.send(
                content=item.content,
                embeds=embeds,
                files=files,
                view=view,
                ephemeral=True,
            )

        await super(MessagePaginator, self).select_choice(ctx, sct)


class MessageView(View):
    def __init__(
        self,
        messages: list[Message],
        parser: Callable[[Message], tuple[str, str]] = msg_parser,
    ):
        super().__init__(timeout=None)
        self.parser = parser
        self._messages = messages
        self.data: dict[str, set[Message]] = {}
        self.setup()

    def group_method(self, messages: set[Message]):
        return {
            k: set(v)
            for k, v in groupby(
                filter(lambda x: x.webhook_id and x.embeds, messages),
                key=lambda x: x.embeds[0].footer.text,
            )
            if k
        }

    @property
    def messages(self):
        return self._messages

    @messages.setter
    def messages(self, messages: list[Message]):
        self._messages = messages
        self.setup()

    @messages.deleter
    def messages(self):
        self._messages = []
        self.setup()

    def setup(self):
        sct: Select = self.select_msg
        sct.options.clear()
        self.data = self.group_method(self.messages)
        for key, value in self.data.items():
            sct.add_option(
                label=key,
                value=key,
                description=f"{len(value)} messages.",
                emoji="\N{HANDSHAKE}",
            )
        if not sct.options:
            sct.append_option(SelectOption(label="Empty", value="Empty"))
            sct.disabled = True
        else:
            sct.disabled = False

    @select(
        placeholder="Messages by Category",
        row=4,
        custom_id="msg-filter",
    )
    async def select_msg(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        item = sct.values[0]
        if items := self.data.get(sct.values[0]):
            view = MessagePaginator(
                member=ctx.user,
                target=ctx,
                messages=items,
                parser=self.parser,
            )
            embed = view.embed
            embed.title = f"{item} Group".title()
            async with view.send(ephemeral=True):
                logger.info(
                    "User %s is reading %s",
                    str(ctx.user),
                    embed.title,
                )
        else:
            await resp.send_message(
                "No values were found that match this category.",
                ephemeral=True,
            )
