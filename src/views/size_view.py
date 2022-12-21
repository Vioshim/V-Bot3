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


from contextlib import suppress

from discord import ButtonStyle, Interaction, Member
from discord.ui import Button, Modal, Select, TextInput, button, select
from discord.utils import find

from src.pagination.view_base import Basic
from src.structures.character import Character, Size

__all__ = (
    "HeightView",
    "WeightView",
)


class HeightModal1(Modal, title="Height"):
    def __init__(self, oc: Character, info: str) -> None:
        super().__init__(title="Height", timeout=None)
        self.text = TextInput(label="Meters", placeholder=info, default=info)
        self.add_item(self.text)
        self.oc = oc

    async def on_submit(self, interaction: Interaction, /) -> None:
        a = Size.XXXS.height_value(self.oc.species.height)
        b = Size.XXXL.height_value(self.oc.species.height)

        text = self.text.value.removesuffix(".").lower()

        if "cm" in text:
            ratio, text = 0.01, text.removesuffix("cm")
        else:
            ratio, text = 1, text.removesuffix("m")

        with suppress(ValueError):
            answer = round(ratio * float(text.strip()), 2)
            if answer <= a:
                answer = Size.XXXS
            elif answer >= b:
                answer = Size.XXXL
            elif item := find(lambda x: x.height_value(self.oc.species.height) == answer, Size):
                answer = item
            self.oc.size = answer

        if isinstance(self.oc.size, Size):
            info = self.oc.size.height_info(self.oc.species.height)
        else:
            info = Size.M.height_info(self.oc.size)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class HeightModal2(Modal, title="Height"):
    def __init__(self, oc: Character, info: str) -> None:
        super().__init__(title="Height", timeout=None)
        info = info.removesuffix('" ft')
        ft_info, in_info = info.split("' ")

        self.text1 = TextInput(label="Feet", placeholder=ft_info, default=ft_info, required=False)
        self.text2 = TextInput(label="Inches", placeholder=in_info, default=in_info, required=False)

        self.add_item(self.text1)
        self.add_item(self.text2)
        self.oc = oc

    async def on_submit(self, interaction: Interaction, /) -> None:
        a = Size.XXXS.height_value(self.oc.species.height)
        b = Size.XXXL.height_value(self.oc.species.height)

        with suppress(ValueError):
            answer = Size.ft_inches_to_meters(
                feet=float(self.text1.value or "0"),
                inches=float(self.text2.value or "0"),
            )
            answer = round(answer, 2)
            if answer <= a:
                answer = Size.XXXS
            elif answer >= b:
                answer = Size.XXXL
            elif item := find(lambda x: x.height_value(self.oc.species.height) == answer, Size):
                answer = item
            self.oc.size = answer

        if isinstance(self.oc.size, Size):
            info = self.oc.size.height_info(self.oc.species.height)
        else:
            info = Size.M.height_info(self.oc.size)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class WeightModal1(Modal, title="Weight"):
    def __init__(self, oc: Character, info: str) -> None:
        super().__init__(title="Weight", timeout=None)
        self.text = TextInput(label="kg", placeholder=info, default=info)
        self.add_item(self.text)
        self.oc = oc

    async def on_submit(self, interaction: Interaction, /) -> None:
        a = Size.XXXS.weight_value(self.oc.species.weight)
        b = Size.XXXL.weight_value(self.oc.species.weight)

        text = self.text.value.lower().removesuffix(".")
        text = text.removesuffix("kg")

        with suppress(ValueError):
            answer = round(float(text.strip()), 2)
            if answer <= a:
                answer = Size.XXXS
            elif answer >= b:
                answer = Size.XXXL
            elif item := find(lambda x: x.weight_value(self.oc.species.weight) == answer, Size):
                answer = item
            self.oc.weight = answer

        if isinstance(self.oc.weight, Size):
            info = self.oc.weight.weight_info(self.oc.species.weight)
        else:
            info = Size.M.weight_info(self.oc.weight)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class WeightModal2(Modal, title="Weight"):
    def __init__(self, oc: Character, info: str) -> None:
        super().__init__(title="Weight", timeout=None)
        self.text = TextInput(label="lbs", placeholder=info, default=info)
        self.add_item(self.text)
        self.oc = oc

    async def on_submit(self, interaction: Interaction, /) -> None:
        a = Size.XXXS.weight_value(self.oc.species.weight)
        b = Size.XXXL.weight_value(self.oc.species.weight)

        text = self.text.value.lower().removesuffix(".")
        text = text.removesuffix("lbs").removesuffix("lb")

        with suppress(ValueError):
            answer = round(Size.lbs_to_kgs(float(text.strip())), 2)
            if answer <= a:
                answer = Size.XXXS
            elif answer >= b:
                answer = Size.XXXL
            elif item := find(lambda x: x.weight_value(self.oc.species.weight) == answer, Size):
                answer = item
            self.oc.weight = answer

        if isinstance(self.oc.weight, Size):
            info = self.oc.weight.weight_info(self.oc.species.weight)
        else:
            info = Size.M.weight_info(self.oc.weight)

        await interaction.response.send_message(info, ephemeral=True, delete_after=3)
        self.stop()


class HeightView(Basic):
    def __init__(self, *, target: Interaction, member: Member, oc: Character):
        super().__init__(target=target, member=member, timeout=None)
        self.choice.options.clear()
        self.oc = oc

        if isinstance(oc.size, Size):
            info = oc.size.height_info(oc.species.height)
        else:
            info = Size.M.height_info(oc.size)

        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"
        for item in items:
            self.choice.add_option(
                label=item.height_info(oc.species.height),
                value=item.name,
                description={Size.M: "Default"}.get(item),
                default=item == oc.size,
            )

    @select(placeholder="Single Choice.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.size = Size[sct.values[0]]
        await self.delete(itx)

    @button(label="Meters", style=ButtonStyle.blurple)
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = HeightModal1(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Feet & Inches", style=ButtonStyle.blurple)
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = HeightModal2(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)


class WeightView(Basic):
    def __init__(self, *, target: Interaction, member: Member, oc: Character):
        super().__init__(target=target, member=member, timeout=None)
        self.choice.options.clear()
        self.oc = oc

        if isinstance(oc.weight, Size):
            info = oc.weight.weight_info(oc.species.weight)
        else:
            info = Size.M.weight_info(oc.weight)

        self.manual_1.label, self.manual_2.label = info.split(" / ")

        items = sorted(Size, key=lambda x: x.value, reverse=True)
        self.choice.placeholder = f"Single Choice. Options: {len(items)}"
        for item in items:
            self.choice.add_option(
                label=item.weight_info(oc.species.weight),
                value=item.name,
                description={Size.M: "Default"}.get(item),
                default=item == oc.weight,
            )

    @select(placeholder="Single Choice.")
    async def choice(self, itx: Interaction, sct: Select):
        self.oc.weight = Size[sct.values[0]]
        await self.delete(itx)

    @button(label="Kg", style=ButtonStyle.blurple)
    async def manual_1(self, itx: Interaction, btn: Button):
        modal = WeightModal1(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Lbs", style=ButtonStyle.blurple)
    async def manual_2(self, itx: Interaction, btn: Button):
        modal = WeightModal2(oc=self.oc, info=btn.label)
        await itx.response.send_modal(modal)
        await modal.wait()
        await self.delete(itx)

    @button(label="Close", style=ButtonStyle.gray)
    async def finish(self, itx: Interaction, btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)
