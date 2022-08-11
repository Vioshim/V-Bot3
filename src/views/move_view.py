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

from itertools import groupby
from typing import Any, Optional

from discord import (
    ButtonStyle,
    DiscordException,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
)
from discord.abc import Messageable
from discord.ui import Button, Select, TextInput, View, button, select

from src.pagination.complex import Complex, DefaultModal
from src.structures.move import Move
from src.utils.etc import LIST_EMOJI

__all__ = ("MoveView", "MoveComplex")


class MoveComplex(Complex[Move]):
    def __init__(
        self,
        member: Member,
        moves: set[Move],
        target: Optional[Messageable] = None,
        keep_working: bool = False,
        max_values: int = 6,
    ):
        total = sorted(moves, key=lambda x: (x.type.id or 0) if isinstance(x, Move) else 0)
        max_values = min(max_values, len(total))
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
            text_component=TextInput(
                label="Moves",
                placeholder=("Move, " * max_values).removesuffix(", "),
                required=False,
            ),
        )
        self.real_max = self.max_values
        self.embed.title = "Select Moves"
        self.total = total
        self.data = {}

    def menu_format(self) -> None:

        self.select_types.options.clear()

        moves: set[Move] = set(self.total) - self.choices

        moves1 = {x for x in moves if isinstance(x, Move)}
        moves2 = {x for x in moves if not isinstance(x, Move)}

        elements = (
            groupby(
                sorted(moves1, key=lambda x: x.category.name),
                key=lambda x: x.category,
            ),
            groupby(
                sorted(moves1, key=lambda x: x.type.id or 0),
                key=lambda x: x.type,
            ),
        )

        data = {"None": moves1, "Abilities": moves2}

        for items in elements:
            data.update({k: set(v) for k, v in items})

        for k, items in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
            if items:
                label = getattr(k, "name", k).title()
                self.data[label] = items
                self.select_types.add_option(
                    label=label,
                    emoji=getattr(k, "emoji", LIST_EMOJI),
                    description=f"Has {len(items)} items.",
                )

        return super(MoveComplex, self).menu_format()

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        data = dict(embed=self.embed)

        self.values = [x for x in self.values if x not in self.choices] or self.total
        self.max_values = min(self.real_max, len(self.values))
        self.embed.description = "\n".join(f"> {x!r}" for x in self.choices)

        if isinstance(page, int):
            self.pos = page
            self.menu_format()
            data["view"] = self

        return data

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        if self.keep_working or len(self.choices) < self.real_max:
            resp: InteractionResponse = interaction.response
            data = self.default_params(page=page)
            try:
                if resp.is_done():
                    self.message = await interaction.edit_original_response(**data)
                else:
                    await resp.edit_message(**data)
            except DiscordException as e:
                interaction.client.logger.exception("View Error", exc_info=e)
                self.stop()
        else:
            await self.delete(interaction)

    @select(placeholder="Filter by Typings / Category", custom_id="filter", max_values=2, row=3)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        self.values = set.intersection(*[self.data[value] for value in sct.values])
        await self.edit(interaction=interaction, page=0)

    @button(
        label="Write down the choice instead.",
        emoji=PartialEmoji(name="channelcreate", id=432986578781077514),
        custom_id="writer",
        style=ButtonStyle.blurple,
        disabled=False,
        row=4,
    )
    async def message_handler(self, interaction: Interaction, _: Button):
        response: InteractionResponse = interaction.response
        component = self.text_component
        if isinstance(component, TextInput):
            component = DefaultModal(view=self)
        await response.send_modal(component)
        await component.wait()


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

    @select(row=1, placeholder="Select the moves", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        response: InteractionResponse = interaction.response
        if item := self.current_choice:
            embed = item.embed
            view = View()
            if url := getattr(item, "url", None):
                view.add_item(Button(label="Click here to check more information at Bulbapedia.", url=url))
            await response.send_message(embed=embed, view=view, ephemeral=True)
        await super(MoveView, self).select_choice(interaction=interaction, sct=sct)
