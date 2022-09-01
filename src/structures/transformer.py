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
