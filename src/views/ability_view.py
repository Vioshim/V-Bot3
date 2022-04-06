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
from discord.ui import Select

from src.pagination.complex import Complex
from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot

__all__ = ("AbilityView",)


def ability_emoji_parser(x: Ability | SpAbility) -> Optional[str]:
    if isinstance(x, Ability):
        return "\N{LARGE BLUE CIRCLE}"
    if isinstance(SpAbility):
        return "\N{LARGE GREEN CIRCLE}"


class AbilityView(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        abilities: set[Ability | SpAbility],
        keep_working: bool = False,
    ):
        super(AbilityView, self).__init__(
            bot=bot,
            member=member,
            target=target,
            values=abilities,
            timeout=None,
            parser=lambda x: (x.name, x.description),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            emoji_parser=ability_emoji_parser,
        )
        self.embed.title = "Select an Ability"

    async def custom_choice(self, ctx: Interaction, sct: Select):
        response: InteractionResponse = ctx.response
        for index in sct.values:
            try:
                amount = self.entries_per_page * self._pos
                chunk = self.values[amount : amount + self.entries_per_page]
                item: Ability | SpAbility = chunk[int(index)]
                embed = item.embed
                await response.send_message(
                    embed=embed,
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
    def choice(self) -> Optional[Ability | SpAbility]:
        """Method Override

        Returns
        -------
        set[Move]
            Desired Moves
        """
        if value := super(AbilityView, self).choice:
            return value
