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
from discord.utils import MISSING, get
from frozendict import frozendict
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.submission.oc_parsers import ParserMethods
from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ABILITIES_DEFINING, ALL_ABILITIES, Ability
from src.structures.bot import CustomBot
from src.structures.character import AgeGroup, Character, Size
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pokeball import Pokeball
from src.structures.pronouns import Pronoun
from src.structures.species import (
    Chimera,
    CustomMega,
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Paradox,
    Pokemon,
    Species,
    UltraBeast,
    Variant,
)
from src.utils.etc import RICH_PRESENCE_EMOJI, WHITE_BAR
from src.views.ability_view import SPAbilityView
from src.views.characters_view import CharactersView
from src.views.image_view import ImageView
from src.views.move_view import MovepoolMoveComplex
from src.views.movepool_view import MovepoolView
from src.views.species_view import SpeciesComplex

DEFAULT_MOVES = Movepool.from_dict(tm=["TERABLAST"])


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
        description="The average residents of this world.",
        exclude=["Types"],
        docs={
            "Standard": "1-Ebq40ONEzl0klHqUatG0Sy54mffal6AC2iX2aDHNas",
            "w/Sp. Ability": "1prCYzbqJAAetv_c3HRsXIU22dN7Co-tqykhxWo2SrwY",
        },
    )
    Legendary = dict(
        description="Normal residents that resemble legendaries.",
        exclude=["Types"],
        docs={"Standard": "1N2ZEZd1PEKusdIg9aAYw0_ODmoxHoe5GugkTGZWP21Y"},
    )
    Mythical = dict(
        description="Normal residents that resemble mythicals.",
        exclude=["Types"],
        docs={"Standard": "1rVdi3XMXBadIZc03SrZl-vz3b-AcM2WgBSAfvdgW5Fs"},
    )
    UltraBeast = dict(
        description="Normal residents that resemble ultra beasts.",
        docs={"Standard": "1Xi25gAj6qoh14xYSXsinfMZ3-6loJ_CTCdrRdPlEhW8"},
    )
    Mega = dict(
        description="Those that mega evolved and kept stuck like this.",
        exclude=["Abilities", "Types"],
        docs={
            "Standard": "1Q3-RDADz6nuk1X4PwvIFactqYRyQEGJx8NM4weenGdM",
            "w/Sp. Ability": "1j7dO_sf4wEaO-enKBvmLjrD9gnBh5jMY_QY0XBb0-To",
        },
    )
    Paradox = dict(
        description="From distant past/future, somehow ended up here.",
        docs={"Standard": "1oe-W2uTJBHPuCje5zjMf2KVxWbomjuTgF1kX6UuAhbk"},
    )
    Fusion = dict(
        description="Individuals that share traits of two species.",
        modifier={"Species": ("Species", "Species 1, Species 2")},
        docs={
            "Standard": "1YOGxjJcl-RzIu0rv78GTW3qtN-joLxwrena9PHqJi04",
            "w/Sp. Ability": "1l_fQ2i2By63CgCco29XvkZiAdEpWgs4xkDMunwceLHM",
        },
    )
    Variant = dict(
        description="Fan-made. Species variations (movesets, types)",
        modifier={"Species": ("Variant", "Variant Species")},
        docs={
            "Standard": "1zLNd_5QZ39aBuDEHt3RC4cmymBjRlFmxuesbfSDgDbA",
            "w/Sp. Ability": "12MwUc3uDUOAobHo-fyiwXxh-jI6Tfj5zimOmQHJUWTc",
        },
    )
    Chimera = dict(
        description="Fan-made. rare three way fusions.",
        modifier={"Species": ("Chimera", "Species, Species, Species, ...")},
        docs={"Standard": "1MbaUTR2NDOpsifRO2lVw6t0eAUKFGaOOIOHD0nXC2aA"},
    )
    CustomPokemon = dict(
        description="Fan-made. They are normal residents.",
        modifier={"Species": ("Fakemon", "Fakemon Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "w/Sp. Ability": "12EJpXCJmtDksb1VZjdr8DrMiJeRlpIWI3544r47MVns",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
    )
    CustomLegendary = dict(
        description="Fan-made. Normal residents that resemble legendaries.",
        modifier={"Species": ("Fakemon", "Fakemon Legendary Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
    )
    CustomMythical = dict(
        description="Fan-made. Normal residents that resemble mythicals.",
        modifier={"Species": ("Fakemon", "Fakemon Mythical Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
    )
    CustomUltraBeast = dict(
        description="Fan-made. Normal residents that resemble ultra beasts.",
        modifier={"Species": ("Fakemon", "Fakemon Ultra Beast Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
    )
    CustomMega = dict(
        description="Fan-made. Mega evolved and kept stuck like this.",
        modifier={"Species": ("Fakemon", "Mega Species")},
        docs={"Standard": "1EQci2zxlm7WEpxF4CaH0KhEs4eywY6wIYhbDquc4gts"},
    )
    CustomParadox = dict(
        description="Fan-made. From distant past/future, somehow ended up here.",
        modifier={"Species": ("Fakemon", "Paradox Species")},
        docs={"Standard": "1EQci2zxlm7WEpxF4CaH0KhEs4eywY6wIYhbDquc4gts"},
    )

    async def process(self, oc: Character, ctx: Interaction, ephemeral: bool):
        choices: list[Species] = []
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")

        if mons := self.total_species:
            ocs = [Character.from_mongo_dict(x) async for x in db.find({"server": ctx.guild_id})]
            view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mons, max_values=self.max_values, ocs=ocs)
            async with view.send(ephemeral=ephemeral) as data:
                if 1 <= len(data) <= self.max_values:
                    choices.extend(data)
                else:
                    return

        match self:
            case self.Pokemon | self.Legendary | self.Mythical | self.UltraBeast | self.Paradox | self.Mega:
                if choices:
                    oc.species, abilities = choices[0], choices[0].abilities.copy()
                    if len(abilities) <= oc.max_amount_abilities:
                        oc.abilities = abilities
                    else:
                        oc.abilities &= abilities
            case self.Variant:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label=f"{choices[0].name} Variant"[:45],
                    ephemeral=ephemeral,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        oc.species = Variant(base=choices[0], name=answer)
            case self.CustomMega:
                oc.species = CustomMega(choices[0])
                oc.abilities &= oc.species.abilities
            case self.Chimera:
                if choices:
                    oc.species = Chimera(choices)
            case self.Fusion:
                if len(choices) == 2:
                    oc.species = Fusion(*choices, ratio=0.5)
            case _:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label=f"{self.title} Character's Species.",
                    required=True,
                    ephemeral=ephemeral,
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
    def max_values(self):
        match self:
            case self.Fusion:
                return 2
            case self.Chimera:
                return 3
            case _:
                return 1

    @property
    def total_species(self) -> frozenset[Species]:
        match self:
            case self.Pokemon | self.Chimera:
                mon_total = Pokemon.all()
            case self.CustomMega | Template.Variant:
                mon_total = Species.all(exclude=Mega)
            case self.Legendary:
                mon_total = Legendary.all()
            case self.Mythical:
                mon_total = Mythical.all()
            case self.UltraBeast:
                mon_total = UltraBeast.all()
            case self.Mega:
                mon_total = Mega.all()
            case self.Fusion:
                mon_total = Species.all()
            case self.Paradox:
                mon_total = Paradox.all()
            case _:
                mon_total = []
        return frozenset({x for x in mon_total if not x.banned})

    @property
    def text(self):
        return "\n".join(f"{k}: {v}" for k, v in self.fields.items())

    @property
    def title(self):
        name = self.name.replace("UltraBeast", "Ultra Beast")
        if name.startswith("Custom"):
            name = name.removeprefix("Custom") + " (Custom)"
        return name

    @property
    def formatted_text(self):
        return f"```yaml\n{self.text}\n```"

    @property
    def embed(self):
        embed = Embed(
            title=self.title,
            description=self.formatted_text,
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        for key, doc_id in self.docs.items():
            url = f"https://docs.google.com/document/d/{doc_id}/edit?usp=sharing"
            embed.add_field(name=key, value=f"[Google Docs URL]({url})")
        embed.set_footer(text=self.description)
        return embed

    @property
    def docs_embed(self):
        embed = self.embed
        embed.title = f"Available Templates - {embed.title}"
        embed.description = (
            "Make a copy of our templates, make sure it has reading permissions and then send the URL in this channel."
        )
        return embed


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
    def evaluate(cls, oc: Character) -> Optional[str]:
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
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        handler = text_view.handle(
            label=f"Write the {template.title} character's Name.",
            placeholder=f"> {oc.name}",
            default=oc.name,
            required=True,
            ephemeral=ephemeral,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.name = answer.title()
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
    description = "He, She or Them"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not isinstance(oc.pronoun, Pronoun):
            return "Invalid Pronoun"

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
            parser=lambda x: (x.name, f"Sets Pronoun as {x.name}"),
            sort_key=lambda x: x.name,
            text_component=TextInput(
                label="Pronoun",
                placeholder="He | She | Them",
                default=oc.pronoun.name,
                min_length=2,
                max_length=4,
            ),
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Pronoun.",
            description=f"> {oc.pronoun.name}",
            single=True,
            ephemeral=ephemeral,
        ) as pronoun:
            if isinstance(pronoun, Pronoun):
                oc.pronoun = pronoun
                progress.add(cls.name)


class SpeciesField(TemplateField):
    name = "Species"
    description = "Modify the OC's Species"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        species = oc.species
        if not species:
            return "Missing Species"

        if species.banned:
            return f"{species.name} as species are banned."

        if isinstance(species, (Variant, CustomMega)) and isinstance(species.base, Mega):
            return "This kind of Pokemon can't have variants."
        if isinstance(species, Fakemon) and isinstance(species.evolves_from, Mega):
            return "Fakemon evolutions from this kind of Pokemon aren't possible."
        if isinstance(species, Fusion) and all(isinstance(x, Mega) for x in species.bases):
            return "Fusions can't work with all being mega."
        if isinstance(species, Chimera):
            if not (1 <= len(species.bases) <= 3):
                return "Chimeras require to have 1-3 species."
            if any(isinstance(x, (Legendary, Mythical, Mega, UltraBeast, Paradox)) for x in species.bases):
                return "Chimeras from this kind of Pokemon aren't possible."

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
            parser=lambda x: (x.label_name[:100], None),
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
    async def on_submit(
        cls,
        ctx: Interaction,
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        height = oc.species.height if oc.species else 0
        view = Complex[Size](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=[*Size],
            parser=lambda x: (x.height_info(height), None),
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Size.",
            description=f"> {oc.size.height_info(height)}",
            single=True,
            ephemeral=ephemeral,
        ) as size:
            if isinstance(size, Size):
                oc.size = size
                progress.add(cls.name)


class WeightField(TemplateField):
    name = "Weight"
    description = "Modify the OC's Weight"
    required: bool = False

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
        weight = oc.species.weight if oc.species else 0
        view = Complex[Size](
            member=ctx.user,
            target=ctx,
            timeout=None,
            values=[*Size],
            parser=lambda x: (x.weight_info(weight), None),
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Weight.",
            description=f"> {oc.size.weight_info(weight)}",
            single=True,
            ephemeral=ephemeral,
        ) as weight:
            if isinstance(weight, Size):
                oc.weight = weight
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
        mon_total = {x for x in Pokemon.all() if not x.banned}
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"server": ctx.guild_id})]
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
                return "Possible Typings: {}".format(", ".join("/".join(y.name for y in x) for x in mon_types))

        if not oc.types:
            return "Types have not been specified."

        if len(oc.types) > 2:
            return "Max 2 Pokemon Types: ({})".format(", ".join(x.name for x in oc.types))

    @classmethod
    def check(cls, oc: Character) -> bool:
        item = isinstance(oc.species, (Fakemon, Variant, CustomMega))
        item |= isinstance(oc.species, (Fusion, Chimera)) and len(oc.species.possible_types) > 1
        return item

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
        if isinstance(species, (Chimera, Fusion)):
            values = species.possible_types
            view = Complex[set[TypingEnum]](
                member=ctx.user,
                target=ctx,
                values=values,
                timeout=None,
                parser=lambda x: (y := "/".join(i.name for i in x), f"Adds the typing {y}"),
                silent_mode=True,
            )
            single = True
        else:
            mon_types = TypingEnum.all(ignore=TypingEnum.Shadow if template == Template.Variant else None)
            view = Complex[TypingEnum](
                member=ctx.user,
                target=ctx,
                values=mon_types,
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

        async with view.send(
            title=f"{template.title} Character's Typing",
            single=single,
            ephemeral=ephemeral,
        ) as types:
            if types:
                species.types = frozenset(types)
                progress.add(cls.name)


class MovesetField(TemplateField):
    name = "Moveset"
    description = "Modify the OC's fav. moves"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        species = oc.species

        mons = "SMEARGLE", "DITTO", "MEW"

        if value := ", ".join(x.name for x in oc.moveset if x.banned):
            value = f"Banned Moves: {value}. "

        if not any(
            (
                isinstance(species, Fusion) and any(x.id in mons for x in species.bases),
                isinstance(species, Chimera) and all(x.id in mons for x in species.bases),
                isinstance(species, (CustomMega, Variant)) and species.base.id in mons,
                isinstance(species, Fakemon) and species.evolves_from in mons,
                isinstance(species, Species) and species.id in mons,
            )
        ):
            movepool = DEFAULT_MOVES + oc.total_movepool
            moves = movepool()
            if items := ", ".join(x.name for x in oc.moveset if x not in moves):
                value += f"Not in Movepool: {items}"

        return value or None

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
        moves = {x for x in oc.total_movepool() if not x.banned}
        species = oc.species
        moveset = None
        mons = "SMEARGLE", "DITTO", "MEW"

        movepool = DEFAULT_MOVES.copy()

        if any(
            (
                isinstance(species, Fusion) and any(x.id in mons for x in species.bases),
                isinstance(species, Chimera) and all(x.id in mons for x in species.bases),
                isinstance(species, (CustomMega, Variant)) and species.base.id in mons,
                isinstance(species, Fakemon) and species.evolves_from in mons,
                isinstance(species, Species) and species.id in mons,
                isinstance(species, (Fakemon, Variant)) and not moves,
            )
        ):
            if TypingEnum.Shadow not in oc.types:
                movepool += Movepool(tm={x for x in Move.all() if not x.banned})
            else:
                movepool += Movepool(tm={x for x in Move.all() if x.type == TypingEnum.Shadow})
            moveset = oc.moveset
        else:
            movepool += oc.total_movepool

        view = MovepoolMoveComplex(
            member=ctx.user,
            movepool=movepool,
            target=ctx,
            choices=moveset,
        )
        async with view.send(
            title=f"{template.title} Character's Moveset",
            ephemeral=ephemeral,
        ) as choices:
            oc.moveset = frozenset(choices)
            if isinstance(oc.species, (Fakemon, Variant)) and not oc.movepool:
                oc.species.movepool = Movepool(tutor=oc.moveset.copy())
                progress.add("Movepool")
            progress.add(cls.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Modify the OC's movepool"
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if items := ", ".join(x for x in oc.movepool() if x.banned):
            return f"Banned Movepool: {items}"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant)) and TypingEnum.Shadow not in oc.types

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
            title=f"{template.title} Character's Movepool",
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
        amount = 1 if any(x.name in ABILITIES_DEFINING for x in oc.abilities) else oc.max_amount_abilities

        if not (1 <= len(oc.abilities) <= amount):
            return f"Abilities, Min: 1, Max: {amount}"

        if isinstance(oc.species, (Fakemon, Variant, CustomMega)):
            return None

        if items := ", ".join(x.name for x in oc.abilities if x not in oc.species.abilities):
            return f"Invalid Abilities: {items}"

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
        placeholder = ", ".join(["Ability"] * oc.max_amount_abilities)
        abilities, amount = oc.species.abilities, oc.max_amount_abilities
        if template == Template.CustomUltraBeast:
            abilities = {Ability.get(name="Beast Boost")}
            amount = 1
        elif template == Template.CustomParadox:
            abilities = {Ability.get(name="Protosynthesis"), Ability.get(name="Quark Drive")}
            amount = 1
        elif isinstance(oc.species, (Fakemon, Variant, CustomMega)) or (not abilities):
            abilities = ALL_ABILITIES.values()

        view = Complex[Ability](
            member=ctx.user,
            values=abilities,
            timeout=None,
            target=ctx,
            max_values=amount,
            parser=lambda x: (x.name, x.description),
            text_component=TextInput(
                label="Ability",
                placeholder=placeholder,
                default=", ".join(x.name for x in oc.abilities),
            ),
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Abilities",
            fields=[
                (
                    f"Ability {index} - {item.name}",
                    item.description[:1024],
                )
                for index, item in enumerate(oc.abilities, start=1)
            ],
            ephemeral=ephemeral,
        ) as choices:
            if isinstance(choices, set):
                oc.abilities = frozenset(choices)
                if isinstance(oc.species, (Fakemon, Variant)):
                    oc.species.abilities = frozenset(choices)
                progress.add(cls.name)


class HiddenPowerField(TemplateField):
    name = "Hidden Power"
    description = "Typing that matches with their soul's"
    required: bool = False

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if oc.hidden_power and oc.hidden_power == TypingEnum.Shadow:
            return "Shadow hidden power isn't a thing."

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
            values=TypingEnum.all(ignore=TypingEnum.Shadow),
            max_values=1,
            timeout=None,
            parser=lambda x: (x.name, f"Sets the typing {x.name}"),
            text_component=TextInput(
                label="Hidden Power",
                placeholder="Type",
                required=True,
            ),
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Hidden Power",
            single=True,
            ephemeral=ephemeral,
        ) as types:
            oc.hidden_power = types
            progress.add(cls.name)


class UniqueTraitField(TemplateField):
    name = "Unique Trait"
    description = "No other in species but OC can do it."
    required: bool = True

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.can_have_special_abilities and oc.sp_ability:
            return "Can't have Unique Traits."

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species and oc.can_have_special_abilities

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
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label=f"Write the {template.title}'s Bio.",
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
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label=f"Write the {template.title} Character's Personality.",
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
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=ctx.user, target=ctx)
        async with text_view.handle(
            label="Write the character's Extra Information.",
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
        return bool(oc.species)

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
            description = item.evaluate(self.oc)
            if not description:
                description = item.description
            else:
                emoji = "\N{CROSS MARK}"
            menu = self.fields1 if item.required else self.fields2
            menu.add_option(label=item.name, description=description[:100], emoji=emoji)

        items: list[tuple[str, Select]] = [("Essentials", self.fields1), ("Extras", self.fields2)]

        errors: int = 0
        for x, y in items:
            if count := sum(str(o.emoji) == "\N{CROSS MARK}" for o in y.options):
                y.options.sort(key=lambda x: str(x.emoji) != "\N{CROSS MARK}")
                y.placeholder = f"{x}. ({count} needed changes)."
            else:
                y.placeholder = f"{x}. Click here!"
            errors += count

        self.submit.label = "Save Changes" if self.oc.id else "Submit"
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

            if self.ref_template == Template.CustomUltraBeast:
                self.oc.abilities = frozenset({Ability.get(name="Beast Boost")})

            if self.ref_template == Template.CustomParadox:
                ab1, ab2 = Ability.get(name="Protosynthesis"), Ability.get(name="Quark Drive")
                if not (self.oc.abilities == {ab1} or self.oc.abilities == {ab2}):
                    self.oc.abilities = frozenset()

            match self.ref_template:
                case (
                    Template.Legendary
                    | Template.Mythical
                    | Template.UltraBeast
                    | Template.Chimera
                    | Template.Paradox
                    | Template.CustomLegendary
                    | Template.CustomMythical
                    | Template.CustomUltraBeast
                    | Template.CustomParadox
                ):
                    self.progress -= {UniqueTraitField.name}
                    self.oc.sp_ability = None

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

    async def upload(self):
        db = self.bot.mongo_db("OC Creation")
        data = self.data
        if data_id := data.get("id"):
            key = {"id": data_id, "server": data["server"]}
            await db.replace_one(key, data, upsert=True)

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

            await self.upload()
            self.message = m

    async def send(self, *, ephemeral: bool = False):
        self.ephemeral = ephemeral
        if not ephemeral:
            self.remove_item(self.help)
        m = await super(CreationOCView, self).send(embeds=self.embeds, ephemeral=ephemeral)
        await self.upload()
        return m

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

    @button(label="Delete Character", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=3)
    async def finish_oc(self, ctx: Interaction, _: Button):
        if self.oc.id and self.oc.thread:
            if not (channel := ctx.guild.get_channel_or_thread(self.oc.thread)):
                channel = await ctx.guild.fetch_channel(self.oc.thread)
            await channel.edit(archived=False)
            await channel.get_partial_message(self.oc.id).delete(delay=0)
        await self.delete(ctx)

    @button(label="Close this Menu", row=3)
    async def cancel(self, ctx: Interaction, _: Button):
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
        await view.send(ephemeral=False)

        if isinstance(self.oc.image, str) and isinstance(file := await ctx.client.get_file(self.oc.image), File):
            embeds = view.embeds
            attachments = [file]
            embeds[0].set_image(url=f"attachment://{file.filename}")
            message = await view.message.edit(attachments=attachments, embeds=embeds)
            if image := message.embeds[0].image:
                self.oc.image = image.url
                await view.upload()

        await self.delete(ctx)

    @button(label="Request Help", row=3)
    async def help(self, ctx: Interaction, _: Button):
        await self.help_method(ctx)

    @button(disabled=True, label="Submit", style=ButtonStyle.green, row=3)
    async def submit(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        try:
            await resp.defer(ephemeral=True, thinking=True)
            cog = ctx.client.get_cog("Submission")
            word = "modified" if self.oc.id else "registered"
            await cog.register_oc(self.oc, image_as_is=True)
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
                user: Member = interaction.client.supporting.get(interaction.user, interaction.user)
                view = CreationOCView(bot=interaction.client, ctx=interaction, user=user, oc=item)

                await view.send(ephemeral=True)
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
                    await view.send(ephemeral=False)
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
                embed = self.template.docs_embed
                await resp.edit_message(embed=embed, view=None)
        self.stop()


class SubmissionView(View):
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
        if values := [
            Character.from_mongo_dict(x)
            async for x in db.find(
                {
                    "author": member.id,
                    "server": ctx.guild_id,
                }
            )
        ]:
            values.sort(key=lambda x: x.name)
            if ctx.user == member or ctx.user.guild_permissions.manage_messages:
                view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
                view.embed.title = "Select Character to modify"
            else:
                view = CharactersView(member=ctx.user, target=ctx, ocs=values)
            view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            async with view.send(single=True):
                ctx.client.logger.info("%s is reading/modifying characters", str(ctx.user))
        else:
            await ctx.followup.send(f"{member.mention} doesn't have characters.", ephemeral=True)

    @button(label="Character Creation", emoji="\N{PENCIL}", row=2, custom_id="add-oc")
    async def oc_add(self, ctx: Interaction, _: Button):
        cog = ctx.client.get_cog("Submission")
        db: AsyncIOMotorCollection = ctx.client.mongo_db("OC Creation")
        user: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        resp: InteractionResponse = ctx.response
        ephemeral = bool((role := ctx.guild.get_role(719642423327719434)) and role in ctx.user.roles)
        await resp.defer(ephemeral=ephemeral, thinking=True)
        users = {ctx.user.id, user.id}
        try:
            cog.ignore |= users
            items = [data async for data in db.find({"server": ctx.guild_id, "author": {"$in": list(users)}})] or [{}]
            for data in items:
                msg_id, template, author, character, progress = (
                    data.get("id", 0),
                    data.get("template", Template.Pokemon),
                    data.get("author", user.id),
                    data.get("character", {}),
                    data.get("progress", []),
                )
                character = Character.from_mongo_dict(character)

                if not (member := ctx.guild.get_member(author) or ctx.client.get_user(author)):
                    member = await ctx.client.fetch_user(author)

                view = CreationOCView(
                    bot=ctx.client,
                    ctx=ctx,
                    user=member,
                    oc=character,
                    template=template,
                    progress=progress,
                )

                message = ctx.channel.get_partial_message(msg_id)

                try:
                    message = await message.edit(view=view)
                except DiscordException:
                    try:
                        message = await view.send(ephemeral=ephemeral)
                    except DiscordException:
                        message = None
                finally:
                    await db.delete_one({"id": msg_id, "server": ctx.guild_id})

                if message and (embeds := message.embeds):
                    view.message = message
                    if not character.image_url and embeds and embeds[0].image:
                        character.image_url = embeds[0].image.url
                    await view.wait()
        except Exception as e:
            await ctx.followup.send(str(e), ephemeral=ephemeral)
            ctx.client.logger.exception("Character Creation Exception", exc_info=e)
        finally:
            cog.ignore -= users

    @button(label="Character Modification", emoji="\N{PENCIL}", row=2, custom_id="modify-oc")
    async def oc_update(self, ctx: Interaction, _: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = ctx.client.supporting.get(member, member)
        if values := [
            Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": ctx.guild_id})
        ]:
            values.sort(key=lambda x: x.name)
            view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
            view.embed.title = "Select Character to modify"
            view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
            async with view.send(single=True):
                ctx.client.logger.info("%s is modifying characters", str(ctx.user))
        else:
            await ctx.followup.send("You don't have characters to modify", ephemeral=True)
