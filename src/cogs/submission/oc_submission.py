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
    PartialMessage,
    SelectOption,
    TextStyle,
    Thread,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import MISSING, get
from frozendict import frozendict
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.submission.oc_parsers import ParserMethods
from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ALL_ABILITIES, Ability
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pronouns import Pronoun
from src.structures.species import (
    _BEASTBOOST,
    Chimera,
    CustomMega,
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
from src.utils.etc import RICH_PRESENCE_EMOJI, WHITE_BAR
from src.utils.functions import int_check
from src.views.ability_view import SPAbilityView
from src.views.characters_view import CharactersView, PingView
from src.views.image_view import ImageView
from src.views.move_view import MoveComplex
from src.views.movepool_view import MovepoolView
from src.views.species_view import SpeciesComplex


@dataclass(unsafe_hash=True, slots=True)
class TemplateItem:
    description: str = ""
    fields: frozendict[str, str] = field(default_factory=frozendict)
    docs: frozendict[str, str] = field(default_factory=frozendict)
    custom: bool = False

    def __init__(self, data: dict[str, str]) -> None:
        self.description = data.get("description", "")
        modifier = data.get("modifier", {})
        self.custom = data.get("custom", False)
        default = {
            "Name": "Name",
            "Species": "Species",
            "Types": "Type, Type",
            "Age": "Age",
            "Pronoun": "He/She/Them",
            "Abilities": "Ability, Ability",
            "Moveset": "Move, Move, Move, Move, Move, Move",
        }
        exclude = data.get("exclude", [])
        fields = {x[0]: x[1] for k, v in default.items() if (x := modifier.get(k, (k, v))) and x[0] not in exclude}
        self.fields = frozendict(fields)
        self.docs = frozendict(data.get("docs", {}))


class Template(TemplateItem, Enum):
    Pokemon = dict(
        description="The residents of this world.",
        exclude=["Types"],
        docs={
            "Standard": "1-Ebq40ONEzl0klHqUatG0Sy54mffal6AC2iX2aDHNas",
            "w/Sp. Ability": "1prCYzbqJAAetv_c3HRsXIU22dN7Co-tqykhxWo2SrwY",
        },
    )
    Legendary = dict(
        description="Legendaries that came from other world which want a new home/purpose.",
        exclude=["Types"],
        docs={"Standard": "1N2ZEZd1PEKusdIg9aAYw0_ODmoxHoe5GugkTGZWP21Y"},
    )
    Mythical = dict(
        description="Mythicals that came from other world which want a new home/purpose.",
        exclude=["Types"],
        docs={"Standard": "1rVdi3XMXBadIZc03SrZl-vz3b-AcM2WgBSAfvdgW5Fs"},
    )
    UltraBeast = dict(
        description="Ultra Beasts that came from other world which want a new home/purpose.",
        docs={"Standard": "1Xi25gAj6qoh14xYSXsinfMZ3-6loJ_CTCdrRdPlEhW8"},
    )
    Mega = dict(
        description="People that mega evolved and kept stuck like this.",
        exclude=["Abilities", "Types"],
        docs={
            "Standard": "1Q3-RDADz6nuk1X4PwvIFactqYRyQEGJx8NM4weenGdM",
            "w/Sp. Ability": "1j7dO_sf4wEaO-enKBvmLjrD9gnBh5jMY_QY0XBb0-To",
        },
    )
    Fusion = dict(
        description="They are also known as Hybrids sometimes, fusions that contain legendaries can't have special abilities.",
        modifier={"Species": ("Species", "Species 1, Species 2")},
        docs={
            "Standard": "1YOGxjJcl-RzIu0rv78GTW3qtN-joLxwrena9PHqJi04",
            "w/Sp. Ability": "1l_fQ2i2By63CgCco29XvkZiAdEpWgs4xkDMunwceLHM",
        },
        custom=True,
    )
    CustomPokemon = dict(
        description="Community created species which are assumed to be foreigners",
        modifier={"Species": ("Fakemon", "Fakemon Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "w/Sp. Ability": "12EJpXCJmtDksb1VZjdr8DrMiJeRlpIWI3544r47MVns",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
        custom=True,
    )
    CustomLegendary = dict(
        description="Community created species which are assumed to be foreigners",
        modifier={"Species": ("Fakemon", "Fakemon Legendary Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
        custom=True,
    )
    CustomMythical = dict(
        description="Community created species which are assumed to be foreigners",
        modifier={"Species": ("Fakemon", "Fakemon Mythical Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
        custom=True,
    )
    CustomUltraBeast = dict(
        description="Community created species which are assumed to be foreigners",
        modifier={"Species": ("Fakemon", "Fakemon Ultra Beast Species")},
        docs={
            "Standard": "1CS0Y5fiEyaVUavHh5cJURU4OtLihUzRwn8_GRFDkI2s",
            "Evolution": "1_BoUubkuk5PJ62VyLboRWEaCX7SSrG80ZlltKkAAkaA",
            "Evolution w/ Sp. Ability": "1ZYUEwb0YHdzMTw1U1psRHvyQ_I2ya9_OQVev_aU3W1Q",
        },
        custom=True,
    )
    CustomMega = dict(
        description="Community created species which are assumed to be foreigners",
        modifier={"Species": ("Fakemon", "Mega Species")},
        docs={"Standard": "1EQci2zxlm7WEpxF4CaH0KhEs4eywY6wIYhbDquc4gts"},
        custom=True,
    )
    Variant = dict(
        description="Community created variants of canon species",
        modifier={"Species": ("Variant", "Variant Species")},
        docs={
            "Standard": "1zLNd_5QZ39aBuDEHt3RC4cmymBjRlFmxuesbfSDgDbA",
            "w/Sp. Ability": "12MwUc3uDUOAobHo-fyiwXxh-jI6Tfj5zimOmQHJUWTc",
        },
        custom=True,
    )
    Chimera = dict(
        description="Pokemon created by science, either by the Pixy foundation's research in current times or by clandestine researchers.",
        modifier={"Species": ("Chimera", "Species, Species, Species, ...")},
        docs={"Standard": "1MbaUTR2NDOpsifRO2lVw6t0eAUKFGaOOIOHD0nXC2aA"},
        custom=True,
    )

    async def process(self, oc: Character, ctx: Interaction, ephemeral: bool):
        choices: list[Species] = []
        if mon_total := self.total_species:
            view = SpeciesComplex(
                member=ctx.user,
                target=ctx,
                mon_total=mon_total,
                max_values=self.max_values,
            )
            async with view.send(ephemeral=ephemeral) as data:
                if 1 <= len(data) <= self.max_values:
                    choices.extend(data)
                else:
                    return

        match self:
            case self.CustomPokemon | self.CustomLegendary | self.CustomMythical | self.CustomUltraBeast:
                async with ModernInput(member=ctx.user, target=ctx).handle(
                    label="Character's Species.",
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
                oc.species = Chimera(choices)
            case self.Fusion:
                oc.species = Fusion(*choices)
            case self.Legendary | self.Mythical | self.UltraBeast | self.Mega:
                oc.species = choices[0]
                oc.abilities = choices[0].abilities.copy()
            case _:
                if choices:
                    oc.species = choices[0]
                    oc.abilities &= oc.species.abilities

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
            case self.Pokemon:
                mon_total = Pokemon.all()
            case self.CustomMega | Template.Variant:
                mon_total = {x for x in Species.all() if not isinstance(x, Mega)}
            case self.Legendary:
                mon_total = Legendary.all()
            case self.Mythical:
                mon_total = Mythical.all()
            case self.UltraBeast:
                mon_total = UltraBeast.all()
            case self.Mega:
                mon_total = Mega.all()
            case self.Fusion | self.Chimera:
                mon_total = Species.all()
            case _:
                mon_total = []
        return frozenset({x for x in mon_total if not x.banned})

    @property
    def text(self):
        return "\n".join(f"{k}: {v}" for k, v in self.fields.items())

    @property
    def title(self):
        if self.custom:
            return self.name.removeprefix("Custom") + " (Custom)"
        return self.name

    @property
    def formatted_text(self):
        return f"```yaml\n{self.text}\n```"

    @property
    def doc_urls(self):
        return {k: f"https://docs.google.com/document/d/{v}/edit?usp=sharing" for k, v in self.docs.items()}

    @property
    def embed(self):
        embed = Embed(
            title=self.title,
            description=self.formatted_text,
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        for key, url in self.doc_urls.items():
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
    description = "Fill the OC's Name"

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
            label="Write the character's Name.",
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
    description = "Optional. Fill the OC's Age"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if oc.age and not (13 <= oc.age <= 99):
            return "Invalid Age"

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
        age = str(oc.age) if oc.age else "Unknown"
        handler = text_view.handle(
            label="Write the character's Age.",
            placeholder=f"> {age}",
            default=age,
            required=False,
            ephemeral=ephemeral,
        )
        async with handler as answer:
            if isinstance(answer, str):
                oc.age = int_check(answer, 13, 99)
                progress.add(cls.name)


class PronounField(TemplateField):
    name = "Pronoun"
    description = "Optional. Fill the OC's Pronoun"

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
            ephemeral=ephemeral,
        ) as pronoun:
            if isinstance(pronoun, Pronoun):
                oc.pronoun = pronoun
                progress.add(cls.name)


class SpeciesField(TemplateField):
    name = "Species"
    description = "Fill the OC's Species"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        species = oc.species
        if not species:
            return "Missing Species"

        if species.banned:
            return f"{species.name} as species are banned."

        CORE = (Legendary, Mythical, Mega, UltraBeast)

        if isinstance(species, (Variant, CustomMega)) and isinstance(species.base, Mega):
            return "This kind of Pokemon can't have variants."
        if isinstance(species, Fakemon) and isinstance(species.evolves_from, Mega):
            return "Fakemon evolutions from this kind of Pokemon aren't possible."
        if isinstance(species, Fusion) and all(isinstance(x, CORE) for x in species.bases):
            return "Fusions require at least one common Pokemon."
        if isinstance(species, Chimera) and not (1 <= len(species.bases) <= 3):
            return "Chimeras require to have 1-3 species."

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


class PreEvoSpeciesField(TemplateField):
    name = "Pre-Evolution"
    description = "Optional. Fill the OC's Pre evo Species"

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
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        mon_total = {x for x in Pokemon.all() if not x.banned}
        view = SpeciesComplex(member=ctx.user, target=ctx, mon_total=mon_total)
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
    escription = "Fill the OC's Types"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        species = oc.species
        if isinstance(species, (Fakemon, Variant, Fusion)):
            mon_types = species.possible_types
            if oc.types not in mon_types:
                name = ", ".join("/".join(y.name for y in x) for x in mon_types)
                return f"Possible Typings: {name}"
        elif isinstance(species, Chimera):
            items = [*{x.types for x in species.bases}]
            if not items:
                return "Chimera needs species."

            mon_types = frozenset.union(*items)
            if not oc.types.issubset(mon_types):
                return f"Chimera requires from typings: {', '.join(x.name for x in mon_types)}."

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
        if isinstance(species, Fusion):
            values = species.possible_types
            view = Complex[set[TypingEnum]](
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
            if isinstance(species, Chimera):
                elements = frozenset.union(*[x.types for x in species.bases])
            else:
                elements = TypingEnum

            view = Complex[TypingEnum](
                member=ctx.user,
                target=ctx,
                values=elements,
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

        async with view.send(title="Select Typing", single=single, ephemeral=ephemeral) as types:
            if types:
                species.types = frozenset(types)
                progress.add(cls.name)


class MovesetField(TemplateField):
    name = "Moveset"
    description = "Optional. Fill the OC's fav. moves"

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
            moves = oc.total_movepool()
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
            moves = {x for x in Move.all() if not x.banned}
            moveset = oc.moveset

        view = MoveComplex(member=ctx.user, moves=moves, target=ctx, choices=moveset)
        async with view.send(ephemeral=ephemeral) as choices:
            oc.moveset = frozenset(choices)
            if isinstance(oc.species, (Fakemon, Variant)) and not oc.movepool:
                oc.species.movepool = Movepool(tutor=oc.moveset.copy())
                progress.add("Movepool")
            progress.add(cls.name)


class MovepoolField(TemplateField):
    name = "Movepool"
    description = "Optional. Fill the OC's movepool"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if items := ", ".join(x for x in oc.movepool() if x.banned):
            return f"Banned Movepool: {items}"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant))

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
        await view.send(ephemeral=ephemeral)
        await view.wait()
        progress.add(cls.name)


class AbilitiesField(TemplateField):
    name = "Abilities"
    description = "Fill the OC's Abilities"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not (1 <= len(oc.abilities) <= oc.max_amount_abilities):
            return f"Abilities, Min: 1, Max: {oc.max_amount_abilities}"

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
        abilities = oc.species.abilities
        if isinstance(oc.species, (Fakemon, Variant, CustomMega)) or (not abilities):
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
        async with view.send(ephemeral=ephemeral) as choices:
            if isinstance(choices, set):
                oc.abilities = frozenset(choices)
                if isinstance(oc.species, (Fakemon, Variant)):
                    oc.species.abilities = frozenset(choices)
                progress.add(cls.name)


class HiddenPowerField(TemplateField):
    name = "Hidden Power"
    description = "Optional. Fill the OC's Hidden Power"

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
            values=TypingEnum,
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
            title="Select Hidden Power",
            single=True,
            ephemeral=ephemeral,
        ) as types:
            oc.hidden_power = types
            progress.add(cls.name)


class SpAbilityField(TemplateField):
    name = "Special Ability"
    description = "Optional. Fill the OC's Special Ability"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.can_have_special_abilities and oc.sp_ability:
            return "Can't have Special Abilities."

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
        oc.sp_ability = view.sp_ability
        progress.add(cls.name)


class BackstoryField(TemplateField):
    name = "Backstory"
    description = "Optional. Fill the OC's Backstory"

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
            label="Write the character's Backstory.",
            placeholder=oc.backstory,
            default=oc.backstory,
            required=False,
            ephemeral=ephemeral,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.backstory = answer or None
                progress.add(cls.name)


class ExtraField(TemplateField):
    name = "Extra Information"
    description = "Optional. Fill the OC's Extra Information"

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
    description = "Fill the OC's Image"

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
        message = getattr(ctx, "message", ctx)
        self.ephemeral = isinstance(message, Message) and message.flags.ephemeral
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

    def setup(self, embed_update: bool = True):
        self.kind.options = [
            SelectOption(
                label=x.name,
                emoji="\N{MEMO}",
                default=x == self.ref_template,
            )
            for x in Template
        ]
        self.fields.options.clear()
        for item in filter(lambda x: x.check(self.oc), TemplateField.all()):
            emoji = "\N{BLACK SQUARE BUTTON}" if (item.name in self.progress) else "\N{BLACK LARGE SQUARE}"
            description = item.evaluate(self.oc)
            if not description:
                description = item.description
            else:
                emoji = "\N{CROSS MARK}"
            self.fields.add_option(label=item.name, description=description[:100], emoji=emoji)

        self.fields.options.sort(key=lambda x: str(x.emoji) != "\N{CROSS MARK}")

        self.submit.label = "Save Changes" if self.oc.id else "Submit"
        self.submit.disabled = any(str(x.emoji) == "\N{CROSS MARK}" for x in self.fields.options)
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
                    | Template.Chimera
                ):
                    self.progress -= {"Special Ability"}
                    self.oc.sp_ability = None
                    if self.ref_template == Template.CustomUltraBeast:
                        self.oc.abilities = frozenset({_BEASTBOOST})

            await self.update(ctx)
        except Exception as e:
            self.bot.logger.exception("Exception in OC Creation", exc_info=e)
            self.stop()

    async def upload(self):
        if (m := self.message) and not m.flags.ephemeral:
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

    async def update(self, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        self.setup()
        embeds = self.embeds
        files = [self.oc.image] if "Image" in self.progress and isinstance(self.oc.image, File) else MISSING

        try:
            if resp.is_done():
                message = self.message or ctx.message
                if not message.flags.ephemeral:
                    message = PartialMessage(channel=message.channel, id=message.id)
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

    @select(placeholder="Click here!", row=1)
    async def fields(self, ctx: Interaction, sct: Select):
        if item := TemplateField.get(name=sct.values[0]):
            await item.on_submit(ctx, self.ref_template, self.progress, self.oc, self.ephemeral)
        await self.update(ctx)

    async def delete(self, ctx: Optional[Interaction] = None) -> None:
        db = self.bot.mongo_db("OC Creation")
        if (m := self.message) and not m.flags.ephemeral:
            await db.delete_one({"id": m.id})
        return await super(CreationOCView, self).delete(ctx)

    @button(label="Delete Character", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=2)
    async def finish_oc(self, ctx: Interaction, _: Button):
        if self.oc.id and self.oc.thread:
            if not (channel := ctx.guild.get_channel_or_thread(self.oc.thread)):
                channel = await ctx.guild.fetch_channel(self.oc.thread)
            await channel.edit(archived=False)
            msg = PartialMessage(channel=channel, id=self.oc.id)
            await msg.delete(delay=0)
        await self.delete(ctx)

    @button(label="Close this Menu", row=2)
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

    @button(label="Request Help", row=2)
    async def help(self, ctx: Interaction, _: Button):
        await self.help_method(ctx)

    @button(disabled=True, label="Submit", style=ButtonStyle.green, row=2)
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
                if item.author in [user.id, interaction.user.id]:
                    view = CreationOCView(bot=interaction.client, ctx=interaction, user=user, oc=item)
                    await view.send(ephemeral=True)
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
                if oc := Character.process(**item):
                    view = CreationOCView(bot=interaction.client, ctx=interaction, user=author, oc=oc)
                    if self.ephemeral:
                        await resp.edit_message(embeds=view.embeds, view=view)
                    else:
                        await view.send(ephemeral=False)
        except Exception as e:
            if not resp.is_done():
                if isinstance(interaction.channel, Thread) and interaction.channel.archived:
                    await interaction.channel.edit(archived=True)
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
                ephemeral = bool((role := ctx.guild.get_role(719642423327719434)) and role in ctx.user.roles)
                modal = SubmissionModal(self.template.text, ephemeral=ephemeral)
                await resp.send_modal(modal)
                await modal.wait()
            case "Message":
                await resp.edit_message(
                    content=self.template.formatted_text,
                    embed=None,
                    view=None,
                )
            case "Google Document":
                await resp.edit_message(
                    embed=self.template.docs_embed,
                    view=None,
                )
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
        embed.set_image(url="https://cdn.discordapp.com/attachments/748384705098940426/957468209597018142/image.png")
        embed.set_footer(text="After sending, bot will ask for backstory, extra info and image.")
        await ctx.followup.send(embed=embed, view=TemplateView(template), ephemeral=True)

    @button(label="Character Creation", emoji="\N{PENCIL}", row=1, custom_id="add-oc")
    async def oc_add(self, ctx: Interaction, _: Button):
        cog = ctx.client.get_cog("Submission")
        user = ctx.client.supporting.get(ctx.user, ctx.user)
        resp: InteractionResponse = ctx.response
        ephemeral = bool((role := ctx.guild.get_role(719642423327719434)) and role in ctx.user.roles)
        await resp.defer(ephemeral=ephemeral, thinking=True)
        users = {ctx.user.id, user.id}
        try:
            cog.ignore |= users
            view = CreationOCView(ctx.client, ctx, user)
            await view.send(ephemeral=ephemeral)
            await view.wait()
        except Exception as e:
            await ctx.followup.send(str(e), ephemeral=ephemeral)
            ctx.client.logger.exception("Character Creation Exception", exc_info=e)
        finally:
            cog.ignore -= users

    @button(label="Character Modification", emoji="\N{PENCIL}", row=1, custom_id="modify-oc")
    async def oc_update(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        member = ctx.client.supporting.get(member, member)
        ocs = ctx.client.get_cog("Submission").ocs.values()
        values: list[Character] = [oc for oc in ocs if member.id == oc.author]
        if not values:
            return await ctx.followup.send("You don't have characters to modify", ephemeral=True)
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
        view.embed.title = "Select Character to modify"
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(single=True):
            ctx.client.logger.info("%s is modifying characters", str(ctx.user))
