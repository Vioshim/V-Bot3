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

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    TextStyle,
    User,
)
from discord.ui import Button, Modal, Select, TextInput, button, select

from src.pagination.complex import Complex
from src.pagination.view_base import Basic
from src.structures.character import Character, FakemonCharacter, VariantCharacter
from src.structures.movepool import Movepool
from src.utils.functions import yaml_handler
from src.views.move_view import MoveView

__all__ = (
    "MovepoolView",
    "MovepoolViewSelector",
    "MovepoolModal",
)

PLACEHOLDER = "Move, Move, Move"


class MovepoolModal(Modal):
    def __init__(self, oc: Character) -> None:
        super().__init__(title=f"Movepool for {oc.name}", timeout=None)
        movepool = oc.movepool
        self.level = TextInput(
            style=TextStyle.paragraph,
            label="Level Moves",
            placeholder="1: Move, Move\n2: Move, Move",
            required=False,
            default="\n".join(f"{k}: {', '.join(x.name for x in v)}" for k, v in movepool.level.items() if v),
        )
        self.tm = TextInput(
            style=TextStyle.paragraph,
            label="TM Moves",
            placeholder=PLACEHOLDER,
            required=False,
            default=", ".join(x.name for x in movepool.tm),
        )
        self.tutor = TextInput(
            style=TextStyle.paragraph,
            label="Tutor Moves",
            placeholder=PLACEHOLDER,
            required=False,
            default=", ".join(x.name for x in movepool.tutor),
        )
        self.egg = TextInput(
            style=TextStyle.paragraph,
            label="Egg Moves",
            placeholder=PLACEHOLDER,
            required=False,
            default=", ".join(x.name for x in movepool.egg),
        )
        self.event = TextInput(
            style=TextStyle.paragraph,
            label="Event Moves",
            placeholder=PLACEHOLDER,
            required=False,
            default=", ".join(x.name for x in movepool.event),
        )
        self.add_item(self.level)
        self.add_item(self.tm)
        self.add_item(self.tutor)
        self.add_item(self.egg)
        self.add_item(self.event)
        self.oc = oc

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        if not isinstance(self.oc, (VariantCharacter, FakemonCharacter)):
            await resp.send_message(
                "Movepool can't be changed for the Species.",
                ephemeral=True,
            )
            return

        movepool = Movepool.from_dict(
            level=yaml_handler(self.level.value),
            tm=yaml_handler(self.tm.value),
            tutor=yaml_handler(self.tutor.value),
            egg=yaml_handler(self.egg.value),
            event=yaml_handler(self.event.value),
        )

        self.oc.species.movepool = movepool
        self.oc.moveset &= frozenset(movepool())
        await resp.send_message("Movepool has been changed.", ephemeral=True)
        self.stop()


class MovepoolView(Basic):
    def __init__(
        self,
        target: Interaction | TextChannel,
        member: Member,
        oc: Character,
    ):
        super().__init__(target=target, member=member, timeout=None)
        self.oc = oc
        self.embed.title = f"Modify Movepool for {oc.name}"

    @button(label="Modify Movepool")
    async def modify(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        modal = MovepoolModal(self.oc)
        await resp.send_modal(modal)
        await modal.wait()
        await self.delete()
        self.stop()

    @button(label="Keep Current")
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message(
            "Keeping current movepool",
            ephemeral=True,
        )
        await self.delete()
        self.stop()


def movepool_parser(movepool: Movepool):
    def inner(item: str):
        moves = movepool[item]
        return item.title(), f"{len(moves):02d} moves in this category."

    return inner


class MovepoolViewSelector(Complex):
    def __init__(
        self,
        *,
        member: Member | User,
        movepool: Movepool,
        target: Interaction | TextChannel,
        timeout: float = None,
    ):
        super().__init__(
            member=member,
            values=movepool.__slots__,
            target=target,
            parser=movepool_parser(movepool),
            emoji_parser="\N{FLOPPY DISK}",
            keep_working=True,
            sort_key=str,
            timeout=timeout,
        )
        self.movepool = movepool

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
        view = MoveView(
            bot=interaction.client,
            member=interaction.user,
            target=interaction,
            moves=self.movepool[self.current_choice],
        )
        await interaction.response.send_message(
            embed=view.embed,
            view=view,
            ephemeral=True,
        )
        await super(MovepoolViewSelector, self).select_choice(interaction, sct)
