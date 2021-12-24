# Copyright 2021 Vioshim
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
from contextlib import suppress
from dataclasses import asdict
from enum import Enum
from typing import Optional, Type, Union

from discord import (
    ButtonStyle,
    DiscordException,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    Thread,
    User,
)
from discord.ui import Button, Select, View, button, select

from src.enums.abilities import Abilities
from src.enums.moves import Moves
from src.enums.pronouns import Pronoun
from src.pagination.complex import Complex, ComplexInput
from src.pagination.text_input import TextInput
from src.pagination.view_base import Basic
from src.structures.ability import SpAbility
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.functions import int_check
from src.views import ImageView

SP_ABILITY_ITEMS = ["name", "origin", "description", "pros", "cons"]

__all__ = ("Modification", "ModifyView")


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
        await resp.defer(ephemeral=True)
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
        backup = set(self.oc.abilities)
        if len(self.oc.abilities) > 1:
            view = ComplexInput(
                bot=self.bot,
                member=self.member,
                target=ctx,
                values=self.oc.abilities,
                timeout=None,
                parser=lambda x: (x.value.name, x.description),
            )
            async with view.send(
                    title="Select an Ability to Remove.",
                    fields=[
                        dict(
                            name=f"Ability {index} - {item.value.name}",
                            value=item.description,
                            inline=False,
                        ) for index, item in enumerate(backup, start=1)
                    ],
            ) as items:
                if isinstance(items, set):
                    self.oc.abilities -= items
                    backup = set(self.oc.abilities)
                else:
                    return self.stop()

        text_view = TextInput(
            bot=self.bot,
            member=self.member,
            target=ctx,
            required=True,
        )
        text_view.embed.description = (
            "If you need to write too much, "
            "I recommend to move to Google documents, otherwise, try to be concise."
        )

        data: dict[str, str] = {}

        for item in SP_ABILITY_ITEMS:
            word = "method" if item == "origin" else item
            title = f"Write the Special Ability's {item.title()}"
            async with text_view.handle(title=title) as answer:
                data[word] = answer
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
            values=SP_ABILITY_ITEMS,
            target=ctx,
            timeout=None,
            max_values=5,
            parser=lambda x: (
                name := str(x).title(),
                f"Modify Sp. Ability's {name}",
            ),
        )
        text_view = TextInput(
            bot=self.bot,
            member=self.member,
            target=ctx,
            required=True,
        )
        backup = asdict(self.oc.sp_ability)
        data: dict[str, str] = {}
        text_view.embed.description = (
            "If you need to write too much, "
            "I recommend to move to Google documents, otherwise, try to be concise."
        )
        async with view.send(title="Sp.Ability Modify") as elements:
            if not isinstance(elements, set):
                return self.stop()
            for item in elements:
                word: str = "method" if item == "origin" else item
                title = f"Special Ability's {item}. Current Below".title()
                description = backup.get(word)
                async with text_view.handle(
                        title=title,
                        description=description,
                ) as answer:
                    if not isinstance(answer, str):
                        break
                    elif answer:
                        backup[word] = answer

            else:
                self.oc.sp_ability = SpAbility(**data)

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
        await resp.defer(ephemeral=True)
        self.oc.sp_ability = None
        await resp.send_message("Special Ability removed.", ephemeral=True)
        self.stop()


class Mod(metaclass=ABCMeta):
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


class NameMod(Mod):
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
        text_view = TextInput(bot=bot, member=member, target=target)
        handler = text_view.handle(
            title="Write the character's Name. Current below",
            description=f"> {oc.name}",
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = answer.title()
                return False


class AgeMod(Mod):
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
        text_view = TextInput(bot=bot, member=member, target=target)
        handler = text_view.handle(
            title="Write the character's Age. Current below",
            description=f"> {oc.name}",
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.age = int_check(answer, 1, 99)
                return False


class PronounMod(Mod):
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
            parser=lambda x: (name := x.name, f"Sets Pronoun as {name}"),
        )
        aux: Optional[bool] = None
        async with view.send(
                title="Write the character's Pronoun. Current below",
                description=f"> {oc.pronoun.name}",
                single=True,
        ) as item:
            if isinstance(item, Pronoun):
                aux = item != oc.pronoun
                oc.pronoun = item
        return aux


class BackstoryMod(Mod):
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
        text_view = TextInput(bot=bot, member=member, target=target)
        handler = text_view.handle(
            title="Write the character's Backstory. Current below",
            description=oc.backstory or "No backstory was provided.",
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
                return False


class ExtraMod(Mod):
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
        text_view = TextInput(bot=bot, member=member, target=target)
        handler = text_view.handle(
            title="Write the character's Extra information. Current below",
            description=oc.backstory or "No extra information was provided.",
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.extra = answer or None
                return False


class MovesetMod(Mod):
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
        moves_view = ComplexInput(
            bot=bot,
            member=member,
            values=oc.movepool()
            or [item for item in Moves if not item.banned],
            timeout=None,
            target=target,
            max_values=6,
        )
        async with moves_view.send(
                title="Select the Moves. Current Moves below",
                description="\n".join(repr(item) for item in oc.moveset)
                or "No moves",
        ) as moves:
            if isinstance(moves, set):
                oc.moveset = frozenset(moves)


class AbilitiesMod(Mod):
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
            values=oc.species.abilities or Abilities,
            timeout=None,
            target=target,
            max_values=oc.max_amount_abilities,
            parser=lambda x: (x.value.name, x.description),
        )
        async with view.send(
                title="Select the abilities. Current ones below",
                fields=[
                    dict(
                        name=f"Ability {index} - {item.value.name}",
                        value=item.description,
                        inline=False,
                    ) for index, item in enumerate(oc.abilities, start=1)
                ],
        ) as abilities:
            if isinstance(abilities, set):
                oc.abilities = frozenset(abilities)


class ImageMod(Mod):
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
        aux: Optional[bool] = None
        async with view.send() as image:
            if isinstance(image, str):
                if msg := view.received:
                    await msg.delete(delay=100)
                aux = oc.image != image
                oc.image = image
        return aux


class SpAbilityMod(Mod):
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
    SpAbility = SpAbilityMod()

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
        self.used = False
        data = list(Modification)
        if not oc.can_have_special_abilities:
            data.remove(Modification.SpAbility)

        self.edit.options = [
            SelectOption(
                label=f"OC's {item.name}".title(),
                value=item.name,
                description=f"Edit OC's {item}",
                emoji="\N{PENCIL}",
            ) for item in data
        ]
        self.edit.max_values = len(self.edit.options)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if self.member != interaction.user:
            msg = f"This menu has been requested by {self.member}"
            await resp.send_message(msg, ephemeral=True)
            return False
        if self.used:
            await resp.send_message(
                "You're already using the options.",
                ephemeral=True,
            )
            return False
        self.used = True
        await resp.defer(ephemeral=True)
        return True

    @select(placeholder="Select Fields to Edit", row=0)
    async def edit(self, _: Select, ctx: Interaction):
        modifying: bool = False
        for item in ctx.data.get("values", []):
            result = await Modification[item].method(
                oc=self.oc,
                bot=self.bot,
                member=self.member,
                target=ctx,
            )
            if result is None:
                break
            else:
                modifying |= result
        else:
            try:
                webhook = await self.bot.fetch_webhook(919280056558317658)
                thread: Thread = await self.bot.fetch_channel(self.oc.thread)
                embed = self.oc.embed
                embed.set_image(url="attachment://image.png")
                await webhook.edit_message(self.oc.id,
                                           embed=embed,
                                           thread=thread)
                async with self.bot.database() as db:
                    await self.oc.update(db)
            except DiscordException as e:
                self.bot.logger.exception(
                    "Error at updating %s's %s, will re-register",
                    str(self.member),
                    str(type(self.oc)),
                    exc_info=e,
                )
                modifying = True

            if modifying:
                cog = self.bot.get_cog("Submission")
                cog.ocs.pop(self.oc.id, None)
                cog.rpers.setdefault(self.oc.author, set())
                cog.rpers[self.oc.author] -= {self.oc}
                async with self.bot.database() as db:
                    await self.oc.delete(db)

                with suppress(DiscordException):
                    webhook = await self.bot.fetch_webhook(919280056558317658)
                    await webhook.delete_message(self.oc.id,
                                                 thread_id=self.oc.thread)

                await cog.registration(ctx=ctx,
                                       oc=self.oc,
                                       standard_register=False)
        self.used = False
        self.stop()

    @button(label="Don't make any changes", row=1)
    async def cancel(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.send_message("Edit has been cancelled", ephemeral=True)
        return self.stop()

    @button(style=ButtonStyle.red, label="Delete Character", row=1)
    async def delete(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        cog = self.bot.get_cog("Submission")
        cog.ocs.pop(self.oc.id, None)
        cog.rpers.setdefault(self.oc.author, set())
        cog.rpers[self.oc.author] -= {self.oc}
        async with self.bot.database() as db:
            await self.oc.delete(db)

        await resp.send_message("Character has been removed", ephemeral=True)

        with suppress(DiscordException):
            webhook = await self.bot.fetch_webhook(919280056558317658)
            await webhook.delete_message(self.oc.id, thread_id=self.oc.thread)
        return self.stop()
