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
from typing import Optional, TypeVar, Union

from discord import (
    ButtonStyle,
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
from src.structures.bot import CustomBot
from src.utils.matches import REGEX_URL

_M = TypeVar("_M", bound=Messageable)


def check(ctx: Interaction):
    def inner(message: Message):
        if ctx.user == message.author and ctx.channel == message.channel:
            if REGEX_URL.match(message.content or ""):
                return True
            return bool(message.attachments)
        return False

    return inner


class ImageView(Basic):
    def __init__(
        self,
        bot: CustomBot,
        member: Union[Member, User],
        target: _M,
        default_img: str = None,
    ):
        super(ImageView, self).__init__(
            bot=bot,
            member=member,
            target=target,
        )
        self.embed.set_image(url=default_img)
        self.received: Optional[Message] = None
        self.text: Optional[str] = default_img
        self.default_image.disabled = not default_img

    @asynccontextmanager
    async def send(self):
        try:
            try:
                await super(ImageView, self).send()
            except HTTPException:
                self.embed.remove_image()
                self.default_image.disabled = True
                await super(ImageView, self).send()
            finally:
                await self.wait()
                yield self.text
        except Exception as e:
            self.bot.logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
        finally:
            await self.delete()

    @button(label="I'll send an Image", row=0)
    async def insert_image(self, btn: Button, ctx: Interaction):
        btn.disabled = True
        resp: InteractionResponse = ctx.response
        if isinstance(target := self.target, Interaction):
            await target.edit_original_message(view=None)
        else:
            await self.message.edit(view=None)
        await resp.send_message(
            content="Alright, now send the URL or Attach an image.",
            ephemeral=True,
        )
        received: Message = await self.bot.wait_for("message", check=check(ctx))
        if attachments := received.attachments:
            self.text = attachments[0].url
            self.received = received
        elif file := await self.bot.get_file(
            url=received.content,
            filename="image",
        ):
            self.received = await ctx.channel.send(file=file)
            self.text = self.received.attachments[0].url
            await received.delete()
        else:
            self.text = None
        self.stop()

    @button(label="I like the default one", row=0)
    async def default_image(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        if isinstance(target := self.target, Interaction):
            await target.edit_original_message(view=None)
        else:
            await self.message.edit(view=None)
        await resp.send_message(
            content="Keeping default image.",
            ephemeral=True,
        )
        self.stop()

    @button(label="Cancel Submission", style=ButtonStyle.red, row=0)
    async def cancel(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        if isinstance(target := self.target, Interaction):
            await target.edit_original_message(view=None)
        else:
            await self.message.edit(view=None)
        await resp.send_message(
            content="Submission has been concluded.",
            ephemeral=True,
        )
        self.text = None
        self.stop()
