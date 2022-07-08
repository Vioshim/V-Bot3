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

from itertools import groupby
from threading import Thread

from discord import (
    CategoryChannel,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    TextChannel,
    User,
)
from discord.ui import Button, Select, View, select
from discord.utils import utcnow

from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS, MAP_ELEMENTS2, WHITE_BAR
from src.views.characters_view import CharactersView

__all__ = ("RegionView",)


class AreaSelection(View):
    def __init__(self, bot: CustomBot, cat: CategoryChannel, member: Member):
        super(AreaSelection, self).__init__(timeout=None)
        self.bot = bot
        self.cat = cat
        self.member = member
        if isinstance(member, User):
            guild = member.mutual_guilds[0]
        else:
            guild = member.guild
        registered = guild.get_role(719642423327719434)
        if registered not in member.roles:
            btn = Button(
                label="Go to OC-Submission in order to get access to the RP.",
                url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
                emoji="\N{OPEN BOOK}",
                row=1,
            )
            self.add_item(btn)
        cog = bot.get_cog("Submission")
        self.entries: dict[str, set[Character]] = {}

        def foo(oc: Character):
            ch = guild.get_channel_or_thread(oc.location)
            return bool(ch and cat == ch.category)

        def foo2(oc: Character):
            ch = guild.get_channel_or_thread(oc.location)
            if isinstance(ch, Thread):
                ch = ch.parent
            return ch

        entries = groupby(filter(foo, cog.ocs.values()), key=foo2)
        self.entries = {str(k.id): set(v) for k, v in entries if k}
        self.total = sum(len(item) for item in self.entries.values())

        self.selection.options = [
            SelectOption(
                label=f"{len(self.entries.get(str(item.id), [])):02d}{item.name[1:]}".replace("-", " ").title(),
                value=str(item.id),
                description=(item.topic or "No description yet.")[:50],
                emoji=item.name[0],
            )
            for item in cat.channels
            if not item.name.endswith("-ooc")
        ]

    @select(placeholder="Select a location to check", row=0)
    async def selection(self, ctx: Interaction, sct: Select):
        channel: TextChannel = self.bot.get_channel(int(sct.values[0]))
        self.bot.logger.info("%s is reading Channel Information of %s", str(ctx.user), channel.name)
        ocs = self.entries.get(sct.values[0], set())
        view = CharactersView(target=ctx, member=ctx.user, ocs=ocs, keep_working=True)
        embed = view.embed
        embed.title = channel.name[2:].replace("-", " ").title()
        embed.description = channel.topic or "No description yet"
        embed.color = ctx.user.color
        embed.timestamp = utcnow()
        embed.set_author(name=ctx.user.display_name, icon_url=ctx.user.display_avatar.url)
        embed.set_footer(text=f"There's {len(ocs):02d} OCs here.")
        async with view.send(ephemeral=True, embed=embed):
            self.bot.logger.info("%s user is checking ocs at %s", str(ctx.user), channel.name)


class RegionView(View):
    @select(
        placeholder="Select Regions",
        custom_id="region",
        row=0,
        options=[
            SelectOption(
                label=item.name,
                description=(item.short_desc or item.desc)[:100],
                value=item.category,
                emoji=item.emoji,
            )
            for item in MAP_ELEMENTS
        ],
    )
    async def choice(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        info = MAP_ELEMENTS2[int(sct.values[0])]
        cat = ctx.guild.get_channel(info.category)
        embed = Embed(title=info.name, description=info.desc, timestamp=utcnow(), color=ctx.user.color)
        embed.set_image(url=info.image or WHITE_BAR)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        view = AreaSelection(bot=ctx.client, cat=cat, member=ctx.user)
        ctx.client.logger.info(
            "%s is reading Map Information of %s",
            str(ctx.user),
            cat.name,
        )
        await ctx.followup.send(
            content=f"There's a total of {view.total:02d} OCs in {cat.name}.",
            view=view,
            embed=embed,
            ephemeral=True,
        )
