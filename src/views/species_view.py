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

from functools import lru_cache
from typing import Any, Iterable, Optional

from discord import Interaction, Member
from discord.ui import Select, select

from src.pagination.complex import Complex
from src.structures.mon_typing import TypingEnum
from src.structures.species import Chimera, CustomMega, Fusion, Species, Variant
from src.utils.etc import LIST_EMOJI

__all__ = ("SpeciesComplex",)


class SpeciesComplex(Complex[Species]):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        mon_total: Iterable[Species],
        max_values: int = 1,
    ):

        self.total = mon_total = {x for x in mon_total if not x.banned}
        max_values = min(len(self.total), max_values)

        self.reference1: dict[Species, int] = {}
        self.reference2: dict[Species, int] = {}
        self.reference3: dict[Species, int] = {}

        for oc in target.client.get_cog("Submission").ocs.values():
            if not target.guild.get_member(oc.author):
                continue

            if isinstance(oc.species, (Fusion, Chimera)):
                for mon in oc.species.bases:
                    self.reference1.setdefault(mon, 0)
                    self.reference1[mon] += 1
            elif isinstance(oc.species, (Variant, CustomMega)):
                mon = oc.species.base
                self.reference2.setdefault(mon, 0)
                self.reference2[mon] += 1
            elif isinstance(mon := oc.species, Species):
                self.reference3.setdefault(mon, 0)
                self.reference3[mon] += 1

        @lru_cache(maxsize=None)
        def parser(x: Species):
            data = dict(
                Species=self.reference3.get(x, 0),
                Fusions=self.reference1.get(x, 0),
                Variants=self.reference2.get(x, 0),
            )
            if text := ", ".join(f"{x}: {y}" for x, y in data.items() if y):
                phrase = f"{sum(data.values())} OCs ({text})"
            else:
                phrase = "Unused Species."
            return x.name, phrase

        super(SpeciesComplex, self).__init__(
            member=member,
            target=target,
            values=mon_total,
            timeout=None,
            parser=parser,
            keep_working=False,
            sort_key=lambda x: x.name,
            max_values=max_values,
            silent_mode=True,
            real_max=max_values,
        )
        self.embed.title = "Select Species"
        self.data = {}

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        data = dict(embed=self.embed)

        self.values = [x for x in self.values if x not in self.choices] or self.total
        self.max_values = min(self.real_max, len(self.values))
        self.embed.description = "\n".join(sorted(f"> • {x.name}" for x in self.choices))

        if isinstance(page, int):
            self.pos = page
            self.menu_format()
            data["view"] = self

        return data

    def menu_format(self) -> None:
        self.select_types.options.clear()
        total: set[Species] = set(self.total) - self.choices

        data: dict[str | TypingEnum, set[Species]] = {}
        for item in total:
            for t in item.types:
                data.setdefault(t, set())
                data[t].add(item)

        items = [("No Filter", total)]
        items.extend(sorted(data.items(), key=lambda x: x[0].name))
        for k, items in items:
            if items:
                if isinstance(k, TypingEnum):
                    label, emoji = k.name, k.emoji
                else:
                    label, emoji = k, LIST_EMOJI

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
        elif types := TypingEnum.deduce_many(*sct.values):
            self.values = {x for x in self.total if x.types == types}
        await self.edit(interaction=interaction, page=0)
