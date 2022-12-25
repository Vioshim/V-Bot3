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


from typing import Any, Iterable, Optional

from discord import Color, Embed, Interaction, InteractionResponse, Member
from discord.ui import Select, select

from src.pagination.complex import Complex
from src.structures.character import Character
from src.structures.mon_typing import TypingEnum
from src.structures.species import (
    Chimera,
    CustomMega,
    CustomParadox,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Paradox,
    Pokemon,
    Species,
    UltraBeast,
    Variant,
)
from src.utils.etc import LIST_EMOJI, WHITE_BAR

__all__ = ("SpeciesComplex",)


def emoji_parser(x: Species):
    match x:
        case o if isinstance(o, Pokemon):
            return "\N{LARGE BLUE SQUARE}"
        case o if isinstance(o, Mythical):
            return "\N{LARGE GREEN SQUARE}"
        case o if isinstance(o, Legendary):
            return "\N{LARGE YELLOW SQUARE}"
        case o if isinstance(o, Paradox):
            return "\N{LARGE BROWN SQUARE}"
        case o if isinstance(o, UltraBeast):
            return "\N{LARGE PURPLE SQUARE}"
        case o if isinstance(o, Mega):
            return "\N{LARGE ORANGE SQUARE}"
        case _:
            return "\N{LARGE RED SQUARE}"


class SpeciesComplex(Complex[Species]):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        mon_total: Iterable[Species],
        max_values: int = 1,
        silent_mode: bool = True,
        keep_working: bool = False,
        ocs: set[Character] = None,
    ):

        self.total = mon_total = sorted({x for x in mon_total if not x.banned}, key=lambda x: x.name)
        max_values = min(len(self.total), max_values)

        self.reference1: dict[Species, int] = {}
        self.reference2: dict[Species, int] = {}
        self.reference3: dict[Species, int] = {}

        values: set[Character] = set()
        if ocs:
            values.update(ocs)

        for oc in values:
            mon = oc.species
            if isinstance(mon, (Fusion, Chimera)):
                for x in mon.bases:
                    self.reference1.setdefault(x, 0)
                    self.reference1[x] += 1
            elif isinstance(mon, (Variant, CustomMega, CustomParadox)):
                self.reference2.setdefault(mon.base, 0)
                self.reference2[mon.base] += 1
            elif isinstance(mon, Species):
                self.reference3.setdefault(mon, 0)
                self.reference3[mon] += 1

        def parser(x: Species):
            data = dict(
                Species=self.reference3.get(x, 0),
                Fusions=self.reference1.get(x, 0),
                Variants=self.reference2.get(x, 0),
            )
            if text := ", ".join(f"{x}: {y}" for x, y in data.items() if y):
                return x.name, f"{sum(data.values())} OCs ({text})"
            return x.name, "Unused Species."

        super(SpeciesComplex, self).__init__(
            member=member,
            target=target,
            values=mon_total,
            timeout=None,
            parser=parser,
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            max_values=max_values,
            silent_mode=silent_mode,
            emoji_parser=emoji_parser,
            real_max=max_values,
            auto_text_component=True,
            auto_choice_info=True,
            auto_conclude=False,
        )
        self.embed.title = "Select Species"
        self.data = {}

    def default_params(self, page: Optional[int] = None) -> dict[str, Any]:
        self.values = [x for x in self.values if x not in self.choices] or self.total
        self.max_values = min(self.real_max, len(self.values))
        return super(SpeciesComplex, self).default_params(page)

    def menu_format(self) -> None:
        self.select_types.options.clear()
        total: set[Species] = set(self.total) - self.choices

        data: dict[str | TypingEnum, set[Species]] = {}
        for item in total:
            for t in item.types:
                data.setdefault(t, set())
                data[t].add(item)

        items = [("No Filter", set(total))]
        items.extend(sorted(data.items(), key=lambda x: x[0].name))
        for k, items in items:
            if items:
                if isinstance(k, TypingEnum):
                    label, emoji = k.name, k.emoji
                else:
                    label, emoji = k, LIST_EMOJI

                info = dict(
                    mono=len({x for x in items if len(x.types) == 1}),
                    dual=len({x for x in items if len(x.types) == 2}),
                )

                if description := ", ".join(f"{v} {k}-types" for k, v in info.items() if v):
                    description = f"Has {description}."

                self.data[label] = items

                self.select_types.add_option(
                    label=label,
                    emoji=emoji,
                    description=description,
                )

        return super(SpeciesComplex, self).menu_format()

    @select(placeholder="Filter by Typings", custom_id="filter", max_values=2, row=3)
    async def select_types(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response

        if "No Filter" in sct.values:
            items = set.intersection(*[self.data[value] for value in sct.values])
        elif types := TypingEnum.deduce_many(*sct.values):
            items = {x for x in self.total if x.types == types}
        else:
            items = self.values

        if items:
            self.values = sorted(items, key=lambda x: x.name)
            await self.edit(interaction=interaction, page=0)
        else:
            embed = Embed(
                title="No entries found",
                description="\n".join(f"• {x}" for x in sct.values),
                color=Color.blurple(),
                timestamp=interaction.created_at,
            )
            embed.set_image(url=WHITE_BAR)
            await resp.send_message(embed=embed, ephemeral=True)
