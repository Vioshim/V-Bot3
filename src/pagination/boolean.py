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

from contextlib import asynccontextmanager
from typing import Optional, TypeVar, Union

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    User,
)
from discord.abc import Messageable
from discord.ui import Button, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot
from src.utils.functions import embed_modifier

__all__ = ("BooleanView",)

_M = TypeVar("_M", bound=Messageable)


class BooleanView(Basic):
    def __init__(
        self,
        *,
        bot: CustomBot,
        member: Union[Member, User],
        target: _M = None,
        timeout: Optional[float] = None,
        embed: Embed = None,
    ):
        super(BooleanView, self).__init__(
            bot=bot,
            member=member,
            target=target,
            timeout=timeout,
            embed=embed,
        )
        self.value: Optional[bool] = None

    @asynccontextmanager
    async def handle(self, **kwargs):
        data = dict(
            bot=self.bot,
            member=kwargs.get("member", self.member),
            target=kwargs.get("target", self.target),
            embed=kwargs.get("embed", self.embed),
            timeout=kwargs.get("timeout", self.timeout),
        )

        data["embed"] = embed_modifier(data["embed"], **kwargs)

        aux = BooleanView(**data)
        try:
            if origin := kwargs.get("origin"):
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
            yield aux.value
        except Exception as e:
            self.bot.logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
        finally:
            await aux.delete()

    @button(
        label="Yes",
        row=0,
    )
    async def confirm(
        self,
        interaction: Interaction,
        _: Button,
    ):
        resp: InteractionResponse = interaction.response
        try:
            self.value = True
            await resp.edit_message(
                content=f"{self.embed.title}\nAnswer: Yes",
                view=None,
            )
            await self.message.delete(delay=1)
        except DiscordException as e:
            self.bot.logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()

    @button(
        label="No",
        row=0,
    )
    async def deny(
        self,
        interaction: Interaction,
        _: Button,
    ):
        resp: InteractionResponse = interaction.response
        try:
            self.value = False
            await resp.edit_message(
                content=f"{self.embed.title}\nAnswer: No",
                view=None,
            )
            await self.message.delete(delay=1)
        except DiscordException as e:
            self.bot.logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()

    @button(
        label="Cancel Process",
        style=ButtonStyle.red,
        row=0,
    )
    async def cancel(
        self,
        interaction: Interaction,
        _: Button,
    ):
        resp: InteractionResponse = interaction.response
        try:
            self.value = None
            await resp.edit_message(
                content="Process has been cancelled",
                view=None,
            )
            await self.message.delete(delay=1)
        except DiscordException as e:
            self.bot.logger.exception(
                "Error deleting message",
                exc_info=e,
            )
        finally:
            self.stop()
