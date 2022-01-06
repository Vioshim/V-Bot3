# Copyright 2021 Vioshim
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

from abc import ABCMeta, abstractmethod
from unicodedata import lookup

from discord import (
    ButtonStyle,
    CategoryChannel,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    User,
)
from discord.ui import Button, Select, View, button
from discord.utils import utcnow

from src.cogs.information.area_selection import AreaSelection
from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.utils.etc import MAP_URL


class ReaderComplex(Complex, metaclass=ABCMeta):
    def __init__(
        self,
        bot: CustomBot,
        member: Member | User,
        values: list[Select],
        target: Interaction,
        embeds: dict[str, dict[str, Embed]],
        buttons: dict[str, dict[str, list[Button]]],
    ):
        super(ReaderComplex, self).__init__(
            bot=bot,
            timeout=None,
            member=member,
            values=values,
            target=target,
            parser=lambda x: (
                x.placeholder,
                f"Function has {len(x.options):02d} choices to read.",
            ),
            emoji_parser="\N{BLUE BOOK}",
        )
        self.embeds = embeds
        self.buttons = buttons

    async def custom_choice(self, _: Select, ctx: Interaction):
        response: InteractionResponse = ctx.response
        index: str = ctx.data["values"][0]
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        item: Select = chunk[int(index)]
        view = View(timeout=None)
        item.callback = self.read(item.placeholder)
        view.add_item(item)
        await self.target.edit_original_message(view=view)
        await response.pong()

    @abstractmethod
    def read(self, key: str):
        """Method to read from the existing FAQ Data

        Parameters
        ----------
        key : str
            Item to read
        """


class FAQComplex(ReaderComplex):
    def read(self, key: str):
        """Method to read from the existing FAQ Data

        Parameters
        ----------
        key : str
            Item to read
        """

        async def inner(ctx: Interaction):
            resp: InteractionResponse = ctx.response
            if data := ctx.data.get("values", []):
                self.bot.logger.info(
                    "%s is reading %s[%s]", str(ctx.user), key, idx := data[0]
                )
                info_embed = self.embeds[key][idx].copy()
                info_embed.colour = ctx.user.colour
                if guild := ctx.guild:
                    info_embed.set_footer(
                        text=guild.name, icon_url=guild.icon.url
                    )

                view = View(timeout=None)
                for info_btn in self.buttons[key].get(idx, []):
                    view.add_item(info_btn)

                self.target.edit_original_message(embed=info_embed, view=view)
                await resp.pong()

        return inner


class MapComplex(ReaderComplex):
    def read(self, key: str):
        async def inner(ctx: Interaction):
            resp: InteractionResponse = ctx.response
            if data := ctx.data.get("values", []):
                idx: str = data[0]
                info_embed = self.embeds[key][idx].copy()
                info_embed.colour = ctx.user.colour

                category: CategoryChannel = self.bot.get_channel(int(idx))
                self.bot.logger.info(
                    "%s is reading Map Information of %s",
                    str(ctx.user),
                    category.name,
                )

                view = AreaSelection(
                    bot=self.bot,
                    cat=category,
                    member=ctx.user,
                )

                info_embed.set_footer(
                    text=f"There's a total of {view.total:02d} OCs in this area."
                )

                for info_btn in self.buttons.get(key, {}).get(idx, []):
                    view.add_item(info_btn)

                self.target.edit_original_message(embed=info_embed, view=view)
                await resp.pong()

        return inner


class InformationView(View):
    def __init__(
        self,
        bot: CustomBot,
        raw_data: dict[str, list[dict]],
    ):
        super(InformationView, self).__init__(timeout=None)
        self.bot = bot
        self.raw_data = raw_data

        embeds: dict[str, dict[str, Embed]] = {}
        buttons: dict[str, dict[str, list[Button]]] = {}

        for k, v in raw_data.items():
            embeds.setdefault(k, {})
            buttons.setdefault(k, {})
            for index, info in enumerate(v):
                embed = Embed(
                    title=info.get("label"),
                    description=info.get("content"),
                    colour=0xFFFFFE,
                    timestamp=utcnow(),
                )
                if thumbnail := info.get("thumbnail"):
                    embed.set_thumbnail(url=thumbnail)
                if image := info.get("image"):
                    embed.set_image(url=image)
                for field in info.get("fields", []):
                    embed.add_field(**field)
                ref_index = str(
                    value if (value := info.get("category")) else index
                )
                embeds[k][ref_index] = embed
                buttons[k].setdefault(ref_index, [])
                for btn in info.get("buttons", []):
                    buttons[k][ref_index].append(Button(**btn))

        self.embeds = embeds
        self.buttons = buttons
        self.faq_data = [
            Select(
                placeholder=k,
                values=[
                    SelectOption(
                        label=item["label"],
                        value=str(index),
                        description=item["title"][:100],
                        emoji="\N{BLUE BOOK}",
                    )
                    for index, item in enumerate(v)
                ],
            )
            for k, v in raw_data.items()
            if k != "Map Information"
        ]
        self.map_information = [
            Select(
                placeholder=k,
                values=[
                    SelectOption(
                        label=item["label"],
                        value=str(item["category"]),
                        description=item["content"][:100],
                        emoji=lookup(item["emoji"]),
                    )
                    for item in value
                ],
            )
            for value in raw_data.get("Map Information", [])
        ]

    async def read(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        resp: InteractionResponse = interaction.response
        if btn.label == "F.A.Q.":
            data = FAQComplex
            values = self.faq_data
        else:
            data = MapComplex
            values = self.map_information

        view = data(
            bot=self.bot,
            member=interaction.user,
            values=values,
            target=interaction,
            embeds=self.embeds,
            buttons=self.buttons,
        )
        embed = view.embed
        embed.title = f"Parallel Yonder's {btn.label}"
        embed.description = (
            "Select an option which you'd like to read more information about"
        )
        if isinstance(view, MapComplex):
            embed.set_image(url=MAP_URL)
        await resp.send_message(embed=embed, view=view, ephemeral=True)

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
        await self.read(btn, interaction)

    @button(
        label="Map Information",
        custom_id="Map Information",
        style=ButtonStyle.blurple,
    )
    async def map_info(
        self,
        btn: Button,
        interaction: Interaction,
    ):
        await self.read(btn, interaction)
