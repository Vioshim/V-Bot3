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

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from discord import (
    ButtonStyle,
    Color,
    Embed,
    File,
    Interaction,
    InteractionResponse,
    Member,
    Object,
    SelectOption,
    TextStyle,
    Webhook,
)
from discord.ui import Button, Select, TextInput, button, select
from discord.utils import MISSING

from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability
from src.structures.character import Character
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import (
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Pokemon,
    Species,
    UltraBeast,
    Variant,
)
from src.utils.etc import WHITE_BAR
from src.utils.functions import int_check
from src.views.ability_view import SPAbilityView
from src.views.characters_view import CharactersView, PingView
from src.views.image_view import ImageView
from src.views.move_view import MoveComplex
from src.views.movepool_view import MovepoolView
from src.views.species_view import SpeciesComplex


@dataclass(unsafe_hash=True)
class Template:
    name: bool = True
    species: bool = True
    age: bool = True
    pronoun: bool = True
    types: bool = True
    abilities: bool = True
    sp_ability: bool = False
    moveset: bool = True

    def clear(self):
        self.name: bool = False
        self.species: bool = False
        self.age: bool = False
        self.pronoun: bool = False
        self.types: bool = False
        self.abilities: bool = False
        self.sp_ability: bool = False
        self.moveset: bool = False


TEMPLATES: dict[str, Template] = dict(
    Pokemon=Template(sp_ability=True, types=False),
    Legendary=Template(age=False, abilities=False, types=False),
    Mythical=Template(age=False, abilities=False, types=False),
    UltraBeast=Template(age=False, abilities=False, types=False),
    Mega=Template(abilities=False, types=False),
    Fusion=Template(),
    CustomPokemon=Template(sp_ability=True),
    CustomLegendary=Template(age=False),
    CustomMythical=Template(age=False),
    CustomUltraBeast=Template(age=False),
    CustomMega=Template(types=True),
    Variant=Template(sp_ability=True),
)


class TemplateField(ABC):
    name: str = ""
    description: str = ""

    def check(self, oc: Character) -> bool:
        return True

    def evaluate(self, oc: Character) -> bool:
        """Abstract method which evaluates a character"""
        return True

    @abstractmethod
    async def on_submit(
        self,
        ctx: Interaction,
        template: str,
        progress: set[str],
        oc: Character,
    ):
        """Abstract method which affects progress and the character"""


class NameField(TemplateField):
    name = "Name"
    description = "Fill the OC's Name"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.name)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        handler = text_view.handle(
            label="Write the character's Name.",
            placeholder=f"> {oc.name}",
            default=oc.name,
            required=True,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = answer.title()
                progress.add(self.name)


class AgeField(TemplateField):
    name = "Age"
    description = "Optional. Fill the OC's Age"

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        age = str(oc.age) if oc.age else "Unknown"
        handler = text_view.handle(
            label="Write the character's Age.",
            placeholder=f"> {age}",
            default=age,
            required=False,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.age = int_check(answer, 13, 99)
                progress.add(self.name)


class PronounField(TemplateField):
    name = "Pronoun"
    description = "Optional. Fill the OC's Pronoun"

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        default = getattr(oc.pronoun, "name", "Them")
        view: Complex[Pronoun] = Complex(
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=Pronoun,
            parser=lambda x: (x.name, f"Sets Pronoun as {x.name}"),
            sort_key=lambda x: x.name,
            text_component=TextInput(
                label="Pronoun",
                placeholder="He | She | Them",
                default=default,
                min_length=2,
                max_length=4,
            ),
            silent_mode=True,
        )
        async with view.send(
            title="Write the character's Pronoun. Current below",
            description=f"> {default}",
            single=True,
            ephemeral=True,
        ) as pronoun:
            if isinstance(pronoun, Pronoun):
                oc.pronoun = pronoun
                progress.add(self.name)


class SpeciesField(TemplateField):
    name = "Species"
    description = "Fill the OC's Species"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.species)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):

        match template:
            case "Pokemon":
                mon_total = Pokemon.all()
            case "Legendary":
                mon_total = Legendary.all()
            case "Mythical":
                mon_total = Mythical.all()
            case "UltraBeast":
                mon_total = UltraBeast.all()
            case "Mega":
                mon_total = Mega.all()
            case _:
                mon_total = Species.all()

        mon_total = {x for x in mon_total if not x.banned}

        view = SpeciesComplex(
            member=ctx.user,
            target=ctx,
            mon_total=mon_total,
            fusion=template == "Fusion",
        )

        if template.startswith("Custom"):
            view.embed.title = "Select if it has a canon Pre-Evo (Skip if not needed)"
        elif template == "Variant":
            view.embed.title = "Select Base Species"

        async with view.send() as choices:
            choices: list[Species] = list(choices)
            if choices:
                if len(choices) != view.max_values:
                    return
                if template.startswith("Custom"):
                    oc.species = Fakemon(
                        abilities=oc.abilities,
                        base_image=oc.image_url,
                        movepool=Movepool(other=oc.moveset),
                        evolves_from=choices[0],
                    )
                elif template == "Variant":
                    oc.species = Variant(base=choices[0], name="")
                elif template == "Fusion":
                    oc.species = Fusion(*choices)
                    oc.abilities = frozenset()
                else:
                    oc.species = choices[0]
                    if not oc.image:
                        oc.image = choices[0].base_image

                oc.abilities &= frozenset(oc.species.abilities)
                oc.moveset &= frozenset(oc.total_movepool())
            elif template.startswith("Custom"):
                oc.species = Fakemon(
                    abilities=oc.abilities,
                    base_image=oc.image_url,
                    movepool=Movepool(other=oc.moveset),
                )
            else:
                return

        if not oc.species:
            return

        if oc.species.name:
            progress.add(self.name)
        else:
            species = getattr(oc.species, "name", "Species")
            text_view = ModernInput(member=ctx.user, target=ctx)
            handler = text_view.handle(
                label="Write the character's Species.",
                default=species,
                required=True,
                origin=view.message,
            )
            async with handler as answer:
                if isinstance(answer, str):
                    oc.species.name = answer.title()
                    progress.add(self.name)


class TypesField(TemplateField):
    name = "Types"
    escription = "Fill the OC's Types"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.types)

    def check(self, oc: Character) -> bool:
        return oc.species and isinstance(oc.species, (Fusion, Fakemon, Variant))

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        species = oc.species
        if isinstance(species, Fusion):  # type: ignore
            values = species.possible_types
            view = Complex[set[Typing]](
                member=ctx.user,
                target=ctx,
                values=values,
                timeout=None,
                parser=lambda x: (y := "/".join(i.name for i in x), f"Adds the typing {y}"),
                text_component=TextInput(
                    label="Fusion Typing",
                    placeholder=" | ".join("/".join(i.name for i in x).title() for x in values),
                ),
                silent_mode=True,
            )
            single = True
        else:
            view = Complex[Typing](
                member=ctx.user,
                target=ctx,
                values=Typing.all(),
                max_values=2,
                timeout=None,
                parser=lambda x: (x.name, f"Adds the typing {x.name}"),
                text_component=TextInput(
                    label="Character's Types",
                    placeholder="Type, Type",
                    required=True,
                ),
                silent_mode=True,
            )
            single = False

        async with view.send(title="Select Typing", single=single) as types:
            if types:
                species.types = frozenset(types)
                progress.add(self.name)


class MovesetField(TemplateField):
    name = "Moveset"
    description = "Optional. Fill the OC's fav. moves"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.moveset)

    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        moves = oc.total_movepool()
        mon = Pokemon.from_ID("SMEARGLE")
        if isinstance(oc.species, Fusion):
            condition = mon in oc.species.bases
        elif isinstance(oc.species, Variant):
            condition = mon == oc.species.base
        elif isinstance(oc.species, Fakemon):
            condition = mon == oc.species.evolves_from
        else:
            condition = mon == oc.species

        if condition or not moves:
            moves = Move.all()

        moves = {x for x in moves if not x.banned}

        view = MoveComplex(member=ctx.user, moves=moves, target=ctx)
        async with view.send(title="Write the character's moveset. Current below") as choices:
            oc.moveset = frozenset(choices)
            progress.add(self.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Optional. Fill the OC's movepool"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.movepool)

    def check(self, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant))

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        view = MovepoolView(ctx, ctx.user, oc)
        await view.send()
        await view.wait()
        progress.add(self.name)


class AbilitiesField(TemplateField):
    name = "Abilities"
    description = "Fill the OC's Abilities"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.abilities)

    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        placeholder = ", ".join(["Ability"] * oc.max_amount_abilities)
        abilities = oc.species.abilities
        if isinstance(oc.species, (Fakemon, Variant)) or (not abilities):
            abilities = ALL_ABILITIES.values()
        view = Complex[Ability](
            member=ctx.user,
            values=abilities,
            timeout=None,
            target=ctx,
            max_values=oc.max_amount_abilities,
            parser=lambda x: (x.name, x.description),
            text_component=TextInput(
                label="Ability",
                placeholder=placeholder,
                default=", ".join(x.name for x in oc.abilities),
            ),
            silent_mode=True,
        )
        view.embed.title = "Select the abilities. Current ones below"
        for index, item in enumerate(oc.abilities, start=1):
            view.embed.add_field(
                name=f"Ability {index} - {item.name}",
                value=item.description,
                inline=False,
            )
        async with view.send() as choices:
            if isinstance(choices, set):
                oc.abilities = frozenset(choices)
                progress.add(self.name)


class SpAbilityField(TemplateField):
    name = "Special Ability"
    description = "Optional. Fill the OC's Special Ability"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.sp_ability)

    def check(self, oc: Character) -> bool:
        return oc.species and oc.can_have_special_abilities

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        view = SPAbilityView(ctx.user, oc)
        await ctx.followup.send("Continue with Submission", view=view)
        await view.wait()
        oc.sp_ability = view.sp_ability
        progress.add(self.name)


class BackstoryField(TemplateField):
    name = "Backstory"
    description = "Optional. Fill the OC's Backstory"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.backstory)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Backstory.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            oc.backstory = answer or None
            progress.add(self.name)


class ExtraField(TemplateField):
    name = "Extra Information"
    description = "Optional. Fill the OC's Extra Information"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.extra)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Extra Information.",
            placeholder=oc.extra,
            default=oc.extra,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            oc.extra = answer or None
            progress.add(self.name)


class ImageField(TemplateField):
    name = "Image"
    description = "Fill the OC's Image"

    def evaluate(self, oc: Character) -> bool:
        return bool(oc.image)

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        default_image = oc.image_url or oc.image or oc.default_image
        view = ImageView(member=ctx.user, default_img=default_image, target=ctx)
        async with view.send() as text:
            if text and isinstance(text, str):
                oc.image = text
                progress.add(self.name)

        if isinstance(oc.image, str):
            oc.image = await ctx.client.get_file(oc.generated_image)
        if not oc.image:
            oc.image = default_image


FIELDS: dict[str, TemplateField] = {
    "Name": NameField(),
    "Age": AgeField(),
    "Pronoun": PronounField(),
    "Species": SpeciesField(),
    "Types": TypesField(),
    "Moveset": MovesetField(),
    "Movepool": MovepoolField(),
    "Abilities": AbilitiesField(),
    "Special Ability": SpAbilityField(),
    "Backstory": BackstoryField(),
    "Extra": ExtraField(),
    "Image": ImageField(),
}


def convert_template(oc: Character):
    if oc.species:
        return type(oc.species).__name__.replace("Fakemon", "CustomPokemon")
    return "Pokemon"


class CreationOCView(Basic):
    def __init__(self, ctx: Interaction, user: Member, oc: Optional[Character] = None):
        super(CreationOCView, self).__init__(target=ctx, member=user, timeout=None)
        self.embed.title = "Character Creation"
        oc = oc.copy() if oc else Character(author=user.id, server=ctx.guild.id)
        self.oc = oc
        self.user = user
        self.embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        self.ref_template = convert_template(oc)
        self.progress: set[str] = set()
        self.current: Optional[str] = None
        if not oc.id:
            self.remove_item(self.finish_oc)
        self.setup()

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        cog = interaction.client.get_cog("Submission")
        condition = self.user == cog.supporting.get(interaction.user, interaction.user)

        embed = Embed(color=Color.red(), timestamp=interaction.created_at)
        embed.set_author(name=self.user.display_name, icon_url=self.user.display_avatar.url)
        embed.set_image(url=WHITE_BAR)

        if not condition:
            embed.title = "This OC isn't yours"
        elif self.current and self.user == interaction.user:
            embed.title = f"You're currently filling the OC's {self.current}"

        if embed.title:
            data = dict(
                Completed="\n".join(
                    f"• {x.label}" for x in self.fields.options if str(x.emoji) == "\N{WHITE HEAVY CHECK MARK}"
                ),
                Missing="\n".join(f"• {x.label}" for x in self.fields.options if str(x.emoji) == "\N{CROSS MARK}"),
            )
            for key, value in filter(all, data.items()):
                embed.add_field(name=key, value=value, inline=False)
            await resp.send_message(embed=embed, ephemeral=True)

        return condition

    def setup(self):
        self.kind.options = [
            SelectOption(
                label=x,
                value=x,
                emoji="\N{MEMO}",
                default=x == self.ref_template,
            )
            for x in TEMPLATES
        ]
        self.fields.options = [
            SelectOption(
                label=k,
                value=k,
                description=v.description,
                emoji=(
                    "\N{WHITE HEAVY CHECK MARK}"
                    if (v.description.startswith("Optional") or k in self.progress or v.evaluate(self.oc))
                    else "\N{CROSS MARK}"
                ),
            )
            for k, v in FIELDS.items()
            if v.check(self.oc)
        ]
        self.submit.disabled = not all(str(x.emoji) == "\N{WHITE HEAVY CHECK MARK}" for x in self.fields.options)

    @select(placeholder="Select Kind", row=0)
    async def kind(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        try:
            self.oc.species = None
            self.progress -= {"Species", "Types", "Abilities", "Moveset"}
            self.ref_template = sct.values[0]
            if not TEMPLATES[self.ref_template].sp_ability:
                self.progress -= {"Special Ability"}
                self.oc.sp_ability = None
            self.setup()
            await resp.edit_message(embed=self.oc.embed, view=self)
        except Exception as e:
            ctx.client.logger.exception("Exception in OC Creation", exc_info=e)
            await resp.send_message(str(e), ephemeral=True)
            self.stop()

    @select(placeholder="Fill the Fields", row=1)
    async def fields(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        try:
            item = FIELDS[sct.values[0]]
            self.current = item.name
            await item.on_submit(ctx, self.ref_template, self.progress, self.oc)
            self.setup()
        except Exception as e:
            ctx.client.logger.exception("Exception in OC Creation", exc_info=e)
            await ctx.followup.send(str(e), ephemeral=True)
        finally:
            embed = self.oc.embed

            embed.set_author(
                name=self.user.display_name,
                icon_url=self.user.display_avatar.url,
            )

            if isinstance(self.oc.image, File):
                files = [self.oc.image]
                embed.set_image(url=f"attachment://{self.oc.image.filename}")
            else:
                files = MISSING

            m = await self.message.edit(embed=embed, view=self, attachments=files)
            if files and m.embeds[0].image.proxy_url:
                self.oc.image = m.embeds[0].image.proxy_url
            self.message = m
            self.current = None

    @button(label="Delete Character", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=2)
    async def finish_oc(self, ctx: Interaction, btn: Button):
        if self.oc.id and self.oc.thread:
            webhook: Webhook = await ctx.client.webhook(919277769735680050)
            thread = Object(id=self.oc.thread)
            await webhook.delete_message(self.oc.id, thread=thread)
        await self.delete()

    @button(label="Close this Menu", row=2)
    async def cancel(self, ctx: Interaction, btn: Button):
        await self.delete()

    @button(
        disabled=True,
        label="Submit",
        style=ButtonStyle.green,
        row=2,
    )
    async def submit(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        cog = ctx.client.get_cog("Submission")
        word = "modified" if self.oc.id else "registered"
        await cog.register_oc(self.oc, image_as_is=True)
        registered = ctx.guild.get_role(719642423327719434)
        if registered and registered not in self.user.roles:
            await self.user.add_roles(registered)
        await ctx.followup.send(f"Character {word} without Issues!", ephemeral=True)
        await self.delete()


class ModCharactersView(CharactersView):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        ocs: set[Character],
        keep_working: bool = False,
    ):
        super(ModCharactersView, self).__init__(member, target, ocs, keep_working)

    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        try:
            if item := self.current_choice:
                embed = item.embed
                guild = self.member.guild
                if author := guild.get_member(item.author):
                    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)

                cog = interaction.client.get_cog("Submission")
                user: Member = cog.supporting.get(interaction.user, interaction.user)
                if item.author in [user.id, interaction.user.id]:
                    view = CreationOCView(ctx=interaction, user=user, oc=item)
                    await view.send(embed=embed, ephemeral=True)
                else:
                    if isinstance(self.target, Interaction):
                        target = self.target
                    else:
                        target = interaction
                    view = PingView(oc=item, reference=target)
                    await interaction.followup.send(embed=embed, view=view, ephemeral=True)
                await view.wait()
        except Exception as e:
            interaction.client.logger.exception("Error in ModOCView", exc_info=e)
        finally:
            await super(CharactersView, self).select_choice(interaction, sct)
