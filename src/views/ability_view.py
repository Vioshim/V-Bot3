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
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
    SelectOption,
    TextChannel,
    TextStyle,
    Webhook,
)
from discord.ui import Modal, Select, TextInput, select

from src.pagination.complex import Complex
from src.pagination.view_base import Basic
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
            default=sp_ability.name[:100],
        )
        self.description = TextInput(
            label="Description",
            placeholder="Describe how it works",
            max_length=1024,
            style=TextStyle.paragraph,
            default=sp_ability.description[:1024],
        )
        self.origin = TextInput(
            label="Origin",
            placeholder="Explain the story of how your oc obtained this",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.origin[:600],
        )
        self.pros = TextInput(
            label="Pros",
            placeholder="How it makes your oc's life easier?",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.pros[:600],
        )
        self.cons = TextInput(
            label="Cons",
            placeholder="How it makes your oc's life harder?",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.cons[:600],
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
        if not self.sp_ability.valid:
            self.sp_ability = None
        await resp.edit_message(view=None)
        self.stop()


class SPAbilityView(Basic):
    def __init__(self, target: Interaction, member: Member, oc: Character):
        super(SPAbilityView, self).__init__(target=target, member=member, timeout=None)
        self.embed.title = "Special Ability Settings"
        self.sp_ability: Optional[SpAbility] = None
        self.member = member
        self.oc = oc

    @select(
        placeholder="Available Options",
        options=[
            SelectOption(
                label="Add Sp. Ability",
                value="add",
                description="Provide Sp. Ability (Name, Desc, Origin, Pros, Cons)",
                emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
            ),
            SelectOption(
                label="No Sp. Ability",
                value="remove",
                description="Removes Sp. Ability",
                emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
            ),
            SelectOption(
                label="Keep as is",
                value="default",
                description="Skip this process",
                emoji=PartialEmoji(name="emoteupdate", id=460539246508507157),
            ),
        ],
    )
    async def setting(self, ctx: Interaction, sct: Select):
        match sct.values[0]:
            case "add":
                await self.confirm(ctx)
            case "remove":
                await self.deny(ctx)
            case "default":
                await self.cancel(ctx)
        await self.delete(ctx)

    async def confirm(self, ctx: Interaction):
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

        if sp_ability and sp_ability.valid:
            self.sp_ability = sp_ability

    async def deny(self, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        self.sp_ability = None
        self.embed.description = "Alright, no Sp Ability"
        await resp.edit_message(embed=self.embed, view=None)

    async def cancel(self, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        self.sp_ability = SpAbility()
        self.embed.description = "Process concluded"
        await resp.edit_message(embed=self.embed, view=None)
