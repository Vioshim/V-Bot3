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

from asyncio import Future, get_running_loop
from contextlib import asynccontextmanager
from typing import Optional, TypeVar, Union

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    User,
)
from discord.abc import Messageable
from discord.ui import Button, InputText, Modal, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot
from src.utils.functions import text_check

__all__ = ("ModernInput", "TextModal")

_M = TypeVar("_M", bound=Messageable)
DEFAULT_MSG = "Alright, now write down the information."


class ModernInput(Basic):
    def __init__(
        self,
        *,
        bot: CustomBot,
        input_text: InputText = None,
        member: Union[Member, User],
        target: _M = None,
        timeout: Optional[float] = None,
        embed: Embed = None,
    ):
        super(ModernInput, self).__init__(
            bot=bot,
            member=member,
            target=target,
            timeout=timeout,
            embed=embed,
        )
        self.text: Optional[str] = None
        self.input_text = input_text
        if input_text:
            self.embed.title = input_text.label or self.embed.title
            self.embed.description = (
                input_text.value
                or input_text.placeholder
                or self.embed.description
            )
            self.empty.disabled = input_text.required
        else:
            self.remove_item(self.confirm2)

    @asynccontextmanager
    async def handle(self, **kwargs):
        data = dict(
            bot=self.bot,
            member=kwargs.pop("member", self.member),
            target=kwargs.pop("target", self.target),
        )
        origin = kwargs.pop("origin", None)
        if placeholder := kwargs.get("placeholder"):
            kwargs["placeholder"] = placeholder[:100]
        data["input_text"] = InputText(**kwargs)
        aux = ModernInput(**data)
        try:
            if origin:
                if isinstance(origin, Interaction):
                    origin = await origin.original_message()
                await origin.edit(
                    content=None,
                    embed=aux.embed,
                    view=aux,
                )
                await aux.wait()
                await origin.edit(
                    content="Process concluded with success.",
                    embed=None,
                    view=None,
                )
            else:
                await aux.send()
                await aux.wait()
            yield aux.text
        except Exception as e:
            self.bot.logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
            yield None
        finally:
            await aux.delete()

    @button(
        label="Proceed with Message",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def confirm(
        self,
        _: Button,
        interaction: Interaction,
    ):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(
            content=DEFAULT_MSG,
            view=None,
        )
        try:
            message: Message = await self.bot.wait_for(
                "message", check=text_check(interaction)
            )
            self.text = message.content
            await message.delete()
            msg = await interaction.original_message()
            await msg.edit(
                content="Parameter has been added.",
                view=None,
                embed=None,
            )
        except DiscordException as e:
            self.bot.logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()

    @button(
        label="Proceed with Modal",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def confirm2(
        self,
        _: Button,
        interaction: Interaction,
    ):
        resp: InteractionResponse = interaction.response
        modal = TextModal(self.input_text)
        await resp.send_modal(modal=modal)
        await modal.wait()
        self.text = modal.text

    @button(
        label="Cancel the Process",
        style=ButtonStyle.red,
        row=0,
    )
    async def cancel(
        self,
        _: Button,
        interaction: Interaction,
    ):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(
            content="Process Concluded",
            view=None,
            embed=None,
        )
        self.text = None
        self.stop()

    @button(
        label="Continue without Message",
        row=0,
    )
    async def empty(
        self,
        _: Button,
        interaction: Interaction,
    ):
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
            self.bot.logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()


class TextModal(Modal):
    def __init__(self, item: InputText) -> None:
        super(TextModal, self).__init__(title=DEFAULT_MSG)
        self.text: Optional[str] = None
        self.add_item(item)
        loop = get_running_loop()
        self._stopped: Future[bool] = loop.create_future()

    async def callback(self, interaction: Interaction) -> None:
        """Runs whenever the modal is closed."""
        self.text = self.children[0].value or ""
        # Stop the modal.
        self.stop()
        # Respond to the interaction.
        await interaction.response.send_message(
            "Parameter has been added.", ephemeral=True
        )

    def stop(self) -> None:
        """Stops listening to interaction events from the modal."""
        if not self._stopped.done():
            self._stopped.set_result(True)

    async def wait(self) -> bool:
        """Waits for the modal to be closed."""
        return await self._stopped
