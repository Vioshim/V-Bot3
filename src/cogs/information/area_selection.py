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
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    TextChannel,
    User,
)
from discord.ui import Button, Select, button, select
from discord.utils import utcnow
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS, WHITE_BAR, MapPair
from src.views.characters_view import CharactersView

__all__ = ("RegionViewComplex",)


def role_gen(guild: Guild):
    for item in MAP_ELEMENTS:
        if x := guild.get_role(item.role):
            yield x


class AreaSelection(Complex[TextChannel]):
    def __init__(
        self,
        target: Interaction,
        cat: CategoryChannel,
        ocs: set[Character],
        role: Role,
    ):
        channels = [x for x in cat.channels if not x.name.endswith("-ooc")]

        self.entries: dict[str, set[Character]] = {}
        self.role = role

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
            emoji_parser=lambda x: x.name[0],
        )

    @select(row=1, placeholder="Select a location to check", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        try:
            resp: InteractionResponse = interaction.response
            await resp.defer(ephemeral=True, thinking=True)
            channel: TextChannel = self.current_choice
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
            interaction.client.logger.info("%s user is checking ocs at %s", interaction.user, channel.name)
        except Exception as e:
            interaction.client.logger.exception("Error in location view", exc_info=e)
        finally:
            await super(AreaSelection, self).select_choice(interaction=interaction, sct=sct)

    @button(row=4, label="Add Role", custom_id="role_add")
    async def add_role(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        btn.disabled = True
        self.remove_role.disabled = False
        await resp.edit_message(view=self)
        role = ctx.guild.get_role(1033371159426764901)
        all_roles = set(role_gen(ctx.guild))
        if all(x in ctx.user.roles for x in all_roles if x != self.role):
            await ctx.user.remove_roles(all_roles)
            await ctx.user.add_roles(role)
        elif self.role not in ctx.user.roles:
            await ctx.user.add_roles(self.role)

    @button(row=4, label="Remove Role", custom_id="role_remove")
    async def remove_role(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        btn.disabled = True
        self.add_role.disabled = False
        await resp.edit_message(view=self)
        role = ctx.guild.get_role(1033371159426764901)
        all_roles = {x for x in role_gen(ctx.guild) if x != self.role}
        if any(x not in ctx.user.roles for x in all_roles):
            if role in ctx.user.roles:
                await ctx.user.remove_roles(role)
            await ctx.user.add_roles(all_roles)
        elif self.role in ctx.user.roles:
            await ctx.user.remove_roles(self.role)


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
            ocs = [Character.from_mongo_dict(x) async for x in db.find({})]
            role = interaction.guild.get_role(info.role)
            view = AreaSelection(target=interaction, cat=cat, ocs=ocs, role=role)

            view.add_role.disabled = role in interaction.user.roles
            view.remove_role.disabled = role not in interaction.user.roles

            interaction.client.logger.info("%s is reading Map Information of %s", interaction.user, cat.name)
            registered = interaction.guild.get_role(719642423327719434)
            if registered not in interaction.user.roles:
                embed.add_field(name="Note", value="Go to <#852180971985043466> in order to get access to the RP.")
            embed.set_footer(text=f"There's a total of {view.total:02d} OCs in {cat.name}.")
            await view.simple_send(ephemeral=True, embed=embed)
        except Exception as e:
            interaction.client.logger.exception("Error in region view.", exc_info=e)
        finally:
            await super(RegionViewComplex, self).select_choice(interaction=interaction, sct=sct)

    @button(row=4, label="Add all roles", custom_id="role_add")
    async def add_role(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        btn.disabled = True
        self.remove_role.disabled = False
        await resp.edit_message(view=self)
        if roles := {x for x in role_gen(ctx.guild) if x not in ctx.user.roles}:
            await ctx.user.remove_roles(roles)
        if self.role and self.role not in ctx.user.roles:
            await ctx.user.add_roles(self.role)

    @button(row=4, label="Remove all roles", custom_id="role_remove")
    async def remove_role(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        btn.disabled = True
        self.add_role.disabled = False
        await resp.edit_message(view=self)
        roles = {x for x in role_gen(ctx.guild)}
        if self.role:
            roles.add(self.role)
        await ctx.user.remove_roles(roles)
