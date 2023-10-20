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

import asyncio
from contextlib import asynccontextmanager
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
from src.structures.bot import CustomBot
from src.utils.etc import STICKER_EMOJI
from src.utils.matches import REGEX_URL

_M = TypeVar("_M", bound=Messageable)


def check(ctx: Interaction):
    def inner(message: Message):
        return (
            ctx.user == message.author
            and ctx.channel == message.channel
            and (
                bool(REGEX_URL.match(message.content))
                or any(str(x.content_type).startswith("image/") for x in message.attachments)
            )
        )

    return inner


class ImageView(Basic):
    def __init__(
        self,
        member: Member | User,
        target: _M,
        default_img: File | str | Asset = "",
    ):
        super(ImageView, self).__init__(member=member, target=target, timeout=None)
        if isinstance(default_img, str) and default_img:
            self.embed.set_image(url=default_img)
        elif isinstance(default_img, File):
            self.embed.set_image(url=f"attachment://{default_img.filename}")
        elif isinstance(default_img, Asset):
            self.embed.set_image(url=default_img.url.split("?")[0])
        else:
            self.embed.set_image(url=None)

        self.embed.title = "Image"
        self.received: Optional[Message] = None
        self.text: Optional[str] = default_img

    @asynccontextmanager
    async def send(self, **kwargs):
        file = self.text if isinstance(self.text, File) else None
        try:
            await super(ImageView, self).send(file=file, **kwargs)
        except HTTPException:
            self.embed.set_image(url=None)
            await super(ImageView, self).send(file=file, **kwargs)
        finally:
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
    async def insert_image(self, ctx: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = ctx.response

        if "keep" in sct.values:
            self.text = ""
            await resp.edit_message(content="Keeping default image.", embeds=[], view=None)
        elif "remove" in sct.values:
            self.text = None
            await resp.edit_message(content="Removed default image.", embeds=[], view=None)
        else:
            sct.disabled = True
            await resp.edit_message(content="Alright, now send the URL or Attach an image.", embeds=[], view=self)

            done, _ = await asyncio.wait(
                [
                    asyncio.create_task(ctx.client.wait_for("message", check=check(ctx))),
                    asyncio.create_task(self.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if not isinstance(received := task.result(), Message):
                    continue

                if attachments := received.attachments:
                    self.text = attachments[0].proxy_url.split("?")[0]
                    self.received = received
                    await received.delete(delay=0)
                elif file := await ctx.client.get_file(url=received.content, filename="image"):
                    await received.delete(delay=0)
                    self.received = foo = await ctx.channel.send(file=file)
                    if attachments := self.received.attachments:
                        self.text = attachments[0].proxy_url.split("?")[0]
                    await foo.delete(delay=0)
                elif self.message.embeds and (image := self.message.embeds[0].image):
                    self.text = image.proxy_url
                else:
                    self.text = None

        await self.delete(ctx)
