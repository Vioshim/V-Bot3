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


from datetime import datetime
from typing import Optional

from discord import (
    Color,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    RawMessageDeleteEvent,
    Role,
    Thread,
    app_commands,
)
from discord.app_commands import Choice
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, find, format_dt, snowflake_time

from src.cogs.roles.roles import (
    RP_SEARCH_ROLES,
    RoleSelect,
    RPModal,
    RPRolesView,
    RPSearchManage,
)
from src.structures.bot import CustomBot
from src.utils.etc import MAP_ELEMENTS2, WHITE_BAR

__all__ = ("Roles", "setup")

IMAGE = "https://cdn.discordapp.com/attachments/748384705098940426/990454127639269416/unknown.png"


class Roles(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.ref_msg: Optional[Message] = None

    async def cog_load(self):
        await self.load_self_roles()
        await self.load_rp_searches()

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")
        self.view = RoleSelect(timeout=None)
        self.bot.add_view(view=self.view, message_id=992522335808671854)
        self.bot.logger.info("Finished loading Self Roles")

    async def load_rp_searches(self):
        self.bot.logger.info("Loading existing RP Searches")
        db = self.bot.mongo_db("RP Search")
        async for item in db.find({}):
            msg_id, member_id, role_id, aux, ocs = (
                item["id"],
                item["member"],
                item["role"],
                item["message"],
                item["ocs"],
            )
            created_at = snowflake_time(msg_id)
            self.role_cool_down.setdefault(role_id, created_at)
            self.cool_down.setdefault(member_id, created_at)
            if self.role_cool_down[role_id] < created_at:
                self.role_cool_down[role_id] = created_at
            if self.cool_down[member_id] < created_at:
                self.cool_down[member_id] = created_at
            view = RPSearchManage(member_id=member_id, ocs=ocs)
            self.bot.add_view(view=view, message_id=msg_id)
            self.bot.add_view(view=view, message_id=aux)
        self.bot.logger.info("Finished loading existing RP Searches")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ref_msg:
            channel = self.bot.get_channel(958122815171756042)
            async for m in channel.history(limit=1):
                view = RPRolesView(timeout=None)
                if m.author == self.bot.user and not m.webhook_id:
                    self.ref_msg = await m.edit(content=IMAGE, view=view)
                else:
                    self.ref_msg = await channel.send(content=IMAGE, view=view)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        db2 = self.bot.mongo_db("RP Sessions")
        if msg := payload.cached_message:
            channel = msg.channel
        elif not (channel := guild.get_channel_or_thread(payload.channel_id)):
            channel = await guild.fetch_channel(payload.channel_id)

        if channel.category_id not in MAP_ELEMENTS2:
            return

        if isinstance(channel, Thread):
            channel_id, thread_id = channel.parent_id, channel.id
        else:
            channel_id, thread_id = channel.id, None

        await db2.delete_one(
            {
                "category": channel.category_id,
                "thread": thread_id,
                "channel": channel_id,
                "id": payload.message_id,
            }
        )

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.flags.ephemeral or not msg.guild:
            return
        if msg.webhook_id and msg.channel.id == 958122815171756042:
            view = RPRolesView(timeout=None)
            if m := self.ref_msg:
                await m.delete(delay=0)
            self.ref_msg = await msg.channel.send(content=IMAGE, view=view)
        elif msg.channel.category_id in MAP_ELEMENTS2 and "»〛" not in msg.channel.name and not msg.author.bot:
            db2 = self.bot.mongo_db("RP Sessions")
            log_w = await self.bot.webhook(1001125143071965204)
            w = await self.bot.webhook(msg.channel)

            if isinstance(msg.channel, Thread):
                channel_id, thread_id = msg.channel.parent_id, msg.channel.id
                thread = msg.channel
            else:
                channel_id, thread_id = msg.channel.id, None
                thread = MISSING

            key = {"category": msg.channel.category_id, "thread": thread_id, "channel": channel_id}

            if entry := await db2.find_one(key):
                message_id = entry["id"]
                try:
                    await w.delete_message(message_id, thread=thread)
                except NotFound:
                    pass

                date = snowflake_time(message_id)
                embed = Embed(
                    title="RP has started!",
                    description=format_dt(date, "R"),
                    color=Color.blurple(),
                    timestamp=date,
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(text=msg.guild.name, icon_url=msg.guild.icon)
                username = avatar_url = MISSING
                if member := msg.guild.get_member(entry["author"]):
                    username, avatar_url = member.display_name, member.display_avatar.url

                view = View()
                view.add_item(Button(label="Jump URL", url=msg.channel.jump_url))

                await log_w.send(
                    embed=embed,
                    username=username,
                    avatar_url=avatar_url,
                    view=view,
                    thread=Object(id=1001949202621931680),
                )

                await db2.delete_one(entry)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.choices(role=[Choice(name=k, value=str(v)) for k, v in RP_SEARCH_ROLES.items()])
    async def ping(self, interaction: Interaction, role: str, member: Optional[Member] = None):
        """Command used to ping roles, and even users.

        Parameters
        ----------
        interaction : Interaction
            Interaction
        role : str
            Role to ping
        member : Optional[Member], optional
            Member to ping
        """
        resp: InteractionResponse = interaction.response
        cog = interaction.client.get_cog("Submission")
        guild = interaction.guild
        role: Role = guild.get_role(int(role))
        user: Member = cog.supporting.get(interaction.user, interaction.user)
        ocs = [oc for oc in cog.ocs.values() if oc.author == user.id]
        modal = RPModal(user=user, role=role, ocs=ocs, to_user=member)
        if await modal.check(interaction):
            await resp.send_modal(modal)

    @commands.command()
    @commands.guild_only()
    @commands.check(lambda x: x.message.channel.category_id in MAP_ELEMENTS2)
    async def finish(self, ctx: commands.Context):
        db1 = self.bot.mongo_db("RP Channels")
        db2 = self.bot.mongo_db("RP Sessions")
        log_w = await self.bot.webhook(1001125143071965204)
        w = await self.bot.webhook(ctx.channel)

        await ctx.message.delete(delay=0)

        if isinstance(ctx.channel, Thread):
            channel_id, thread_id = ctx.channel.parent_id, ctx.channel.id
            thread = ctx.channel
        else:
            channel_id, thread_id = ctx.channel.id, None
            thread = MISSING

        key = {"category": ctx.channel.category_id, "thread": thread_id, "channel": channel_id}

        if entry := await db2.find_one(key):
            message_id = entry["id"]
            if any([item.id == message_id async for item in ctx.channel.history(limit=1, before=ctx.message)]):
                return

            try:
                m = await w.fetch_message(message_id, thread=thread)
                e = m.embeds[0]

                try:
                    emoji = ctx.channel.name.split("〛")[0][0]
                except ValueError:
                    emoji = None

                await db1.replace_one(
                    key,
                    key
                    | {
                        "name": e.title,
                        "topic": e.description,
                        "image": e.image.url,
                        "emoji": emoji,
                    },
                    upsert=True,
                )
                await m.delete(delay=0)
            except NotFound:
                pass

            date = snowflake_time(message_id)
            embed = Embed(
                title="RP has concluded!",
                description=format_dt(date, "R"),
                color=Color.blurple(),
                timestamp=date,
            )
            embed.set_image(url=WHITE_BAR)
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
            username = avatar_url = MISSING
            if member := ctx.guild.get_member(entry["author"]):
                username, avatar_url = member.display_name, member.display_avatar.url

            view = View()
            view.add_item(Button(label="Jump URL", url=ctx.channel.jump_url))

            await log_w.send(
                embed=embed,
                username=username,
                avatar_url=avatar_url,
                view=view,
                thread=Object(id=1001949202621931680),
            )

            await db2.delete_one(entry)

        embed = Embed(
            title=ctx.channel.name,
            description=getattr(ctx.channel, "topic", ""),
            timestamp=ctx.message.created_at,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text="This channel is free to use.!")
        view = View()
        if ooc := find(lambda x: "»〛" in x.name, ctx.channel.category.channels):
            emoji, name = ooc.name.split("»〛")
            view.add_item(Button(label=name, emoji=emoji[0], url=ooc.jump_url))

        if data := await db1.find_one(key):
            if name := data["name"]:
                embed.title = name
            if topic := data["topic"]:
                embed.description = topic
            if image := data["image"]:
                embed.set_image(url=image)

        message = await w.send(
            embed=embed,
            view=view,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url,
            wait=True,
            thread=thread,
        )

        await db2.replace_one(
            key,
            key | {"id": message.id, "author": ctx.author.id},
            upsert=True,
        )


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
