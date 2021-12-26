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
from discord import (
    ButtonStyle,
    CategoryChannel,
    Interaction,
    InteractionResponse,
    Member,
    PermissionOverwrite,
    SelectOption,
    TextChannel,
)
from discord.ui import Button, Select, View, button, select
from discord.utils import utcnow

from src.cogs.submission.cog import Submission
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import MAP_BUTTONS
from src.views.characters_view import CharactersView


class AreaSelection(View):

    # noinspection PyTypeChecker
    def __init__(self, bot: CustomBot, cat: CategoryChannel, member: Member):
        super(AreaSelection, self).__init__(timeout=None)
        self.bot = bot
        self.cat = cat
        self.member = member
        registered = member.guild.get_role(719642423327719434)
        if registered not in member.roles:
            self.remove_item(self.read_one)
            self.remove_item(self.read_all)
            self.remove_item(self.disable_all)
            btn = Button(
                label="Go to OC-Submission in order to get access to the RP.",
                url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
                emoji="\N{OPEN BOOK}",
                row=1,
            )
            self.add_item(btn)
        perms = cat.overwrites.get(member, PermissionOverwrite())
        if perms.read_messages:
            self.read_one.label = "Toggle OFF"
            self.read_one.style = ButtonStyle.red
        else:
            self.read_one.label = "Toggle ON"
            self.read_one.style = ButtonStyle.green
        cog: Submission = bot.get_cog("Submission")
        self.entries: dict[str, set[Character]] = {}
        self.total: int = 0
        for location, ocs in cog.located.items():
            if ch := cat.guild.get_channel(location):
                if cat == ch.category:
                    self.entries[str(ch.id)] = ocs
                    self.total += len(ocs)

        self.selection.options = [
            SelectOption(
                label=f"{len(self.entries.get(str(item.id), [])):02d}{item.name[1:]}".replace(
                    "-", " "
                ).title(),
                value=str(item.id),
                description=topic[:50] if (topic := item.topic) else "No description yet.",
                emoji=item.name[0],
            )
            for item in cat.channels
            if not item.is_news()
        ]

    # noinspection PyTypeChecker
    @select(placeholder="Select a location to check", row=0)
    async def selection(self, _: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        if data := ctx.data.get("values", []):

            channel: TextChannel = self.bot.get_channel(int(idx := data[0]))
            self.bot.logger.info(
                "%s is reading Channel Information of %s",
                str(ctx.user),
                channel.name,
            )

            ocs = self.entries.get(idx, set())
            view = CharactersView(target=ctx, member=ctx.user, ocs=ocs, bot=self.bot)

            embed = view.embed

            embed.title = channel.name[2:].replace("-", " ").title()
            embed.description = channel.topic or "No description yet"
            embed.color = ctx.user.color
            embed.timestamp = utcnow()
            embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar.url)
            embed.set_footer(text=f"There's {len(ocs):02d} OCs here.")
            await resp.send_message(embed=embed, view=view, ephemeral=True)

    # noinspection PyTypeChecker
    @button(label="Toggle view ON/OFF", row=1)
    async def read_one(self, btn: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        permissions = self.cat.overwrites
        perms = permissions.get(ctx.user, PermissionOverwrite())
        perms.read_messages = btn.label == "Toggle ON"
        await self.cat.set_permissions(target=ctx.user, overwrite=perms)
        await ctx.followup.send("Permissions have been changed.", ephemeral=True)

    # noinspection PyTypeChecker
    @button(label="Enable all", row=1)
    async def read_all(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        for item in MAP_BUTTONS:
            category: CategoryChannel = ctx.guild.get_channel(int(item.value))
            permissions = category.overwrites
            perms = permissions.get(ctx.user, PermissionOverwrite())
            if not perms.read_messages:
                perms.read_messages = True
                await category.set_permissions(
                    ctx.user, overwrite=perms, reason="Region Selection"
                )
        await ctx.followup.send("Now you can see all the areas", ephemeral=True)

    # noinspection PyTypeChecker
    @button(label="Disable all", row=1)
    async def disable_all(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        for item in MAP_BUTTONS:
            category: CategoryChannel = ctx.guild.get_channel(int(item.value))
            permissions = category.overwrites
            perms = permissions.get(ctx.user, PermissionOverwrite())
            if perms.read_messages is not False:
                perms.read_messages = False
                await category.set_permissions(
                    ctx.user, overwrite=perms, reason="Region Selection"
                )
        await ctx.followup.send("Now you can't see all the areas", ephemeral=True)
