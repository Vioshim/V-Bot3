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

from typing import Iterable

from discord import ButtonStyle, Interaction
from discord.ui import Button, View

from src.structures.bot import CustomBot
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.views.move_view import MoveView

__all__ = (
    "MovepoolButton",
    "MovepoolView",
)


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
            disabled=not moves,
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


class MovepoolView(View):
    def __init__(
        self,
        bot: CustomBot,
        movepool: Movepool,
        timeout: float = None,
    ):
        super(MovepoolView, self).__init__(timeout=timeout)
        self.bot = bot
        for item in movepool.__slots__:
            btn = MovepoolButton(bot=bot, movepool=movepool[item], label=item)
            self.add_item(btn)
