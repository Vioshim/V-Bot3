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
from enum import Enum

from discord import (
    ButtonStyle,
    Interaction,
    InteractionResponse,
    Member,
    PartialEmoji,
    SelectOption,
)
from discord.ui import Button, Select, TextInput, View, button, select

from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
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
from src.utils.functions import int_check, multiple_pop
from src.views.image_view import ImageView
from src.views.move_view import MoveComplex
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


class Templates(Enum):
    Pokemon = Template(sp_ability=True, types=False)
    Legendary = Template(age=False, abilities=False, types=False)
    Mythical = Template(age=False, abilities=False, types=False)
    UltraBeast = Template(age=False, abilities=False, types=False)
    Mega = Template(abilities=False, types=False)
    Fusion = Template()
    CustomPokemon = Template(sp_ability=True)
    CustomLegendary = Template(age=False)
    CustomMythical = Template(age=False)
    CustomUltraBeast = Template(age=False)
    CustomMega = Template(types=True)
    Variant = Template(sp_ability=True)


class TemplateField(ABC):
    def __init_subclass__(cls, *, name: str, description: str) -> None:
        cls.name, cls.description = name, description

    def check(self, oc: Character) -> bool:
        return True

    @classmethod
    @abstractmethod
    async def on_submit(
        self,
        ctx: Interaction,
        template: Templates,
        progress: dict,
        oc: Character,
    ):
        """Abstract method which affects progress and the character"""


class NameField(TemplateField, name="Name", description="Fill the OC's Name"):
    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
                progress[cls.name] = True


class AgeField(TemplateField, name="Age", description="Fill the OC's Age"):
    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
                progress[cls.name] = True


class PronounField(TemplateField, name="Pronoun", description="Fill the OC's Pronoun"):
    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
        )
        async with view.send(
            title="Write the character's Pronoun. Current below",
            description=f"> {default}",
            single=True,
            ephemeral=True,
        ) as pronoun:
            if isinstance(pronoun, Pronoun):
                oc.pronoun = pronoun
                progress[cls.name] = True


class SpeciesField(TemplateField, name="Species", description="Fill the OC's Species"):
    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):

        match template:
            case Templates.Pokemon:
                mon_total = Pokemon.all()
            case Templates.Legendary:
                mon_total = Legendary.all()
            case Templates.Mythical:
                mon_total = Mythical.all()
            case Templates.UltraBeast:
                mon_total = UltraBeast.all()
            case Templates.Mega:
                mon_total = Mega.all()
            case _:
                mon_total = Species.all()

        mon_total = {x for x in mon_total if not x.banned}

        view = SpeciesComplex(
            member=ctx.user,
            target=ctx,
            mon_total=mon_total,
            fusion=template == Templates.Fusion,
        )

        if template.name.startswith("Custom"):
            view.embed.title = "Select if it has a canon Pre-Evo (Skip if not needed)"
        elif template == Templates.Variant:
            view.embed.title = "Select Base Species"

        async with view.send(ephemeral=True) as choices:
            choices: list[Species] = list(choices)
            if choices:
                if len(choices) != view.max_values:
                    return

                if template == Templates.Variant:
                    oc.species = Variant(base=choices[0], name="")
                elif template == Templates.Fusion:
                    oc.species = Fusion(*choices)
                elif template.name.startswith("Custom"):
                    oc.species = Fakemon(
                        abilities=oc.abilities,
                        base_image=oc.image_url,
                        movepool=Movepool(other=oc.moveset),
                        evolves_from=choices[0],
                    )
                else:
                    oc.species = choices[0]
                    oc.image = choices[0].base_image

            elif not template.name.startswith("Custom"):
                return

        if not oc.species:
            return

        if oc.species.name:
            progress[cls.name] = True
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
                    progress[cls.name] = True


class TypesField(TemplateField, name="Types", description="Fill the OC's Types"):
    def check(self, oc: Character) -> bool:
        return oc.species and isinstance(oc.species, (Fusion, Fakemon, Variant))

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
            )
            single = False

        async with view.send(title="Select Typing", ephemeral=True, single=single) as types:
            if types:
                species.types = frozenset(types)
                progress[cls.name] = True


class MovesetField(TemplateField, name="Moveset", description="Fill the OC's fav. moves"):
    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
            ephemeral=True,
        ) as choices:
            oc.moveset = choices
            progress[cls.name] = True


class AbilitiesField(TemplateField, name="Abilities", description="Fill the OC's Abilities"):
    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
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
        )
        view.embed.title = "Select the abilities. Current ones below"
        for index, item in enumerate(oc.abilities, start=1):
            view.embed.add_field(
                name=f"Ability {index} - {item.name}",
                value=item.description,
                inline=False,
            )
        async with view.send(ephemeral=True) as choices:
            if isinstance(choices, set):
                oc.abilities = frozenset(choices)
                progress[cls.name] = True


class SpAbilityField(TemplateField, name="Special Ability", description="Optional. Fill the OC's Special Ability"):
    def check(self, oc: Character) -> bool:
        return oc.species and oc.can_have_special_abilities

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
        view = SPAbilityView(ctx.user)
        await ctx.followup.send("Continue with Submission", view=view)
        await view.wait()
        oc.sp_ability = view.sp_ability


class BackstoryField(TemplateField, name="Backstory", description="Optional. Fill the OC's Backstory"):
    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Backstory.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=True,
        ) as answer:
            if isinstance(answer, str):
                oc.backstory = answer


class ExtraField(TemplateField, name="Extra Information", description="Optional. Fill the OC's Extra Information"):
    def check(self, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Extra Information.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=True,
        ) as answer:
            if isinstance(answer, str):
                oc.extra = answer


class ImageField(TemplateField, name="Image", description="Fill the OC's Image"):
    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Templates, progress: dict, oc: Character):
        view = ImageView(
            member=ctx.user,
            default_img=oc.image or oc.default_image,
            target=ctx,
        )
        async with view.send(ephemeral=True) as text:
            if text and isinstance(text, str):
                oc.image = text
                progress[cls.name] = True

        if file := await ctx.bot.get_file(text):
            embed = oc.embed
            embed.set_image(url=f"attachment://{file.filename}")
            msg = await ctx.message.edit(embed=embed, file=file)
            oc.image = msg.embeds[0].image.url


FIELDS: dict[str, TemplateField] = {
    "Name": NameField,
    "Age": AgeField,
    "Pronoun": PronounField,
    "Species": SpeciesField,
    "Types": TypesField,
    "Moveset": MovesetField,
    "Abilities": AbilitiesField,
    "Special Ability": SpAbilityField,
    "Backstory": BackstoryField,
    "Extra": ExtraField,
    "Image": ImageField,
}


class CreationOCView(View):
    def __init__(self, user: Member):
        super(CreationOCView, self).__init__(timeout=None)
        self.oc = Character(author=user.id)
        self.user = user
        self.ref_template = Templates.Pokemon
        self.progress: dict[str, bool] = {}
        self.setup()

    async def interaction_check(self, interaction: Interaction) -> bool:
        cog = interaction.client.get_cog("Submission")
        aux = cog.supporting.get(interaction.user, interaction.user)
        condition = interaction.user in [self.user, aux]
        if not condition:
            resp: InteractionResponse = interaction.response
            await resp.send_message("This OC isn't yours", ephemeral=True)
        return condition

    def setup(self):
        self.kind.options = [
            SelectOption(
                label=x.name,
                value=x.name,
                emoji="\N{MEMO}",
                default=x == self.ref_template,
            )
            for x in Templates
        ]
        self.fields.options = [
            SelectOption(
                label=k,
                value=k,
                description=v.description,
                emoji=(
                    "\N{WHITE HEAVY CHECK MARK}"
                    if (v.description.startswith("Optional") or self.progress.get(k))
                    else "\N{CROSS MARK}"
                ),
            )
            for k, v in FIELDS.items()
            if v.check(self.oc)
        ]
        self.submit.disabled = any(x.emoji == "\N{CROSS MARK}" for x in self.fields.options)

    @select(
        placeholder="Select Kind",
        row=0,
    )
    async def kind(self, ctx: Interaction, sct: Select):
        self.oc.species = None
        multiple_pop(self.progress, "Species", "Types", "Abilities")
        self.ref_template = Templates[sct.values[0]]
        if not self.ref_template.value.sp_ability:
            self.progress.pop("Special Ability", None)
            self.oc.sp_ability = None
        self.setup()
        await ctx.edit_original_message(view=self)

    @select(
        placeholder="Fill the Fields",
        row=1,
    )
    async def fields(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        item = FIELDS[sct.values[0]]
        await item.on_submit(ctx, self.ref_template, self.progress, self.oc)
        self.setup()
        await ctx.edit_original_message(view=self)

    @button(
        emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}",
        style=ButtonStyle.red,
        row=2,
    )
    async def cancel(self, ctx: Interaction, btn: Button):
        await ctx.delete_original_message()
        self.stop()

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
