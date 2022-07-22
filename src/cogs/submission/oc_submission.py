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

from discord import (
    ButtonStyle,
    File,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
    SelectOption,
)
from discord.ui import Button, Select, TextInput, button, select
from discord.utils import MISSING

from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability, SPAbilityView
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
from src.utils.functions import embed_handler, int_check
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
            required=True,
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

        async with view.send(ephemeral=True) as choices:
            choices: list[Species] = list(choices)
            if choices:
                if len(choices) != view.max_values:
                    return

                if template == "Variant":
                    oc.species = Variant(base=choices[0], name="")
                elif template == "Fusion":
                    oc.species = Fusion(*choices)
                    oc.abilities = frozenset()
                elif template.startswith("Custom"):
                    oc.species = Fakemon(
                        abilities=oc.abilities,
                        base_image=oc.image_url,
                        movepool=Movepool(other=oc.moveset),
                        evolves_from=choices[0],
                    )
                else:
                    oc.species = choices[0]
                    oc.image = choices[0].base_image

                oc.abilities &= frozenset(oc.species.abilities)
                oc.moveset &= frozenset(oc.total_movepool())

            elif not template.startswith("Custom"):
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

    def check(self, oc: Character) -> bool:
        return oc.species and isinstance(oc.species, (Fusion, Fakemon, Variant))

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        species = oc.species
        if isinstance(species, Fusion):  # type: ignore
            values = species.possible_types
            view: Complex[set[Typing]] = Complex(
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
            view: Complex[Typing] = Complex(
                member=ctx.user,
                target=ctx,
                values=Typing.all(),
                max_values=2,
                timeout=None,
                parser=lambda x: (str(x), f"Adds the typing {x}"),
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
        description = "\n".join(repr(move) for move in oc.moveset) or "No Moves"
        async with view.send(
            title="Write the character's moveset. Current below",
            description=description,
        ) as choices:
            oc.moveset = choices
            progress.add(self.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Optional. Fill the OC's movepool"

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

    def check(self, oc: Character) -> bool:
        return oc.species and oc.can_have_special_abilities

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        view = SPAbilityView(ctx.user)
        await ctx.followup.send("Continue with Submission", view=view)
        await view.wait()
        oc.sp_ability = view.sp_ability
        progress.add(self.name)


class BackstoryField(TemplateField):
    name = "Backstory"
    description = "Optional. Fill the OC's Backstory"

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Backstory.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=True,
        ) as answer:
            if isinstance(answer, str):
                oc.backstory = answer
                progress.add(self.name)


class ExtraField(TemplateField):
    name = "Extra Information"
    description = "Optional. Fill the OC's Extra Information"

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Extra Information.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=True,
        ) as answer:
            if isinstance(answer, str):
                oc.extra = answer

                progress.add(self.name)


class ImageField(TemplateField):
    name = "Image"
    description = "Fill the OC's Image"

    async def on_submit(self, ctx: Interaction, template: str, progress: set[str], oc: Character):
        view = ImageView(
            member=ctx.user,
            default_img=oc.image or oc.default_image,
            target=ctx,
        )
        async with view.send() as text:
            if text and isinstance(text, str):
                oc.image = text
                progress.add(self.name)

        oc.image = await ctx.client.get_file(oc.generated_image)


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


class CreationOCView(Basic):
    def __init__(self, ctx: Interaction, user: Member):
        super(CreationOCView, self).__init__(target=ctx, member=user, timeout=None)
        self.embed.title = "Character Creation"
        self.oc = Character(author=user.id)
        self.user = user
        self.ref_template = "Pokemon"
        self.progress: set[str] = set()
        self.setup()

    async def interaction_check(self, interaction: Interaction) -> bool:
        cog = interaction.client.get_cog("Submission")
        aux = cog.supporting.get(interaction.user, interaction.user)
        condition = aux == self.user
        if not condition:
            resp: InteractionResponse = interaction.response
            await resp.send_message("This OC isn't yours", ephemeral=True)
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
                    if (v.description.startswith("Optional") or k in self.progress)
                    else "\N{CROSS MARK}"
                ),
            )
            for k, v in FIELDS.items()
            if v.check(self.oc)
        ]
        self.submit.disabled = any(x.emoji == "\N{CROSS MARK}" for x in self.fields.options)

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

    @select(placeholder="Fill the Fields", row=1)
    async def fields(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        try:
            item = FIELDS[sct.values[0]]
            await item.on_submit(ctx, self.ref_template, self.progress, self.oc)
            self.setup()
        except Exception as e:
            ctx.client.logger.exception("Exception in OC Creation", exc_info=e)
            await ctx.followup.send(str(e), ephemeral=True)
        finally:
            embed = self.oc.embed

            if not resp.is_done():
                await resp.pong()

            files = [self.oc.image] if isinstance(self.oc.image, File) else MISSING
            embed = embed_handler(self.message, embed)
            if files or self.message.attachments:
                embed.set_image(url="attachment://image.png")

            m = await self.message.edit(embed=embed, view=self, attachments=files)
            self.oc.image = m.embeds[0].image.proxy_url
            self.message = m

    @button(
        emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}",
        style=ButtonStyle.red,
        row=2,
    )
    async def cancel(self, ctx: Interaction, btn: Button):
        await self.delete()

    @button(
        emoji=PartialEmoji(name="Google", id=999567989592555580),
        style=ButtonStyle.blurple,
        disabled=True,
        row=2,
    )
    async def url(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message("This is a test", ephemeral=True)

    @button(
        disabled=True,
        label="Submit",
        style=ButtonStyle.green,
        row=2,
    )
    async def submit(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message("This is a test", ephemeral=True)
        await ctx.message.edit(view=None)
        self.stop()
