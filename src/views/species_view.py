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


from discord import Interaction, Member
from discord.ui import Select, select

from src.pagination.complex import Complex
from src.structures.mon_typing import Typing
from src.structures.species import Fusion, Species, Variant

__all__ = ("SpeciesComplex",)


class SpeciesComplex(Complex[Species]):
    def __init__(self, member: Member, target: Interaction, mon_total: set[Species], fusion: bool = False):

        self.total = {x for x in mon_total if not x.banned}
        max_values = min(len(self.total), 2 if fusion else 1)

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

    def menu_format(self) -> None:
        self.select_types.options.clear()
        total: set[Species] = set(self.total) - self.choices

        self.data = {"No Filter": total}

        data: dict[Typing, set[Species]] = {}
        for item in total:
            for t in item.types:
                data.setdefault(t, set())
                data[t].add(item)

        for k, items in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
            if items:
                label = k.name
                self.data[label] = items
                self.select_types.add_option(
                    label=label,
                    emoji=k.emoji,
                    description=f"Has {len(items)} Species.",
                )

        return super(SpeciesComplex, self).menu_format()

    @select(placeholder="Filter by Typings", custom_id="filter", max_values=2)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        self.values = set.intersection(*[self.data[value] for value in sct.values])
        await self.edit(interaction=interaction, page=0)
