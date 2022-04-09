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

from random import sample
from typing import Optional, Union

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    TextStyle,
    Webhook,
)
from discord.ui import Select, TextInput, select

from src.pagination.complex import Complex
from src.structures.ability import Ability, SpAbility

__all__ = ("AbilityView",)


def ability_emoji_parser(x: Ability | SpAbility) -> Optional[str]:
    if isinstance(x, Ability):
        return "\N{LARGE BLUE CIRCLE}"
    if isinstance(SpAbility):
        return "\N{LARGE GREEN CIRCLE}"


class AbilityView(Complex):
    def __init__(
        self,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        abilities: set[Ability | SpAbility],
        keep_working: bool = False,
        max_values: int = 1,
    ):
        placeholder = ", ".join(["Ability"] * max_values)
        super(AbilityView, self).__init__(
            member=member,
            target=target,
            values=abilities,
            timeout=None,
            parser=lambda x: (x.name, x.description),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            emoji_parser=ability_emoji_parser,
            max_values=max_values,
            text_component=TextInput(
                label="Ability",
                style=TextStyle.paragraph,
                placeholder=placeholder,
                default=", ".join(x.name for x in sample(abilities, 2)),
            ),
        )
        self.embed.title = "Select an Ability"

    @select(
        row=1,
        placeholder="Select the elements",
        custom_id="selector",
    )
    async def select_choice(
        self,
        interaction: Interaction,
        sct: Select,
    ) -> None:
        response: InteractionResponse = interaction.response
        item: Ability | SpAbility = self.current_choice
        await response.send_message(embed=item.embed, ephemeral=True)
        await super(AbilityView, self).select_choice(interaction, sct)
