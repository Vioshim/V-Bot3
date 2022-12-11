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

from discord import (
    CategoryChannel,
    Embed,
    ForumChannel,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    Thread,
    User,
)
from discord.ui import Select, select
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS, WHITE_BAR, MapPair
from src.views.characters_view import CharactersView

__all__ = ("RegionViewComplex",)


class LocationSelection(Complex[Thread]):
    def __init__(
        self,
        target: Interaction,
        base: ForumChannel,
        ocs: set[Character],
    ):
        self.entries: dict[int, set[Character]] = {}

        def foo(oc: Character):
            ch = target.guild.get_channel_or_thread(oc.location)
            return isinstance(ch, Thread) and ch.parent == base

        values = [x for x in ocs if x.location and foo(x)]
        values.sort(key=lambda x: x.location)
        entries = groupby(values, key=lambda x: x.location)
        self.entries = {k: set(v) for k, v in entries if k}
        self.total = sum(map(len, self.entries.values()))
        channels = sorted(base.threads, key=lambda x: len(self.entries.get(x.id, [])), reverse=True)
        super(LocationSelection, self).__init__(
            target=target,
            member=target.user,
            values=channels,
            silent_mode=True,
            keep_working=True,
            parser=lambda x: (
                f"{len(self.entries.get(x.id, [])):02d}{x.name[1:]}".replace("-", " ").title(),
                None,
            ),
            sort_key=lambda x: x.name,
            emoji_parser=lambda x: x.name[0],
        )

    @select(row=1, placeholder="Select a location to check", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        try:
            resp: InteractionResponse = interaction.response
            await resp.defer(ephemeral=True, thinking=True)
            channel: Thread = self.current_choice
            ocs = self.entries.get(channel.id, set())
            view = CharactersView(target=interaction, member=interaction.user, ocs=ocs, keep_working=True)
            embed = view.embed
            embed.title = channel.name[2:].replace("-", " ").title()
            embed.description = channel.topic or "No description yet"
            embed.color = interaction.user.color
            embed.timestamp = interaction.created_at
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"There's {len(ocs):02d} OCs here.")
            await view.simple_send(ephemeral=True, embed=embed)
            interaction.client.logger.info("%s user is checking ocs at %s", interaction.user, channel.name)
        except Exception as e:
            interaction.client.logger.exception("Error in location view", exc_info=e)
        finally:
            await super(AreaSelection, self).select_choice(interaction=interaction, sct=sct)


class AreaSelection(Complex[ForumChannel]):
    def __init__(
        self,
        target: Interaction,
        cat: CategoryChannel,
        ocs: set[Character],
    ):
        channels: list[ForumChannel] = [x for x in cat.channels if not x.name.endswith(" OOC")]

        self.entries: dict[int, set[Character]] = {}

        def foo(oc: Character):
            ch = target.guild.get_channel_or_thread(oc.location)
            return bool(ch and cat == ch.category)

        def foo2(oc: Character):
            ch = target.guild.get_channel_or_thread(oc.location)
            if isinstance(ch, Thread):
                ch = ch.parent
            return ch

        entries = groupby(sorted(filter(foo, ocs), key=lambda x: foo2(x).id), key=foo2)
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
            sort_key=lambda x: x.name,
            emoji_parser=lambda x: x.name[0],
        )

    @select(row=1, placeholder="Select an area to check", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        try:
            resp: InteractionResponse = interaction.response
            await resp.defer(ephemeral=True, thinking=True)
            channel: ForumChannel = self.current_choice
            ocs = self.entries.get(channel.id, set())
            view = LocationSelection(target=interaction, base=channel, ocs=ocs)
            embed = view.embed
            embed.title = channel.name[2:].replace("-", " ").title()
            embed.description = channel.topic or "No description yet"
            embed.color = interaction.user.color
            embed.timestamp = interaction.created_at
            embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar)
            embed.set_footer(text=f"There's {len(ocs):02d} OCs here.")
            await view.simple_send(ephemeral=True, embed=embed)
            interaction.client.logger.info("%s user is checking ocs at %s", interaction.user, channel.name)
        except Exception as e:
            interaction.client.logger.exception("Error in location view", exc_info=e)
        finally:
            await super(AreaSelection, self).select_choice(interaction=interaction, sct=sct)


class RegionViewComplex(Complex[MapPair]):
    def __init__(self, *, member: Member | User, target: Interaction, role: Role):
        super(RegionViewComplex, self).__init__(
            member=member,
            values=MAP_ELEMENTS,
            target=target,
            timeout=None,
            parser=lambda x: (x.name, x.short_desc or x.desc),
            silent_mode=True,
            keep_working=True,
        )
        self.role = role
        self.embed.title = "Map Selection Tool"
        self.embed.description = "Tool will also show you how many characters have been in certain areas."

    @select(row=1, placeholder="Select region to read about", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        try:
            resp: InteractionResponse = interaction.response
            await resp.defer(ephemeral=True, thinking=True)
            info = self.current_choice
            cat = interaction.guild.get_channel(info.category)
            embed = Embed(
                title=info.name,
                description=info.desc,
                timestamp=interaction.created_at,
                color=interaction.user.color,
            )
            embed.set_image(url=info.image or WHITE_BAR)
            db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(x) async for x in db.find({"server": interaction.guild_id})]
            view = AreaSelection(target=interaction, cat=cat, ocs=ocs)
            interaction.client.logger.info("%s is reading Map Information of %s", interaction.user, cat.name)
            embed.set_footer(text=f"There's a total of {view.total:02d} OCs in {cat.name}.")
            await view.simple_send(ephemeral=True, embed=embed)
        except Exception as e:
            interaction.client.logger.exception("Error in region view.", exc_info=e)
        finally:
            await super(RegionViewComplex, self).select_choice(interaction=interaction, sct=sct)
