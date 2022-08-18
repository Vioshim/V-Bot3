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


from typing import Any

from discord import Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transformer
from rapidfuzz import process
from rapidfuzz.utils import default_process


def processor(key: Any):
    key: str = getattr(key, "name", key)
    return default_process(key)


class ABCTransformer(Transformer):
    async def on_autocomplete(
        self,
        ctx: Interaction,
        value: int | float | str,
    ) -> list[Choice[int | float | str]]:
        """Method

        Parameters
        ----------
        ctx : Interaction
            Interaction
        value : str
            Value

        Returns
        -------
        list[Choice[_T]]
            Choices
        """
        return []

    async def autocomplete(
        self,
        ctx: Interaction,
        value: int | float | str,
    ) -> list[Choice[int | float | str]]:
        items = await self.on_autocomplete(ctx, value)
        if options := process.extract(
            value,
            choices=items,
            limit=25,
            processor=processor,
            score_cutoff=60,
        ):
            return [x[0] for x in options]
        return items[:25]
