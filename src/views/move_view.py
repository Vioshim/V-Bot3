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

from discord import Color, Embed, Interaction, InteractionResponse, Member
from discord.abc import Messageable
from discord.ui import Select, select

from src.pagination.complex import Complex
from src.structures.mon_typing import TypingEnum
from src.structures.move import Category, Move
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
        total = sorted(moves, key=lambda x: getattr(x, "name", str(x)))
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
            auto_conclude=False,
            auto_text_component=True,
            auto_choice_info=True,
        )
        self.real_max = self.max_values
        self.embed.title = "Select Moves"
        if choices:
            self.choices.update(choices)
        self.total = total
        self.data = {}
        self.menu_format()

    def generate_elements(self) -> list[tuple[Category | TypingEnum | str, set[Move]]]:
        moves: set[Move] = set(self.total) - self.choices
        moves1 = {x for x in moves if isinstance(x, Move)}
        items = []
        if moves2 := {x for x in moves if not isinstance(x, Move)}:
            items.append(("Abilities", moves2))
        items.extend(
            (k, set(v)) for k, v in groupby(sorted(moves1, key=lambda x: x.category.name), key=lambda x: x.category)
        )
        items.extend((k, set(v)) for k, v in groupby(sorted(moves1, key=lambda x: x.type.name), key=lambda x: x.type))
        items.sort(key=lambda x: len(x[1]), reverse=True)
        items = items[:25]
        self.select_types.max_values = len(items)
        return items

    def menu_format(self) -> None:
        self.select_types.options.clear()
        values = self.generate_elements()
        for k, items in values:
            label = getattr(k, "name", str(k)).title()
            self.data[label] = items
            emoji = getattr(k, "emoji", LIST_EMOJI)
            description = f"Has {len(items)} items."
            self.select_types.add_option(label=label, emoji=emoji, description=description)

        if not self.select_types.options:
            self.remove_item(self.select_types)
        elif self.select_types not in self.children:
            self.add_item(self.select_types)

        return super(MoveComplex, self).menu_format()

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        self.values = [x for x in self.values if x not in self.choices] or self.total
        self.max_values = min(self.real_max, len(self.values))
        return super().default_params(page)

    @select(placeholder="Filter by Typings / Category", custom_id="filter", max_values=2, min_values=0, row=3)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response
        if len(sct.values) == 0:
            self.values = self.total
            await self.edit(interaction=interaction, page=0)
        elif items := set.intersection(*[set(self.data.get(value, [])) for value in sct.values]):
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
            await response.send_message(embed=item.embed, ephemeral=True)
        await super(MoveView, self).select_choice(interaction=interaction, sct=sct)


class MovepoolMoveComplex(MoveComplex):
    def __init__(
        self,
        member: Member,
        movepool: Movepool,
        target: Optional[Messageable] = None,
        keep_working: bool = False,
        max_values: int = 6,
        choices: set[Move] = None,
    ):
        self.movepool = movepool
        super(MovepoolMoveComplex, self).__init__(
            member,
            movepool(),
            target,
            keep_working,
            max_values,
            choices,
        )

    def generate_elements(self) -> list[set[Move]]:
        items = super(MovepoolMoveComplex, self).generate_elements()
        movepool = self.movepool.without_moves(self.choices)
        data: dict[str, list[Move]] = movepool.to_dict(allow_empty=False, flatten_levels=True)
        items.extend((k, set(v)) for k, v in data.items())
        items.sort(key=lambda x: len(x[1]), reverse=True)
        items = items[:25]
        self.select_types.max_values = len(items)
        return items


class MovepoolView(MoveView, MovepoolMoveComplex):
    def __init__(
        self,
        member: Member,
        movepool: Movepool,
        target: Optional[Messageable] = None,
        keep_working: bool = True,
    ):
        self.movepool = movepool
        super(MovepoolMoveComplex, self).__init__(
            member=member,
            moves=movepool(),
            target=target,
            keep_working=keep_working,
            max_values=1,
        )
        self.modifying_embed = False
