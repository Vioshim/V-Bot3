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


from typing import Optional, Union

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    TextChannel,
    TextStyle,
    Webhook,
)
from discord.ui import Button, Modal, Select, TextInput, button, select

from src.pagination.complex import Complex
from src.pagination.view_base import Basic
from src.structures.ability import Ability, SpAbility, UTraitKind
from src.structures.character import Character
from src.utils.etc import EMOTE_CREATE_EMOJI, EMOTE_REMOVE_EMOJI, EMOTE_UPDATE_EMOJI

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
            text_component=TextInput(label="Ability", placeholder=", ".join(["Ability"] * max_values)),
        )
        self.embed.title = "Select an Ability"

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        response: InteractionResponse = interaction.response
        item: Ability | SpAbility = self.current_choice
        await response.send_message(embed=item.embed, ephemeral=True)
        await super(AbilityView, self).select_choice(interaction, sct)


class SPAbilityModal(Modal):
    def __init__(self, sp_ability: SpAbility) -> None:
        super(SPAbilityModal, self).__init__(title=f"Unique Trait - {sp_ability.kind.title}", timeout=None)
        self.sp_ability = sp_ability
        self.name = TextInput(
            label="How your OC refers to it?",
            max_length=100,
            default=sp_ability.name[:100],
            required=False,
        )
        self.description = TextInput(
            label="Describe how it works",
            max_length=1024,
            style=TextStyle.paragraph,
            default=sp_ability.description[:1024],
            required=False,
        )
        self.origin = TextInput(
            label="How your oc obtained this?",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.origin[:600],
            required=False,
        )
        self.pros = TextInput(
            label="How it makes your oc's life easier?",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.pros[:600],
            required=False,
        )
        self.cons = TextInput(
            label="How it makes your oc's life harder?",
            max_length=600,
            style=TextStyle.paragraph,
            default=sp_ability.cons[:600],
            required=False,
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
            kind=self.sp_ability.kind,
        )
        if not self.sp_ability.valid:
            self.sp_ability = None
        await resp.edit_message(view=None)
        self.stop()


class SPAbilityView(Basic):
    def __init__(self, target: Interaction, member: Member, oc: Character):
        super(SPAbilityView, self).__init__(target=target, member=member, timeout=None)
        self.embed.title = "Unique Trait Settings"
        self.embed.description = "Unique powers are something that most people have, they don't necessarily have to use pros and cons, they are just traits, but the field is optional if needed."
        self.sp_ability: SpAbility = oc.sp_ability or SpAbility()
        for x in self.setting.options:
            x.default = x.value == self.sp_ability.kind.name
        self.member = member
        self.oc = oc

    @select(
        placeholder="Unique Trait Kinds",
        options=[
            SelectOption(
                label=x.title,
                value=x.name,
                description=x.desc,
                emoji=x.emoji,
            )
            for x in sorted(UTraitKind, key=lambda x: x.name)
        ],
    )
    async def setting(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        kind = UTraitKind[sct.values[0]]
        if self.sp_ability is None:
            self.sp_ability = SpAbility()
        self.sp_ability.kind = kind
        sct.options.clear()
        for x in sorted(UTraitKind, key=lambda x: x.name):
            sct.add_option(
                label=x.title,
                value=x.name,
                description=x.desc,
                default=x == kind,
                emoji=x.emoji,
            )
        await resp.edit_message(view=self)

    @button(label="Modify", emoji=EMOTE_CREATE_EMOJI, custom_id="modify")
    async def confirm(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        modal = SPAbilityModal(self.sp_ability)
        await resp.send_modal(modal)
        await modal.wait()
        sp_ability = modal.sp_ability
        if sp_ability and sp_ability.valid:
            self.sp_ability = sp_ability
        await self.delete(ctx)

    @button(label="Remove", emoji=EMOTE_REMOVE_EMOJI, custom_id="remove")
    async def deny(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        self.sp_ability.clear()
        self.embed.description = "Alright, no Unique Trait"
        await resp.edit_message(embed=self.embed, view=None)
        await self.delete(ctx)

    @button(label="Keep as is", emoji=EMOTE_UPDATE_EMOJI, custom_id="default")
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        self.embed.description = "Process concluded"
        await resp.edit_message(embed=self.embed, view=None)
        await self.delete(ctx)
