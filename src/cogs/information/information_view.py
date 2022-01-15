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

from contextlib import suppress
from dataclasses import InitVar, dataclass, field
from typing import Iterable, Optional
from unicodedata import lookup

from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    NotFound,
    User,
)
from discord.ui import Button, Select, View, button
from discord.utils import utcnow

from src.cogs.information.area_selection import AreaSelection
from src.pagination.complex import Complex
from src.structures.ability import Ability
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import MAP_URL, WHITE_BAR


@dataclass(unsafe_hash=True)
class Map:
    label: str
    category: int
    content: str
    emoji: InitVar[str] = None
    map: str = None
    embed: Embed = field(init=False)

    def __post_init__(self, emoji: str = None):
        try:
            self.emoji = lookup(emoji)
        except KeyError:
            self.emoji = emoji
        embed = Embed(
            title=self.label,
            description=self.content,
            timestamp=utcnow(),
        )
        embed.set_footer(text=f"ID: {self.category}")
        if image := self.map:
            embed.set_image(url=image)
        else:
            embed.set_image(url=WHITE_BAR)
        self.embed = embed


@dataclass(unsafe_hash=True)
class FAQ:
    index: int
    label: Optional[str] = None
    title: InitVar[str] = None
    content: InitVar[str] = None
    fields: InitVar[Iterable[dict[str, str]]] = None
    buttons: InitVar[Iterable[Button]] = None
    thumbnail: InitVar[str] = None
    image: InitVar[str] = None
    embed: Embed = field(init=False)
    view: View = field(init=False)

    def __int__(self):
        return self.index

    def __post_init__(
        self,
        title: str = None,
        content: str = None,
        fields: Iterable[dict[str, str]] = None,
        buttons: Iterable[Button] = None,
        thumbnail: str = None,
        image: str = None,
    ):
        self.title = title
        self.content = content
        fields = fields or []
        buttons = buttons or []
        self.thumbnail = thumbnail
        self.image = image
        embed = Embed(
            title=title,
            description=content,
            colour=0xFFFFFE,
            timestamp=utcnow(),
        )
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        if image:
            embed.set_image(url=image)
        for item in fields:
            embed.add_field(**item)
        self.embed = embed
        self.view = View(timeout=None)
        for item in buttons:
            if isinstance(item, dict):
                item = Button(**item)
            if isinstance(item, Button):
                self.view.add_item(item)

    @property
    def tuple(self):
        return self.label, self.content


@dataclass(unsafe_hash=True)
class Section:
    title: str
    description: str
    emoji: Optional[str] = None
    items: frozenset[FAQ] = field(default_factory=frozenset)

    def __post_init__(self):
        if emoji := self.emoji:
            try:
                self.emoji = lookup(emoji)
            except KeyError:
                self.emoji = emoji
        else:
            self.emoji = "\N{BLUE BOOK}"

    @property
    def tuple(self):
        return (
            self.title,
            f"Function has {len(self.items):02d} choices to read.",
        )

    @property
    def items_ordered(self):
        data = list(self.items)
        data.sort(key=int)
        return data


class MapComplex(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member | User,
        values: list[Map],
        target: Interaction,
    ):
        super(MapComplex, self).__init__(
            bot=bot,
            timeout=None,
            member=member,
            values=values,
            target=target,
            parser=lambda x: (x.label, x.content),
            silent_mode=True,
            keep_working=True,
        )

    async def custom_choice(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        index: str = sct.values[0]
        item: Map = self.current_chunk[int(index)]
        category: CategoryChannel = self.bot.get_channel(item.category)
        self.bot.logger.info(
            "%s is reading Map Information of %s",
            str(self.member),
            item.label,
        )
        embed = item.embed.copy()
        embed.color = self.member.color
        view = AreaSelection(
            bot=self.bot,
            cat=category,
            member=self.member,
        )
        embed.set_footer(
            text=f"There's a total of {view.total:02d} OCs in this area."
        )
        await resp.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )


class FAQComplex(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member | User,
        values: list[FAQ],
        target: Interaction,
    ):
        super(FAQComplex, self).__init__(
            bot=bot,
            timeout=None,
            member=member,
            values=values,
            target=target,
            parser=lambda x: x.tuple,
            silent_mode=True,
            keep_working=True,
        )

    async def custom_choice(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        index: str = sct.values[0]
        item: FAQ = self.current_chunk[int(index)]
        self.bot.logger.info(
            "%s is reading its entry [%s]: %s",
            str(self.member),
            str(item.index),
            item.title,
        )
        embed = item.embed.copy()
        embed.color = self.member.color

        await resp.send_message(
            embed=embed,
            view=item.view,
            ephemeral=True,
        )


class SectionComplex(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member | User,
        values: list[Section],
        target: Interaction,
    ):
        super(SectionComplex, self).__init__(
            bot=bot,
            timeout=None,
            member=member,
            values=values,
            target=target,
            parser=lambda x: x.tuple,
            silent_mode=True,
            keep_working=True,
        )

    async def custom_choice(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        index: str = sct.values[0]
        item: Section = self.current_chunk[int(index)]
        self.bot.logger.info(
            "%s is reading %s",
            str(self.member),
            item.title,
        )
        view = FAQComplex(
            bot=self.bot,
            member=self.member,
            values=item.items_ordered,
            target=ctx,
        )
        embed = view.embed

        embed.title = f"Parallel Yonder's {item.title}"
        embed.description = item.description

        await resp.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )


class InformationView(View):
    def __init__(
        self,
        bot: CustomBot,
        raw_data: dict[str, list | dict],
    ):
        super(InformationView, self).__init__(timeout=None)
        self.bot = bot
        self.elements: list[Section] = []
        self.map_information: list[Map] = []

        for key, values in raw_data.items():
            if isinstance(values, dict):
                items = []
                for index, item in enumerate(values["items"]):
                    items.append(FAQ(**item, index=index))
                section = Section(
                    emoji=values["emoji"],
                    description=values["description"],
                    title=key,
                    items=frozenset(items),
                )
                self.elements.append(section)
            elif isinstance(values, list):
                self.map_information = [Map(**info) for info in values]

        items = []
        abilities = list(Ability.all())
        abilities.sort(key=lambda x: x.name)
        for index, item in enumerate(abilities):
            fields = []
            if battle := item.battle:
                fields.append(
                    dict(name="In Battles", value=battle, inline=False)
                )
            if outside := item.outside:
                fields.append(
                    dict(name="Out of Battles", value=outside, inline=False)
                )
            if random_fact := item.random_fact:
                fields.append(
                    dict(name="Random Fact", value=random_fact, inline=False)
                )
            items.append(
                FAQ(
                    index=index,
                    label=item.name,
                    title=item.name,
                    content=item.description,
                    fields=fields,
                )
            )

        self.elements.append(
            Section(
                emoji="<:pokeball:852189914157809705>",
                description="This is a description of all abilities, of course I haven't defined every single one of them yet, but these descriptions should at least work as heads up.",
                title="Abilities F.A.Q.",
                items=frozenset(items),
            )
        )

        items = []
        moves = list(Move.all())
        moves.sort(key=lambda x: x.name)
        for index, item in enumerate(moves):
            title = item.name
            if item.banned:
                title = f"{title} - Move Banned"
            fields = [
                dict(name="Base", value=str(item.base)),
                dict(name="Accuracy", value=str(item.accuracy)),
                dict(name="PP", value=str(item.pp)),
            ]

            element = FAQ(
                index=index,
                label=item.name,
                title=title,
                thumbnail=item.type.emoji.url,
                content=item.desc,
                fields=fields,
            )
            element.embed.color = item.type.color
            items.append(element)

        self.elements.append(
            Section(
                emoji="<:pokeball:852189914157809705>",
                description="This is a description of all Moves, of course I haven't defined every single one of them yet, but these descriptions should at least work as heads up.",
                title="Moves F.A.Q.",
                items=frozenset(items),
            )
        )

        btn = Button(
            label="Self Roles",
            url="https://discord.com/channels/719343092963999804/719709333369258015/",
        )
        self.add_item(btn)
        btn = Button(
            label="Character Creation",
            url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
        )
        self.add_item(btn)

    @button(
        label="F.A.Q.",
        custom_id="F.A.Q.",
        style=ButtonStyle.blurple,
    )
    async def faq(
        self,
        _: Button,
        interaction: Interaction,
    ):
        """Function for F.A.Q. information

        Parameters
        ----------
        _ : Button
            Button
        ctx : Interaction
            User Interaction
        """
        resp: InteractionResponse = interaction.response

        if isinstance(member := interaction.user, User):
            guild = member.mutual_guilds[0]
            member = guild.get_member(member.id)

        view = SectionComplex(
            bot=self.bot,
            member=member,
            values=self.elements,
            target=interaction,
        )

        embed = view.embed

        embed.title = "Parallel Yonder's FAQ"
        embed.description = "This command is pretty much a summary of common things that tend to be asked or are enforced, feel free to take a look and have fun."

        await resp.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )

    @button(
        label="Map Information",
        custom_id="Map Information",
        style=ButtonStyle.blurple,
    )
    async def map_info(
        self,
        btn: Button,
        ctx: Interaction,
    ):
        """Function for map information

        Parameters
        ----------
        btn : Button
            Button
        ctx : Interaction
            User Interaction
        """
        resp: InteractionResponse = ctx.response

        if isinstance(member := ctx.user, User):
            guild = member.mutual_guilds[0]
            member = guild.get_member(member.id)

        view = MapComplex(
            bot=self.bot,
            member=member,
            values=self.map_information,
            target=ctx,
        )

        embed = view.embed

        with suppress(NotFound):
            if not (artist := member.guild.get_member(536565959004127232)):
                artist = await self.bot.fetch_user(536565959004127232)
            embed.set_author(
                name=f"Drawn by {artist}",
                icon_url=artist.display_avatar.url,
            )

        embed.title = f"Parallel Yonder's {btn.label}"
        embed.color = Color.blurple()
        embed.url = MAP_URL
        embed.set_image(url=MAP_URL)

        await resp.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
