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
from random import sample
from typing import Optional, Union

from discord import (
    ButtonStyle,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
    TextChannel,
    TextStyle,
    Webhook,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select

from src.pagination.complex import Complex
from src.structures.ability import Ability, SpAbility
from src.structures.character import Character

__all__ = ("AbilityView", "SPAbilityModal", "SPAbilityView")


def ability_emoji_parser(x: Ability | SpAbility) -> Optional[str]:
    if isinstance(x, Ability):
        return "\N{LARGE BLUE CIRCLE}"
    if isinstance(x, SpAbility):
        return "\N{LARGE GREEN CIRCLE}"


class AbilityView(Complex[Ability | SpAbility]):
    def __init__(
        self,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        abilities: set[Ability | SpAbility],
        keep_working: bool = False,
        max_values: int = 1,
    ):
        placeholder = ", ".join(["Ability"] * max_values)
        default = ", ".join(x.name for x in sample(abilities, 2))
        super(AbilityView, self).__init__(
            member=member,
            target=target,
            values=abilities,
            timeout=None,
            parser=lambda x: (x.name, x.description),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
            emoji_parser=ability_emoji_parser,
            max_values=max_values,
            text_component=TextInput(
                label="Ability",
                style=TextStyle.paragraph,
                placeholder=placeholder,
                default=default,
            ),
        )
        self.embed.title = "Select an Ability"

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        response: InteractionResponse = interaction.response
        item: Ability | SpAbility = self.current_choice
        await response.send_message(embed=item.embed, ephemeral=True)
        await super(AbilityView, self).select_choice(interaction, sct)


class SPAbilityModal(Modal):
    def __init__(self, sp_ability: SpAbility = None) -> None:
        super(SPAbilityModal, self).__init__(title="Special Ability", timeout=None)
        if not sp_ability:
            sp_ability = SpAbility()
        self.sp_ability = sp_ability
        self.name = TextInput(
            label="Name",
            placeholder="How your OC refers to it?",
            max_length=100,
            default=sp_ability.name,
        )
        self.description = TextInput(
            label="Description",
            placeholder="Describe how it works",
            style=TextStyle.paragraph,
            default=sp_ability.description,
        )
        self.origin = TextInput(
            label="Origin",
            placeholder="Explain the story of how your oc obtained this",
            style=TextStyle.paragraph,
            default=sp_ability.origin,
        )
        self.pros = TextInput(
            label="Pros",
            placeholder="How it makes your oc's life easier?",
            style=TextStyle.paragraph,
            default=sp_ability.pros,
        )
        self.cons = TextInput(
            label="Cons",
            placeholder="How it makes your oc's life harder?",
            style=TextStyle.paragraph,
            default=sp_ability.cons,
        )
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.origin)
        self.add_item(self.pros)
        self.add_item(self.cons)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        self.sp_ability = SpAbility(
            name=self.name.value,
            description=self.description.value,
            origin=self.origin.value,
            pros=self.pros.value,
            cons=self.cons.value,
        )
        if self.sp_ability == SpAbility():
            self.sp_ability = None
        await resp.send_message("Special ability added/modified", ephemeral=True)
        self.stop()


class SPAbilityView(View):
    def __init__(self, member: Member, oc: Character):
        super(SPAbilityView, self).__init__(timeout=None)
        self.sp_ability: Optional[SpAbility] = None
        self.member = member
        self.oc = oc

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user == self.member

    @button(
        label="Add Sp. Ability",
        style=ButtonStyle.blurple,
        emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
    )
    async def confirm(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        modal = SPAbilityModal(self.sp_ability)
        await resp.send_modal(modal)
        await modal.wait()

        sp_ability = modal.sp_ability
        backup: set[Ability] = set(self.oc.abilities)

        if len(self.oc.abilities) > 1:
            view = Complex[Ability](
                member=self.member,
                target=ctx,
                values=backup,
                timeout=None,
                parser=lambda x: (x.name, x.description),
                silent_mode=True,
            )
            async with view.send(
                title="Select an Ability to Remove.",
                fields=[
                    dict(
                        name=f"Ability {index} - {item.name}",
                        value=item.description,
                        inline=False,
                    )
                    for index, item in enumerate(backup, start=1)
                ],
            ) as items:
                if isinstance(items, set):
                    self.oc.abilities -= items
                else:
                    sp_ability = None

        self.sp_ability = sp_ability
        self.stop()

    @button(
        label="No Sp. Ability",
        style=ButtonStyle.blurple,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
    )
    async def deny(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.edit_message(content="Alright, no Sp Ability", view=None)
        self.sp_ability = None
        self.stop()

    @button(
        label="Cancel",
        style=ButtonStyle.red,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
    )
    async def cancel(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        self.sp_ability = SpAbility()
        await resp.edit_message(content="Process concluded", view=None)
        self.stop()
