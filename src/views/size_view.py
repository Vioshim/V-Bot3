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


from itertools import combinations_with_replacement
from typing import Optional

import numpy as np
from discord import ButtonStyle, Interaction, Member
from discord.ui import Button, Modal, Select, TextInput, button, select

from src.pagination.view_base import Basic
from src.structures.character import Character, Size
from src.structures.species import Fakemon, Fusion, Species

__all__ = (
    "HeightView",
    "WeightView",
)


class HeightModal(Modal, title="Height"):
    def __init__(self, oc: Character, species: Optional[Species] = None) -> None:
        super(HeightModal, self).__init__(title="Height", timeout=None)
        self.oc = oc
        self.species = oc.species if species is None else species

    @property
    def value(self) -> float:
        return 0

    async def on_submit(self, interaction: Interaction, /) -> None:
        height: float = getattr(self.species, "height", 0.0)

        if isinstance(self.species, Fusion):
            heights = [x.height for x in self.species.bases]
        else:
            heights = (height,)

        items = {x.height_value(height) for height in heights for x in Size}
        min_item, max_item = min(items), max(items)

        proportion = self.oc.size_category.value
        value = self.value / proportion
        answer = max(min_item, min(max_item, value))
        self.oc.size = Size.Average if answer <= 0 else answer

        if isinstance(self.oc.size, Size):
            info = self.oc.size.height_info(proportion * height)
        else:
            info = Size.Average.height_info(proportion * self.oc.size)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class HeightModal1(HeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None, species: Optional[Species] = None) -> None:
        super(HeightModal1, self).__init__(oc=oc, species=species)
        self.text = TextInput(label="Meters", placeholder=info, default=info)
        self.add_item(self.text)

    @property
    def value(self) -> float:
        text = self.text.value.removesuffix(".").lower()
        if "cm" in text:
            ratio, text = 0.01, text.removesuffix("cm")
        else:
            ratio, text = 1.00, text.removesuffix("m")

        try:
            return round(ratio * float(text.strip()), 2)
        except ValueError:
            return 0


class HeightModal2(HeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None, species: Optional[Species] = None) -> None:
        super(HeightModal2, self).__init__(oc=oc, species=species)
        info = info.removesuffix('" ft') if info else ""
        ft_info, in_info = info.split("' ")

        self.text1 = TextInput(label="Feet", placeholder=ft_info, default=ft_info, required=False)
        self.text2 = TextInput(label="Inches", placeholder=in_info, default=in_info, required=False)

        self.add_item(self.text1)
        self.add_item(self.text2)

    @property
    def value(self) -> float:
        try:
            return round(
                Size.ft_inches_to_meters(
                    feet=float(self.text1.value or "0"),
                    inches=float(self.text2.value or "0"),
                ),
                2,
            )
        except ValueError:
            return 0


class WeightModal(Modal, title="Weight"):
    def __init__(self, oc: Character, info: Optional[str] = None, species: Optional[Species] = None) -> None:
        super(WeightModal, self).__init__(title="Weight", timeout=None)
        self.oc = oc
        self.species = oc.species if species is None else species

    @property
    def value(self) -> float:
        return 0

    async def on_submit(self, interaction: Interaction, /) -> None:
        weight: float = getattr(self.species, "weight", 0)

        if isinstance(self.species, Fusion):
            weights = [x.weight for x in sorted(self.species.bases, key=lambda x: x.weight)]
        else:
            weights = (weight,)

        items = {x.weight_value(weight) for weight in weights for x in Size}
        min_item, max_item = min(items), max(items)
        proportion = self.oc.size_category.value

        value = self.value / proportion
        answer = max(min_item, min(max_item, value))
        self.oc.weight = Size.Average if answer <= 0 else answer

        if isinstance(self.oc.weight, Size):
            info = self.oc.weight.weight_info(proportion * weight)
        else:
            info = Size.Average.weight_info(proportion * self.oc.weight)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class WeightModal1(WeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None, species: Optional[Species] = None) -> None:
        super(WeightModal1, self).__init__(oc=oc, species=species)
        self.text = TextInput(label="kg", placeholder=info, default=info)
        self.add_item(self.text)

    @property
    def value(self) -> float:
        text = self.text.value.lower().removesuffix(".")
        text = text.removesuffix("kg").removesuffix("kgs")
        try:
            return round(float(text.strip()), 2)
        except ValueError:
            return 0


class WeightModal2(WeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None, species: Optional[Species] = None) -> None:
        super(WeightModal2, self).__init__(oc=oc, species=species)
        self.text = TextInput(label="lbs", placeholder=info, default=info)
        self.add_item(self.text)

    @property
    def value(self) -> float:
        text = self.text.value.lower().removesuffix(".")
        text = text.removesuffix("lbs").removesuffix("lb")
        try:
            return round(Size.lbs_to_kgs(float(text.strip())), 2)
        except ValueError:
            return 0


class HeightView(Basic):
    def __init__(
        self,
        *,
        target: Interaction,
        member: Member,
        oc: Character,
        species: Optional[Species] = None,
    ):
        super(HeightView, self).__init__(target=target, member=member, timeout=None)
        self.oc = oc
        self.species = oc.species if species is None else species
        self.format()

    def format(self):
        self.reference.options.clear()
        self.choice.options.clear()

        if isinstance(self.oc.species, Fusion):
            bases = self.oc.species.bases
        else:
            bases = [self.oc.species] if self.oc.species else []

        proportion = self.oc.size_category.value
        if data := {f for x in combinations_with_replacement(bases, len(bases)) if (f := Fusion(*x)) and f.id}:
            for item in sorted(data, key=lambda x: x.height, reverse=True):
                self.reference.add_option(
                    label=item.name,
                    value=item.id,
                    description=Size.Average.height_info(proportion * item.height),
                    default=item == self.species,
                )
        else:
            self.remove_item(self.reference)

        height = self.species.height if self.species else 0

        if isinstance(self.oc.species, Fusion):
            s_a, *_, s_b = sorted(self.oc.species.bases, key=lambda x: x.height)
            height_a, height_b = s_a.height, s_b.height
        else:
            height = 0
            if self.oc.species and not isinstance(self.oc.species, Fakemon):
                height = self.oc.species.height
            height_a = height_b = height

        min_value, max_value = (
            Size.Minimum.height_value(height_a) * proportion,
            Size.Maximum.height_value(height_b) * proportion,
        )

        if isinstance(self.oc.size, Size):
            height = self.oc.size.height_value(height) * proportion
        else:
            height = Size.Average.height_value(self.oc.size) * proportion

        info = Size.Average.height_info(height)

        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"

        for value, item in zip(np.linspace(min_value, max_value, len(items)), items):
            label = Size.Average.height_info(value)
            self.choice.add_option(
                label=label,
                value=item.name,
                description=item.reference_name,
                default=info == label,
                emoji=item.emoji,
            )

        return self

    @select(placeholder="Species for reference", min_values=0)
    async def reference(self, itx: Interaction, sct: Select):
        if sct.values:
            self.species = Fusion.from_ID(sct.values[0])
        await itx.response.edit_message(view=self.format())

    @select(placeholder="Select a Size.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.size = Size[sct.values[0]].height_value(self.species.height if self.species else 0)
        await self.delete(itx)

    @button(label="Meters", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = HeightModal1(oc=self.oc, info=btn.label, species=self.species)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Feet & Inches", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = HeightModal2(oc=self.oc, info=btn.label, species=self.species)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if btn.label and "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)


class WeightView(Basic):
    def __init__(self, *, target: Interaction, member: Member, oc: Character, species: Optional[Species] = None):
        super(WeightView, self).__init__(target=target, member=member, timeout=None)
        self.choice.options.clear()
        self.oc = oc
        self.species = oc.species if species is None else species
        self.format()

    def format(self):
        self.reference.options.clear()
        self.choice.options.clear()

        if isinstance(self.oc.species, Fusion):
            bases = self.oc.species.bases
        else:
            bases = [self.oc.species] if self.oc.species else []

        proportion = self.oc.size_category.value
        if data := {f for x in combinations_with_replacement(bases, len(bases)) if (f := Fusion(*x)) and f.id}:
            for item in sorted(data, key=lambda x: x.weight, reverse=True):
                self.reference.add_option(
                    label=item.name,
                    value=item.id,
                    description=Size.Average.weight_info(proportion * item.weight),
                    default=item == self.species,
                )
        else:
            self.remove_item(self.reference)

        weight = self.species.weight if self.species else 0

        if isinstance(self.oc.species, Fusion):
            s_a, *_, s_b = sorted(self.oc.species.bases, key=lambda x: x.height)
            height_a, height_b = s_a.height, s_b.height
        else:
            height = 0
            if self.oc.species and not isinstance(self.oc.species, Fakemon):
                height = self.oc.species.height
            height_a = height_b = height

        min_value, max_value = (
            Size.Minimum.height_value(height_a),
            Size.Maximum.height_value(height_b),
        )
        min_value *= proportion
        max_value *= proportion

        if isinstance(self.oc.weight, Size):
            weight = self.oc.weight.height_value(weight) * proportion

        else:
            weight = Size.Average.weight_value(self.oc.weight) * proportion

        info = Size.Average.height_info(weight)
        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"

        for value, item in zip(np.linspace(min_value, max_value, len(items)), items):
            label = Size.Average.weight_info(value)
            self.choice.add_option(
                label=label,
                value=item.name,
                description=item.reference_name,
                default=label == info,
                emoji=item.emoji,
            )

        return self

    @select(placeholder="Species for reference", min_values=0)
    async def reference(self, itx: Interaction, sct: Select):
        if sct.values:
            self.species = Fusion.from_ID(sct.values[0])
        await itx.response.edit_message(view=self.format())

    @select(placeholder="Single Choice.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.weight = Size[sct.values[0]].weight_value(self.species.weight if self.species else 0)
        await self.delete(itx)

    @button(label="Kg", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = WeightModal1(oc=self.oc, info=btn.label, species=self.species)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Lbs", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = WeightModal2(oc=self.oc, info=btn.label, species=self.species)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if btn.label and "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)
