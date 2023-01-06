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
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
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
    Message,
    SelectOption,
    TextStyle,
)
from discord.ui import (
    Button,
    Modal,
    Select,
    TextInput,
    UserSelect,
    View,
    button,
    select,
)
from discord.utils import MISSING, get, time_snowflake
from frozendict import frozendict
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.submission.oc_parsers import ParserMethods
from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability
from src.structures.bot import CustomBot
from src.structures.character import AgeGroup, Character, Nature, Size
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pokeball import Pokeball
from src.structures.pronouns import Pronoun
from src.structures.species import (
    Chimera,
    CustomMega,
    CustomParadox,
    Fakemon,
    Fusion,
    Mega,
    Paradox,
    Pokemon,
    Species,
    Variant,
)
from src.utils.etc import RICH_PRESENCE_EMOJI, WHITE_BAR
from src.views.ability_view import SPAbilityView
from src.views.characters_view import BaseCharactersView, CharactersView, PingView
from src.views.image_view import ImageView
from src.views.move_view import MovepoolMoveComplex
from src.views.movepool_view import MovepoolView
from src.views.size_view import HeightView, WeightView
from src.views.species_view import SpeciesComplex


@dataclass(unsafe_hash=True, slots=True)
class TemplateItem:
    description: str = ""
    fields: frozendict[str, str] = field(default_factory=frozendict)
    docs: frozendict[str, str] = field(default_factory=frozendict)

    def __init__(self, data: dict[str, str]) -> None:
        self.description = data.get("description", "")
        modifier = data.get("modifier", {})
        default = dict(
            Name="Name",
            Species="Species",
            Types="Type, Type",
            Age="Age",
            Pronoun="He/She/Them",
            Abilities="Ability, Ability",
            Moveset="Move, Move, Move, Move, Move, Move",
        )

        exclude = data.get("exclude", [])
        fields = {x[0]: x[1] for k, v in default.items() if (x := modifier.get(k, (k, v))) and x[0] not in exclude}
        self.fields = frozendict(fields)
        self.docs = frozendict(data.get("docs", {}))


class Template(TemplateItem, Enum):
    Pokemon = dict(
        description="Normal residents that resemble Pokemon.",
        exclude=["Types"],
        docs={
            "Standard": "1_fj55cpyiHJ6zZ4I3FF0o9FbBhl936baflE_7EV8wUc",
            "Unique Trait": "1dyRmRALOGgDCwscJoEXblIvoDcKwioNlsRoWw7VrOb8",
        },
    )
    Fusion = dict(
        description="Individuals that share traits of two species.",
        modifier={"Species": ("Species", "Species 1, Species 2")},
        docs={
            "Standard": "1i023rpuSBi8kLtiZ559VaxaOn-GMKqPo53QGiKZUFxM",
            "Unique Trait": "1pQ-MXvidesq9JjK1sXcsyt7qBVMfDHDAqz9fXdf5l6M",
        },
    )
    Variant = dict(
        description="Fan-made. Species variations (movesets, types)",
        modifier={"Species": ("Variant", "Variant Species")},
        docs={
            "Standard": "1T4Y8rVotXpRnAmCrOrVguIHszi8lY_iuSZcP2v2MiTY",
            "Unique Trait": "1o2C_GEp9qg2G8R49tC_j_9EIRgFsvc225gEku8NYE7A",
        },
    )
    CustomPokemon = dict(
        description="Fan-made. They are normal residents.",
        modifier={"Species": ("Fakemon", "Fakemon Species")},
        docs={
            "Standard": "1R9s-o018-ClHHP_u-eEIa038dfmQdNxssbP74PfVezY",
            "Unique Trait": "1CSi0yHJngnWRVdVnqUWwnNK9qXSubxPNSWAZtShSDF8",
            "Evolution": "1v48lBR4P5ucWtAFHBy0DpIzUCUPCQHVFlz4q-it-pj8",
            "Evolution w/ Unique Trait": "1NCHKjzdIQhxM4djpBrFrDxHgBU6ISCr_qRaRwHLJMWA",
        },
    )
    CustomMega = dict(
        description="Fan-made. Mega evolved and kept stuck like this.",
        modifier={"Species": ("Fakemon", "Mega Species")},
        docs={
            "Standard": "1KOQMm-ktM0Ad8nIncDxcYUQehF2elWYUg09FId6J_B0",
            "Unique Trait": "1tQPKNdxQTA33eUwNgWVGZMYJ3iQzloZIbSNirRXqhj4",
        },
    )
    CustomParadox = dict(
        description="Fan-made. From distant past/future, somehow ended up here.",
        modifier={"Species": ("Fakemon", "Paradox Species")},
        docs={
            "Standard": "1R9s-o018-ClHHP_u-eEIa038dfmQdNxssbP74PfVezY",
            "Unique Trait": "1CSi0yHJngnWRVdVnqUWwnNK9qXSubxPNSWAZtShSDF8",
        },
    )

    async def process(self, oc: Character, ctx: Interaction, ephemeral: bool):
        choices: list[Species] = []
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")

        if mons := self.total_species:
            date_value = time_snowflake(ctx.created_at - timedelta(days=14))
            key = {
                "server": ctx.guild_id,
                "$or": [
                    {"id": {"$gte": date_value}},
                    {"location": {"$gte": date_value}},
                    {"last_used": {"$gte": date_value}},
                ],
            }
            if role := get(ctx.guild.roles, name="Registered"):
                key["author"] = {"$in": [x.id for x in role.members]}
            ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
            view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mons, max_values=self.max_values, ocs=ocs)
            async with view.send(ephemeral=ephemeral) as data:
                if self.min_values <= len(data) <= self.max_values:
                    choices.extend(data)
                else:
                    return

        match self:
            case self.Pokemon:
                oc.species, abilities = choices[0], choices[0].abilities.copy()
                if len(abilities) <= oc.max_amount_abilities:
                    oc.abilities = abilities
                else:
                    oc.abilities &= abilities
            case self.Fusion:
                oc.species = Fusion(*choices, ratio=0.5)
            case self.Variant:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label=f"{choices[0].name} Variant"[:45],
                    ephemeral=ephemeral,
                    default=choices[0].name,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        oc.species = Variant(base=choices[0], name=answer)
            case self.CustomParadox:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label=f"Paradox {choices[0].name}"[:45],
                    ephemeral=ephemeral,
                    default=choices[0].name,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        oc.species = CustomParadox(choices[0], name=answer)
            case self.CustomMega:
                oc.species = CustomMega(choices[0])
                oc.abilities &= oc.species.abilities
            case self.CustomPokemon:
                name = oc.species.name if isinstance(oc.species, Fakemon) else None
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label="OC's Species.",
                    required=True,
                    ephemeral=ephemeral,
                    default=name,
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

    @property
    def min_values(self):
        match self:
            case self.Fusion:
                return 2
            case _:
                return 1

    @property
    def max_values(self):
        match self:
            case self.Fusion:
                return 2
            case _:
                return 1

    @property
    def total_species(self) -> frozenset[Species]:
        match self:
            case self.Pokemon | self.Fusion:
                mon_total = Species.all()
            case (self.CustomMega | self.Variant | self.CustomParadox):
                mon_total = Species.all(exclude=(Mega, Paradox))
            case _:
                mon_total = []
        return frozenset({x for x in mon_total if not x.banned})

    @property
    def text(self):
        return "\n".join(f"{k}: {v}" for k, v in self.fields.items())

    @property
    def title(self):
        name = self.name
        if name.startswith("Custom"):
            name = name.removeprefix("Custom") + " (Custom)"
        return name.strip()

    @property
    def formatted_text(self):
        return f"```yaml\n{self.text}\n```"

    @property
    def gdocs(self):
        embed = Embed(
            title=f"Available Templates - {self.title}",
            description="Make a copy of our templates, make sure it has reading permissions and then send the URL in this channel.",
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)

        view = View()
        for index, (key, doc_id) in enumerate(self.docs.items()):
            url = f"https://docs.google.com/document/d/{doc_id}/edit?usp=sharing"
            view.add_item(Button(label=key, url=url, row=index, emoji=RICH_PRESENCE_EMOJI))

        embed.set_footer(text=self.description)
        return embed, view


class TemplateField(ABC):
    name: str = ""
    description: str = ""
    required: bool = False

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
    def evaluate(cls, _: Character) -> Optional[str]:
        return None

    @classmethod
    @abstractmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        """Abstract method which affects progress and the character"""


class NameField(TemplateField):
    name = "Name"
    description = "Modify the OC's Name"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.name:
            return "Missing Name"

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        handler = text_view.handle(
            label="OC's Name.",
            placeholder=f"> {oc.name}",
            default=oc.name,
            required=True,
            ephemeral=ephemeral,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = " ".join(answer.strip().title().split())
                progress.add(cls.name)


class AgeField(TemplateField):
    name = "Age"
    description = "Modify the OC's Age"
    required: bool = True

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[AgeGroup](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=AgeGroup,
            parser=lambda x: (x.name, x.description),
            sort_key=lambda x: x.key,
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Age.",
            description=f"> {oc.age.name}",
            single=True,
            ephemeral=ephemeral,
        ) as age:
            if isinstance(age, AgeGroup):
                oc.age = age
                progress.add(cls.name)


class PronounField(TemplateField):
    name = "Pronoun"
    description = "He, She, Them"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.pronoun:
            return "No pronoun added."

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Pronoun](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=Pronoun,
            max_values=len(Pronoun),
            parser=lambda x: (x.name, f"Adds {x.name} as pronoun."),
            sort_key=lambda x: x.name,
            silent_mode=True,
            auto_choice_info=True,
            auto_conclude=False,
        )
        async with view.send(
            title=f"{template.title} Character's Pronoun.",
            description=f"> {oc.pronoun_text}",
            ephemeral=ephemeral,
        ) as pronoun:
            if pronoun:
                oc.pronoun = frozenset(pronoun)
                progress.add(cls.name)


class SpeciesField(TemplateField):
    name = "Species"
    description = "Modify the OC's Species"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not (species := oc.species):
            return "Missing Species"

        if species.banned or isinstance(species, Chimera):
            return f"{species.name} as species are banned."

        if isinstance(species, (Variant, CustomMega, CustomParadox)) and isinstance(species.base, (Paradox, Mega)):
            return f"{species.base.name} can't have variants."

        if isinstance(species, Fakemon) and isinstance(species.species_evolves_from, (Paradox, Mega)):
            return f"{species.species_evolves_from.name} can't custom evolve."

        if isinstance(species, Fusion) and len(species.bases) != 2:
            return "Must include 2 species."

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        await template.process(oc=oc, ctx=ctx, ephemeral=ephemeral)
        if species := oc.species:
            progress.add(cls.name)
            moves = species.total_movepool()
            if not oc.moveset and len(moves) <= 6:
                oc.moveset = frozenset(moves)
            if not oc.abilities and len(species.abilities) == 1:
                oc.abilities = species.abilities.copy()
            oc.size = oc.weight = Size.M


class FusionRatioField(TemplateField):
    name = "Proportion"
    description = "Modify the OC's Fusion Ratio"
    required: bool = False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, Fusion)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        mon: Fusion = oc.species
        view = Complex[Fusion](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=mon.ratios,
            emoji_parser=lambda x: "\N{BLACK SQUARE BUTTON}" if x.ratio == mon.ratio else "\N{BLACK LARGE SQUARE}",
            parser=lambda x: (x.label_name[:100], {0.5: "Default"}.get(x.ratio)),
            sort_key=lambda x: x.ratio,
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Proportion.",
            description=f"> {mon.label_name}",
            single=True,
            ephemeral=ephemeral,
        ) as species:
            if isinstance(species, Fusion):
                oc.species = species
                oc.species.types = mon.types
                oc.size = oc.weight = Size.M
                progress.add(cls.name)


class SizeField(TemplateField):
    name = "Size"
    description = "Modify the OC's Size"
    required: bool = False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    def evaluate(cls, oc: Character):
        if not isinstance(oc.size, float):
            return

        info: list[str] = []
        m = Move.get(name="Transform")
        if m not in oc.total_movepool:
            if oc.size < Size.XXXS.height_value(oc.species.height):
                info = Size.XXXS.height_info(oc.species.height)
                info.append(f"Min {info}")

            if oc.size > Size.XXXL.height_value(oc.species.height):
                info = Size.XXXL.height_info(oc.species.height)
                info.append(f"Max {info}")
        elif not (0.1 <= oc.size <= 100.0):
            info.append("Invalid height.")

        return ", ".join(info)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):

        if isinstance(oc.size, Size):
            height = oc.species.height if oc.species else 0
            info = oc.size.height_info(height)
        else:
            info = Size.M.height_info(oc.size)

        view = HeightView(target=ctx, member=ctx.user, oc=oc)
        await view.send(
            title=f"{template.title} Character's Size.",
            description=f"> {info}",
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class WeightField(TemplateField):
    name = "Weight"
    description = "Modify the OC's Weight"
    required: bool = False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    def evaluate(cls, oc: Character):
        if not isinstance(oc.weight, float):
            return

        info: list[str] = []
        m = Move.get(name="Transform")
        if m not in oc.total_movepool:
            if oc.weight < Size.XXXS.weight_value(oc.species.weight):
                info = Size.XXXS.weight_info(oc.species.weight)
                info.append(f"Min {info}")

            if oc.weight > Size.XXXL.weight_value(oc.species.weight):
                info = Size.XXXL.weight_info(oc.species.weight)
                info.append(f"Max {info}")
        elif not (0.1 <= oc.weight <= 999.9):
            info.append("Invalid weight")

        return ", ".join(info)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):

        if isinstance(oc.weight, Size):
            weight = oc.species.weight if oc.species else 0
            info = oc.weight.weight_info(weight)
        else:
            info = Size.M.weight_info(oc.weight)

        weight = oc.species.weight if oc.species else 0
        view = WeightView(target=ctx, member=ctx.user, oc=oc)
        await view.send(
            title=f"{template.title} Character's Weight.",
            description=f"> {info}",
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class PreEvoSpeciesField(TemplateField):
    name = "Pre-Evolution"
    description = "Modify the OC's Pre evo Species"
    required: bool = False

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if isinstance(species := oc.species, Fakemon):
            mon = species.species_evolves_from
            if mon and not isinstance(mon, Pokemon):
                return "Invalid Pre-Evolution Species. Has to be a Common Pokemon"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, Fakemon)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        mon_total = {x for x in Species.all(exclude=(Paradox, Mega)) if not x.banned}
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        key = {"server": ctx.guild_id}
        if role := get(ctx.guild.roles, name="Registered"):
            key["author"] = {"$in": [x.id for x in role.members]}
        ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
        view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mon_total, ocs=ocs)
        async with view.send(
            title="Select if it has a canon Pre-Evo (Skip if not needed)",
            single=True,
            ephemeral=ephemeral,
        ) as choice:
            oc.species.evolves_from = choice.id if choice else None
            progress.add(cls.name)
            moves = oc.species.movepool()
            if not oc.moveset and len(moves) <= 6:
                oc.moveset = frozenset(moves)


class TypesField(TemplateField):
    name = "Types"
    description = "Modify the OC's Types"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if isinstance(species := oc.species, Species):
            if not (mon_types := species.possible_types):
                return "No possible types for current species"
            if oc.types not in mon_types:
                return ", ".join("/".join(y.name for y in x) for x in mon_types)

        if not oc.types:
            return "Types have not been specified."

        if TypingEnum.Shadow in oc.types:
            return "Shadow typing is not valid"

        if TypingEnum.Typeless in oc.types:

            if len(oc.types) != 1:
                return "Typeless can't have types, duh."

            if not isinstance(oc.species, (Variant, Fakemon)):
                return "For Variants or Custom pokemon"

        if len(oc.types) > 2:
            return f"Max 2 Pokemon Types: ({', '.join(x.name for x in oc.types)})"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant, CustomMega, Fusion, CustomParadox))

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        species = oc.species

        if single := isinstance(species, Fusion):

            def parser(x: set[TypingEnum]):
                return (y := "/".join(i.name for i in x), f"Adds the typing {y}")

            values, max_values = species.possible_types, 1

        else:

            def parser(x: TypingEnum):
                return (x.name, f"Adds the typing {x.name}")

            ignore = [TypingEnum.Shadow, TypingEnum.Typeless]
            if template in [Template.Variant, Template.CustomPokemon]:
                ignore.remove(TypingEnum.Typeless)

            values, max_values = TypingEnum.all(*ignore), 2

        view = Complex(
            member=ctx.user,
            target=ctx,
            values=values,
            parser=parser,
            sort_key=parser,
            max_values=max_values,
            timeout=None,
            silent_mode=True,
            auto_text_component=True,
            auto_choice_info=True,
            auto_conclude=False,
        )

        async with view.send(
            title=f"{template.title} Character's Typing",
            single=single,
            ephemeral=ephemeral,
        ) as types:
            if types:
                types = frozenset(types)
                if not isinstance(oc.image, File) and species.types != types:
                    oc.image = None
                species.types = types
                progress.add(cls.name)


class MovesetField(TemplateField):
    name = "Moveset"
    description = "Modify the OC's fav. moves"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if len(oc.moveset) > 6:
            return "Max 6 Preferred Moves."

        m1, m2 = Move.get(name="Transform"), Move.get(name="Sketch")

        movepool = Movepool.default(oc.total_movepool)
        shadow = TypingEnum.Shadow in oc.types

        if m1 in movepool or m2 in movepool or shadow:
            movepool = Movepool(other=Move.all(banned=False, shadow=shadow))

        moves = movepool()
        return ", ".join(x.name for x in oc.moveset if x not in moves)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        m1, m2 = Move.get(name="Transform"), Move.get(name="Sketch")
        movepool = Movepool.default(oc.total_movepool)
        shadow = TypingEnum.Shadow in oc.types

        if m1 in movepool or m2 in movepool or shadow:
            movepool = Movepool(other=Move.all(banned=False, shadow=shadow))

        view = MovepoolMoveComplex(
            member=ctx.user,
            movepool=movepool,
            target=ctx,
            choices={x for x in oc.moveset if x in movepool},
        )
        async with view.send(
            title=f"{template.title} Character's Moveset",
            ephemeral=ephemeral,
        ) as choices:
            if choices:
                oc.moveset = frozenset(choices)
                if (
                    isinstance(
                        oc.species,
                        (Fakemon, Variant, CustomParadox),
                    )
                    and not oc.movepool
                    and not shadow
                ):
                    oc.species.movepool = Movepool(tutor=oc.moveset.copy())
                    progress.add(MovepoolField.name)
                progress.add(cls.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Modify the OC's movepool"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        return ", ".join(x for x in oc.movepool() if x.banned)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant, CustomParadox)) and TypingEnum.Shadow not in oc.types

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = MovepoolView(ctx, ctx.user, oc)
        await view.send(
            title=f"{template.title} OC's Movepool"[:45],
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class AbilitiesField(TemplateField):
    name = "Abilities"
    description = "Modify the OC's Abilities"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        amount = oc.max_amount_abilities
        m = Move.get(name="Transform")

        if not 1 <= len(oc.abilities) <= amount:
            return f"Abilities, Min: 1, Max: {amount}"

        if (
            not isinstance(
                oc.species,
                (Fakemon, Variant, CustomMega, CustomParadox),
            )
            and m not in oc.total_movepool
        ):
            return ", ".join(x.name for x in oc.abilities if x not in oc.species.abilities)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        abilities, amount, m = (
            oc.species.abilities,
            oc.max_amount_abilities,
            Move.get(name="Transform"),
        )
        if template == Template.CustomParadox:
            abilities = {Ability.get(name="Protosynthesis"), Ability.get(name="Quark Drive")}
            amount = 1
        elif (
            isinstance(
                oc.species,
                (Fakemon, Variant, CustomMega),
            )
            or (not abilities)
            or m in oc.total_movepool
        ):
            abilities = ALL_ABILITIES.values()

        view = Complex[Ability](
            member=ctx.user,
            values=abilities,
            timeout=None,
            target=ctx,
            max_values=amount,
            sort_key=lambda x: x.name,
            parser=lambda x: (x.name, x.description),
            silent_mode=True,
            auto_text_component=True,
            auto_choice_info=True,
            auto_conclude=False,
        )
        async with view.send(
            title=f"{template.title} Character's Abilities",
            ephemeral=ephemeral,
        ) as choices:
            if choices:
                oc.abilities = frozenset(choices)
                if isinstance(oc.species, (Fakemon, Variant, CustomParadox)):
                    oc.species.abilities = frozenset(choices)
                progress.add(cls.name)


class HiddenPowerField(TemplateField):
    name = "Hidden Power"
    description = "Typing that matches with their soul's"
    required: bool = False

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if oc.hidden_power and oc.hidden_power in [TypingEnum.Shadow, TypingEnum.Typeless]:
            return "Invalid Hidden Power."

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[TypingEnum](
            member=ctx.user,
            target=ctx,
            values=TypingEnum.all(TypingEnum.Shadow, TypingEnum.Typeless),
            timeout=None,
            sort_key=lambda x: x.name,
            parser=lambda x: (x.name, f"Sets the typing {x.name}"),
            silent_mode=True,
            auto_text_component=True,
        )
        async with view.send(
            title=f"{template.title} Character's Hidden Power",
            single=True,
            ephemeral=ephemeral,
        ) as types:
            oc.hidden_power = types
            progress.add(cls.name)


class NatureField(TemplateField):
    name = "Nature"
    description = "OC's Nature"
    required: bool = False

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Nature](
            member=ctx.user,
            target=ctx,
            values=Nature,
            timeout=None,
            sort_key=lambda x: x.name,
            parser=lambda x: (x.name, x.description),
            silent_mode=True,
            auto_text_component=True,
        )
        async with view.send(
            title=f"{template.title} Character's Nature",
            single=True,
            ephemeral=ephemeral,
        ) as nature:
            oc.nature = nature
            progress.add(cls.name)


class UniqueTraitField(TemplateField):
    name = "Unique Trait"
    description = "No other in species but OC can do it."
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if (sp_ability := oc.sp_ability) and (
            text := ", ".join(
                k
                for k, v in dict(
                    name=sp_ability.name,
                    origin=sp_ability.origin,
                    description=sp_ability.description,
                ).items()
                if not v
            )
        ):
            return f"Missing {text}."

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = SPAbilityView(ctx, ctx.user, oc)
        await view.send(ephemeral=ephemeral)
        await view.wait()

        if view.sp_ability.valid:
            oc.sp_ability = view.sp_ability
        else:
            oc.sp_ability = None
        progress.add(cls.name)


class BackstoryField(TemplateField):
    name = "Bio"
    description = "Define who is the character."
    required: bool = True

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="OC's Bio.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=False,
            ephemeral=ephemeral,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
                progress.add(cls.name)


class PersonalityField(TemplateField):
    name = "Personality"
    description = "Modify the OC's Personality"
    required: bool = False

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="OC's Personality.",
            placeholder=oc.personality,
            ephemeral=ephemeral,
            default=oc.personality,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.personality = answer or None
                progress.add(cls.name)


class ExtraField(TemplateField):
    name = "Extra Information"
    description = "Modify the OC's Extra Information"
    required: bool = False

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="OC's Extra Information.",
            placeholder=oc.extra,
            ephemeral=ephemeral,
            default=oc.extra,
            required=False,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.extra = answer or None
                progress.add(cls.name)


class ImageField(TemplateField):
    name = "Image"
    description = "Modify the OC's Image"
    required: bool = True

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species and oc.types

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.image:
            return "No Image has been defined"
        if oc.image == oc.default_image or isinstance(oc.image, File):
            return "Default Image in Memory"

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        default_image = oc.image_url or oc.image or oc.default_image
        view = ImageView(member=ctx.user, default_img=default_image, target=ctx)
        async with view.send(ephemeral=ephemeral) as text:
            if text and isinstance(text, str):
                oc.image = text
                progress.add(cls.name)

        if oc.image == oc.default_image or (oc.image != default_image and (isinstance(oc.image, str) or not oc.image)):
            db: AsyncIOMotorCollection = ctx.client.mongo_db("OC Background")
            if img := await db.find_one({"author": oc.author, "server": oc.server}):
                url = oc.generated_image(img["image"])
                ctx.client.logger.info(url)
                img = await ctx.client.get_file(url)

            if img is None:
                url = oc.generated_image()
                ctx.client.logger.info(url)
                img = await ctx.client.get_file(url)

            if img:
                oc.image = img

        return None


class PokeballField(TemplateField):
    name = "Pokeball"
    description = "Specify if OC has a pokeball or not"
    required: bool = False

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species

    @classmethod
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Pokeball](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=Pokeball,
            parser=lambda x: (x.label, None),
            sort_key=lambda x: x.name,
            silent_mode=True,
            auto_text_component=True,
        )
        current = oc.pokeball.label if oc.pokeball else None
        async with view.send(
            title=f"{template.title} Character's Pokeball.",
            description=f"> {current}",
            single=True,
            ephemeral=ephemeral,
        ) as pokeball:
            oc.pokeball = pokeball
            progress.add(cls.name)


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
        if not oc.author:
            oc.author = user.id
        if not oc.server:
            oc.server = ctx.guild_id
        self.oc = oc
        self.user = user
        self.embeds = oc.embeds
        message = getattr(ctx, "message", ctx)
        self.ephemeral = isinstance(message, Message) and message.flags.ephemeral
        if not isinstance(template, Template):
            if isinstance(template, str):
                name = template
            else:
                name = type(oc.species).__name__

            name = name.replace("Fakemon", "CustomPokemon")
            if name == "CustomPokemon":
                if get(oc.abilities, name="Beast Boost"):
                    name = "CustomUltraBeast"
                elif get(oc.abilities, name="Protosynthesis") or get(oc.abilities, name="Quark Drive"):
                    name = "CustomParadox"

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

    def setup(self, embed_update: bool = True):
        self.kind.options = [
            SelectOption(
                label=x.title,
                value=x.name,
                emoji="\N{MEMO}",
                default=x == self.ref_template,
                description=x.description[:100],
            )
            for x in Template
        ]
        self.fields1.options.clear()
        self.fields2.options.clear()
        for item in filter(lambda x: x.check(self.oc), TemplateField.all()):
            emoji = "\N{BLACK SQUARE BUTTON}" if (item.name in self.progress) else "\N{BLACK LARGE SQUARE}"

            if not (description := item.evaluate(self.oc)):
                description = item.description
            else:
                emoji = "\N{CROSS MARK}"

            menu = self.fields1 if item.required else self.fields2
            menu.add_option(label=item.name, description=description[:100], emoji=emoji)

        items = {"Essentials": self.fields1, "Extras": self.fields2}

        errors: int = 0
        for x, y in items.items():
            if count := sum(str(o.emoji) == "\N{CROSS MARK}" for o in y.options):
                y.options.sort(key=lambda x: str(x.emoji) != "\N{CROSS MARK}")
                y.placeholder = f"{x}. ({count} needed changes)."
            else:
                y.placeholder = f"{x}. Click here!"
            errors += count

        self.submit.label = "Save Changes" if self.oc.id else "Submit"
        self.cancel.label = "Close this Menu"
        self.finish_oc.label = "Delete OC"
        self.help.label = "Request Help"
        self.submit.disabled = bool(errors)

        if embed_update:
            embeds = self.oc.embeds
            embeds[0].set_author(name=self.user.display_name, icon_url=self.user.display_avatar)
            if not self.oc.image_url:
                embeds[0].set_image(url="attachment://image.png")
            self.embeds = embeds

    @select(placeholder="Select Kind", row=0)
    async def kind(self, ctx: Interaction, sct: Select):
        try:
            self.oc.species = None
            items: list[TemplateField] = [SpeciesField, TypesField, AbilitiesField, MovepoolField]
            self.progress -= {x.name for x in items}
            self.ref_template = Template[sct.values[0]]
            self.oc.size = self.oc.weight = Size.M

            if self.ref_template == Template.CustomParadox and not (
                len(self.oc.abilities) == 1
                and (get(self.oc.abilities, name="Protosynthesis") or get(self.oc.abilities, name="Quark Drive"))
            ):
                self.oc.abilities = frozenset()

            await self.update(ctx)
        except Exception as e:
            self.bot.logger.exception("Exception in OC Creation", exc_info=e)
            self.stop()

    @property
    def data(self):
        data = {}
        reference = self.message or self.oc
        if reference and reference.id:
            data["id"] = reference.id

        return data | dict(
            template=self.ref_template.name,
            author=self.user.id,
            character=self.oc.to_mongo_dict(),
            progress=list(self.progress),
            server=self.oc.server,
        )

    async def update(self, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        if self.is_finished():
            return
        self.setup()
        embeds = self.embeds
        files = [self.oc.image] if "Image" in self.progress and isinstance(self.oc.image, File) else MISSING

        try:
            if resp.is_done():
                message = self.message or ctx.message
                if not message.flags.ephemeral:
                    message = message.channel.get_partial_message(message.id)
                try:
                    m = await message.edit(embeds=embeds, view=self, attachments=files)
                except DiscordException:
                    m = await ctx.edit_original_response(embeds=embeds, view=self, attachments=files)
            else:
                await resp.edit_message(embeds=embeds, view=self, attachments=files)
                m = await ctx.original_response()
        except (DiscordException, AttributeError):
            await self.help_method(ctx)
        else:
            if files and m.embeds[0].image.proxy_url:
                self.oc.image = m.embeds[0].image.proxy_url
                self.setup(embed_update=False)
                m = await m.edit(view=self)

            self.message = m

    async def handler_send(self, *, ephemeral: bool = False, embeds: list[Embed] = None):
        self.ephemeral = ephemeral
        self.embeds = embeds or self.embeds
        if not ephemeral:
            self.remove_item(self.help)
        return await self.send(embeds=self.embeds, ephemeral=ephemeral, content=str(self.oc.id or ""))

    @select(placeholder="Essentials. Click here!", row=1)
    async def fields1(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        if item := TemplateField.get(name=sct.values[0]):
            self.ephemeral = ctx.message.flags.ephemeral or self.ephemeral
            await resp.defer(ephemeral=self.ephemeral, thinking=True)
            await item.on_submit(ctx, self.ref_template, self.progress, self.oc, self.ephemeral)
        await self.update(ctx)

    @select(placeholder="Extras. Click here!", row=2)
    async def fields2(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        if item := TemplateField.get(name=sct.values[0]):
            self.ephemeral = ctx.message.flags.ephemeral or self.ephemeral
            await resp.defer(ephemeral=self.ephemeral, thinking=True)
            await item.on_submit(ctx, self.ref_template, self.progress, self.oc, self.ephemeral)
        await self.update(ctx)

    async def delete(self, ctx: Optional[Interaction] = None) -> None:
        db = self.bot.mongo_db("OC Creation")
        if m := self.message or ctx.message:
            guild_id = ctx.guild_id if ctx else self.oc.server
            await db.delete_one({"id": m.id, "server": guild_id})
        return await super(CreationOCView, self).delete(ctx)

    @button(label="Delete OC", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=3)
    async def finish_oc(self, ctx: Interaction, btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await ctx.response.edit_message(view=self)

        if self.oc.id and self.oc.thread:
            if not (channel := ctx.guild.get_channel_or_thread(self.oc.thread)):
                channel = await ctx.guild.fetch_channel(self.oc.thread)
            await channel.edit(archived=False)
            await channel.get_partial_message(self.oc.id).delete(delay=0)
        await self.delete(ctx)

    @button(emoji="\N{PRINTER}", style=ButtonStyle.blurple, row=3)
    async def printer(self, ctx: Interaction, _: Button):
        await ctx.response.defer(ephemeral=True, thinking=True)
        file = await self.oc.to_docx(ctx.client)
        await ctx.followup.send(file=file, ephemeral=True)
        ctx.client.logger.info("User %s printed %s", str(ctx.user), repr(self.oc))

    @button(label="Close this Menu", row=3)
    async def cancel(self, ctx: Interaction, btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await ctx.response.edit_message(view=self)
        await self.delete(ctx)

    async def help_method(self, ctx: Interaction):
        channel = ctx.guild.get_channel(852180971985043466)

        view = CreationOCView(
            bot=self.bot,
            ctx=channel,
            user=self.member,
            oc=self.oc,
            template=self.ref_template,
            progress=self.progress,
        )
        await view.handler_send(ephemeral=False)

        if isinstance(self.oc.image, str) and isinstance(file := await ctx.client.get_file(self.oc.image), File):
            embeds = view.embeds
            attachments = [file]
            embeds[0].set_image(url=f"attachment://{file.filename}")
            message = await view.message.edit(attachments=attachments, embeds=embeds)
            if image := message.embeds[0].image:
                self.oc.image = image.url

        await self.delete(ctx)

    @button(label="Request Help", row=3)
    async def help(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        await self.help_method(ctx)

    @button(disabled=True, label="Submit", style=ButtonStyle.green, row=3)
    async def submit(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        try:
            await resp.defer(ephemeral=True, thinking=True)
            cog = ctx.client.get_cog("Submission")
            word = "modified" if self.oc.id else "registered"
            self.oc.location, self.oc.last_used = None, ctx.id
            await cog.register_oc(self.oc, image_as_is=True)
            msg = await ctx.followup.send(f"Character {self.oc.name} {word} without Issues!", ephemeral=True, wait=True)
            await msg.delete(delay=2)
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
                user: Member = interaction.client.supporting.get(interaction.user, interaction.user)
                embeds = item.embeds
                if author := interaction.guild.get_member(item.author):
                    embeds[0].set_author(name=author.display_name, icon_url=author.display_avatar)
                if (
                    interaction.user.guild_permissions.manage_messages
                    or interaction.user.id == interaction.guild.owner_id
                    or item.author in [interaction.user.id, user.id]
                ):
                    view = CreationOCView(bot=interaction.client, ctx=interaction, user=user, oc=item)
                    await view.handler_send(ephemeral=True, embeds=embeds)
                else:
                    view = PingView(oc=item, reference=interaction)
                    await interaction.followup.send(content=item.id, embeds=embeds, view=view, ephemeral=True)

        except Exception as e:
            interaction.client.logger.exception("Error in ModOCView", exc_info=e)
        finally:
            await super(CharactersView, self).select_choice(interaction, sct)


class SubmissionModal(Modal):
    def __init__(self, text: str, ephemeral: bool = False):
        super(SubmissionModal, self).__init__(title="Character Submission Template")
        self.ephemeral = ephemeral
        self.text = TextInput(
            style=TextStyle.paragraph,
            label=self.title,
            placeholder="Template or Google Document goes here",
            default=text,
            required=True,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        refer_author = interaction.user
        try:
            author = interaction.client.supporting.get(refer_author, refer_author)
            async for item in ParserMethods.parse(text=self.text.value, bot=interaction.client):
                oc = Character.process(**item)
                view = CreationOCView(bot=interaction.client, ctx=interaction, user=author, oc=oc)
                if self.ephemeral:
                    await resp.edit_message(embeds=view.embeds, view=view)
                else:
                    await view.handler_send(ephemeral=False)
        except Exception as e:
            if not resp.is_done():
                await resp.defer(ephemeral=True, thinking=True)
            await interaction.followup.send(str(e), ephemeral=True)
            interaction.client.logger.exception(
                "Exception when registering, user: %s",
                str(interaction.user),
                exc_info=e,
            )
        else:
            if not resp.is_done():
                await resp.pong()
        finally:
            self.stop()


class TemplateView(View):
    def __init__(self, template: Template):
        super(TemplateView, self).__init__(timeout=None)
        self.template = template

    @select(
        placeholder="Select Submission Method",
        custom_id="method",
        options=[
            SelectOption(
                label="Form",
                description="This will pop-up a Menu.",
                emoji=RICH_PRESENCE_EMOJI,
            ),
            SelectOption(
                label="Message",
                description="Template to send within the channel.",
                emoji=RICH_PRESENCE_EMOJI,
            ),
            SelectOption(
                label="Google Document",
                description="Get URL, Copy Document, Send new URL in channel.",
                emoji=RICH_PRESENCE_EMOJI,
            ),
        ],
    )
    async def method(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        match sct.values[0]:
            case "Form":
                ephemeral = bool(get(ctx.user.roles, name="Registered"))
                modal = SubmissionModal(self.template.text, ephemeral=ephemeral)
                await resp.send_modal(modal)
                await modal.wait()
            case "Message":
                content = self.template.formatted_text
                await resp.edit_message(content=content, embed=None, view=None)
            case "Google Document":
                embed, view = self.template.gdocs
                await resp.edit_message(embed=embed, view=view)
        self.stop()


class SubmissionView(Basic):
    @select(
        placeholder="Click here to read our Templates",
        row=0,
        custom_id="read",
        options=[
            SelectOption(
                label=x.title,
                value=x.name,
                description=x.description[:100],
                emoji=RICH_PRESENCE_EMOJI,
            )
            for x in Template
        ],
    )
    async def show_template(self, ctx: Interaction, sct: Select) -> None:
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        embed = Embed(title="How do you want to register your character?", color=0xFFFFFE)
        template = Template[sct.values[0]]
        embed.set_image(url="https://hmp.me/dx38")
        embed.set_footer(text="After sending, bot will ask for backstory, extra info and image.")
        await ctx.followup.send(embed=embed, view=TemplateView(template), ephemeral=True)

    @select(cls=UserSelect, placeholder="Read User's OCs", custom_id="user-ocs", min_values=0, row=1)
    async def user_ocs(self, ctx: Interaction, sct: UserSelect):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        resp: InteractionResponse = ctx.response
        member: Member = sct.values[0] if sct.values else ctx.user
        await resp.defer(ephemeral=True, thinking=True)
        values = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": ctx.guild_id})]
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        ctx.client.logger.info("%s is reading/modifying characters", str(ctx.user))
        await view.simple_send()

    @button(label="Creation", emoji="\N{PENCIL}", row=2, custom_id="add-oc")
    async def oc_add(self, ctx: Interaction, _: Button):
        cog = ctx.client.get_cog("Submission")
        user: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        resp: InteractionResponse = ctx.response
        ephemeral = bool((role := ctx.guild.get_role(719642423327719434)) and role in ctx.user.roles)
        await resp.defer(ephemeral=ephemeral, thinking=True)
        users = {ctx.user.id, user.id}
        try:
            cog.ignore |= users
            view = CreationOCView(
                bot=ctx.client,
                ctx=ctx,
                user=user,
                template=Template.Pokemon,
            )
            await view.handler_send(ephemeral=ephemeral)
            await view.wait()
        except Exception as e:
            await ctx.followup.send(str(e), ephemeral=ephemeral)
            ctx.client.logger.exception("Character Creation Exception", exc_info=e)
        finally:
            cog.ignore -= users

    @button(label="Modification", emoji="\N{PENCIL}", row=2, custom_id="modify-oc")
    async def oc_update(self, ctx: Interaction, _: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = ctx.client.supporting.get(member, member)
        values = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": ctx.guild_id})]
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        await view.simple_send(title="Select Character to modify")
        ctx.client.logger.info("%s is modifying characters", str(ctx.user))

    @button(style=ButtonStyle.red, emoji="\N{WASTEBASKET}", row=2, custom_id="delete-oc")
    async def oc_delete(self, ctx: Interaction, _: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = ctx.client.supporting.get(member, member)
        key = {"author": member.id, "server": ctx.guild_id}
        values = [Character.from_mongo_dict(x) async for x in db.find(key)]
        values.sort(key=lambda x: x.name)
        view = BaseCharactersView(
            member=ctx.user,
            target=ctx,
            ocs=values,
            max_values=len(values),
            auto_conclude=False,
        )
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(title="Select Characters to delete") as choices:
            if choices and isinstance(choices, set):
                thread_id = values[0].thread
                if not (channel := ctx.guild.get_channel_or_thread(thread_id)):
                    channel = await ctx.guild.fetch_channel(thread_id)
                await channel.edit(archived=False)
                for oc in choices:
                    msg = channel.get_partial_message(oc.id)
                    await msg.delete(delay=0)
                ctx.client.logger.info("%s is deleting %s characters", str(ctx.user), len(choices))
