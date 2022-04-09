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

from contextlib import asynccontextmanager, suppress
from logging import getLogger, setLoggerClass
from typing import Optional, TypeVar, Union

from discord import (
    ButtonStyle,
    DiscordException,
    File,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    User,
)
from discord.abc import Messageable
from discord.ui import Button, button

from src.pagination.view_base import Basic
from src.structures.logger import ColoredLogger
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
    def __init__(
        self,
        member: Union[Member, User],
        target: _M,
        default_img: File | str = None,
    ):
        super(ImageView, self).__init__(
            member=member,
            target=target,
        )
        if isinstance(default_img, str):
            self.embed.set_image(url=default_img)
        elif isinstance(default_img, File):
            self.embed.set_image(url=f"attachment://{default_img.filename}")
        self.embed.title = "Image"
        self.received: Optional[Message] = None
        self.text: Optional[str] = default_img
        self.default_image.disabled = not default_img

    @asynccontextmanager
    async def send(self):
        file: Optional[file] = None
        if isinstance(self.text, File):
            file = self.text
        try:
            await super(ImageView, self).send(file=file)
        except HTTPException:
            self.embed.set_image(url=None)
            self.default_image.disabled = True
            await super(ImageView, self).send(file=file)
        except Exception as e:
            logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
        finally:
            self.text = self.message.embeds[0].image.url
            await self.wait()
            await self.delete()
            yield self.text

    @button(label="I'll send an Image", row=0)
    async def insert_image(self, ctx: Interaction, btn: Button):
        btn.disabled = True
        resp: InteractionResponse = ctx.response
        if message := self.message:
            await message.edit(view=None)
        elif isinstance(target := self.target, Interaction):
            await target.response.edit_message(view=None)
        await resp.send_message(
            content="Alright, now send the URL or Attach an image.",
            ephemeral=True,
        )
        received: Message = await ctx.client.wait_for("message", check=check(ctx))
        if attachments := received.attachments:
            self.text = attachments[0].proxy_url
            self.received = received
            with suppress(DiscordException):
                await received.delete()
        elif file := await ctx.client.get_file(
            url=received.content,
            filename="image",
        ):
            with suppress(DiscordException):
                await received.delete()
            self.received = foo = await ctx.channel.send(file=file)
            self.text = self.received.attachments[0].proxy_url
            with suppress(DiscordException):
                await foo.delete()
        elif image := self.message.embeds[0].image:
            self.text = image.url
        else:
            self.text = None
        self.stop()

    @button(label="I like the image", row=0)
    async def default_image(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        if message := self.message:
            await message.edit(view=None)
        elif isinstance(target := self.target, Interaction):
            await target.response.edit_message(view=None)

        await resp.send_message(
            content="Keeping default image.",
            ephemeral=True,
        )
        self.stop()

    @button(label="Cancel Submission", style=ButtonStyle.red, row=0)
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        if message := self.message:
            await message.edit(view=None)
        elif isinstance(target := self.target, Interaction):
            await target.response.edit_message(view=None)
        await resp.send_message(
            content="Submission has been concluded.",
            ephemeral=True,
        )
        self.text = None
        self.stop()
