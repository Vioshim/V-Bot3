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
from abc import ABCMeta, abstractmethod
from enum import Enum
from itertools import combinations
from logging import getLogger, setLoggerClass
from random import choice as random_choice
from random import sample
from typing import Iterable, Optional, Type

from discord import (
    ButtonStyle,
    Guild,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    NotFound,
    Object,
    PartialEmoji,
    TextStyle,
    Thread,
    User,
    Webhook,
)
from discord.abc import Messageable
from discord.ui import Button, Select, TextInput, button, select

from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability, SPAbilityModal
from src.structures.character import Character
from src.structures.logger import ColoredLogger
from src.structures.mon_typing import Typing
from src.structures.move import ALL_MOVES, Move
from src.structures.pronouns import Pronoun
from src.structures.species import Fakemon, Fusion, Species, Variant
from src.utils.functions import int_check
from src.views.image_view import ImageView
from src.views.movepool_view import MovepoolView

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

__all__ = ("Modification", "ModificationComplex")

DEFAULT_INFO_MSG = (
    "If you need to write too much, I recommend to move to Google documents, otherwise, try to be concise."
)


class SPView(Basic):
    def __init__(self, oc: Type[Character], member: User | Member, target: Interaction):
        super(SPView, self).__init__(target=target, member=member)
        self.oc = oc
        self.add.disabled = oc.sp_ability is not None
        self.modify.disabled = oc.sp_ability is None
        self.remove.disabled = oc.sp_ability is None

    @button(
        label="Add",
        custom_id="add",
        emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
        style=ButtonStyle.blurple,
    )
    async def add(self, ctx: Interaction, _: Button) -> None:
        """Method to add a special ability

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        modal = SPAbilityModal()
        await resp.send_modal(modal)
        await modal.wait()
        self.oc.sp_ability = modal.sp_ability
        backup = set(self.oc.abilities)
        if len(self.oc.abilities) > 1:
            view: Complex[Ability] = Complex(
                member=self.member,
                target=ctx,
                values=self.oc.abilities,
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
                editing_original=True,
            ) as items:
                if isinstance(items, set):
                    self.oc.abilities -= items
                else:
                    self.sp_ability = None
        self.stop()

    @button(
        label="Modify",
        custom_id="modify",
        emoji=PartialEmoji(name="emoteupdate", id=460539246508507157),
        style=ButtonStyle.blurple,
    )
    async def modify(self, ctx: Interaction, _: Button) -> None:
        """Method to modify a special ability

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        modal = SPAbilityModal(self.oc.sp_ability)
        await resp.send_modal(modal)
        await modal.wait()
        self.oc.sp_ability = modal.sp_ability
        self.stop()

    @button(
        label="Remove",
        custom_id="remove",
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
        style=ButtonStyle.blurple,
    )
    async def remove(self, ctx: Interaction, _: Button) -> None:
        """Method to delete a special ability

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        self.oc.sp_ability = None
        await resp.send_message("Special Ability removed.", ephemeral=True)
        self.stop()


class Mod(metaclass=ABCMeta):
    @property
    @abstractmethod
    def label(self) -> str:
        """Label to display"""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description to display"""

    @classmethod
    @abstractmethod
    def check(cls, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Member
            Member interacting

        Returns
        -------
        bool
            If it can be used or not
        """

    @classmethod
    @abstractmethod
    async def method(cls, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """
        This is the abstract method that gets applied
        in the current modifications.

        Parameters
        ----------
        oc : Type[Character]
            Character to modify
        member : Union[User, Member]
            User that interacts with the bot
        target : T
            Context

        Returns
        -------
        bool
            If it requires to update or not
        """


class NameMod(Mod):
    label: str = "Name"
    description: str = "Modify the OC's Name"

    @classmethod
    def check(cls, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Member | User
            User
        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    @classmethod
    async def method(cls, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(member=member, target=target)
        handler = text_view.handle(
            label="Write the character's Name.",
            placeholder="> oc.name",
            default=oc.name,
            origin=target,
            required=True,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = answer.title()
            return False


class AgeMod(Mod):
    label: str = "Age"
    description: str = "Modify the OC's Age"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(member=member, target=target)
        age = str(oc.age) if oc.age else "Unknown"
        handler = text_view.handle(
            label="Write the character's Age.",
            placeholder=f"> {age}",
            default=age,
            origin=target,
            required=True,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.age = int_check(answer, 13, 99)
            return False


class PronounMod(Mod):
    label: str = "Pronoun"
    description: str = "Modify the OC's Pronoun"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view: Complex[Pronoun] = Complex(
            member=member,
            target=target,
            timeout=None,
            values=Pronoun,
            parser=lambda x: (x.name, f"Sets Pronoun as {x.name}"),
            sort_key=lambda x: x.name,
            text_component=TextInput(
                label="Pronoun",
                placeholder="He | She | Them",
                default=oc.pronoun.name,
                min_length=2,
                max_length=4,
            ),
        )
        aux: Optional[bool] = None
        async with view.send(
            title="Write the character's Pronoun. Current below",
            description=f"> {oc.pronoun.name}",
            editing_original=True,
            single=True,
        ) as choice:
            if isinstance(choice, Pronoun):
                aux = choice != oc.pronoun
                oc.pronoun = choice
        return aux


class BackstoryMod(Mod):
    label: str = "Backstory"
    description: str = "Modify the OC's Backstory"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(member=member, target=target)
        backstory = oc.backstory[:4000] if oc.backstory else "No backstory was provided."
        handler = text_view.handle(
            label="Write the character's Backstory.",
            style=TextStyle.paragraph,
            default=backstory,
            origin=target,
            required=False,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
            return False


class ExtraMod(Mod):
    label: str = "Extra Information"
    description: str = "Modify the OC's Extra Information"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(member=member, target=target)
        extra = oc.extra[:4000] if oc.extra else "No Extra Information was provided."
        handler = text_view.handle(
            label="Write the character's Extra Information.",
            style=TextStyle.paragraph,
            default=extra,
            origin=target,
            required=False,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.extra = answer or None
            return False


class MovesetMod(Mod):
    label: str = "Moveset"
    description: str = "Modify the OC's Moveset"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        moves: set[Move] = set(oc.total_movepool() or ALL_MOVES.values())

        view: Complex[Move] = Complex(
            member=member,
            values=moves,
            timeout=None,
            target=target,
            max_values=min(len(moves), 6),
            text_component=TextInput(
                label="Moveset",
                style=TextStyle.paragraph,
                placeholder="Move, Move, Move, Move, Move, Move",
                default=", ".join(x.name for x in oc.moveset),
            ),
            emoji_parser=lambda x: x.type.emoji,
        )
        aux: Optional[bool] = None
        description = "\n".join(repr(move) for move in oc.moveset) or "No Moves"
        async with view.send(
            title="Write the character's moveset. Current below",
            description=description,
            editing_original=True,
        ) as choices:
            if isinstance(choices, set):
                oc.moveset = frozenset(choices)
        return aux


class AbilitiesMod(Mod):
    label: str = "Abilities"
    description: str = "Modify the OC's Abilities"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return len(oc.species.abilities) > 1

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """

        placeholder = ", ".join(["Ability"] * oc.max_amount_abilities)
        view: Complex[Ability] = Complex(
            member=member,
            values=oc.species.abilities or ALL_ABILITIES.values(),
            timeout=None,
            target=target,
            max_values=oc.max_amount_abilities,
            parser=lambda x: (x.name, x.description),
            text_component=TextInput(
                label="Ability",
                style=TextStyle.paragraph,
                placeholder=placeholder,
                default=", ".join(x.name for x in oc.abilities),
            ),
        )
        async with view.send(
            title="Select the abilities. Current ones below",
            fields=[
                dict(
                    name=f"Ability {index} - {item.name}",
                    value=item.description,
                    inline=False,
                )
                for index, item in enumerate(oc.abilities, start=1)
            ],
            editing_original=True,
        ) as choices:
            if isinstance(choices, set):
                oc.abilities = frozenset(choices)
            return False


class ImageMod(Mod):
    label: str = "Image"
    description: str = "Modify the OC's Image"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return True

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = ImageView(member=member, default_img=oc.image_url, target=target)
        async with view.send(editing_original=True) as text:
            if text and isinstance(text, str):
                if oc.image_url == text:
                    return False
                oc.image = text
                return True


class MovepoolMod(Mod):
    label: str = "Movepool"
    description: str = "Used to change Movepool"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines if it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return isinstance(
            oc.species,
            (
                Fakemon,
                Variant,
            ),
        )

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            Member
        target : Interaction
            Target

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = MovepoolView(target, member, oc)
        await view.send(editing_original=True)
        await view.wait()
        return False


class EvolutionMod(Mod):
    label: str = "Evolution"
    description: str = "Used to Evolve OCs"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return bool(oc.evolves_to)

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        values = oc.species.species_evolves_to
        view: Complex[Species] = Complex(
            member=member,
            values=values,
            timeout=None,
            target=target,
            parser=lambda x: (x.name, f"Evolve to {x.name}"),
            text_component=TextInput(
                label="Evolve to",
                style=TextStyle.paragraph,
                placeholder=" | ".join(x.name for x in set(values)),
                default=random_choice(values).name,
            ),
        )
        async with view.send(
            title="Select the Evolution",
            editing_original=True,
            single=True,
        ) as species:
            if not species:
                return

            oc.species = species

        if not oc.types and isinstance(species, Fusion):
            possible_types = species.possible_types
            view2: Complex[set[Typing]] = Complex(
                member=member,
                values=possible_types,
                timeout=None,
                target=target,
                parser=lambda x: (
                    "/".join(i.name for i in x).title(),
                    f"Sets the typing to {'/'.join(i.name for i in x).title()}",
                ),
                text_component=TextInput(
                    label="Fusion Typing",
                    placeholder=" | ".join("/".join(i.name for i in x).title() for x in possible_types),
                    default="/".join(i.name for i in random_choice(possible_types)).title(),
                ),
            )
            async with view2.send(
                title="Select the new typing",
                editing_original=True,
                single=True,
            ) as types:
                if not types:
                    return
                species.types = types

        placeholder = ", ".join(["Ability"] * oc.max_amount_abilities)
        if isinstance(species := oc.species, Variant):
            view: Complex[Typing] = Complex(
                member=member,
                target=target,
                values=Typing.all(),
                max_values=2,
                timeout=None,
                parser=lambda x: (
                    str(x),
                    f"Adds the typing {x}",
                ),
                text_component=TextInput(
                    label="Character's Types",
                    placeholder="Type, Type",
                    required=True,
                    default=", ".join(x.name for x in species.types),
                ),
            )
            async with view.send(
                title="Select Typing",
                description="Press the skip button in case you're going for single type.",
            ) as types:
                if not types:
                    return
                species.types = frozenset(types)
                species.movepool = species.base.movepool.copy()
            abilities: Iterable[Ability] = ALL_ABILITIES.values()
            default = ", ".join(x.name for x in species.abilities)
        else:
            abilities: Iterable[Ability] = species.abilities or ALL_ABILITIES.values()
            default = ", ".join(x.name for x in sample(abilities, k=oc.max_amount_abilities))
        view3: Complex[Ability] = Complex(
            member=member,
            values=abilities,
            timeout=None,
            target=target,
            max_values=oc.max_amount_abilities,
            parser=lambda x: (x.name, x.description),
            text_component=TextInput(
                label="Ability",
                style=TextStyle.paragraph,
                placeholder=placeholder,
                default=default,
            ),
        )
        async with view3.send(editing_original=True) as abilities:
            if isinstance(abilities, set):
                oc.abilities = frozenset(abilities)

        default_image: str = oc.default_image

        view4 = ImageView(member=member, default_img=default_image, target=target)
        async with view4.send(editing_original=True) as image:
            if isinstance(image, str):
                oc.image = image
            return True


class DevolutionMod(Mod):
    label: str = "Devolve"
    description: str = "Used to devolve OCs"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        if isinstance(species := oc.species, Fusion):
            return bool(species.total_species_evolves_from)
        return bool(species.evolves_from)

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        current = oc.species

        total: list[Species | Fusion] = []

        if isinstance(current, Fusion):
            total.extend(current.total_species_evolves_from)
        elif item := current.species_evolves_from:
            total.append(item)

        view = Complex(
            member=member,
            values=set(total),
            timeout=None,
            target=target,
            parser=lambda x: (x.name, f"Devolve to {x.name}"),
            text_component=TextInput(
                label="Devolving",
                style=TextStyle.paragraph,
                placeholder=" | ".join(x.name for x in set(total)),
                default=random_choice(total).name,
                required=True,
            ),
        )
        async with view.send(
            editing_original=True,
            title="Select the Devolution",
            single=True,
        ) as species:
            if not isinstance(species, Species):
                return

        if not species.types and isinstance(species, Fusion):
            possible_types = species.possible_types
            view = Complex(
                member=member,
                values=possible_types,
                timeout=None,
                target=target,
                parser=lambda x: (
                    "/".join(i.name for i in x).title(),
                    f"Sets the typing to {'/'.join(i.name for i in x).title()}",
                ),
                text_component=TextInput(
                    label="Fusion Typing",
                    placeholder=" | ".join("/".join(i.name for i in x).title() for x in possible_types),
                    default="/".join(i.name for i in random_choice(possible_types)).title(),
                ),
            )
            async with view.send(
                title="Select the Fusion's new typing",
                editing_original=True,
                single=True,
            ) as types:
                if not types:
                    return
                species.types = types

        if isinstance(oc.species, Variant):
            oc.species = Variant(base=species, name=species.name)
        else:
            oc.species = species

        oc.moveset &= set(species.total_movepool()) & set(current.total_movepool())

        default_image = oc.default_image

        view = ImageView(member=member, default_img=default_image, target=target)
        async with view.send(editing_original=True) as image:
            if image and isinstance(image, str):
                oc.image = image
            return True


class FusionEvolveMod(Mod):
    label: str = "Fuse Evolve"
    description: str = "Used to fuse within the evolution line."

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        if not isinstance(species := oc.species, Fusion):
            return bool(species.evolves_to)
        return False

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        items = [oc.species]
        items.extend(oc.species.species_evolves_to)
        values = [Fusion(mon1=i, mon2=j) for i, j in combinations(items, r=2)]
        view = Complex(
            member=member,
            values=set(values),
            timeout=None,
            target=target,
            parser=lambda x: (x.name, f"Evolve to {x.name}"),
            text_component=TextInput(
                label="Evolving",
                style=TextStyle.paragraph,
                placeholder=" | ".join(x.name for x in values),
                default=random_choice(values).name,
                required=True,
            ),
        )
        async with view.send(
            title="Select the Fused Evolution",
            single=True,
            editing_original=True,
        ) as species:
            if not isinstance(species, Fusion):
                return

        possible_types = species.possible_types
        view = Complex(
            member=member,
            values=set(possible_types),
            timeout=None,
            target=target,
            parser=lambda x: (
                "/".join(i.name for i in x).title(),
                f"Sets the typing to {'/'.join(i.name for i in x).title()}",
            ),
            text_component=TextInput(
                label="Fusion Typing",
                placeholder=" | ".join("/".join(i.name for i in x).title() for x in possible_types),
                default="/".join(i.name for i in random_choice(possible_types)).title(),
            ),
        )
        async with view.send(
            title="Select the Fusion's new typing",
            editing_original=True,
            single=True,
        ) as types:
            if not types:
                return
            species.types = types

        oc.species = species

        default_image: str = oc.default_image

        view = ImageView(
            member=member,
            default_img=default_image,
            target=target,
        )
        async with view.send(editing_original=True) as image:
            if image and isinstance(image, str):
                oc.image = image
            return True


class SpAbilityMod(Mod):
    label: str = "Special Ability"
    description: str = "Modify/Add the OC's Special Abilities"

    def check(self, oc: Type[Character], member: Member) -> bool:
        """Determines whetere it can be used or not by a character

        Parameters
        ----------
        oc : Type[Character]
            Character

        Returns
        -------
        bool
            If it can be used or not
        """
        return oc.can_have_special_abilities

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = SPView(oc=oc, member=member, target=target)
        view.embed.title = "Special Ability Management"
        await view.send(editing_original=True)
        await view.wait()
        return False


class Modification(Enum):
    """Enumeration of OC Modifications"""

    Name = NameMod()
    Age = AgeMod()
    Pronoun = PronounMod()
    Backstory = BackstoryMod()
    Extra = ExtraMod()
    Moveset = MovesetMod()
    Abilities = AbilitiesMod()
    Image = ImageMod()
    Movepool = MovepoolMod()
    Evolution = EvolutionMod()
    FusionEvolve = FusionEvolveMod()
    Devolution = DevolutionMod()
    SpAbility = SpAbilityMod()

    @property
    def label(self) -> str:
        value: Mod = self.value
        return value.label

    @property
    def description(self) -> str:
        value: Mod = self.value
        return value.description

    def check(self, oc: Type[Character], member: Member) -> bool:
        value: Mod = self.value
        return value.check(oc=oc, member=member)

    async def method(self, oc: Type[Character], member: User | Member, target: Interaction) -> Optional[bool]:
        """Modifications for the given context

        Parameters
        ----------
        oc : Type[Character]
            Character to modify
        member : Union[User, Member]
            User interacting
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool if updatable, None if cancelled.
        """
        value: Mod = self.value
        return await value.method(oc, member, target)

    @classmethod
    async def process(cls, oc: Type[Character], member: User | Member, target: Interaction, params: list[str]):
        for item in map(lambda x: Modification[x], params):
            value = await item.method(oc=oc, member=member, target=target)
            yield item.name, value


class ModificationComplex(Complex[str]):
    def __init__(self, *, oc: Character, member: Member | User, target: Optional[Messageable] = None):
        self.oc = oc
        values = {x.name: (x.label, x.description) for x in Modification if x.check(oc=oc, member=member)}
        super(ModificationComplex, self).__init__(
            member=member,
            values=list(values.keys()),
            parser=lambda x: values[x],
            target=target,
            timeout=None,
            emoji_parser=PartialEmoji(name="list", id=432986579007569922),
            silent_mode=True,
        )

    @select(row=1, placeholder="Select Fields to Edit", custom_id="selector")
    async def select_choice(self, ctx: Interaction, sct: Select) -> None:
        resp: InteractionResponse = ctx.response
        await resp.edit_message(view=None)
        modifying: bool = False
        async for name, result in Modification.process(
            oc=self.oc,
            member=ctx.user,
            target=ctx,
            params=self.current_choices,
        ):
            if isinstance(result, bool):
                logger.info(
                    "Field %s, modified by %s to Character(%s) aka %s",
                    name,
                    str(ctx.user),
                    repr(self.oc),
                    self.oc.name,
                )
                modifying |= result
            elif result is None:
                logger.info(
                    "At %s, %s cancelled modifications to Character(%s) aka %s",
                    name,
                    str(ctx.user),
                    repr(self.oc),
                    self.oc.name,
                )
                break
        webhook: Webhook = await ctx.client.webhook(919277769735680050)
        guild: Guild = webhook.guild
        embed = self.oc.embed
        embed.set_image(url="attachment://image.png")
        kwargs = dict(embed=embed, thread=Object(id=self.oc.thread))
        if modifying and (file := await ctx.client.get_file(self.oc.generated_image)):
            kwargs["attachments"] = [file]
        msg = None
        try:
            try:
                msg = await webhook.edit_message(self.oc.id, **kwargs)
            except HTTPException:
                if not (thread := guild.get_thread(self.oc.thread)):
                    thread: Thread = await ctx.client.fetch_channel(self.oc.thread)
                await thread.edit(archived=False)
                msg = await webhook.edit_message(self.oc.id, **kwargs)
        except NotFound:
            cog = ctx.client.get_cog("Submission")
            await cog.registration(ctx=ctx, oc=self.oc, worker=ctx.user)
        finally:
            if msg:
                self.oc.image_url = msg.embeds[0].image.url
                async with ctx.client.database() as db:
                    await self.oc.update(db)
            self.embed = self.oc.embed
            self.modifying_embed = True
        super(ModificationComplex, self).select_choice(ctx, sct)

    @button(
        label="Don't make any changes",
        style=ButtonStyle.blurple,
        emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
        row=4,
    )
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.edit_message(content="Alright, no changes.", view=None)
        return self.stop()

    @button(
        label="Delete Character",
        style=ButtonStyle.red,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
        row=4,
    )
    async def delete_oc(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        webhook: Webhook = await ctx.client.webhook(919277769735680050)
        guild: Guild = webhook.guild
        try:
            try:
                await webhook.delete_message(
                    self.oc.id,
                    thread=Object(id=self.oc.thread),
                )
            except HTTPException:
                if not (thread := guild.get_thread(self.oc.thread)):
                    thread: Thread = await guild.fetch_channel(self.oc.thread)
                await thread.edit(archived=False)
                await webhook.delete_message(self.oc.id, thread=thread)
        except NotFound:
            cog = ctx.client.get_cog("Submission")
            cog.ocs.pop(self.oc.id, None)
            async with ctx.client.database() as db:
                logger.info(
                    "Character Removed as message was removed! > %s - %s > %s",
                    self.oc.name,
                    repr(self.oc),
                    self.oc.document_url or "None",
                )
                await self.oc.delete(db)
        finally:
            await resp.edit_message(content="Character Has been Deleted", view=None)
            self.stop()
