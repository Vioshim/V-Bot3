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
    TextChannel,
    User,
)
from discord.ui import Select, select
from discord.utils import utcnow

from src.pagination.complex import Complex
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS, MAP_URL, WHITE_BAR, MapPair
from src.views.characters_view import CharactersView

__all__ = ("RegionViewComplex",)


class AreaSelection(Complex[TextChannel]):
    def __init__(self, target: Interaction, cat: CategoryChannel):
        channels = [x for x in cat.channels if not x.name.endswith("-ooc")]

        cog = target.client.get_cog("Submission")
        self.entries: dict[str, set[Character]] = {}

        def foo(oc: Character):
            ch = target.guild.get_channel_or_thread(oc.location)
            return bool(ch and cat == ch.category)

        def foo2(oc: Character):
            ch = target.guild.get_channel_or_thread(oc.location)
            if isinstance(ch, Thread):
                ch = ch.parent
            return ch

        entries = groupby(sorted(filter(foo, cog.ocs.values()), key=foo2), key=foo2)
        self.entries = {k.id: set(v) for k, v in entries if k}
        self.total = sum(map(len, self.entries.values()))

        channels.sort(key=lambda x: len(self.entries.get(x.id, [])), reverse=True)

        super(AreaSelection, self).__init__(
            target=target,
            member=target.user,
            values=channels,
            silent_mode=True,
            keep_working=True,
            parser=lambda x: (
                f"{len(self.entries.get(x.id, [])):02d}{x.name[1:]}".replace("-", " ").title(),
                x.topic or "No description yet.",
            ),
            emoji_parser=lambda x: x.name[0],
        )

    @select(row=1, placeholder="Select a location to check", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        channel: TextChannel = self.current_choice
        self.bot.logger.info("%s is reading Channel Information of %s", str(interaction.user), channel.name)
        ocs = self.entries.get(channel.id, set())
        view = CharactersView(target=interaction, member=interaction.user, ocs=ocs, keep_working=True)
        embed = view.embed
        embed.title = channel.name[2:].replace("-", " ").title()
        embed.description = channel.topic or "No description yet"
        embed.color = interaction.user.color
        embed.timestamp = utcnow()
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"There's {len(ocs):02d} OCs here.")
        await view.simple_send(ephemeral=True, embed=embed)
        self.bot.logger.info("%s user is checking ocs at %s", str(interaction.user), channel.name)
        await super(AreaSelection, self).select_choice(interaction=interaction, sct=sct)


class RegionViewComplex(Complex[MapPair]):
    def __init__(self, *, member: Member | User, target: Interaction):
        super(RegionViewComplex, self).__init__(
            member=member,
            values=MAP_ELEMENTS,
            target=target,
            timeout=None,
            parser=lambda x: (x.name, x.short_desc or x.desc),
            silent_mode=True,
            keep_working=True,
        )
        self.embed.title = "Map Selection Tool"
        self.embed.description = "Tool will also show you how many characters have been in certain areas."
        self.embed.set_image(url=MAP_URL)

    @select(row=1, placeholder="Select region to read about", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        resp: InteractionResponse = interaction.response
        if isinstance(interaction.channel, Thread) and interaction.channel.archived:
            await interaction.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        info = self.current_choice
        cat = interaction.guild.get_channel(info.category)
        embed = Embed(title=info.name, description=info.desc, timestamp=utcnow(), color=interaction.user.color)
        embed.set_image(url=info.image or WHITE_BAR)
        view = AreaSelection(target=interaction, cat=cat)
        interaction.client.logger.info(
            "%s is reading Map Information of %s",
            str(interaction.user),
            cat.name,
        )
        registered = interaction.guild.get_role(719642423327719434)
        if registered not in interaction.user.roles:
            embed.add_field(name="Note", value="Go to <#852180971985043466> in order to get access to the RP.")
        embed.set_footer(text=f"There's a total of {view.total:02d} OCs in {cat.name}.")
        await view.simple_send(ephemeral=True, embed=embed)
        await super(RegionViewComplex, self).select_choice(interaction=interaction, sct=sct)
