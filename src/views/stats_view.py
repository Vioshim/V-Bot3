# Copyright 2021 Vioshim
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

from typing import Optional, TypeVar

from discord import Member
from discord.abc import Messageable

from src.enums.stats import Stats
from src.pagination.complex import Complex
from src.structures.bot import CustomBot

_M = TypeVar("_M", bound=Messageable)


class StatsView(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: _M,
    ):
        super(StatsView, self).__init__(
            bot=bot,
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
