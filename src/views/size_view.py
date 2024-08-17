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


from typing import Optional

import numpy as np
from discord import ButtonStyle, Interaction, Member
from discord.ui import Button, Modal, Select, TextInput, button, select

from src.pagination.view_base import Basic
from src.structures.character import Character, Size, SizeCategory

__all__ = ("HeightView",)


class HeightModal(Modal, title="Height"):
    def __init__(self, oc: Character) -> None:
        super(HeightModal, self).__init__(title="Height", timeout=None)
        self.oc = oc

    @property
    def value(self) -> float:
        return 0

    async def on_submit(self, interaction: Interaction, /) -> None:
        value = self.value
        self.oc.size = max(0.1, min(30, value))
        info = Size.Average.height_info(self.oc.size)
        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class HeightModal1(HeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None) -> None:
        super(HeightModal1, self).__init__(oc=oc)
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
    def __init__(self, oc: Character, info: Optional[str] = None) -> None:
        super(HeightModal2, self).__init__(oc=oc)
        info = info.removesuffix('" ft') if info else ""
        try:
            ft_info, in_info = info.split("' ")
        except ValueError:
            ft_info, in_info = "0", info.removesuffix('"')

        self.text1 = TextInput(label="Feet", placeholder=ft_info, default=ft_info, required=False)
        self.text2 = TextInput(label="Inches", placeholder=in_info, default=in_info, required=False)

        self.add_item(self.text1)
        self.add_item(self.text2)

    @property
    def value(self) -> float:
        try:
            result = Size.ft_inches_to_meters(
                feet=float(self.text1.value or "0"),
                inches=float(self.text2.value or "0"),
            )
            return round(result, 2)
        except ValueError:
            return 0


AMOUNT = 9


class HeightView(Basic):
    def __init__(self, *, target: Interaction, member: Member, oc: Character):
        super(HeightView, self).__init__(target=target, member=member, timeout=None)
        self.oc = oc
        self.format()

    def format(self):
        height = Size.Average.height_value(self.oc.size)
        info = Size.Average.height_info(height)
        self.manual_1.label, self.manual_2.label = info.split(" / ")

        current_category = self.oc.size_category

        self.category.options.clear()
        for item in SizeCategory:
            self.category.add_option(
                label=item.label_for(self.oc.age.scale),
                value=item.name,
                default=item == current_category,
                description=item.description,
            )

        self.choice.options.clear()
        middle = AMOUNT // 2
        minimum = current_category.minimum * self.oc.age.scale
        maximum = current_category.maximum * self.oc.age.scale
        ref = current_category.average * self.oc.age.scale
        for index, value in enumerate(np.linspace(maximum, minimum, AMOUNT)):
            if index == middle:
                emoji = "🟩"
            elif index < middle:
                emoji = "🟦"
            else:
                emoji = "🟧"

            label = Size.Average.height_info(value)
            info = Size.Average.height_info(1.65 * value / ref)
            self.choice.add_option(label=label, value=str(value), emoji=emoji, description=f"POV: {info}")

        return self

    @select(placeholder="Multiplier for Size", min_values=0, max_values=1)
    async def category(self, itx: Interaction, sct: Select):
        try:
            size_category = SizeCategory[sct.values[0]]
        except (KeyError, IndexError):
            size_category = SizeCategory.Average

        self.oc.size = size_category.average * self.oc.age.scale
        await itx.response.edit_message(view=self.format())

    @select(placeholder="Select a Size.", min_values=1, max_values=1)
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.size = round(float(sct.values[0]), 2)
        await self.delete(itx)

    @button(label="Meters", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = HeightModal1(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Feet & Inches", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = HeightModal2(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if btn.label and "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)
