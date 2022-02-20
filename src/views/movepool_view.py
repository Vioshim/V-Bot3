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

from asyncio import Future, get_running_loop
from typing import Iterable

from discord import (
    ButtonStyle,
    InputTextStyle,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
)
from discord.ui import Button, InputText, Modal, View, button

from src.pagination.view_base import Basic
from src.structures.bot import CustomBot
from src.structures.character import (
    Character,
    FakemonCharacter,
    VariantCharacter,
)
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.utils.functions import yaml_handler
from src.views.move_view import MoveView

__all__ = (
    "MovepoolButton",
    "MovepoolView",
    "MovepoolViewSelector",
    "MovepoolModal",
)

PLACEHOLDER = "Move, Move, Move"


class MovepoolModal(Modal):
    def __init__(self, oc: Character) -> None:
        super().__init__(title=f"Movepool for {oc.name}")
        data = oc.movepool.as_display_dict
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="Level Moves",
                placeholder="1: Move, Move\n2: Move, Move",
                required=False,
                value="\n".join(
                    f"{k}: {', '.join(v)}"
                    for k, v in data.get("level", {}).items()
                    if v
                ),
            )
        )
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="TM Moves",
                placeholder=PLACEHOLDER,
                required=False,
                value=", ".join(data.get("tm", [])),
            )
        )
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="Tutor Moves",
                placeholder=PLACEHOLDER,
                required=False,
                value=", ".join(data.get("tutor", [])),
            )
        )
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="Egg Moves",
                placeholder=PLACEHOLDER,
                required=False,
                value=", ".join(data.get("egg", [])),
            )
        )
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="Event Moves",
                placeholder=PLACEHOLDER,
                required=False,
                value=", ".join(data.get("event", [])),
            )
        )
        loop = get_running_loop()
        self._stopped: Future[bool] = loop.create_future()
        self.oc = oc

    def stop(self) -> None:
        if not self._stopped.done():
            self._stopped.set_result(True)

    async def wait(self) -> bool:
        return await self._stopped

    async def callback(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        if not isinstance(self.oc, (VariantCharacter, FakemonCharacter)):
            await resp.send_message(
                "Movepool can't be changed for the Species.",
                ephemeral=True,
            )
            return

        kwargs = {}
        for item in self.children:
            key = item.label.lower().removesuffix(" moves")
            if value := yaml_handler(item.value):
                kwargs[key] = value

        movepool = Movepool.from_dict(**kwargs)

        self.oc.species.movepool = movepool
        self.oc.moveset &= frozenset(movepool())

        await resp.send_message("Movepool has been changed.", ephemeral=True)


class MovepoolView(Basic):
    def __init__(
        self,
        bot: CustomBot,
        target: Interaction | TextChannel,
        member: Member,
        oc: Character,
    ):
        super().__init__(bot=bot, target=target, member=member, timeout=None)
        self.oc = oc
        self.embed.title = f"Modify Movepool for {oc.name}"
        self.embed.clear_fields()
        for key, value in oc.movepool.as_display_dict.items():

            if isinstance(value, dict):
                if text := "\n".join(
                    f"{k}: {', '.join(v)}" for k, v in value.items() if v
                ):
                    self.embed.add_field(
                        name=f"{key.title()} Moves",
                        value=f"```yaml\n{text[:1000]}\n```",
                    )
            elif text := ", ".join(value):
                self.embed.add_field(
                    name=f"{key.title()} Moves",
                    value=f"```yaml\n{text[:1000]}\n```",
                )

    @button(label="Modify Movepool")
    async def modify(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        modal = MovepoolModal(self.oc)
        await resp.send_modal(modal)
        await modal.wait()
        await self.delete()
        self.stop()

    @button(label="Keep Current")
    async def cancel(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.send_message(
            "Keeping current movepool",
            ephemeral=True,
        )
        await self.delete()
        self.stop()


class MovepoolButton(Button):
    def __init__(
        self,
        bot: CustomBot,
        moves: Iterable[Move],
        label: str = None,
    ):
        moves = set(moves)
        super().__init__(
            style=ButtonStyle.blurple,
            label=label,
        )
        self.moves = moves
        self.bot = bot

    async def callback(self, interaction: Interaction):
        view = MoveView(
            bot=self.bot,
            member=interaction.user,
            target=interaction,
            moves=self.moves,
        )
        await interaction.response.send_message(
            embed=view.embed,
            view=view,
            ephemeral=True,
        )


class MovepoolViewSelector(View):
    def __init__(
        self,
        bot: CustomBot,
        movepool: Movepool,
        timeout: float = None,
    ):
        super(MovepoolViewSelector, self).__init__(timeout=timeout)
        self.bot = bot
        for item in movepool.__slots__:
            if moves := movepool[item]:
                btn = MovepoolButton(bot=bot, moves=moves, label=item)
                self.add_item(btn)
