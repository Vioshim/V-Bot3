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

from __future__ import annotations

from contextlib import suppress
from dataclasses import asdict, astuple, dataclass
from enum import Enum
from typing import Optional, TypeVar

from discord import Interaction, InteractionResponse, Member, TextStyle
from discord.abc import Messageable
from discord.ui import TextInput
from yaml import safe_load

from src.pagination.complex import Complex, DefaultModal
from src.utils.functions import yaml_handler

_M = TypeVar("_M", bound=Messageable)


@dataclass(unsafe_hash=True)
class StatItem:
    HP: int = 3
    ATK: int = 3
    DEF: int = 3
    SPA: int = 3
    SPE: int = 3
    SPD: int = 3

    def __repr__(self) -> str:
        """repr method

        Returns
        -------
        str
            UI friendly representation
        """
        return " ".join(f"{k}:{v}" for k, v in asdict(self).items())


class Stats(Enum):
    """
    Class which represents the most common fakemon stats
    """

    PHYSICAL_ATTACKER = StatItem(2, 4, 5, 1, 2, 4)
    PHYSICAL_BALANCED = StatItem(3, 5, 5, 1, 1, 3)
    PHYSICAL_DEFENDER = StatItem(4, 5, 4, 2, 1, 2)
    OVERALL_ATTACKER = StatItem(1, 1, 5, 5, 1, 5)
    OVERALL_BALANCED = StatItem(3, 3, 3, 3, 3, 3)
    OVERALL_DEFENDER = StatItem(5, 5, 1, 1, 5, 1)
    SPECIAL_ATTACKER = StatItem(2, 2, 1, 5, 4, 4)
    SPECIAL_BALANCED = StatItem(3, 1, 1, 5, 5, 3)
    SPECIAL_DEFENDER = StatItem(4, 1, 2, 4, 5, 2)

    def __str__(self) -> str:
        """str method

        Returns
        -------
        str
            Name
        """
        return self.name.replace("_", " ").title()

    @property
    def emoji(self) -> str:
        """Emoji which represents the set

        Returns
        -------
        str
            Emoji
        """
        match self.name.split("_"):
            case [_, "ATTACKER"]:
                return "\N{CROSSED SWORDS}"
            case [_, "ATTACKER"]:
                return "\N{SHIELD}"
            case _:
                return "\N{SCALES}"


DEFAULT = """
HP: 3
ATK: 3
DEF: 3
SPA: 3
SPD: 3
SPE: 3
""".strip()


class StatsModal(DefaultModal):
    stat = TextInput(
        label="Stats",
        style=TextStyle.paragraph,
        placeholder=DEFAULT.replace("3", "1 - 5"),
        default=DEFAULT,
        required=True,
    )

    def __init__(self, view: StatsView) -> None:
        super().__init__(view, title="Fill the Stats")
        self.text = Optional[StatItem] = None

    async def on_submit(self, interaction: Interaction) -> None:
        text = yaml_handler(self.stat.value or "")
        resp: InteractionResponse = interaction.response
        if not isinstance(item := safe_load(text), dict):
            with suppress(TypeError):
                stats = StatItem(**item)
                info = astuple(stats)
                if all(1 <= stat <= 5 for stat in info) and sum(info) <= 18:
                    await resp.send_message(
                        f"Stats asigned as {stats!r}", ephemeral=True
                    )
                    self.text = stats
                    self.stop()
                    self.view.stop()


class StatsView(Complex):
    def __init__(
        self,
        member: Member,
        target: _M,
    ):
        super(StatsView, self).__init__(
            member=member,
            target=target,
            values=Stats,
            timeout=None,
        )
        self.embed.title = "Select the Set of Stats"
        self.embed.description = (
            "Keep in mind that stats for fakemon work from 1 to 5"
            "\n\n"
            "> **1** - Very Low\n"
            "> **2** - Low\n"
            "> **3** - Average\n"
            "> **4** - High\n"
            "> **5** - Very High"
        )

    @property
    def choice(self) -> Optional[Stats]:
        """Override Method

        Returns
        -------
        Optional[Stats]
            Desired stats
        """
        return super(StatsView, self).choice
