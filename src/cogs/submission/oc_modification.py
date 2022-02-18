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
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional, Type, Union

from discord import (
    ButtonStyle,
    DiscordException,
    InputTextStyle,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    Thread,
    User,
)
from discord.ui import Button, InputText, Select, View, button, select

from src.pagination.complex import Complex, ComplexInput
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, SpAbility
from src.structures.bot import CustomBot
from src.structures.character import (
    Character,
    FakemonCharacter,
    VariantCharacter,
)
from src.structures.move import ALL_MOVES
from src.structures.pronouns import Pronoun
from src.structures.species import Fusion
from src.utils.functions import int_check
from src.views import ImageView, MovepoolView

__all__ = ("Modification", "ModifyView")

DEFAULT_INFO_MSG = "If you need to write too much, I recommend to move to Google documents, otherwise, try to be concise."


class SPView(Basic):
    def __init__(
        self,
        bot: CustomBot,
        oc: Type[Character],
        member: Union[Member, User],
        target: Interaction,
    ):
        super(SPView, self).__init__(
            bot=bot,
            target=target,
            member=member,
            timeout=None,
        )
        self.oc = oc
        self.used: bool = False
        self.add.disabled = oc.sp_ability is not None
        self.modify.disabled = oc.sp_ability is None
        self.delete.disabled = oc.sp_ability is None

    async def interaction_check(self, interaction: Interaction) -> bool:
        check = await super(SPView, self).interaction_check(interaction)
        resp: InteractionResponse = interaction.response
        if not check:
            return False
        if self.used:
            await resp.send_message(
                "You're already using one of the options.",
                ephemeral=True,
            )
            return False
        self.used = True
        return True

    @button(label="Add", custom_id="add")
    async def add(self, _: Button, ctx: Interaction) -> None:
        """Method to add a special ability

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        backup = set(self.oc.abilities)
        if len(self.oc.abilities) > 1:
            view = ComplexInput(
                bot=self.bot,
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
            ) as items:
                if isinstance(items, set):
                    self.oc.abilities -= items
                    backup = set(self.oc.abilities)
                else:
                    return self.stop()

        else:
            await resp.send_message("Proceeding", ephemeral=True)

        message = await ctx.original_message()

        text_view = ModernInput(
            bot=self.bot,
            input_text=InputText(
                placeholder=DEFAULT_INFO_MSG,
                required=True,
            ),
            member=self.member,
            target=ctx,
        )

        data: dict[str, str] = {}

        for item in SpAbility.__slots__:
            if item == "name":
                item_style = InputTextStyle.short
            else:
                item_style = InputTextStyle.long
            title = f"Write the Special Ability's {item.title()}"
            async with text_view.handle(
                placeholder=DEFAULT_INFO_MSG,
                style=item_style,
                label=title,
                origin=message,
            ) as answer:
                data[item] = answer
                if not isinstance(answer, str):
                    break
        else:
            self.oc.sp_ability = SpAbility(**data)

        self.oc.abilities = frozenset(backup)
        return self.stop()

    @button(label="Modify", custom_id="modify")
    async def modify(self, _: Button, ctx: Interaction) -> None:
        """Method to modify a special ability

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            Interaction
        """
        view = Complex(
            bot=self.bot,
            member=self.member,
            values=list(SpAbility.__slots__),
            target=ctx,
            timeout=None,
            parser=lambda x: (
                str(x).title(),
                f"Modify Sp. Ability's {x}".title(),
            ),
            silent_mode=True,
        )

        async with view.send(
            title="Sp.Ability Modify", ephemeral=True
        ) as elements:
            if not isinstance(elements, set):
                return self.stop()

            text_view = ModernInput(
                bot=self.bot,
                member=self.member,
                target=ctx,
            )
            backup = asdict(self.oc.sp_ability)

            msg = await ctx.original_message()

            for item in SpAbility.__slots__:
                if item not in elements:
                    continue
                if item == "name":
                    item_style = InputTextStyle.short
                else:
                    item_style = InputTextStyle.long
                title = f"Special Ability's {item}".title()
                value: str = backup.get(item)
                async with text_view.handle(
                    label=title,
                    style=item_style,
                    placeholder=DEFAULT_INFO_MSG,
                    value=value,
                    origin=msg,
                    required=True,
                ) as answer:
                    if not (answer and isinstance(answer, str)):
                        break
                    backup[item] = answer

            else:
                self.oc.sp_ability = SpAbility(**backup)

        self.stop()

    @button(label="Remove", custom_id="remove")
    async def delete(self, _: Button, ctx: Interaction) -> None:
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


@dataclass(unsafe_hash=True, slots=True)
class Mod(metaclass=ABCMeta):
    label: str = ""
    description: str = ""

    @abstractmethod
    def check(self, oc: Type[Character]) -> bool:
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

    @abstractmethod
    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """
        This is the abstract method that gets applied
        in the current modifications.

        Parameters
        ----------
        oc : Type[Character]
            Character to modify
        bot : CustomBot
            Bot instance
        member : Union[User, Member]
            User that interacts with the bot
        target : T
            Context

        Returns
        -------
        bool
            If it requires to update or not
        """


@dataclass(unsafe_hash=True, slots=True)
class NameMod(Mod):
    label: str = "Name"
    description: str = "Modify the OC's Name"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(bot=bot, member=member, target=target)
        handler = text_view.handle(
            label="Write the character's Name.",
            placeholder="> oc.name",
            value=oc.name,
            origin=target,
            required=True,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = answer.title()
                return False


@dataclass(unsafe_hash=True, slots=True)
class AgeMod(Mod):
    label: str = "Age"
    description: str = "Modify the OC's Age"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(bot=bot, member=member, target=target)
        age = str(oc.age) if oc.age else "Unknown"
        handler = text_view.handle(
            label="Write the character's Age.",
            placeholder=f"> {age}",
            value=age,
            origin=target,
            required=True,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.age = int_check(answer, 13, 99)
                return False


@dataclass(unsafe_hash=True, slots=True)
class PronounMod(Mod):
    label: str = "Pronoun"
    description: str = "Modify the OC's Pronoun"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = Complex(
            bot=bot,
            member=member,
            target=target,
            timeout=None,
            values=Pronoun,
            parser=lambda x: (x.name, f"Sets Pronoun as {x.name}"),
            sort_key=lambda x: x.name,
        )
        aux: Optional[bool] = None
        origin = await target.original_message()
        view.embed.title = "Write the character's Pronoun. Current below"
        view.embed.description = f"> {oc.pronoun.name}"
        await origin.edit(embed=view.embed, view=view)
        await view.wait()
        if isinstance(item := view.choice, Pronoun):
            aux = item != oc.pronoun
            oc.pronoun = item
        return aux


@dataclass(unsafe_hash=True, slots=True)
class BackstoryMod(Mod):
    label: str = "Backstory"
    description: str = "Modify the OC's Backstory"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(bot=bot, member=member, target=target)
        backstory = (
            oc.backstory[:4000]
            if oc.backstory
            else "No backstory was provided."
        )
        handler = text_view.handle(
            label="Write the character's Backstory.",
            style=InputTextStyle.paragraph,
            value=backstory,
            origin=target,
            required=False,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
                return False


@dataclass(unsafe_hash=True, slots=True)
class ExtraMod(Mod):
    label: str = "Extra Information"
    description: str = "Modify the OC's Extra Information"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        text_view = ModernInput(bot=bot, member=member, target=target)
        extra = (
            oc.extra[:4000]
            if oc.extra
            else "No Extra Information was provided."
        )
        handler = text_view.handle(
            label="Write the character's Extra Information.",
            style=InputTextStyle.paragraph,
            value=extra,
            origin=target,
            required=False,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.extra = answer or None
                return False


@dataclass(unsafe_hash=True, slots=True)
class MovesetMod(Mod):
    label: str = "Moveset"
    description: str = "Modify the OC's Moveset"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        moves = oc.movepool() or ALL_MOVES.values()

        view = ComplexInput(
            bot=bot,
            member=member,
            values=moves,
            timeout=None,
            target=target,
            max_values=6,
        )
        aux: Optional[bool] = None
        origin = await target.original_message()
        view.embed.title = "Write the character's moveset. Current below"
        view.embed.description = (
            "\n".join(repr(move) for move in oc.moveset) or "No Moves"
        )
        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        if isinstance(moves := view.choices, set):
            oc.moveset = frozenset(moves)
        return aux


@dataclass(unsafe_hash=True, slots=True)
class AbilitiesMod(Mod):
    label: str = "Abilities"
    description: str = "Modify the OC's Abilities"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = ComplexInput(
            bot=bot,
            member=member,
            values=oc.species.abilities or ALL_ABILITIES.values(),
            timeout=None,
            target=target,
            max_values=oc.max_amount_abilities,
            parser=lambda x: (x.name, x.description),
        )
        origin = await target.original_message()
        view.embed.title = "Select the abilities. Current ones below"
        for index, item in enumerate(oc.abilities, start=1):
            view.embed.add_field(
                name=f"Ability {index} - {item.name}",
                value=item.description,
                inline=False,
            )
        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        if isinstance(abilities := view.choices, set):
            oc.abilities = frozenset(abilities)


@dataclass(unsafe_hash=True, slots=True)
class ImageMod(Mod):
    label: str = "Image"
    description: str = "Modify the OC's Image"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = ImageView(
            bot=bot,
            member=member,
            default_img=oc.image,
            target=target,
        )
        origin = await target.original_message()
        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        aux: Optional[bool] = None
        if isinstance(image := view.text, str):
            if msg := view.received:
                await msg.delete(delay=100)
            aux = oc.image != image
            oc.image = image
        return aux


@dataclass(unsafe_hash=True, slots=True)
class MovepoolMod(Mod):
    label: str = "Movepool"
    description: str = "Used to change Movepool"

    def check(self, oc: Type[Character]) -> bool:
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
        return isinstance(
            oc,
            (
                FakemonCharacter,
                VariantCharacter,
            ),
        )

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            Member
        target : Interaction
            Target

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        origin = await target.original_message()
        view = MovepoolView(oc)
        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        return False


@dataclass(unsafe_hash=True, slots=True)
class EvolutionMod(Mod):
    label: str = "Evolution"
    description: str = "Used to Evolve OCs"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        origin = await target.original_message()

        if len(values := oc.species.species_evolves_to) == 1:
            species = values[0]
        else:
            view = ComplexInput(
                bot=bot,
                member=member,
                values=set(values),
                timeout=None,
                target=target,
                parser=lambda x: (x.name, f"Evolve to {x.name}"),
            )
            view.embed.title = "Select the Evolution"
            await origin.edit(content=None, embed=view.embed, view=view)
            await view.wait()
            if not (species := view.choice):
                return

        oc.species = species
        if not oc.types and isinstance(species, Fusion):
            possible_types = species.possible_types
            view = ComplexInput(
                bot=bot,
                member=member,
                values=possible_types,
                timeout=None,
                target=target,
                parser=lambda x: (
                    "/".join(i.name for i in x).title(),
                    f"Sets the typing to {'/'.join(i.name for i in x).title()}",
                ),
            )
            view.embed.title = "Select the Fusion's new typing"
            await origin.edit(content=None, embed=view.embed, view=view)
            await view.wait()
            if not (types := view.choice):
                return
            species.types = types

        default_image: str = oc.default_image or oc.image

        view = ImageView(
            bot=bot,
            member=member,
            default_img=default_image,
            target=target,
        )

        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        if isinstance(image := view.text, str):
            if msg := view.received:
                await msg.delete(delay=30)
            oc.image = image
        return True


@dataclass(unsafe_hash=True, slots=True)
class DevolutionMod(Mod):
    label: str = "Devolve"
    description: str = "Used to devolve OCs"

    def check(self, oc: Type[Character]) -> bool:
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
        return bool(oc.evolves_from)

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        origin = await target.original_message()

        current = oc.species
        oc.species = oc.species.species_evolves_from
        if not oc.types and isinstance(oc.species, Fusion):
            possible_types = oc.species.possible_types
            view = ComplexInput(
                bot=bot,
                member=member,
                values=possible_types,
                timeout=None,
                target=target,
                parser=lambda x: (
                    "/".join(i.name for i in x).title(),
                    f"Sets the typing to {'/'.join(i.name for i in x).title()}",
                ),
            )
            view.embed.title = "Select the Fusion's new typing"
            await origin.edit(content=None, embed=view.embed, view=view)
            await view.wait()
            if not (types := view.choice):
                return
            oc.species.types = types

        oc.moveset &= set(oc.species.movepool()) & set(current.movepool())

        default_image = oc.default_image or oc.image

        view = ImageView(
            bot=bot,
            member=member,
            default_img=default_image,
            target=target,
        )

        await origin.edit(content=None, embed=view.embed, view=view)
        await view.wait()
        await origin.edit(content="Modification done", embed=None, view=None)
        if isinstance(image := view.text, str):
            if msg := view.received:
                await msg.delete(delay=30)
            oc.image = image
        return True


@dataclass(unsafe_hash=True, slots=True)
class SpAbilityMod(Mod):
    label: str = "Special Ability"
    description: str = "Modify/Add the OC's Special Abilities"

    def check(self, oc: Type[Character]) -> bool:
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

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Method

        Parameters
        ----------
        oc : Type[Character]
            Character
        bot : CustomBot
            Bot
        member : Union[User, Member]
            User
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool If Updatable, None if cancelled
        """
        view = SPView(bot=bot, oc=oc, member=member, target=target)
        view.embed.title = "Special Ability Management"
        await view.send()
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
    Devolution = DevolutionMod()
    SpAbility = SpAbilityMod()

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def description(self) -> str:
        return self.value.description

    def check(self, oc: Type[Character]) -> bool:
        return self.value.check(oc)

    async def method(
        self,
        oc: Type[Character],
        bot: CustomBot,
        member: Union[User, Member],
        target: Interaction,
    ) -> Optional[bool]:
        """Modifications for the given context

        Parameters
        ----------
        oc : Type[Character]
            Character to modify
        bot : CustomBot
            Bot instance
        member : Union[User, Member]
            User interacting
        target : T
            Context

        Returns
        -------
        Optional[bool]
            Bool if updatable, None if cancelled.
        """
        return await self.value.method(oc, bot, member, target)


class ModifyView(View):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        oc: Character,
        target: Interaction,
    ):
        """Modification view

        Parameters
        ----------
        bot : CustomBot
            bot
        member : Member
            member
        oc : Character
            character
        """
        super(ModifyView, self).__init__(timeout=None)
        self.bot = bot
        self.member = member
        self.oc = oc
        self.target = target

        self.edit.options = [
            SelectOption(
                label=item.label,
                value=item.name,
                description=item.description,
                emoji="\N{PENCIL}",
            )
            for item in Modification
            if item.check(oc)
        ]
        self.edit.max_values = len(self.edit.options)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if self.member != interaction.user:
            msg = f"This menu has been requested by {self.member}"
            await resp.send_message(msg, ephemeral=True)
            return False
        await resp.defer(ephemeral=True)
        return True

    @select(placeholder="Select Fields to Edit", row=0)
    async def edit(self, _: Select, ctx: Interaction):
        await self.target.edit_original_message(view=None)
        modifying: bool = False
        for item in ctx.data.get("values", []):
            mod = Modification[item]
            result = await mod.method(
                oc=self.oc,
                bot=self.bot,
                member=self.member,
                target=ctx,
            )
            if result is None:
                self.bot.logger.info(
                    "At %s, %s cancelled modifications to Character(%s) aka %s",
                    mod.label,
                    str(ctx.user),
                    repr(self.oc),
                    self.oc.name,
                )
                break
            else:
                self.bot.logger.info(
                    "Field %s, modified by %s to Character(%s) aka %s",
                    mod.label,
                    str(ctx.user),
                    repr(self.oc),
                    self.oc.name,
                )
                modifying |= result

        try:
            webhook = await self.bot.fetch_webhook(919280056558317658)
            thread: Thread = await self.bot.fetch_channel(self.oc.thread)
            if thread.archived:
                await thread.edit(archived=False)
            embed = self.oc.embed
            embed.set_image(url="attachment://image.png")
            if not modifying:
                msg = await webhook.edit_message(
                    self.oc.id, embed=embed, thread=thread
                )
            elif file := await self.bot.get_file(self.oc.generated_image):
                msg = await webhook.edit_message(
                    self.oc.id,
                    file=file,
                    attachments=[],
                    embed=embed,
                    thread=thread,
                )
            else:
                msg = await webhook.edit_message(
                    self.oc.id,
                    embed=embed,
                    thread=thread,
                )
            self.oc.image = msg.embeds[0].image.url
            async with self.bot.database() as db:
                await self.oc.update(db)
        except DiscordException as e:
            self.bot.logger.exception(
                "Error at updating %s's %s named %s, will re-register",
                str(self.member),
                repr(self.oc),
                self.oc.name,
                exc_info=e,
            )
            cog = self.bot.get_cog("Submission")
            await cog.registration(ctx=ctx, oc=self.oc)
        self.stop()

    @button(label="Don't make any changes", row=1)
    async def cancel(self, _: Button, ctx: Interaction):
        await self.target.edit_original_message(view=None)
        await ctx.followup.send("Alright, no changes.", ephemeral=True)
        return self.stop()

    @button(style=ButtonStyle.red, label="Delete Character", row=1)
    async def delete(self, _: Button, ctx: Interaction):
        await self.target.edit_original_message(view=None)
        webhook = await self.bot.fetch_webhook(919280056558317658)
        thread: Thread = await self.bot.fetch_channel(self.oc.thread)
        if thread.archived:
            await thread.edit(archived=False)
        await webhook.delete_message(self.oc.id, thread_id=self.oc.thread)
        await ctx.followup.send("Character Has been Deleted", ephemeral=True)
        return self.stop()
