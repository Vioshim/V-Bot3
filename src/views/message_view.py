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
    return remove_markdown(value or "Unknown")


def get_date(message: Message):
    return naturaltime(message.created_at.replace(tzinfo=None)).title()


def msg_parser(msg: Message):
    return get_title(msg), get_date(msg)


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
        if item.content or item.embeds:
            embeds = item.embeds
        else:
            for attach in item.attachments:
                with suppress(HTTPException, NotFound, Forbidden):
                    file = await attach.to_file(use_cached=True)
                    files.append(file)
            embeds = [Embed(title=sticker.name).set_image(url=sticker.url) for sticker in item.stickers]
            if not (files or embeds):
                await ctx.followup.send("Message information is unknown.", ephemeral=True)
                with suppress(HTTPException, NotFound, Forbidden):
                    await item.delete()

        if not response.is_done():
            await ctx.followup.send(
                content=item.content,
                embeds=embeds,
                files=files,
                view=view,
                ephemeral=True,
            )

        await super(MessagePaginator, self).select_choice(ctx, sct)


class MessageView(Complex):

    def __init__(
        self,
        messages: list[Message],
    ):
        super().__init__(timeout=None)
        self._data: dict[str, set[Message]] = {
            k: set(v)
            for k, v in groupby(
                filter(lambda x: x.webhook_id, messages),
                key=lambda x: x.embeds[0].footer.text,
            )
            if k and v
        }
        self.setup()

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: list[Message] | dict[str, set[Message]]):
        if isinstance(data, list):
            self._data: dict[str, set[Message]] = {
                k: set(v)
                for k, v in groupby(
                    filter(lambda x: x.webhook_id, data),
                    key=lambda x: x.embeds[0].footer.text,
                )
                if k and v
            }
        else:
            self._data = data
        self.setup()

    def setup(self):
        sct: Select = self.select_msg
        sct.options.clear()
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
        if items := self.data.get(sct.values[0], set()):
            view = MessagePaginator(
                member=ctx.user,
                target=ctx,
                messages=items,
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
