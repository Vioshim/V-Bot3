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

from contextlib import asynccontextmanager
from logging import getLogger, setLoggerClass
from typing import Optional, TypeVar

from discord import (
    Asset,
    File,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    SelectOption,
    User,
)
from discord.abc import Messageable
from discord.ui import Select, select

from src.pagination.view_base import Basic
from src.structures.logger import ColoredLogger
from src.utils.etc import STICKER_EMOJI
from src.utils.matches import REGEX_URL

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


_M = TypeVar("_M", bound=Messageable)


def check(ctx: Interaction):
    def inner(message: Message):
        if ctx.user == message.author and ctx.channel == message.channel:
            if REGEX_URL.match(message.content or ""):
                return True
            if attachments := message.attachments:
                return attachments[0].content_type.startswith("image/")
        return False

    return inner


class ImageView(Basic):
    def __init__(self, member: Member | User, target: _M, default_img: File | str | Asset = None):
        super(ImageView, self).__init__(member=member, target=target, timeout=None)
        if isinstance(default_img, str):
            self.embed.set_image(url=default_img)
        elif isinstance(default_img, File):
            self.embed.set_image(url=f"attachment://{default_img.filename}")
        elif isinstance(default_img, Asset):
            self.embed.set_image(url=default_img.url)

        self.embed.title = "Image"
        self.received: Optional[Message] = None
        self.text: Optional[str] = default_img
        self.default_image.disabled = not default_img

    @asynccontextmanager
    async def send(self, **kwargs):
        file: Optional[file] = None
        if isinstance(self.text, File):
            file = self.text
        try:
            await super(ImageView, self).send(file=file, **kwargs)
        except HTTPException:
            self.embed.set_image(url=None)
            self.default_image.disabled = True
            await super(ImageView, self).send(file=file, **kwargs)
        except Exception as e:
            logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
        finally:
            if self.message:
                self.text = self.message.embeds[0].image.url
            await self.wait()
            await self.delete()
            yield self.text

    @select(
        placeholder="Image Options. Click Here",
        options=[
            SelectOption(
                label="I'll send an Image",
                value="image",
                description="It works with URLs and Attchments.",
                emoji=STICKER_EMOJI,
            ),
            SelectOption(
                label="I like the image",
                value="keep",
                description="Use this to not make changes.",
                emoji=STICKER_EMOJI,
            ),
            SelectOption(
                label="Remove image",
                value="remove",
                description="Use this to remove stored image.",
                emoji=STICKER_EMOJI,
            ),
        ],
    )
    async def insert_image(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response

        if "keep" in sct.values:
            return await resp.edit_message(content="Keeping default image.", embeds=[], view=None)
        elif "remove" in sct.values:
            self.text = None
            return await resp.edit_message(content="Removed default image.", embeds=[], view=None)

        await resp.edit_message(content="Alright, now send the URL or Attach an image.", embeds=[])

        received: Message = await ctx.client.wait_for("message", check=check(ctx))
        if attachments := received.attachments:
            self.text = attachments[0].proxy_url
            self.received = received
            await received.delete(delay=0)
        elif file := await ctx.client.get_file(url=received.content, filename="image"):
            await received.delete(delay=0)
            self.received = foo = await ctx.channel.send(file=file)
            self.text = self.received.attachments[0].proxy_url
            await foo.delete(delay=0)
        elif image := self.message.embeds[0].image:
            self.text = image.url
        else:
            self.text = None
        self.stop()
