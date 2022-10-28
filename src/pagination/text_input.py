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


import asyncio
from contextlib import asynccontextmanager
from logging import getLogger, setLoggerClass
from typing import Optional, TypeVar, Union

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    PartialEmoji,
    User,
)
from discord.abc import Messageable
from discord.ui import Button, Modal, TextInput, button

from src.pagination.view_base import Basic
from src.structures.logger import ColoredLogger
from src.utils.functions import text_check

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

__all__ = ("ModernInput", "TextModal")

_M = TypeVar("_M", bound=Messageable)
DEFAULT_MSG = "Alright, now write down the information."


class ModernInput(Basic):
    def __init__(
        self,
        *,
        input_text: TextInput = None,
        member: Union[Member, User],
        target: _M = None,
        timeout: Optional[float] = None,
        embed: Optional[Embed] = None,
    ):
        super(ModernInput, self).__init__(member=member, target=target, timeout=timeout, embed=embed)
        self.text: Optional[str] = None
        self.input_text = input_text
        if input_text:
            self.embed.title = input_text.label or self.embed.title
            self.embed.description = (input_text.value or input_text.placeholder or self.embed.description or "")[:4096]
            self.empty.disabled = input_text.required
        else:
            self.remove_item(self.confirm2)

    @asynccontextmanager
    async def handle(self, **kwargs):
        data = dict(member=kwargs.pop("member", self.member), target=kwargs.pop("target", self.target))
        origin = kwargs.pop("origin", None)
        ephemeral = kwargs.pop("ephemeral", False)
        if placeholder := kwargs.get("placeholder"):
            kwargs["placeholder"] = placeholder[:100]
        data["input_text"] = input_text = TextInput(**kwargs)
        aux = ModernInput(**data)
        embed = aux.embed
        embed.description = input_text.value or placeholder or self.embed.description
        try:
            if origin:
                if isinstance(origin, Interaction):
                    origin = await origin.edit_original_response(content=None, embed=embed, view=aux)
                elif isinstance(origin, Message):
                    origin = await origin.edit(content=None, embed=embed, view=aux)
                if not aux.is_finished():
                    await aux.wait()
                await origin.edit(content="Process concluded with success.", embed=None, view=None)
            else:
                await aux.send(ephemeral=ephemeral)
                if not aux.is_finished():
                    await aux.wait()
            yield aux.text
        except Exception as e:
            logger.exception("Exception occurred, target: %s, user: %s", str(self.target), str(self.member), exc_info=e)
            yield None
        finally:
            await aux.delete()

    @button(
        emoji=PartialEmoji(name="ChannelThread", id=816771501596344341),
        label="Message",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def confirm(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(content=DEFAULT_MSG, view=None)

        done, pending = await asyncio.wait(
            [
                interaction.client.wait_for(
                    "message",
                    check=text_check(interaction),
                ),
                self.wait(),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()

        for task in done:
            if isinstance(message := task.result(), Message):
                self.text = message.content
                await message.delete(delay=0)

        await self.delete(interaction)

    @button(
        emoji=PartialEmoji(name="StatusRichPresence", id=842328614883295232),
        label="Modal",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def confirm2(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        modal = TextModal(self.input_text)
        await resp.send_modal(modal)
        await modal.wait()
        self.text = modal.text
        self.stop()

    @button(
        emoji=PartialEmoji(name="blank", id=993894870328557639),
        label="Empty",
        row=0,
    )
    async def empty(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        self.text = ""
        try:
            await resp.edit_message(
                content="Default Value has been chosen",
                view=None,
            )
            if message := self.message:
                await message.delete(delay=1)
        except DiscordException as e:
            logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()

    @button(label="Cancel the Process", style=ButtonStyle.red, row=0)
    async def cancel(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(
            content="Process Concluded",
            view=None,
            embed=None,
        )
        self.text = None
        self.stop()


class TextModal(Modal):
    def __init__(self, item: TextInput) -> None:
        super(TextModal, self).__init__(title=DEFAULT_MSG)
        self.text: Optional[str] = None
        self.item = item
        self.add_item(item)

    async def on_submit(self, interaction: Interaction) -> None:
        """Runs whenever the modal is closed."""
        resp: InteractionResponse = interaction.response
        self.text = self.item.value or ""
        await resp.send_message("Parameter has been added.", ephemeral=True)
        self.stop()
