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
from src.structures.bot import CustomBot
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
        )

    async def custom_choice(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        index: str = sct.values[0]
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        item: Map = chunk[int(index)]
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
        )

    async def custom_choice(self, sct: Select, ctx: Interaction):
        index: str = sct.values[0]
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        item: Section = chunk[int(index)]
        view = Complex(
            bot=self.bot,
            member=self.member,
            values=item.items_ordered,
            target=ctx,
            timeout=None,
            parser=lambda x: x.tuple,
            emoji_parser=item.emoji,
        )
        async with view.send(ephemeral=True, single=True) as element:
            if isinstance(element, FAQ):
                embed = element.embed.copy()
                embed.colour = ctx.user.colour
                if guild := ctx.guild:
                    embed.set_footer(
                        text=guild.name,
                        icon_url=guild.icon.url,
                    )
                await ctx.edit_original_message(
                    embed=element.embed,
                    view=element.view,
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
                    title=key,
                    items=frozenset(items),
                )
                self.elements.append(section)
            elif isinstance(values, list):
                self.map_information = [Map(**info) for info in values]

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
        btn: Button,
        interaction: Interaction,
    ):
        """Function for F.A.Q. information

        Parameters
        ----------
        btn : Button
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
        embed.title = f"Parallel Yonder's {btn.label}"
        await resp.send_message(embed=embed, view=view, ephemeral=True)

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

        with suppress(NotFound):
            artist = await self.bot.fetch_user(536565959004127232)
            view.embed.set_author(
                name=f"Drawn by {artist}",
                icon_url=artist.display_avatar.url,
            )

        view.embed.title = f"Parallel Yonder's {btn.label}"
        view.embed.color = Color.blurple()
        view.embed.url = MAP_URL
        view.embed.set_image(url=MAP_URL)

        await resp.send_message(
            embed=view.embed,
            view=view,
            ephemeral=True,
        )
