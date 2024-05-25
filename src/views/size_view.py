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

from discord import ButtonStyle, Interaction, Member
from discord.ui import Button, Modal, Select, TextInput, button, select
from discord.utils import find

from src.pagination.view_base import Basic
from src.structures.character import Character, Size
from src.structures.move import Move
from src.structures.species import Fusion

__all__ = (
    "HeightView",
    "WeightView",
)


class HeightModal(Modal, title="Height"):
    def __init__(self, oc: Character) -> None:
        super(HeightModal, self).__init__(title="Height", timeout=None)
        self.oc = oc

    @property
    def value(self) -> float:
        return 0

    async def on_submit(self, interaction: Interaction, /) -> None:
        m = Move.get(name="Transform")
        height: float = getattr(self.oc.species, "height", 0)

        if m and m in self.oc.total_movepool:
            height_a, height_b = 0.1, 20
        elif isinstance(self.oc.species, Fusion):
            s_a, *_, s_b = sorted(self.oc.species.bases, key=lambda x: x.height)
            height_a, height_b = s_a.height, s_b.height
        else:
            height_a = height_b = height

        a = Size.XXXS.height_value(height_a)
        b = Size.XXXL.height_value(height_b)

        answer = self.value

        if answer == a:
            answer = Size.XXXS
        elif answer == b:
            answer = Size.XXXL
        elif answer < a:
            answer = height_a
        elif answer > b:
            answer = height_b
        elif item := find(lambda x: round(x.height_value(height), 2) == answer, Size):
            answer = item

        self.oc.size = Size.M if answer <= 0 else answer

        if isinstance(self.oc.size, Size):
            info = self.oc.size.height_info(height)
        else:
            info = Size.M.height_info(self.oc.size)

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
        ft_info, in_info = info.split("' ")

        self.text1 = TextInput(label="Feet", placeholder=ft_info, default=ft_info, required=False)
        self.text2 = TextInput(label="Inches", placeholder=in_info, default=in_info, required=False)

        self.add_item(self.text1)
        self.add_item(self.text2)

    @property
    def value(self) -> float:
        try:
            answer = Size.ft_inches_to_meters(
                feet=float(self.text1.value or "0"),
                inches=float(self.text2.value or "0"),
            )
            return round(answer, 2)
        except ValueError:
            return 0


class WeightModal(Modal, title="Weight"):
    def __init__(self, oc: Character, info: Optional[str] = None) -> None:
        super(WeightModal, self).__init__(title="Weight", timeout=None)
        self.oc = oc

    @property
    def value(self) -> float:
        return 0

    async def on_submit(self, interaction: Interaction, /) -> None:
        m = Move.get(name="Transform")
        weight: float = getattr(self.oc.species, "weight", 0)

        if m and m in self.oc.total_movepool:
            weight_a, weight_b = 0.1, 999.9
        elif isinstance(self.oc.species, Fusion):
            s_a, *_, s_b = sorted(self.oc.species.bases, key=lambda x: x.weight)
            weight_a, weight_b = s_a.weight, s_b.weight
        else:
            weight_a = weight_b = weight

        a = Size.XXXS.weight_value(weight_a)
        b = Size.XXXL.weight_value(weight_b)

        answer = self.value

        if answer == a:
            answer = Size.XXXS
        elif answer == b:
            answer = Size.XXXL
        elif answer < a:
            answer = weight_a
        elif answer > b:
            answer = weight_b
        elif item := find(lambda x: round(x.weight_value(weight), 2) == answer, Size):
            answer = item

        self.oc.weight = Size.M if answer <= 0 else answer

        if isinstance(self.oc.weight, Size):
            info = self.oc.weight.weight_info(weight)
        else:
            info = Size.M.weight_info(self.oc.weight)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class WeightModal1(WeightModal):
    def __init__(self, oc: Character, info: Optional[str] = None) -> None:
        super(WeightModal1, self).__init__(oc=oc)
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
    def __init__(self, oc: Character, info: Optional[str] = None) -> None:
        super(WeightModal2, self).__init__(oc=oc)
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
    def __init__(self, *, target: Interaction, member: Member, oc: Character):
        super(HeightView, self).__init__(target=target, member=member, timeout=None)
        self.choice.options.clear()
        self.oc = oc

        height = oc.species.height if oc.species else 0
        if isinstance(oc.size, Size):
            info = oc.size.height_info(height)
        else:
            info = Size.M.height_info(oc.size)

        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"
        for item in items:
            self.choice.add_option(
                label=item.height_info(height),
                value=item.name,
                description=item.reference_name,
                default=item == oc.size,
                emoji=item.emoji,
            )

    @select(placeholder="Single Choice.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.size = Size[sct.values[0]]
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


class WeightView(Basic):
    def __init__(self, *, target: Interaction, member: Member, oc: Character):
        super(WeightView, self).__init__(target=target, member=member, timeout=None)
        self.choice.options.clear()
        self.oc = oc

        weight = oc.species.weight if oc.species else 0
        if isinstance(oc.weight, Size):
            info = oc.weight.weight_info(weight)
        else:
            info = Size.M.weight_info(oc.weight)

        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"
        for item in items:
            self.choice.add_option(
                label=item.weight_info(weight),
                value=item.name,
                description=item.reference_name,
                default=item == oc.weight,
                emoji=item.emoji,
            )

    @select(placeholder="Single Choice.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.weight = Size[sct.values[0]]
        await self.delete(itx)

    @button(label="Kg", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = WeightModal1(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Lbs", style=ButtonStyle.blurple, emoji="\N{PENCIL}")
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = WeightModal2(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if btn.label and "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)
