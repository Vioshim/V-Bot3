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


from typing import Generic, TypeVar

from discord import Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transformer
from rapidfuzz import process
from rapidfuzz.utils import default_process

E = TypeVar("E")


class ABCTransformer(Generic[E], Transformer):
    score_cutoff: int = 60

    def __init_subclass__(cls, *, score_cutoff: int = 60) -> None:
        cls.score_cutoff = score_cutoff

    def processor(self, key: Choice[int | float | str]) -> str:
        """Rapidfuzz processor

        Parameters
        ----------
        key : Choice[int | float | str]
            Item

        Returns
        -------
        str
            processed value
        """
        key = key.name if isinstance(key, Choice) else str(key)
        return default_process(key)

    async def on_autocomplete(self, ctx: Interaction, value: int | float | str, /) -> list[Choice[int | float | str]]:
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
        raise NotImplementedError("Derived classes need to implement this.")

    async def autocomplete(self, ctx: Interaction, value: int | float | str, /) -> list[Choice[int | float | str]]:
        items = await self.on_autocomplete(ctx, value)
        return [
            x[0]
            for x in process.extract(
                value,
                choices=items,
                limit=25,
                processor=self.processor,
                score_cutoff=self.score_cutoff,
            )
        ]
