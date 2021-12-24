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

from discord import ButtonStyle, Embed, Interaction, InteractionResponse, Member, User
from discord.abc import Messageable
from discord.ui import Button, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot

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
    async def send(self):
        try:
            await super(BooleanView, self).send()
            await self.wait()
            yield self.value
        except Exception as e:
            self.bot.logger.exception(
                "Exception occurred, target: %s, user: %s",
                str(self.target),
                str(self.member),
                exc_info=e,
            )
        finally:
            await self.delete()

    @button(label="Yes", row=0)
    async def confirm(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.send_message(content=f"{self.embed.title}\nAnswer: Yes", ephemeral=True)
        self.value = True
        self.stop()

    @button(label="No", row=0)
    async def deny(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.send_message(content=f"{self.embed.title}\nAnswer: No", ephemeral=True)
        self.value = False
        self.stop()

    @button(label="Cancel Process", style=ButtonStyle.red, row=0)
    async def cancel(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.send_message(content="Process has been cancelled", ephemeral=True)
        self.value = None
        self.stop()
