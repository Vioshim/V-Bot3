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
    Color,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
)
from discord.abc import Messageable
from discord.ui import Button, Select, TextInput, View, button, select

from src.pagination.complex import Complex, DefaultModal
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.utils.etc import LIST_EMOJI, WHITE_BAR

__all__ = ("MoveView", "MoveComplex")


class MoveComplex(Complex[Move]):
    def __init__(
        self,
        member: Member,
        moves: set[Move],
        target: Optional[Messageable] = None,
        keep_working: bool = False,
        max_values: int = 6,
        choices: set[Move] = None,
    ):
        total = sorted(
            moves,
            key=lambda x: x.type.name if isinstance(x, Move) else getattr(x, "name", str(x)),
        )
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
        self.modifying_embed = True
        self.real_max = self.max_values
        self.embed.title = "Select Moves"
        if choices:
            self.choices.update(choices)
        self.embed.description = "\n".join(f"> {x!r}" for x in self.choices)
        self.total = total
        self.data = {}
        self.menu_format()

    def generate_elements(self):
        moves: set[Move] = set(self.total) - self.choices
        moves1 = {x for x in moves if isinstance(x, Move)}
        items = []
        if moves2 := {x for x in moves if not isinstance(x, Move)}:
            items.append(("Abilities", moves2))
        if moves_cat := [
            (k, list(v)) for k, v in groupby(sorted(moves1, key=lambda x: x.category.name), key=lambda x: x.category)
        ]:
            items.append(moves_cat)
        if moves_type := [
            (k, list(v)) for k, v in groupby(sorted(moves1, key=lambda x: x.type.name), key=lambda x: x.type)
        ]:
            items.append(moves_type)
        return items

    def menu_format(self) -> None:
        self.select_types.options.clear()
        elements = self.generate_elements()
        values = [(k, o) for element in elements for k, v in element if (o := set(v))]
        values.sort(key=lambda x: len(x[1]), reverse=True)

        for k, items in values:
            label = getattr(k, "name", str(k)).title()
            self.data[label] = items
            self.select_types.add_option(
                label=label,
                emoji=getattr(k, "emoji", LIST_EMOJI),
                description=f"Has {len(items)} items.",
            )

        if not self.choices:
            self.remove_item(self.move_remove)
        elif self.move_remove not in self.children:
            self.add_item(self.move_remove)
        elif not self.select_types.options:
            self.remove_item(self.select_types)
        elif self.select_types not in self.children:
            self.add_item(self.select_types)

        return super().menu_format()

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

    @select(placeholder="Filter by Typings / Category", custom_id="filter", max_values=2, min_values=0, row=3)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response
        if len(sct.values) == 0:
            self.values = self.total
            await self.edit(interaction=interaction, page=0)
        elif items := set.intersection(*[self.data[value] for value in sct.values]):
            self.values = items
            await self.edit(interaction=interaction, page=0)
        else:
            embed = Embed(
                title="No entries with",
                description="\n".join(f"• {x}" for x in sct.values),
                color=Color.blurple(),
                timestamp=interaction.created_at,
            )
            embed.set_image(url=WHITE_BAR)
            await resp.send_message(embed=embed, ephemeral=True)

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

    @button(
        label="Remove Moves",
        emoji=PartialEmoji(name="channeldelete", id=432986579674333215),
        custom_id="remover",
        style=ButtonStyle.blurple,
        disabled=False,
        row=4,
    )
    async def move_remove(self, interaction: Interaction, _: Button):
        view = MoveComplex(member=self.member, moves=self.choices, target=interaction)
        view.remove_item(view.move_remove)
        async with view.send(
            title="Remove Moves",
            description="\n".join(f"> {x!r}" for x in self.choices),
            editing_original=True,
        ) as choices:
            self.choices -= choices
        await self.edit(interaction, page=0)


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


class MovepoolMoveComplex(MoveComplex):
    def __init__(
        self,
        member: Member,
        movepool: Movepool,
        target: Optional[Messageable] = None,
        keep_working: bool = True,
        max_values: int = 6,
        choices: set[Move] = None,
    ):
        super(MovepoolMoveComplex, self).__init__(member, movepool(), target, keep_working, max_values, choices)
        self.movepool = movepool

    def generate_elements(self) -> list[list[Move]]:
        data: dict[str, list[Move]] = self.movepool.to_dict(allow_empty=False, flatten_levels=True)
        moves = {x for x in (set(self.total) - self.choices) if isinstance(x, Move)}

        items1 = [*data.items()]
        items2 = [(k, list(v)) for k, v in groupby(sorted(moves, key=lambda x: x.type.name), key=lambda x: x.type)]
        items3 = [
            (k, list(v)) for k, v in groupby(sorted(moves, key=lambda x: x.category.name), key=lambda x: x.category)
        ]
        items = [items1, items2]

        if len(items1) + len(items2) <= 25 - len(items3):
            items.append(items3)

        self.select_types.max_values = len(items)

        return items


class MovepoolView(MovepoolMoveComplex, MoveView):
    def __init__(
        self,
        member: Member,
        movepool: Movepool,
        target: Optional[Messageable] = None,
        keep_working: bool = True,
    ):
        super(MovepoolMoveComplex, self).__init__(
            member=member,
            moves=movepool(),
            target=target,
            keep_working=keep_working,
        )
        self.movepool = movepool
