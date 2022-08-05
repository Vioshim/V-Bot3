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
from enum import IntEnum, auto
from typing import Optional

from discord import (
    ButtonStyle,
    Color,
    DiscordException,
    Embed,
    File,
    Interaction,
    InteractionResponse,
    Member,
    NotFound,
    Object,
    SelectOption,
    TextStyle,
    Webhook,
)
from discord.ui import Button, Select, TextInput, button, select
from discord.utils import MISSING, get
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import (
    _BEASTBOOST,
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


class Template(IntEnum):
    Pokemon = auto()
    Legendary = auto()
    Mythical = auto()
    UltraBeast = auto()
    Mega = auto()
    Fusion = auto()
    CustomPokemon = auto()
    CustomLegendary = auto()
    CustomMythical = auto()
    CustomUltraBeast = auto()
    CustomMega = auto()
    Variant = auto()


class TemplateField(ABC):
    name: str = ""
    description: str = ""

    @classmethod
    def all(cls):
        return cls.__subclasses__()

    @classmethod
    def get(cls, **attrs):
        return get(cls.__subclasses__(), **attrs)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc, Character)

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return isinstance(oc, Character)

    @classmethod
    @abstractmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
    ):
        """Abstract method which affects progress and the character"""


class NameField(TemplateField):
    name = "Name"
    description = "Fill the OC's Name"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return bool(oc.name)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
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
                progress.add(cls.name)


class AgeField(TemplateField):
    name = "Age"
    description = "Optional. Fill the OC's Age"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return not oc.age or 13 <= oc.age <= 99

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
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
                progress.add(cls.name)


class PronounField(TemplateField):
    name = "Pronoun"
    description = "Optional. Fill the OC's Pronoun"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return isinstance(oc.pronoun, Pronoun)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        default = getattr(oc.pronoun, "name", "Them")
        view = Complex[Pronoun](
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
                progress.add(cls.name)


class SpeciesField(TemplateField):
    name = "Species"
    description = "Fill the OC's Species"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return oc.species and not oc.species.banned

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        max_values: int = 1

        match template:
            case Template.Pokemon:
                mon_total = Pokemon.all()
            case Template.Legendary:
                mon_total = Legendary.all()
            case Template.Mythical:
                mon_total = Mythical.all()
            case Template.UltraBeast:
                mon_total = UltraBeast.all()
            case Template.Mega:
                mon_total = Mega.all()
            case Template.Fusion:
                mon_total = Species.all()
                max_values = 2
            case (
                Template.CustomPokemon
                | Template.CustomLegendary
                | Template.CustomMythical
                | Template.CustomUltraBeast
                | Template.CustomMega
            ):
                mon_total = []
            case _:
                mon_total = Species.all()

        choices: list[Species] = []

        origin = None
        if mon_total := {x for x in mon_total if not x.banned}:
            view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mon_total, max_values=max_values)
            async with view.send() as data:
                origin = view.message
                choices.extend(data)
                if len(choices) != max_values:
                    return

        match template:
            case (
                Template.CustomPokemon
                | Template.CustomLegendary
                | Template.CustomMythical
                | Template.CustomUltraBeast
                | Template.CustomMega
            ):
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label="Write the character's Species.",
                    required=True,
                    origin=origin,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        if isinstance(oc.species, Fakemon):
                            oc.species.name = answer
                        else:
                            oc.species = Fakemon(
                                name=answer,
                                abilities=oc.abilities,
                                base_image=oc.image_url,
                                movepool=Movepool(other=oc.moveset.copy()),
                            )
            case Template.Variant:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label=f"Write the name of the {choices[0].name} Variant's Species.",
                    required=True,
                    origin=origin,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        oc.species = Variant(base=choices[0], name=answer)
            case Template.Fusion:
                oc.species = Fusion(*choices)
            case Template.Legendary | Template.Mythical | Template.UltraBeast | Template.Mega:
                oc.species = choices[0]
                oc.abilities = choices[0].abilities.copy()
            case _:
                oc.species = choices[0]
                oc.abilities &= oc.species.abilities

        oc.image = oc.image or oc.default_image

        if species := oc.species:
            progress.add(cls.name)
            moves = species.movepool()
            if not oc.moveset and len(moves) <= 6:
                oc.moveset = frozenset(moves)
            if not oc.abilities and len(species.abilities) == 1:
                oc.abilities = species.abilities.copy()


class PreEvoSpeciesField(TemplateField):
    name = "Pre-Evolution"
    description = "Optional. Fill the OC's Pre evo Species"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        if isinstance(species := oc.species, Fakemon):
            mon = species.species_evolves_from
            return not mon or isinstance(mon, Pokemon)
        return True

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, Fakemon)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        mon_total = {x for x in Pokemon.all() if not x.banned}
        view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mon_total)
        async with view.send(title="Select if it has a canon Pre-Evo (Skip if not needed)", single=True) as choice:
            oc.species.evolves_from = choice.id if choice else None
            progress.add(cls.name)
            moves = oc.species.movepool()
            if not oc.moveset and len(moves) <= 6:
                oc.moveset = frozenset(moves)


class TypesField(TemplateField):
    name = "Types"
    escription = "Fill the OC's Types"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        species = oc.species
        if isinstance(species, (Fakemon, Variant, Fusion)):
            return oc.types in species.possible_types
        return False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fusion, Fakemon, Variant))

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
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
                    label="Select Typing",
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
                progress.add(cls.name)


class MovesetField(TemplateField):
    name = "Moveset"
    description = "Optional. Fill the OC's fav. moves"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        if species := oc.species:
            mon = Pokemon.from_ID("SMEARGLE")

            if isinstance(species, Fusion):
                condition = mon in species.bases
            elif isinstance(species, Variant):
                condition = mon == species.base
            elif isinstance(species, Fakemon):
                condition = mon == species.evolves_from
            else:
                condition = mon == species

            value = all(not x.banned for x in oc.moveset)

            if not condition:
                moves = oc.movepool()
                value &= all(x in moves for x in oc.moveset)

            return value

        return False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
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
        description = "\n".join(f"> {x!r}" for x in oc.moveset) or "No Moves"
        view = MoveComplex(member=ctx.user, moves=moves, target=ctx)
        async with view.send(
            title="Write the character's moveset. Current below",
            description=description,
        ) as choices:
            oc.moveset = frozenset(choices)
            if isinstance(oc.species, (Variant, Fakemon)) and not oc.movepool:
                oc.species.movepool = Movepool(tutor=oc.moveset.copy())
                progress.add("Movepool")
            progress.add(cls.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Optional. Fill the OC's movepool"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return all(not x.banned for x in oc.movepool())

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant))

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        view = MovepoolView(ctx, ctx.user, oc)
        await view.send()
        await view.wait()
        progress.add(cls.name)


class AbilitiesField(TemplateField):
    name = "Abilities"
    description = "Fill the OC's Abilities"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        condition = 1 <= len(oc.abilities) <= oc.max_amount_abilities
        if not isinstance(oc.species, (Fakemon, Variant)):
            condition &= all(x in oc.species.abilities for x in oc.abilities)
        return condition

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
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
                if isinstance(oc.species, (Fakemon, Variant)):
                    oc.species.abilities = frozenset(choices)
                progress.add(cls.name)


class HiddenPowerField(TemplateField):
    name = "Hidden Power"
    description = "Optional. Fill the OC's Hidden Power"

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        view = Complex[Typing](
            member=ctx.user,
            target=ctx,
            values=Typing.all(),
            max_values=1,
            timeout=None,
            parser=lambda x: (x.name, f"Sets the typing {x.name}"),
            text_component=TextInput(
                label="Character's Hidden Power",
                placeholder="Type",
                required=True,
            ),
            silent_mode=True,
        )
        async with view.send(title="Select Hidden Power", single=True) as types:
            oc.hidden_power = types
            progress.add(cls.name)


class SpAbilityField(TemplateField):
    name = "Special Ability"
    description = "Optional. Fill the OC's Special Ability"

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        return oc.can_have_special_abilities or not oc.sp_ability

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species and oc.can_have_special_abilities

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        view = SPAbilityView(ctx.user, oc)
        await ctx.followup.send("Continue with Submission", view=view)
        await view.wait()
        oc.sp_ability = view.sp_ability
        progress.add(cls.name)


class BackstoryField(TemplateField):
    name = "Backstory"
    description = "Optional. Fill the OC's Backstory"

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Backstory.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
                progress.add(cls.name)


class ExtraField(TemplateField):
    name = "Extra Information"
    description = "Optional. Fill the OC's Extra Information"

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Extra Information.",
            placeholder=oc.extra,
            default=oc.extra,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.extra = answer or None
                progress.add(cls.name)


class ImageField(TemplateField):
    name = "Image"
    description = "Fill the OC's Image"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    def evaluate(cls, oc: Character) -> bool:
        if oc.image and not isinstance(oc.image, File):
            return oc.image != oc.default_image
        return False

    @classmethod
    async def on_submit(cls, ctx: Interaction, template: Template, progress: set[str], oc: Character):
        default_image = oc.image_url or oc.image or oc.default_image
        view = ImageView(member=ctx.user, default_img=default_image, target=ctx)
        async with view.send() as text:
            if text and isinstance(text, str):
                oc.image = text
                progress.add(cls.name)

        if oc.image == oc.default_image or (oc.image != default_image and (isinstance(oc.image, str) or not oc.image)):
            db: AsyncIOMotorCollection = ctx.client.mongo_db("OC Background")
            if img := await db.find_one({"author": oc.author}):
                img: str = img["image"]
            img = oc.generated_image(img)
            if image := await ctx.client.get_file(img):
                oc.image = image
            ctx.client.logger.info(str(img))

        return None


class CreationOCView(Basic):
    def __init__(
        self,
        bot: CustomBot,
        ctx: Interaction,
        user: Member,
        oc: Optional[Character] = None,
        template: Optional[Template] = None,
        progress: set[str] = None,
    ):
        super(CreationOCView, self).__init__(target=ctx, member=user, timeout=None)
        self.embed.title = "Character Creation"
        self.bot = bot
        oc = oc.copy() if oc else Character()
        oc.author, oc.server = user.id, ctx.guild.id
        self.oc = oc
        self.user = user
        self.embeds = oc.embeds
        self.embeds[0].set_author(name=user.display_name, icon_url=user.display_avatar)

        if not isinstance(template, Template):
            if isinstance(template, str):
                name = template
            else:
                name = type(oc.species).__name__

            name = name.replace("Fakemon", "CustomPokemon")
            if _BEASTBOOST in oc.abilities and name == "CustomPokemon":
                name = "CustomUltraBeast"

            try:
                template = Template[name]
            except KeyError:
                template = Template.Pokemon

        self.ref_template = template
        self.progress: set[str] = set()
        if progress:
            self.progress.update(progress)
        if not oc.id:
            self.remove_item(self.finish_oc)
        self.setup()

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        cog = interaction.client.get_cog("Submission")

        if self.user == cog.supporting.get(interaction.user, interaction.user):
            return True

        embed = Embed(title="This OC isn't yours", color=Color.red(), timestamp=interaction.created_at)
        embed.set_author(name=self.user.display_name, icon_url=self.user.display_avatar)
        embed.set_image(url=WHITE_BAR)

        await resp.send_message(embed=embed, ephemeral=True)
        return False

    def setup(self):
        self.kind.options = [
            SelectOption(
                label=x.name,
                emoji="\N{MEMO}",
                default=x == self.ref_template,
            )
            for x in Template
        ]
        self.fields.options = [
            SelectOption(
                label=item.name,
                description=item.description,
                emoji=(
                    ("\N{BLACK SQUARE BUTTON}" if (item.name in self.progress) else "\N{BLACK LARGE SQUARE}")
                    if (item.evaluate(self.oc))
                    else "\N{CROSS MARK}"
                ),
            )
            for item in TemplateField.all()
            if item.check(self.oc)
        ]
        self.submit.label = "Save Changes" if self.oc.id else "Submit"
        self.submit.disabled = any(str(x.emoji) == "\N{CROSS MARK}" for x in self.fields.options)

    @select(placeholder="Select Kind", row=0)
    async def kind(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        try:
            self.oc.species = None
            self.progress -= {"Species", "Types", "Abilities", "Moveset"}
            self.ref_template = Template[sct.values[0]]

            match self.ref_template:
                case (
                    Template.Legendary
                    | Template.Mythical
                    | Template.UltraBeast
                    | Template.CustomLegendary
                    | Template.CustomMythical
                    | Template.CustomUltraBeast
                ):
                    self.progress -= {"Special Ability"}
                    self.oc.sp_ability = None
                    if self.ref_template == Template.CustomUltraBeast:
                        self.oc.abilities = frozenset({_BEASTBOOST})

            m = self.message
            if m and not m.flags.ephemeral:
                db = self.bot.mongo_db("OC Creation")
                await db.replace_one(
                    dict(id=m.id),
                    dict(
                        id=m.id,
                        template=self.ref_template.name,
                        author=self.user.id,
                        character=self.oc.to_mongo_dict(),
                        progress=list(self.progress),
                    ),
                    upsert=True,
                )

            self.setup()
            if resp.is_done():
                await ctx.edit_original_message(embeds=self.oc.embeds, view=self)
            else:
                await resp.edit_message(embeds=self.oc.embeds, view=self)
        except Exception as e:
            self.bot.logger.exception("Exception in OC Creation", exc_info=e)
            await resp.send_message(str(e), ephemeral=True)
            self.stop()

    @select(placeholder="Click here!", row=1)
    async def fields(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        try:
            if item := TemplateField.get(name=sct.values[0]):
                await item.on_submit(ctx, self.ref_template, self.progress, self.oc)
        except Exception as e:
            ctx.client.logger.exception("Exception in OC Creation", exc_info=e)
            await ctx.followup.send(str(e), ephemeral=True)
        finally:
            self.setup()

        try:
            embeds = self.oc.embeds
            embeds[0].set_author(name=self.user.display_name, icon_url=self.user.display_avatar)
            if not self.oc.image_url:
                embeds[0].set_image(url="attachment://image.png")
            files = [self.oc.image] if isinstance(self.oc.image, File) else MISSING
            try:
                message = self.message or ctx.message
                m = await message.edit(embeds=embeds, view=self, attachments=files)
            except NotFound as e:
                ctx.client.logger.exception(
                    "NotFound Exception Message\n\nctx: %s\nself: %s",
                    repr(ctx.message),
                    repr(self.message),
                    exc_info=e,
                )
                await ctx.followup.send(str(e), ephemeral=True)
                return self.stop()
            except (DiscordException, AttributeError):
                m = await ctx.edit_original_message(embeds=embeds, view=self, attachments=files)

            if files and m.embeds[0].image.proxy_url:
                self.oc.image = m.embeds[0].image.proxy_url
                self.setup()
                m = await m.edit(view=self)

            if not m.flags.ephemeral:
                db = self.bot.mongo_db("OC Creation")
                await db.replace_one(
                    {"id": m.id},
                    {
                        "id": m.id,
                        "template": self.ref_template.name,
                        "author": self.user.id,
                        "character": self.oc.to_mongo_dict(),
                        "progress": list(self.progress),
                    },
                    upsert=True,
                )

            self.message = m
        except Exception as e:
            ctx.client.logger.exception("Exception in OC Creation Edit", exc_info=e)
            await ctx.followup.send(str(e), ephemeral=True)
            self.stop()

    async def delete(self, ctx: Optional[Interaction] = None) -> None:
        try:
            db = self.bot.mongo_db("OC Creation")
            if (m := self.message) and not m.flags.ephemeral:
                await db.delete_one({"id": m.id})
            return await super(CreationOCView, self).delete(ctx)
        except Exception as e:
            self.bot.logger.exception("Exception Deleting View", exc_info=e)

    @button(label="Delete Character", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=2)
    async def finish_oc(self, ctx: Interaction, _: Button):
        try:
            if self.oc.id and self.oc.thread:
                webhook: Webhook = await ctx.client.webhook(919277769735680050)
                thread = Object(id=self.oc.thread)
                await webhook.delete_message(self.oc.id, thread=thread)
            await self.delete(ctx)
        except Exception as e:
            self.bot.logger.exception("Exception Deleting Character", exc_info=e)

    @button(label="Close this Menu", row=2)
    async def cancel(self, ctx: Interaction, _: Button):
        try:
            await self.delete(ctx)
        except Exception as e:
            self.bot.logger.exception("Exception Closing Menu", exc_info=e)

    @button(disabled=True, label="Submit", style=ButtonStyle.green, row=2)
    async def submit(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        try:
            await resp.defer(ephemeral=True, thinking=True)
            cog = ctx.client.get_cog("Submission")
            word = "modified" if self.oc.id else "registered"
            await cog.register_oc(self.oc, image_as_is=True)
            registered = ctx.guild.get_role(719642423327719434)
            if registered and registered not in self.user.roles:
                await self.user.add_roles(registered)
            await ctx.followup.send(f"Character {word} without Issues!", ephemeral=True)
        except Exception as e:
            self.bot.logger.exception("Error in oc %s", btn.label, exc_info=e)
        finally:
            await self.delete(ctx)


class ModCharactersView(CharactersView):
    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        try:
            if item := self.current_choice:
                guild = self.member.guild
                cog = interaction.client.get_cog("Submission")
                user: Member = cog.supporting.get(interaction.user, interaction.user)
                if item.author in [user.id, interaction.user.id]:
                    view = CreationOCView(bot=interaction.client, ctx=interaction, user=user, oc=item)
                    if author := guild.get_member(item.author):
                        view.embeds[0].set_author(name=author.display_name, icon_url=author.display_avatar)
                    await view.send(embeds=view.embeds, ephemeral=True)
                else:
                    if isinstance(self.target, Interaction):
                        target = self.target
                    else:
                        target = interaction

                    ephemeral = self.message.flags.ephemeral
                    view = PingView(oc=item, reference=target)
                    await interaction.followup.send(
                        embeds=item.embeds,
                        view=view,
                        ephemeral=ephemeral,
                    )
                await view.wait()
        except Exception as e:
            interaction.client.logger.exception("Error in ModOCView", exc_info=e)
        finally:
            await super(CharactersView, self).select_choice(interaction, sct)
