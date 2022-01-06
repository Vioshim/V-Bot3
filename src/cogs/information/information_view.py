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

from contextlib import suppress
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
    SelectOption,
    User,
)
from discord.ui import Button, Select, View, button
from discord.utils import utcnow

from src.cogs.information.area_selection import AreaSelection
from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.utils.etc import MAP_URL, WHITE_BAR


class FAQComplex(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member | User,
        values: list[Select],
        target: Interaction,
        embeds: dict[str, dict[str, Embed]],
        buttons: dict[str, dict[str, list[Button]]],
    ):
        super(FAQComplex, self).__init__(
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
        resp: InteractionResponse = ctx.response
        index: str = ctx.data["values"][0]
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        item: Select = chunk[int(index)]
        view = View(timeout=None)
        item.callback = self.read(item.placeholder)
        view.add_item(item)
        self.embed.title = item.placeholder
        await resp.pong()
        await self.target.edit_original_message(embed=self.embed, view=view)
        await view.wait()

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

                await resp.send_message(
                    embed=info_embed, view=view, ephemeral=True
                )
            self.stop()

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
                options=[
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
            SelectOption(
                label=item["label"],
                value=str(item["category"]),
                description=item.get("content", "No description")[:100],
                emoji=lookup(item["emoji"]),
            )
            for item in self.raw_data.get("Map Information", [])
        ]
        btn = Button(
            label="Self Roles",
            url="https://discord.com/channels/719343092963999804/719709333369258015/",
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
        resp: InteractionResponse = interaction.response

        if isinstance(member := interaction.user, User):
            guild = member.mutual_guilds[0]
            member = guild.get_member(member.id)

        view = FAQComplex(
            bot=self.bot,
            member=member,
            values=self.faq_data,
            target=interaction,
            embeds=self.embeds,
            buttons=self.buttons,
        )
        embed = view.embed
        embed.title = f"Parallel Yonder's {btn.label}"
        embed.description = (
            "Select an option which you'd like to read more information about"
        )
        await resp.send_message(embed=embed, view=view, ephemeral=True)

    def map_callback(self, interaction: Interaction):
        async def inner(ctx: Interaction):
            resp: InteractionResponse = ctx.response
            if data := ctx.data.get("values", []):
                idx: str = data[0]
                info_embed = self.embeds["Map Information"][idx].copy()
                if isinstance(member := ctx.user, User):
                    guild = member.mutual_guilds[0]
                    member = guild.get_member(member.id)

                info_embed.colour = member.colour

                category: CategoryChannel = self.bot.get_channel(int(idx))
                self.bot.logger.info(
                    "%s is reading Map Information of %s",
                    str(member),
                    category.name,
                )

                view = AreaSelection(
                    bot=self.bot,
                    cat=category,
                    member=member,
                )

                info_embed.set_footer(
                    text=f"There's a total of {view.total:02d} OCs in this area."
                )

                await interaction.edit_original_message(
                    embed=info_embed, view=view
                )
                await resp.pong()

        return inner

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
        resp: InteractionResponse = ctx.response

        view = View(timeout=None)
        item = Select(placeholder=btn.label, options=self.map_information)
        item.callback = self.map_callback(ctx)
        view.add_item(item)

        embed = Embed(title="Parallel Yonder's Map", color=Color.blurple())
        with suppress(NotFound):
            artist = await self.bot.fetch_user(536565959004127232)
            embed.set_author(
                name=f"Drawn by {artist}",
                icon_url=artist.display_avatar.url,
            )
        embed.set_image(url=WHITE_BAR)

        await resp.send_message(
            content=MAP_URL,
            embed=embed,
            view=view,
            ephemeral=True,
        )
