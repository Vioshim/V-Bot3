# Copyright 2021 Vioshim
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
from discord.ui import Button, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot
from src.utils.functions import embed_modifier, text_check

__all__ = ("TextInput",)

_M = TypeVar("_M", bound=Messageable)


class TextInput(Basic):
    def __init__(
        self,
        *,
        bot: CustomBot,
        member: Union[Member, User],
        target: _M = None,
        timeout: Optional[float] = None,
        embed: Embed = None,
        required: bool = False,
    ):
        super(TextInput, self).__init__(
            bot=bot,
            member=member,
            target=target,
            timeout=timeout,
            embed=embed,
        )
        self.text: Optional[str] = None
        self.aux: Optional[TextInput] = None
        self.empty.disabled = required

    @asynccontextmanager
    async def handle(self, **kwargs):
        data = dict(
            bot=self.bot,
            member=kwargs.get("member", self.member),
            target=kwargs.get("target", self.target),
            embed=kwargs.get("embed", self.embed),
            required=kwargs.get("required", self.empty.disabled),
        )

        data["embed"] = embed_modifier(data["embed"], **kwargs)

        aux = TextInput(**data)
        try:
            if origin := kwargs.get("origin"):
                await origin.edit(view=aux)
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
        finally:
            await aux.delete()

    @button(label="Proceed with Message", style=ButtonStyle.green, row=0)
    async def confirm(self, btn: Button, interaction: Interaction):
        btn.disabled = True
        await interaction.message.edit(view=self)
        resp: InteractionResponse = interaction.response
        try:
            await resp.send_message(
                content="Alright, now write down the information.",
                ephemeral=True,
            )
            message: Message = await self.bot.wait_for(
                "message", check=text_check(interaction)
            )
            self.text = message.content
            await message.delete()
        except DiscordException as e:
            self.bot.logger.exception("Error deleting message", exc_info=e)
        finally:
            self.stop()

    @button(label="Cancel the Process", style=ButtonStyle.red, row=0)
    async def cancel(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.send_message(content="Process Concluded", ephemeral=True)
        self.text = None
        self.stop()

    @button(label="Continue without Message", row=0)
    async def empty(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        self.text = ""
        await resp.send_message(
            content="Default Value has been chosen", ephemeral=True
        )
        try:
            await self.message.delete(delay=1)
        except DiscordException as e:
            self.bot.logger.exception("Error deleting message", exc_info=e)
        finally:
            self.stop()
