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
from discord.ui import Button, Select, View, select

from src.pagination.complex import Complex
from src.structures.move import Move

__all__ = ("MoveView",)


class MoveView(Complex):
    def __init__(
        self,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        moves: set[Move],
        keep_working: bool = False,
    ):
        super(MoveView, self).__init__(
            member=member,
            target=target,
            values=moves,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
        )
        self.embed.title = "Select a Move"

    @select(
        row=1,
        placeholder="Select the elements",
        custom_id="selector",
    )
    async def select_choice(
        self,
        interaction: Interaction,
        _: Select,
    ) -> None:
        response: InteractionResponse = interaction.response
        item: Move = self.current_choice
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

    @property
    def choice(self) -> Optional[Move]:
        """Method Override

        Returns
        -------
        set[Move]
            Desired Moves
        """
        return super(MoveView, self).choice
