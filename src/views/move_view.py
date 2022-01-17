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

from typing import Optional, Union

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Webhook,
)
from discord.ui import Button, Select, View

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.move import Move

__all__ = ("MoveView",)


class MoveView(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        moves: set[Move],
        keep_working: bool = False,
    ):
        super(MoveView, self).__init__(
            bot=bot,
            member=member,
            target=target,
            values=moves,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
        )
        self.embed.title = "Select a Move"

    async def custom_choice(self, sct: Select, ctx: Interaction):
        response: InteractionResponse = ctx.response
        for index in sct.values:
            try:
                amount = self.entries_per_page * self._pos
                chunk = self.values[amount : amount + self.entries_per_page]
                item: Move = chunk[int(index)]
                embed = item.embed
                view = View()
                view.add_item(
                    Button(
                        label="Click here to check more information at Bulbapedia.",
                        url=item.url,
                    )
                )
                await response.send_message(
                    embed=embed,
                    view=view,
                    ephemeral=True,
                )
            except IndexError:
                pass
            except Exception as e:
                self.bot.logger.exception(
                    "Chunk: %s",
                    str(chunk),
                    exc_info=e,
                )

    @property
    def choice(self) -> Optional[Move]:
        """Method Override

        Returns
        -------
        set[Move]
            Desired Moves
        """
        if value := super(MoveView, self).choice:
            return value
