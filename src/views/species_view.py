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


from typing import Any, Optional

from discord import (
    DiscordException,
    Interaction,
    InteractionResponse,
    Member,
    PartialMessage,
)
from discord.ui import Select, select

from src.pagination.complex import Complex
from src.structures.mon_typing import Typing
from src.structures.species import Fusion, Species, Variant
from src.utils.etc import LIST_EMOJI

__all__ = ("SpeciesComplex",)


class SpeciesComplex(Complex[Species]):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        mon_total: set[Species],
        max_values: int = 1,
    ):

        self.total = {x for x in mon_total if not x.banned}
        max_values = min(len(self.total), max_values)

        self.reference: dict[Species, int] = {}

        for oc in target.client.get_cog("Submission").ocs.values():

            if not target.guild.get_member(oc.author):
                continue

            if isinstance(oc.species, Fusion):
                mons = oc.species.bases
            elif isinstance(oc.species, Variant):
                mons = [oc.species.base]
            else:
                mons = [oc.species]

            for mon in mons:
                self.reference.setdefault(mon, 0)
                self.reference[mon] += 1

        super(SpeciesComplex, self).__init__(
            member=member,
            target=target,
            values=mon_total,
            timeout=None,
            parser=lambda x: (x.name, f"Species have {self.reference.get(x, 0)} OCs"),
            keep_working=False,
            sort_key=lambda x: x.name,
            max_values=max_values,
            silent_mode=True,
        )
        self.real_max = max_values
        self.embed.title = "Select Species"
        self.data = {}

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        data = dict(embed=self.embed)

        self.values = [x for x in self.values if x not in self.choices] or self.total
        self.max_values = min(self.real_max, len(self.values))
        self.embed.description = "\n".join(f"> • {x.name}" for x in self.choices)

        if isinstance(page, int):
            self.pos = page
            self.menu_format()
            data["view"] = self

        return data

    async def edit(self, interaction: Interaction, page: Optional[int] = None) -> None:
        """Method used to edit the pagination

        Parameters
        ----------
        page: int, optional
            Page to be accessed, defaults to None
        """
        if self.keep_working or len(self.choices) < self.real_max:
            resp: InteractionResponse = interaction.response
            data = self.default_params(page=page)
            if not resp.is_done():
                return await resp.edit_message(**data)
            try:
                if message := self.message or interaction.message:
                    if message.author == interaction.client.user and not message.flags.ephemeral:
                        message = PartialMessage(channel=message.channel, id=message.id)
                    self.message = await message.edit(**data)
                else:
                    self.message = await interaction.edit_original_response(**data)
            except DiscordException as e:
                interaction.client.logger.exception("View Error", exc_info=e)
                self.stop()
        else:
            await self.delete(interaction)

    def menu_format(self) -> None:
        self.select_types.options.clear()
        total: set[Species] = set(self.total) - self.choices

        data: dict[str | Typing, set[Species]] = {"No Filter": total}
        for item in total:
            for t in item.types:
                data.setdefault(t, set())
                data[t].add(item)

        for k, items in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
            if items:
                if isinstance(k, str):
                    label, emoji = k, LIST_EMOJI
                else:
                    label, emoji = k.name, k.emoji

                aux1 = len({x for x in items if len(x.types) == 1})
                aux2 = len({x for x in items if len(x.types) == 2})

                description = f"Has {aux1} mono-types, {aux2} dual-types."

                self.data[label] = items
                self.select_types.add_option(
                    label=label,
                    emoji=emoji,
                    description=description,
                )

        return super(SpeciesComplex, self).menu_format()

    @select(placeholder="Filter by Typings", custom_id="filter", max_values=2)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        if "No Filter" in sct.values:
            self.values = set.intersection(*[self.data[value] for value in sct.values])
        elif types := Typing.deduce_many(*sct.values):
            self.values = {x for x in self.total if x.types == types}
        await self.edit(interaction=interaction, page=0)
