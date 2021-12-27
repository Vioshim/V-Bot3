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

from unicodedata import lookup

from discord import (
    CategoryChannel,
    Embed,
    Interaction,
    InteractionResponse,
    SelectOption,
)
from discord.ui import Button, Select, View, select
from discord.utils import utcnow

from src.cogs.information.area_selection import AreaSelection
from src.structures.bot import CustomBot


class InformationView(View):
    def __init__(self, bot: CustomBot, raw_data: dict[str, list[dict]]):
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
                ref_index = str(value if (value := info.get("category")) else index)
                embeds[k][ref_index] = embed
                buttons[k].setdefault(ref_index, [])
                for btn in info.get("buttons", []):
                    buttons[k][ref_index].append(Button(**btn))

        self.buttons = buttons
        self.embeds = embeds
        self.server_faq.options = [
            SelectOption(
                label=item["label"],
                value=str(index),
                description=item["title"][:50],
                emoji="\N{BLUE BOOK}",
            )
            for index, item in enumerate(raw_data.get("Server F.A.Q.", []))
        ]
        self.rp_faq.options = [
            SelectOption(
                label=item["label"],
                value=str(index),
                description=item["title"][:50],
                emoji="\N{CLOSED BOOK}",
            )
            for index, item in enumerate(raw_data.get("RP F.A.Q.", []))
        ]
        self.oc_faq.options = [
            SelectOption(
                label=item["label"],
                value=str(index),
                description=item["title"][:50],
                emoji="\N{ORANGE BOOK}",
            )
            for index, item in enumerate(raw_data.get("OC Creation F.A.Q.", []))
        ]
        self.npc_faq.options = [
            SelectOption(
                label=item["label"],
                value=str(index),
                description=item["title"][:50],
                emoji="\N{GREEN BOOK}",
            )
            for index, item in enumerate(raw_data.get("NPC F.A.Q.", []))
        ]
        self.map_faq.options = [
            SelectOption(
                label=value["label"],
                value=str(value.get("category")),
                description=item if (item := value.get("summary")) else value.get("content", "")[:50],
                emoji=lookup(value["emoji"]),
            )
            for value in raw_data.get("Map Information", [])
        ]

    async def read(self, ctx: Interaction, key: str):
        resp: InteractionResponse = ctx.response
        if data := ctx.data.get("values", []):
            self.bot.logger.info("%s is reading %s[%s]", str(ctx.user), key, idx := data[0])
            info_embed = self.embeds[key][idx].copy()
            info_embed.colour = ctx.user.colour
            info_embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)

            view = View(timeout=None)
            for info_btn in self.buttons[key].get(idx, []):
                view.add_item(info_btn)

            return await resp.send_message(embed=info_embed, view=view, ephemeral=True)

    @select(
        placeholder="Server F.A.Q.",
        custom_id="57879ffc62fa57687f7974e3631fe309",
    )
    async def server_faq(self, item: Select, ctx: Interaction):
        await self.read(ctx, item.placeholder)

    @select(placeholder="RP F.A.Q.", custom_id="d359da22f702a8ff8e5378c2514db660")
    async def rp_faq(self, item: Select, ctx: Interaction):
        await self.read(ctx, item.placeholder)

    @select(
        placeholder="OC Creation F.A.Q.",
        custom_id="6e6d91d9ae3dec23fa0a6a786f422a1e",
    )
    async def oc_faq(self, item: Select, ctx: Interaction):
        await self.read(ctx, item.placeholder)

    @select(placeholder="NPC F.A.Q.", custom_id="380c54871c2feec9637ea0bff67f4098")
    async def npc_faq(self, item: Select, ctx: Interaction):
        await self.read(ctx, item.placeholder)

    @select(
        placeholder="Map Information",
        custom_id="b5cc20657d59bff25ab625a504f84b90",
    )
    async def map_faq(self, item: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        if data := ctx.data.get("values", []):
            idx: str = data[0]
            info_embed = self.embeds[item.placeholder][idx].copy()
            info_embed.colour = ctx.user.colour

            category: CategoryChannel = self.bot.get_channel(int(idx))
            self.bot.logger.info(
                "%s is reading Map Information of %s",
                str(ctx.user),
                category.name,
            )

            view = AreaSelection(bot=self.bot, cat=category, member=ctx.user)

            info_embed.set_footer(text=f"There's a total of {view.total:02d} OCs in this area.")

            for info_btn in self.buttons.get(item.placeholder, {}).get(idx, []):
                view.add_item(info_btn)

            return await resp.send_message(embed=info_embed, view=view, ephemeral=True)
