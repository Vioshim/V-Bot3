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
from typing import Optional

from discord import DiscordException, Interaction, InteractionResponse, Member
from discord.abc import Messageable
from discord.ui import Button, Select, View, select

from src.pagination.complex import Complex
from src.structures.mon_typing import Typing
from src.structures.move import Category, Move

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
        total = sorted(moves, key=lambda x: x.type.id or 0)
        super(MoveComplex, self).__init__(
            member=member,
            target=target,
            values=moves,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            max_values=min(max_values, len(total)),
            silent_mode=True,
        )
        self.real_max = self.max_values
        self.embed.title = "Select Moves"
        self.total = total
        self.data = {}

    def menu_format(self) -> None:

        self.select_types.options.clear()
        self.select_types.add_option(label="No Type Filter", description=f"Has {len(self.total)} moves.")

        moves: set[Move] = set(self.total) - self.choices

        data = {k: set(v) for k, v in groupby(sorted(moves, key=lambda x: x.category.name), key=lambda x: x.category)}
        data.update({k: set(v) for k, v in groupby(sorted(moves, key=lambda x: x.type.id or 0), key=lambda x: x.type)})
        data: dict[Typing | Category, set[Move]] = dict(sorted(data.items(), key=lambda x: len(x[1]), reverse=True))

        for k, items in data.items():
            label = k.name.title()
            self.data[label] = items
            self.select_types.add_option(
                label=label,
                emoji=k.emoji,
                description=f"Has {len(items)} moves.",
            )

        return super(MoveComplex, self).menu_format()

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        resp: InteractionResponse = interaction.response
        if self.keep_working or len(self.choices) < self.real_max:
            data = dict(embed=self.embed)

            self.values = [x for x in self.values if x not in self.choices] or self.total
            self.max_values = min(self.real_max, len(self.values))
            self.embed.description = "\n".join(f"> {x!r}" for x in self.choices) or "No Moves"

            if isinstance(page, int):
                self.pos = page
                self.menu_format()
                data["view"] = self

            if not resp.is_done():
                return await resp.edit_message(**data)
            try:
                if message := self.message or interaction.message:
                    await message.edit(**data)
                else:
                    self.message = await interaction.edit_original_message(**data)
            except DiscordException as e:
                interaction.client.logger.exception("View Error", exc_info=e)
                self.stop()
        else:
            if not resp.is_done():
                await resp.pong()
            await self.delete()

    @select(placeholder="Filter by Typings / Category", custom_id="filter", max_values=2)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        self.values = set.intersection(*[self.data[value] for value in sct.values])
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
