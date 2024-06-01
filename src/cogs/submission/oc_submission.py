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
from datetime import timedelta
from enum import Enum
from typing import Optional, TypedDict

from discord import (
    ButtonStyle,
    ChannelType,
    Color,
    DiscordException,
    Embed,
    File,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Object,
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

from src.cogs.roles.roles import RPModal
from src.cogs.submission.area_selection import RegionViewComplex
from src.cogs.submission.oc_parsers import ParserMethods
from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.pagination.view_base import Basic
from src.structures.ability import ABILITIES_DEFINING, ALL_ABILITIES, Ability
from src.structures.bot import CustomBot
from src.structures.character import AgeGroup, Character, Nature, Size
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.pokeball import Pokeball
from src.structures.pronouns import Pronoun
from src.structures.species import (
    CustomMega,
    CustomParadox,
    CustomUltraBeast,
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
from src.utils.etc import (
    DEFAULT_TIMEZONE,
    RICH_PRESENCE_EMOJI,
    STICKER_EMOJI,
    WHITE_BAR,
)
from src.utils.functions import safe_username
from src.views.ability_view import SPAbilityView
from src.views.characters_view import BaseCharactersView, CharactersView, PingView
from src.views.image_view import ImageView
from src.views.move_view import MovepoolMoveComplex
from src.views.movepool_view import MovepoolView
from src.views.size_view import HeightView, WeightView
from src.views.species_view import SpeciesComplex


class TicketModal(Modal, title="Ticket"):
    content = TextInput(
        label="Content",
        placeholder="What would you like to comment / report to Staff?",
        style=TextStyle.paragraph,
        required=True,
    )

    async def on_submit(self, itx: Interaction[CustomBot]):
        """This is a function that creates a thread whenever an user uses it

        Parameters
        ----------
        interaction : Interaction
            Interaction object
        """
        await itx.response.defer(ephemeral=True, thinking=True)
        member: Member = itx.user
        data = itx.created_at.astimezone(tz=DEFAULT_TIMEZONE)
        name = data.strftime("%B %d, %Y")

        db = itx.client.mongo_db("Server")
        if info := await db.find_one(
            {
                "id": itx.guild_id,
                "tickets": {"$exists": True},
                "staff_chat": {"$exists": True},
            },
            {"_id": 0, "tickets": 1, "staff_chat": 1},
        ):
            webhook = await itx.client.webhook(info["tickets"])
            thread = await webhook.channel.create_thread(name=name, type=ChannelType.private_thread, invitable=False)
            embed = Embed(
                title=f"Ticket {name}"[:256],
                description=self.content.value,
                timestamp=data,
                color=member.color,
            )
            embed.set_thumbnail(url=member.display_avatar.url)

            msg = await webhook.send(thread=thread, wait=True, embed=embed)

            view = View()
            view.add_item(Button(label="Go to Message", url=msg.jump_url, emoji=STICKER_EMOJI))
            await thread.add_user(member)

            channel = itx.client.get_partial_messageable(
                id=info["staff_chat"],
                guild_id=itx.guild.id,
            )

            await channel.send(embed=embed, view=view)
            await itx.followup.send("Ticket created successfully", ephemeral=True, view=view)
        else:
            await itx.followup.send("Ticket system not setup yet.", ephemeral=True)

        self.stop()


class TemplateDict(TypedDict):
    description: str
    fields: Optional[dict[str, str | dict[str, str]]]
    docs: Optional[dict[str, str]]
    modifier: Optional[dict[str, tuple[str, str]]]
    exclude: Optional[list[str]]


@dataclass(unsafe_hash=True, slots=True)
class TemplateItem:
    description: str
    fields: frozendict[str, str]
    docs: frozendict[str, str]

    def __init__(self, data: TemplateDict | dict) -> None:
        self.description = data.get("description", "")
        modifier = data.get("modifier") or {}
        default = dict(
            Name="Name",
            Species="Species",
            Types="Type, Type",
            Age="Age",
            Pronoun="He/She/Them",
            Abilities="Ability, Ability",
            Moveset="Move, Move, Move, Move, Move, Move",
        )

        exclude = data.get("exclude", ["Types"]) or []
        fields = {x[0]: x[1] for k, v in default.items() if (x := modifier.get(k, (k, v))) and x[0] not in exclude}
        self.fields = frozendict(fields)
        self.docs = frozendict(
            data.get("docs")
            or {
                "Standard": "1_fj55cpyiHJ6zZ4I3FF0o9FbBhl936baflE_7EV8wUc",
                "Unique Trait": "1dyRmRALOGgDCwscJoEXblIvoDcKwioNlsRoWw7VrOb8",
            }
        )


class Template(TemplateItem, Enum):
    Pokemon = {"description": "Normal residents that resemble Pokemon."}
    Legendary = {"description": "Normal residents that resemble Legendary Pokemon."}
    Mythical = {"description": "Normal residents that resemble Mythical Pokemon."}
    UltraBeast = {"description": "Normal residents that resemble Ultra Beasts."}
    Paradox = {"description": "Normal residents that resemble Paradox Pokemon."}
    Mega = {
        "description": "Permanent Mega Evolutions.",
        "docs": {
            "Standard": "1QRlm692RM5lXBv3bx8YKdnkkeYqz8bYY9MLzR8ElX4s",
            "Unique Trait": "1FWmqSlYpyo-h3TpUXS1F6AlA4AmsshXvTAA2GZMM8_M",
        },
    }
    Fusion = {
        "description": "Individuals that share traits of more than two species.",
        "modifier": {"Species": ("Species", "Species 1, Species 2")},
        "exclude": [],
        "docs": {
            "Standard": "1i023rpuSBi8kLtiZ559VaxaOn-GMKqPo53QGiKZUFxM",
            "Unique Trait": "1pQ-MXvidesq9JjK1sXcsyt7qBVMfDHDAqz9fXdf5l6M",
        },
    }
    Variant = {
        "description": "Fan-made. Species variations (movesets, types)",
        "modifier": {"Species": ("Variant", "Variant Species")},
        "docs": {
            "Standard": "1T4Y8rVotXpRnAmCrOrVguIHszi8lY_iuSZcP2v2MiTY",
            "Unique Trait": "1o2C_GEp9qg2G8R49tC_j_9EIRgFsvc225gEku8NYE7A",
        },
    }
    CustomPokemon = {
        "description": "Fan-made. They are normal residents.",
        "modifier": {"Species": ("Fakemon", "Fakemon Species")},
        "docs": {
            "Standard": "1R9s-o018-ClHHP_u-eEIa038dfmQdNxssbP74PfVezY",
            "Unique Trait": "1CSi0yHJngnWRVdVnqUWwnNK9qXSubxPNSWAZtShSDF8",
            "Evolution": "1v48lBR4P5ucWtAFHBy0DpIzUCUPCQHVFlz4q-it-pj8",
            "Evolution w/ Unique Trait": "1NCHKjzdIQhxM4djpBrFrDxHgBU6ISCr_qRaRwHLJMWA",
        },
    }
    CustomMega = {
        "description": "Fan-made. Mega evolved and kept stuck like this.",
        "modifier": {"Species": ("Fakemon", "Mega Species")},
        "docs": {
            "Standard": "1KOQMm-ktM0Ad8nIncDxcYUQehF2elWYUg09FId6J_B0",
            "Unique Trait": "1tQPKNdxQTA33eUwNgWVGZMYJ3iQzloZIbSNirRXqhj4",
        },
    }
    CustomParadox = {
        "description": "Fan-made. From distant past/future, somehow ended up here.",
        "modifier": {"Species": ("Fakemon", "Paradox Species")},
        "docs": {
            "Standard": "1R9s-o018-ClHHP_u-eEIa038dfmQdNxssbP74PfVezY",
            "Unique Trait": "1CSi0yHJngnWRVdVnqUWwnNK9qXSubxPNSWAZtShSDF8",
        },
    }
    CustomUltraBeast = {
        "description": "Fan-made. From other dimensions, somehow ended up here.",
        "modifier": {"Species": ("Fakemon", "Ultra Beast Species")},
        "docs": {
            "Standard": "1R9s-o018-ClHHP_u-eEIa038dfmQdNxssbP74PfVezY",
            "Unique Trait": "1CSi0yHJngnWRVdVnqUWwnNK9qXSubxPNSWAZtShSDF8",
        },
    }

    async def process(self, oc: Character, itx: Interaction[CustomBot], ephemeral: bool):
        choices: list[Species] = []
        db: AsyncIOMotorCollection = itx.client.mongo_db("Characters")

        if mons := self.total_species:
            key = {"server": itx.guild_id}
            if role := get(itx.guild.roles, name="Roleplayer"):
                key["author"] = {"$in": [x.id for x in role.members]}
            ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
            view = SpeciesComplex(
                member=itx.user,
                target=itx,
                mon_total=mons,
                max_values=self.max_values,
                ocs=ocs,
            )
            async with view.send(ephemeral=ephemeral) as data:
                if self.min_values <= len(data) <= self.max_values:
                    choices.extend(data)
                else:
                    return

        default_measure: bool = False

        match self.name:
            case "Fusion" | "Crossbreed":
                oc.species = Fusion(*choices)
                default_measure = True
            case "Variant":
                async with ModernInput(member=itx.user, target=itx).handle(
                    label=f"{choices[0].name} Variant"[:45],
                    ephemeral=ephemeral,
                    default=choices[0].name,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        if isinstance(oc.species, Variant) and oc.species.base == choices[0]:
                            oc.species.name = answer
                        else:
                            oc.species = Variant(base=choices[0], name=answer)
                            default_measure = True
            case "CustomParadox":
                async with ModernInput(member=itx.user, target=itx).handle(
                    label=f"Paradox {choices[0].name}"[:45],
                    ephemeral=ephemeral,
                    default=choices[0].name,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        if isinstance(oc.species, CustomParadox) and oc.species.base == choices[0]:
                            oc.species.name = answer
                        else:
                            oc.species = CustomParadox(base=choices[0], name=answer)
                            default_measure = True
            case "CustomUltraBeast":
                async with ModernInput(member=itx.user, target=itx).handle(
                    label=f"UB {choices[0].name}"[:45],
                    ephemeral=ephemeral,
                    default=choices[0].name,
                    required=True,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        if isinstance(oc.species, CustomUltraBeast) and oc.species.base == choices[0]:
                            oc.species.name = answer
                        else:
                            oc.species = CustomUltraBeast(base=choices[0], name=answer)
                            default_measure = True
            case "CustomMega":
                default_measure = not (isinstance(oc.species, CustomMega) and oc.species.base == choices[0])
                oc.species = CustomMega(choices[0])
                oc.abilities &= oc.species.abilities
            case "CustomPokemon":
                name = oc.species.name if isinstance(oc.species, Fakemon) else None
                async with ModernInput(member=itx.user, target=itx).handle(
                    label="OC's Species.",
                    required=True,
                    ephemeral=ephemeral,
                    default=name,
                ) as answer:
                    if isinstance(answer, str) and answer:
                        if isinstance(oc.species, Fakemon):
                            oc.species.name = answer
                        else:
                            default_measure = True
                            oc.species = Fakemon(
                                name=answer,
                                abilities=oc.abilities,
                                base_image=oc.image_url,
                                movepool=Movepool(other=oc.moveset.copy()),
                            )
            case _:
                oc.species, abilities = choices[0], choices[0].abilities.copy()
                if len(abilities) <= 2:
                    oc.abilities = abilities
                else:
                    oc.abilities &= abilities
                default_measure = True

        if species := oc.species:
            moves = species.total_movepool()
            if not oc.moveset and len(moves) <= 6:
                oc.moveset = frozenset(moves)
            if not oc.abilities and len(species.abilities) == 1:
                oc.abilities = species.abilities.copy()

        if default_measure:
            oc.size = Size.M
            oc.weight = Size.M

    @property
    def min_values(self):
        return 2 if self == self.Fusion else 1

    @property
    def max_values(self):
        return 3 if self == self.Fusion else 1

    @property
    def total_species(self) -> frozenset[Species]:
        match self.name:
            case "Pokemon" | "Crossbreed":
                mon_total = Pokemon.all()
            case "Fusion":
                mon_total = Species.all()
            case "Legendary":
                mon_total = Legendary.all()
            case "Mythical":
                mon_total = Mythical.all()
            case "UltraBeast":
                mon_total = UltraBeast.all()
            case "Paradox":
                mon_total = Paradox.all()
            case "Mega":
                mon_total = Mega.all()
            case "CustomMega" | "Variant" | "CustomParadox":
                mon_total = Species.all(exclude=(Mega, Paradox))
            case "CustomUltraBeast":
                mon_total = Species.all(exclude=(Mega, Paradox, UltraBeast))
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
    def __init_subclass__(cls, name: Optional[str] = None, required: bool = False) -> None:
        cls.name = name or cls.__name__.removesuffix("Field")
        cls.required = required
        cls.description = cls.__doc__.strip() or ""

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
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        """Abstract method which affects progress and the character"""


class NameField(TemplateField, required=True):
    "Modify the OC's Name"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.name:
            return "Missing Name"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=itx.user, target=itx)
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


class AgeField(TemplateField, required=True):
    "Modify the OC's Age"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[AgeGroup](
            member=itx.user,
            target=itx,
            timeout=None,
            values=AgeGroup,
            parser=lambda x: (x.title, x.description),
            sort_key=lambda x: x.key,
            silent_mode=True,
        )
        async with view.send(
            title=f"{template.title} Character's Age.",
            description=f"> {oc.age.title}",
            single=True,
            ephemeral=ephemeral,
        ) as age:
            if isinstance(age, AgeGroup):
                oc.age = age
                progress.add(cls.name)


class PronounField(TemplateField, required=True):
    "He, She, Them"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.pronoun:
            return "No pronoun added."

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Pronoun](
            member=itx.user,
            target=itx,
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


class SpeciesField(TemplateField, required=True):
    "Modify the OC's Species"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not (species := oc.species):
            return "Missing Species"

        if species.banned:
            return f"{species.name} as species are banned."

        if isinstance(
            species,
            (
                Variant,
                CustomMega,
                CustomParadox,
                CustomUltraBeast,
            ),
        ) and isinstance(species.base, (Paradox, Mega)):
            return f"{species.base.name} can't have variants."

        if isinstance(species, CustomUltraBeast) and isinstance(species.base, UltraBeast):
            return f"{species.base.name} is already an ultra beast."

        if isinstance(species, Fakemon) and isinstance(species.species_evolves_from, (Paradox, Mega)):
            return f"{species.species_evolves_from.name} can't custom evolve."

        if isinstance(species, Fusion) and len(species.bases) < 2:
            return "Must include at least 2 species."

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        await template.process(oc=oc, itx=itx, ephemeral=ephemeral)
        if oc.species:
            progress.add(cls.name)


class SizeField(TemplateField):
    "Modify the OC's Size"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    def evaluate(cls, oc: Character):
        if isinstance(oc.size, Size):
            return

        if Move.get(name="Transform") in oc.total_movepool:
            height_a, height_b = 0.1, 20.0
        elif isinstance(oc.species, Fusion):
            s_a, *_, s_b = sorted(oc.species.bases, key=lambda x: x.height)
            height_a, height_b = s_a.height, s_b.height
        else:
            height_a = height_b = oc.species.height

        if not (Size.Mini_XXXS.height_value(height_a) <= oc.size <= Size.Alpha_XXXL.height_value(height_b)):
            info1 = Size.Mini_XXXS.height_info(height_a)
            info2 = Size.Alpha_XXXL.height_info(height_b)
            return f"Min {info1}, Max: {info2}"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = HeightView(target=itx, member=itx.user, oc=oc)
        await view.send(
            title=f"{template.title} Character's Size.",
            description=f"> {oc.height_text}",
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class WeightField(TemplateField):
    "Modify the OC's Weight"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    def evaluate(cls, oc: Character):
        if isinstance(oc.weight, Size):
            return

        if Move.get(name="Transform") in oc.total_movepool:
            weight_a, weight_b = 0.1, 999.9
        elif isinstance(oc.species, Fusion):
            s_a, *_, s_b = sorted(oc.species.bases, key=lambda x: x.weight)
            weight_a, weight_b = s_a.weight, s_b.weight
        else:
            weight_a = weight_b = oc.species.weight

        if not (Size.Mini_XXXS.weight_value(weight_a) <= oc.weight <= Size.Alpha_XXXL.weight_value(weight_b)):
            info1 = Size.Mini_XXXS.weight_info(weight_a)
            info2 = Size.Alpha_XXXL.weight_info(weight_b)
            return f"Min {info1}, Max: {info2}"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = WeightView(target=itx, member=itx.user, oc=oc)
        await view.send(
            title=f"{template.title} Character's Weight.",
            description=f"> {oc.weight_text}",
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class PreEvoSpeciesField(TemplateField, name="Pre-Evolution"):
    "Modify the OC's Pre evo Species"

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
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        mon_total = {x for x in Species.all(exclude=(Paradox, Mega)) if not x.banned}
        db: AsyncIOMotorCollection = itx.client.mongo_db("Characters")
        key = {"server": itx.guild_id}
        if role := get(itx.guild.roles, name="Roleplayer"):
            key["author"] = {"$in": [x.id for x in role.members]}
        ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
        view = SpeciesComplex(member=itx.user, target=itx, mon_total=mon_total, ocs=ocs)
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


class TypesField(TemplateField, required=True):
    "Modify the OC's Types"

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

        limit = max(len(oc.species.bases), 2) if isinstance(oc.species, Fusion) else 2

        if len(oc.types) > limit:
            return f"Max {limit} Pokemon Types: ({', '.join(x.name for x in oc.types)})"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return isinstance(oc.species, (Fakemon, Variant, CustomMega, Fusion, CustomParadox, CustomUltraBeast))

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
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
            if template.name in ["Variant", "CustomPokemon"]:
                ignore.remove(TypingEnum.Typeless)

            values, max_values = TypingEnum.all(*ignore), 2

        view = Complex(
            member=itx.user,
            target=itx,
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
                species.types = frozenset(types)
                progress.add(cls.name)


class MovesetField(TemplateField, required=True):
    "Modify the OC's fav. moves"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if len(oc.moveset) > 4:
            return "Max 4 Preferred Moves."

        m1, m2 = Move.get(name="Transform"), Move.get(name="Sketch")

        movepool = Movepool.default(oc.total_movepool)

        if m1 in movepool or m2 in movepool:
            movepool = Movepool(other=Move.all(banned=False, shadow=False))

        moves = movepool()
        return ", ".join(x.name for x in oc.moveset if x not in moves)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species and oc.total_movepool

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        m1, m2 = Move.get(name="Transform"), Move.get(name="Sketch")
        movepool = Movepool.default(oc.total_movepool)

        if m1 in movepool or m2 in movepool:
            movepool = Movepool(other=Move.all(banned=False, shadow=False))

        view = MovepoolMoveComplex(
            member=itx.user,
            movepool=movepool,
            target=itx,
            choices={x for x in oc.moveset if x in movepool},
        )
        async with view.send(title=f"{template.title} Character's Moveset", ephemeral=ephemeral) as choices:
            if choices:
                oc.moveset = frozenset(choices)
                if isinstance(oc.species, (Fakemon, Variant, CustomParadox, CustomUltraBeast)) and not oc.movepool:
                    oc.species.movepool = Movepool(tutor=oc.moveset.copy())
                    progress.add(MovepoolField.name)
                progress.add(cls.name)


class MovepoolField(TemplateField, required=True):
    "Modify the OC's movepool"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        return ", ".join(x.name for x in oc.movepool() if x.banned)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return (
            isinstance(oc.species, (Fakemon, Variant, CustomParadox, CustomUltraBeast))
            and TypingEnum.Shadow not in oc.types
        )

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = MovepoolView(itx, itx.user, oc)
        await view.send(
            title=f"{template.title} OC's Movepool"[:45],
            ephemeral=ephemeral,
        )
        await view.wait()
        progress.add(cls.name)


class AbilitiesField(TemplateField, required=True):
    "Modify the OC's Abilities"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        m = Move.get(name="Transform")

        if not 1 <= len(oc.abilities) <= 2:
            return "Abilities, Min: 1, Max: 2"

        if len(values := [x.name for x in oc.abilities if x.name in ABILITIES_DEFINING]) > 1:
            return f"Carrying {', '.join(values)}"

        if isinstance(oc.species, CustomParadox) and "Protosynthesis" not in values and "Quark Drive" not in values:
            return "Protosynthesis/Quark Drive needed."

        if isinstance(oc.species, CustomUltraBeast) and "Beast Boost" not in values:
            return "Beast boost needed."

        if not isinstance(oc.species, (Fakemon, Variant, CustomMega)) and m not in oc.total_movepool:
            return ", ".join(x.name for x in oc.abilities if x not in oc.species.abilities)

    @classmethod
    def check(cls, oc: Character) -> bool:
        return bool(oc.species)

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        abilities, m = oc.species.abilities, Move.get(name="Transform")
        if isinstance(oc.species, (Fakemon, Variant, CustomMega)) or (not abilities) or m in oc.total_movepool:
            abilities = ALL_ABILITIES.values()

        view = Complex[Ability](
            member=itx.user,
            values=abilities,
            timeout=None,
            target=itx,
            max_values=min(len(abilities), 2),
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
                if isinstance(oc.species, (Fakemon, Variant)):
                    oc.species.abilities = frozenset(choices)
                progress.add(cls.name)


class HiddenPowerField(TemplateField, name="Hidden Power"):
    "Typing that matches with their soul's"

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if oc.hidden_power and oc.hidden_power in [TypingEnum.Shadow, TypingEnum.Typeless]:
            return "Invalid Hidden Power."

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[TypingEnum](
            member=itx.user,
            target=itx,
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
    "OC's Nature"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Nature](
            member=itx.user,
            target=itx,
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


class UniqueTraitField(TemplateField, name="Unique Trait", required=True):
    "No other in species but OC can do it."

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = SPAbilityView(itx, itx.user, oc)
        await view.send(ephemeral=ephemeral)
        await view.wait()

        oc.sp_ability = view.sp_ability if view.sp_ability.valid else None
        progress.add(cls.name)


class BioField(TemplateField, required=True):
    "Define who is the character."

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=itx.user, target=itx)
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


class HiddenField(TemplateField, name="Hidden Information", required=False):
    "Define the OC's Hidden Information"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=itx.user, target=itx)
        async with text_view.handle(
            label="OC's Hidden Information.",
            placeholder=oc.hidden_info if ephemeral else "Hidden",
            default=oc.hidden_info,
            required=False,
            ephemeral=ephemeral,
            style=TextStyle.paragraph,
        ) as answer:
            if isinstance(answer, str):
                oc.hidden_info = answer or None
                progress.add(cls.name)


class PersonalityField(TemplateField, required=False):
    "Modify the OC's Personality"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=itx.user, target=itx)
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


class ExtraField(TemplateField, name="Extra Information", required=False):
    "Modify the OC's Extra Information"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        text_view = ModernInput(member=itx.user, target=itx)
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


class ImageField(TemplateField, required=True):
    "Modify the OC's Image"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species and oc.types

    @classmethod
    def evaluate(cls, oc: Character) -> Optional[str]:
        if not oc.image:
            return "No Image has been defined"
        if isinstance(oc.image, File):
            return "Image in Memory"

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        _: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        default_image = oc.image_url or oc.image or oc.default_image
        view = ImageView(member=itx.user, default_img=default_image, target=itx)
        async with view.send(ephemeral=ephemeral) as text:
            if text is None:
                oc.image = None
                progress.discard(cls.name)
            else:
                oc.image_url = text or default_image
                if oc.image:
                    progress.add(cls.name)


class PokeballField:
    "Specify if OC has a pokeball or not"

    @classmethod
    def check(cls, oc: Character) -> bool:
        return oc.species

    @classmethod
    async def on_submit(
        cls,
        itx: Interaction[CustomBot],
        template: Template,
        progress: set[str],
        oc: Character,
        ephemeral: bool = False,
    ):
        view = Complex[Pokeball](
            member=itx.user,
            target=itx,
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
        itx: Interaction[CustomBot],
        user: Member,
        oc: Optional[Character] = None,
        template: Optional[Template] = None,
        progress: set[str] = None,
    ):
        super(CreationOCView, self).__init__(target=itx, member=user, timeout=None)
        self.embed.title = "Character Creation"
        self.bot = bot
        oc = oc.copy() if oc else Character()
        oc.author = oc.author or user.id
        oc.server = itx.guild.id
        self.oc = oc
        self.user = user
        self.embeds = oc.embeds
        message = getattr(itx, "message", itx)
        self.ephemeral = isinstance(message, Message) and message.flags.ephemeral
        if not isinstance(template, Template):
            name = template if isinstance(template, str) else type(oc.species).__name__
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

        self.submit.label = "Save Changes" if self.oc.id else "Submit OC"
        self.cancel.label = "Close this Menu"
        self.finish_oc.label = "Delete OC"

        if bool(errors):
            self.submit.style = ButtonStyle.red
        else:
            self.submit.style = ButtonStyle.green

        self.submit.disabled = False if self.member.guild_permissions.administrator else bool(errors)

        if embed_update:
            embeds = self.oc.embeds
            embeds[0].set_author(name=self.user.display_name, icon_url=self.user.display_avatar)
            self.embeds = embeds

    @select(placeholder="Select Kind", row=0)
    async def kind(self, itx: Interaction[CustomBot], sct: Select):
        try:
            self.oc.species = None
            items = [SpeciesField, TypesField, AbilitiesField, MovepoolField]
            self.progress -= {x.name for x in items}
            self.ref_template = Template[sct.values[0]]
            self.oc.size = self.oc.weight = Size.M
            await self.update(itx)
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

    async def update(self, itx: Interaction):
        resp: InteractionResponse = itx.response
        if self.is_finished():
            return

        condition = ImageField.name not in self.progress
        self.setup(condition)
        embeds, files = self.embeds, MISSING
        embed = embeds[0]
        image = self.oc.image or self.oc.image_url

        if isinstance(self.oc.image, File):
            try:
                self.oc.image.fp.seek(0)
                files = [self.oc.image]
                embed.set_image(url="attachment://image.png")
            except ValueError:
                files, self.oc.image = [], None
                condition = False
                self.progress.discard(ImageField.name)
                embed.set_image(url=image)
        else:
            embed.set_image(url=image)

        try:
            if resp.is_done() and (message := self.message or itx.message):
                try:
                    m = await message.edit(embeds=embeds, view=self, attachments=files)
                except DiscordException:
                    m = await itx.edit_original_response(embeds=embeds, view=self, attachments=files)
            else:
                await resp.edit_message(embeds=embeds, view=self, attachments=files)
                m = await itx.original_response()

            if files and m.embeds:
                self.oc.image = m.embeds[0].image.proxy_url or m.embeds[0].image.url
                self.setup(embed_update=False)
                m = await m.edit(view=self)

            self.message = m
        except DiscordException:
            await self.help_method(itx)

    async def handler_send(self, *, ephemeral: bool = False, embeds: list[Embed] | None = None):
        self.ephemeral = ephemeral
        self.embeds = embeds or self.embeds
        return await self.send(embeds=self.embeds, ephemeral=ephemeral, content=str(self.oc.id or ""))

    @select(placeholder="Essentials. Click here!", row=1)
    async def fields1(self, itx: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = itx.response
        if item := TemplateField.get(name=sct.values[0]):
            self.ephemeral = (itx.message and itx.message.flags.ephemeral) or self.ephemeral
            await resp.defer(ephemeral=self.ephemeral, thinking=True)
            await item.on_submit(itx, self.ref_template, self.progress, self.oc, self.ephemeral)
        await self.update(itx)

    @select(placeholder="Extras. Click here!", row=2)
    async def fields2(self, itx: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = itx.response
        if item := TemplateField.get(name=sct.values[0]):
            self.ephemeral = (itx.message and itx.message.flags.ephemeral) or self.ephemeral
            await resp.defer(ephemeral=self.ephemeral, thinking=True)
            await item.on_submit(itx, self.ref_template, self.progress, self.oc, self.ephemeral)
        await self.update(itx)

    async def delete(self, itx: Optional[Interaction] = None) -> None:
        db = self.bot.mongo_db("OC Creation")
        if m := self.message or (itx and itx.message):
            guild_id = itx.guild_id if itx else self.oc.server
            await db.delete_one({"id": m.id, "server": guild_id})
        return await super(CreationOCView, self).delete(itx)

    @button(label="Delete OC", emoji="\N{PUT LITTER IN ITS PLACE SYMBOL}", style=ButtonStyle.red, row=3)
    async def finish_oc(self, itx: Interaction[CustomBot], btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)

        if self.oc.id and self.oc.thread:
            if not (channel := itx.guild.get_channel_or_thread(self.oc.thread)):
                channel = await itx.guild.fetch_channel(self.oc.thread)
            await channel.edit(archived=False)
            await channel.get_partial_message(self.oc.id).delete(delay=0)
        await self.delete(itx)

    @button(emoji="\N{PRINTER}", style=ButtonStyle.blurple, row=3)
    async def printer(self, itx: Interaction[CustomBot], _: Button):
        await itx.response.defer(ephemeral=True, thinking=True)
        oc_file = await self.oc.to_docx(itx.client)
        await itx.followup.send(file=oc_file, ephemeral=True)
        itx.client.logger.info("User %s printed %s", str(itx.user), repr(self.oc))

    @button(label="Close this Menu", row=3)
    async def cancel(self, itx: Interaction[CustomBot], btn: Button):
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await itx.response.edit_message(view=self)
        await self.delete(itx)

    async def help_method(self, itx: Interaction[CustomBot]):
        db = self.bot.mongo_db("Server")
        if info := await db.find_one(
            {
                "id": itx.guild_id,
                "oc_submission": {"$exists": True},
            },
            {
                "_id": 0,
                "oc_submission": 1,
            },
        ):
            channel = itx.guild.get_channel(info["oc_submission"])

            view = CreationOCView(
                bot=self.bot,
                itx=channel,
                user=self.member,
                oc=self.oc,
                template=self.ref_template,
                progress=self.progress,
            )
            await view.handler_send(ephemeral=False)

        if isinstance(self.oc.image, str) and (oc_file := await itx.client.get_file(self.oc.image)):
            embeds = view.embeds
            attachments = [oc_file]
            embeds[0].set_image(url=f"attachment://{oc_file.filename}")
            message = await view.message.edit(attachments=attachments, embeds=embeds)
            if image := message.embeds[0].image:
                self.oc.image = image.url

        await self.delete(itx)

    @button(disabled=True, label="Submit", style=ButtonStyle.green, row=3)
    async def submit(self, itx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = itx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        try:
            await resp.defer(ephemeral=True, thinking=True)
            cog = itx.client.get_cog("Submission")
            word = "modified" if self.oc.id else "registered"
            self.oc.location, self.oc.last_used = None, itx.id
            await cog.register_oc(self.oc)
            msg = await itx.followup.send(f"Character {self.oc.name} {word} without Issues!", ephemeral=True, wait=True)
            await msg.delete(delay=2)
        except Exception as e:
            self.bot.logger.exception("Error in oc %s", btn.label, exc_info=e)
        finally:
            await self.delete(itx)


class ModCharactersView(CharactersView):
    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, itx: Interaction[CustomBot], sct: Select) -> None:
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        try:
            if item := self.current_choice:
                user: Member = itx.client.supporting.get(itx.user, itx.user)
                embeds = item.embeds
                if author := itx.guild.get_member(item.author):
                    embeds[0].set_author(name=author.display_name, icon_url=author.display_avatar)
                if (
                    itx.user.guild_permissions.manage_messages
                    or itx.user.id == itx.guild.owner_id
                    or item.author in [itx.user.id, user.id]
                ):
                    view = CreationOCView(bot=itx.client, itx=itx, user=user, oc=item)
                    await view.handler_send(ephemeral=True, embeds=embeds)
                else:
                    view = PingView(oc=item, reference=itx)
                    await itx.followup.send(content=item.id, embeds=embeds, view=view, ephemeral=True)

        except Exception as e:
            itx.client.logger.exception("Error in ModOCView", exc_info=e)
        finally:
            await super(CharactersView, self).select_choice(itx, sct)


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

    async def on_submit(self, itx: Interaction[CustomBot]):
        resp: InteractionResponse = itx.response
        refer_author = itx.user
        try:
            db = itx.client.mongo_db("Server")
            info = await db.find_one(
                {
                    "id": itx.guild_id,
                    "staff": {"$exists": True},
                    "oc_images": {"$exists": True},
                },
                {
                    "_id": 0,
                    "staff": 1,
                    "oc_images": 1,
                },
            )

            author: Member = itx.client.supporting.get(refer_author, refer_author)
            async for item in ParserMethods.parse(text=self.text.value, bot=itx.client):
                oc = Character.process(**item)
                oc.server = itx.guild_id

                if isinstance(oc.image, File):
                    w = await itx.client.webhook(info["staff"])
                    msg = await w.send(
                        file=oc.image,
                        wait=True,
                        username=safe_username(author.display_name),
                        avatar_url=author.display_avatar.url,
                        thread=Object(id=info["oc_images"]),
                    )
                    if msg.attachments:
                        oc.image = msg.attachments[0].url

                view = CreationOCView(bot=itx.client, itx=itx, user=author, oc=oc)
                if self.ephemeral:
                    await resp.edit_message(embeds=view.embeds, view=view)
                else:
                    await view.handler_send(ephemeral=False)
        except Exception as e:
            if not resp.is_done():
                await resp.defer(ephemeral=True, thinking=True)
            await itx.followup.send(str(e), ephemeral=True)
            itx.client.logger.exception(
                "Exception when registering, user: %s",
                str(itx.user),
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
    async def method(self, itx: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = itx.response
        match sct.values[0]:
            case "Form":
                ephemeral = bool(get(itx.user.roles, name="Roleplayer"))
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


class TemplateSelectionView(Basic):
    def __init__(self, itx: Interaction[CustomBot], member: Member):
        super(TemplateSelectionView, self).__init__(target=itx, member=member, timeout=None)
        self.show_template.options = [
            SelectOption(
                label=x.title,
                value=x.name,
                description=x.description[:100],
                emoji=RICH_PRESENCE_EMOJI,
            )
            for x in Template
        ]

    @select(placeholder="Click here to read our Templates", row=0, custom_id="read")
    async def show_template(self, itx: Interaction[CustomBot], sct: Select) -> None:
        template = Template[sct.values[0]]
        embed = Embed(title="How do you want to register your character?", color=0xFFFFFE)
        embed.set_image(url="https://hmp.me/dx38")
        embed.set_footer(text="After sending, bot will ask for backstory, extra info and image.")
        await itx.response.edit_message(embed=embed, view=TemplateView(template))


class SubmissionView(Basic):
    @select(cls=UserSelect, placeholder="Read User's OCs", custom_id="user-ocs", min_values=0, row=0)
    async def user_ocs(self, itx: Interaction[CustomBot], sct: UserSelect):
        db: AsyncIOMotorCollection = itx.client.mongo_db("Characters")
        member: Member = sct.values[0] if sct.values else itx.user
        await itx.response.defer(ephemeral=True, thinking=True)
        values = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": itx.guild_id})]
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=itx.user, target=itx, ocs=values)
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        itx.client.logger.info("%s is reading/modifying characters", str(itx.user))
        await view.simple_send()

    @button(
        label="Create",
        emoji="\N{PENCIL}",
        row=1,
        custom_id="add-oc",
        style=ButtonStyle.blurple,
    )
    async def oc_add(self, itx: Interaction[CustomBot], _: Button):
        cog = itx.client.get_cog("Submission")
        user: Member = itx.client.supporting.get(itx.user, itx.user)
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        users = {itx.user.id, user.id}
        try:
            cog.ignore |= users
            view = CreationOCView(
                bot=itx.client,
                itx=itx,
                user=user,
                template=Template.Pokemon,
            )
            await view.handler_send(ephemeral=True)
            await view.wait()
        except Exception as e:
            await itx.followup.send(str(e), ephemeral=True)
            itx.client.logger.exception("Character Creation Exception", exc_info=e)
        finally:
            cog.ignore -= users

    @button(
        label="Modify",
        emoji="\N{PENCIL}",
        row=1,
        custom_id="modify-oc",
        style=ButtonStyle.blurple,
    )
    async def oc_update(self, itx: Interaction[CustomBot], _: Button):
        db: AsyncIOMotorCollection = itx.client.mongo_db("Characters")
        resp: InteractionResponse = itx.response
        member: Member = itx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = itx.client.supporting.get(member, member)
        values = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": itx.guild_id})]
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=itx.user, target=itx, ocs=values)
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        await view.simple_send(title="Select Character to modify")
        itx.client.logger.info("%s is modifying characters", str(itx.user))

    @button(label="Delete", style=ButtonStyle.red, emoji="\N{WASTEBASKET}", row=1, custom_id="delete-oc")
    async def oc_delete(self, itx: Interaction[CustomBot], _: Button):
        db: AsyncIOMotorCollection = itx.client.mongo_db("Characters")
        resp: InteractionResponse = itx.response
        member: Member = itx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = itx.client.supporting.get(member, member)
        key = {"author": member.id, "server": itx.guild_id}
        values = [Character.from_mongo_dict(x) async for x in db.find(key)]
        values.sort(key=lambda x: x.name)
        view = BaseCharactersView(
            member=itx.user,
            target=itx,
            ocs=values,
            max_values=len(values),
            auto_conclude=False,
        )
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(title="Select Characters to delete") as choices:
            if choices and isinstance(choices, set):
                thread_id = values[0].thread
                if not (channel := itx.guild.get_channel_or_thread(thread_id)):
                    channel = await itx.guild.fetch_channel(thread_id)
                await channel.edit(archived=False)
                for oc in choices:
                    msg = channel.get_partial_message(oc.id)
                    await msg.delete(delay=0)
                itx.client.logger.info("%s is deleting %s characters", str(itx.user), len(choices))

    @button(label="Check Map", emoji="\N{WORLD MAP}", row=3, custom_id="see-map")
    async def see_map(self, itx: Interaction[CustomBot], _: Button):
        db = itx.client.mongo_db("Characters")
        key = {"server": itx.guild_id, "location": {"$type": 18}}
        if role := get(itx.guild.roles, name="Roleplayer"):
            key["author"] = {"$in": [x.id for x in role.members]}
        ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]
        view = RegionViewComplex(member=itx.user, target=itx, ocs=ocs)
        await view.simple_send(ephemeral=True)

    @button(label="Ticket", emoji=STICKER_EMOJI, row=2, custom_id="ticket")
    async def create_ticket(self, itx: Interaction[CustomBot], _: Button):
        await itx.response.send_modal(TicketModal(timeout=None))

    @button(label="RP Search", row=2, custom_id="rp-search", emoji="🔍")
    async def rp_search(self, itx: Interaction[CustomBot], _: Button):
        db = itx.client.mongo_db("Characters")
        db1 = itx.client.mongo_db("Characters")

        guild = itx.guild
        user = itx.client.supporting.get(itx.user, itx.user)

        ocs = [
            Character.from_mongo_dict(x)
            async for x in db.find(
                {
                    "author": user.id,
                    "server": guild and guild.id,
                }
            )
        ]
        ocs.sort(key=lambda x: x.name)

        if info := await db1.find_one(
            {"id": itx.guild_id, "looking_for_rp": {"$exists": True}},
            {
                "_id": 0,
                "looking_for_rp": 1,
            },
        ):
            role_id = info["looking_for_rp"]
        else:
            role_id = None

        to_user = itx.guild and itx.guild.get_role(role_id)
        modal = RPModal(user=user, ocs=ocs, to_user=to_user)

        if await modal.check(itx):
            await itx.response.send_modal(modal)

    @button(emoji="\N{INFORMATION SOURCE}", label="Templates (Alternative)", row=2, custom_id="info")
    async def info(self, itx: Interaction[CustomBot], btn: Button):
        view = TemplateSelectionView(itx=itx, member=itx.user)
        embed = Embed(
            title=btn.label,
            description="Select the template you want to use.",
            color=Color.blurple(),
        )
        await itx.response.send_message(embed=embed, view=view, ephemeral=True)
