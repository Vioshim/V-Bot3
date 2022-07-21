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

from typing import Optional

from discord import Interaction, InteractionResponse, Member, SelectOption
from discord.abc import Messageable
from discord.ui import Button, Select, View, select

from src.pagination.complex import Complex
from src.structures.mon_typing import Typing
from src.structures.move import Move

__all__ = ("MoveView", "MoveComplex")

SELECT_TYPINGS = [SelectOption(label="Remove Filter")]
SELECT_TYPINGS.extend(SelectOption(label=x.name, value=str(x), emoji=x.emoji) for x in Typing.all())


class MoveComplex(Complex[Move]):
    def __init__(
        self,
        member: Member,
        moves: set[Move],
        target: Optional[Messageable] = None,
        keep_working: bool = False,
        max_values: int = 6,
    ):
        super(MoveComplex, self).__init__(
            member=member,
            target=target,
            values=moves,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            max_values=max_values,
            silent_mode=True,
        )
        self.moves_total = list(moves)
        self.embed.title = "Select Moves"

    @select(
        placeholder="Filter by Typings",
        custom_id="filter",
        options=SELECT_TYPINGS,
        max_values=1,
    )
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        total = self.moves_total
        mon_type = Typing.from_ID(sct.values[0])
        total = [x for x in total if x.type == mon_type]
        self.values = total
        await self.edit(interaction=interaction, page=0)


class MoveView(MoveComplex):
    def __init__(
        self,
        member: Member,
        moves: set[Move],
        target: Optional[Messageable] = None,
        keep_working: bool = False,
    ):
        super(MoveView, self).__init__(
            member=member,
            moves=moves,
            target=target,
            keep_working=keep_working,
            max_values=1,
        )
        self.embed.title = "Select a Move"

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        response: InteractionResponse = interaction.response
        if item := self.current_choice:
            embed = item.embed
            view = View()
            if url := getattr(item, "url", None):
                view.add_item(Button(label="Click here to check more information at Bulbapedia.", url=url))
            await response.send_message(embed=embed, view=view, ephemeral=True)
        await super(MoveView, self).select_choice(interaction=interaction, sct=sct)
