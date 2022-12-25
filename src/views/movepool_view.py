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


from discord import Interaction, InteractionResponse, Member, TextChannel, TextStyle
from discord.ui import Button, Modal, TextInput, button

from src.pagination.view_base import Basic
from src.structures.character import Character
from src.structures.movepool import Movepool
from src.structures.species import CustomParadox, Fakemon, Variant
from src.utils.functions import yaml_handler

__all__ = ("MovepoolView", "MovepoolModal")

PLACEHOLDER = "Move, Move, Move"


class MovepoolModal(Modal):
    def __init__(self, oc: Character) -> None:
        super(MovepoolModal, self).__init__(title=f"Movepool for {oc.name}"[:45], timeout=None)
        movepool = oc.movepool
        self.level = TextInput(
            style=TextStyle.paragraph,
            label="Level Moves",
            placeholder="1: Move, Move\n2: Move, Move",
            required=False,
            default="\n".join(f"{k}: {o}" for k, v in movepool.level.items() if (o := ", ".join(x.name for x in v))),
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
        if not isinstance(self.oc.species, (Fakemon, Variant, CustomParadox)):
            await resp.send_message("Movepool can't be changed for the Species.", ephemeral=True)
            return

        movepool = Movepool.from_dict(
            level=yaml_handler(self.level.value),
            tm=yaml_handler(self.tm.value),
            tutor=yaml_handler(self.tutor.value),
            egg=yaml_handler(self.egg.value),
            event=yaml_handler(self.event.value),
        )

        movepool.event |= {x for x in self.oc.moveset if x not in movepool}

        self.oc.species.movepool = movepool
        await resp.send_message(repr(movepool), ephemeral=True, delete_after=3)
        self.stop()


class MovepoolView(Basic):
    def __init__(self, target: Interaction | TextChannel, member: Member, oc: Character):
        super(MovepoolView, self).__init__(target=target, member=member, timeout=None)
        self.oc = oc

    @button(label="Modify Movepool")
    async def modify(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        modal = MovepoolModal(self.oc)
        await resp.send_modal(modal)
        await modal.wait()
        await self.delete(ctx)

    @button(label="Keep Current")
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message("Keeping current movepool", ephemeral=True)
        await self.delete(ctx)
