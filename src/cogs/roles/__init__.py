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

from datetime import datetime, time, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

from discord import (
    AllowedMentions,
    Color,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    RawMessageDeleteEvent,
    RawReactionActionEvent,
    Role,
    Thread,
    User,
    app_commands,
)
from discord.app_commands import Choice
from discord.ext import commands
from discord.ext.tasks import loop
from discord.ui import Button, View
from discord.utils import (
    MISSING,
    find,
    format_dt,
    snowflake_time,
    time_snowflake,
    utcnow,
)

from src.cogs.roles.roles import (
    RP_SEARCH_ROLES,
    AFKModal,
    AFKSchedule,
    BasicRoleSelect,
    RegisteredRoleSelect,
    RPModal,
    RPRolesView,
    RPSearchManage,
)
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS2, WHITE_BAR

__all__ = ("Roles", "setup")

IMAGE_EMBED = Embed(color=Color.blurple())
IMAGE_EMBED.set_image(
    url="https://cdn.discordapp.com/attachments/748384705098940426/1044639175271518299/ezgif.com-gif-maker_35.gif"
)


class Roles(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.ref_msg: Optional[Message] = None
        self.ctx_menu1 = app_commands.ContextMenu(
            name="AFK Schedule",
            callback=self.check_afk,
            guild_ids=[719343092963999804],
        )

    async def cog_load(self):
        self.bot.tree.add_command(self.ctx_menu1)
        await self.load_self_roles()
        await self.load_rp_searches()
        self.clean_handler.start()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu1.name, type=self.ctx_menu1.type)
        self.clean_handler.stop()

    @loop(hours=1)
    async def clean_handler(self):
        db = self.bot.mongo_db("RP Search")
        time_id = time_snowflake(utcnow() - timedelta(days=3))

        if not (channel := self.bot.get_channel(958122815171756042)):
            return

        async for item in db.find({"id": {"$lte": time_id}, "server": channel.guild.id}):
            if not (thread := channel.guild.get_thread(item["id"])):
                try:
                    thread = await channel.guild.fetch_channel(item["id"])
                except NotFound:
                    await db.delete_one(item)
                    continue

            if (thread.last_message_id or 0) >= time_id:
                if thread.archived:
                    await thread.edit(archived=False)
                continue

            if not thread.archived:
                await thread.edit(archived=True)

            await channel.get_partial_message(item["id"]).delete(delay=0)
            await thread.get_partial_message(item["message"]).delete(delay=0)
            await db.delete_one(item)

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")
        channel = self.bot.get_partial_messageable(719709333369258015, guild_id=719343092963999804)
        msg1 = channel.get_partial_message(1023688500182261850)
        msg2 = channel.get_partial_message(1023688872531591331)
        await msg1.edit(view=BasicRoleSelect(timeout=None))
        await msg2.edit(view=RegisteredRoleSelect(timeout=None))
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
            if self.role_cool_down.get(role_id, created_at) <= created_at:
                self.role_cool_down[role_id] = created_at
            if self.cool_down.get(role_id, created_at) <= created_at:
                self.cool_down[member_id] = created_at
            view = RPSearchManage(member_id=member_id, ocs=ocs)
            self.bot.add_view(view=view, message_id=msg_id)
            self.bot.add_view(view=view, message_id=aux)
        self.bot.logger.info("Finished loading existing RP Searches")

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ref_msg:
            channel = self.bot.get_channel(958122815171756042)
            self.view = RPRolesView(timeout=None)
            async for msg in channel.history(limit=1):
                if msg.author == self.bot.user and not msg.webhook_id:
                    self.ref_msg = await msg.edit(embed=IMAGE_EMBED, view=self.view)
                else:
                    self.ref_msg = await channel.send(embed=IMAGE_EMBED, view=self.view)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        member = payload.member
        if not all(
            (
                payload.guild_id,
                str(payload.emoji) == "\N{PUBLIC ADDRESS LOUDSPEAKER}",
                not member.bot,
            )
        ):
            return

        db = self.bot.mongo_db("Roleplayers")
        if item := await db.find_one({"id": payload.message_id, "server": payload.guild_id}):
            guild = member.guild
            webhook = await self.bot.webhook(958122815171756042, reason="Ping")
            view = View()
            url = f"https://discord.com/channels/{payload.guild_id}/{payload.message_id}"
            view.add_item(Button(label="Your OCs", url=url))
            if item2 := await db.find_one({"user": member.id}):
                url = f"https://discord.com/channels/{payload.guild_id}/{item2['id']}"
                view.add_item(Button(label="User's OCs", url=url))

            if (author := guild.get_member(item["user"])) and author != member:
                embed = Embed(
                    title=f"Hello {author.display_name}",
                    description=f"{member.display_name} is interested on Rping with your characters.",
                    timestamp=utcnow(),
                    color=member.color,
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(text=guild.name, icon_url=guild.icon)
                msg = await webhook.send(
                    avatar_url=member.display_avatar.url,
                    username=member.display_name,
                    embed=embed,
                    view=view,
                    wait=True,
                )
                thread = await msg.create_thread(name=f"{member.display_name} - {author.display_name}")
                await webhook.send(
                    avatar_url=member.display_avatar.url,
                    username=member.display_name,
                    embed=embed,
                    view=view,
                    thread=thread,
                )
                await thread.send(embed=embed, view=view)
                await thread.add_user(member)
                await thread.add_user(author)

            await msg.remove_reaction(emoji=payload.emoji, member=payload.member)

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
            if msg := self.ref_msg:
                await msg.delete(delay=0)
            self.ref_msg = await msg.channel.send(embed=IMAGE_EMBED, view=self.view)
        elif msg.author.bot:
            return

        db = self.bot.mongo_db("AFK")
        if (users := [x.id for x in msg.mentions if isinstance(x, Member) and str(x.status) == "offline"]) and (
            afk_members := [
                f"• {user.mention} ({user.display_name})"
                async for item in db.find({"user": {"$in": users}})
                if (user := msg.guild.get_member(item["user"]))
                and ((msg.created_at + timedelta(hours=item["offset"])).hour in item["hours"])
            ]
        ):
            embed = Embed(
                title="AFK Schedules",
                description="\n".join(afk_members),
                color=Color.blurple(),
                timestamp=msg.created_at,
            )
            embed.set_image(url=WHITE_BAR)
            embed.set_footer(text="Feel free to use /afk to check their AFK schedules.")

            await msg.channel.send(
                content=msg.author.mention,
                embed=embed,
                delete_after=3,
                allowed_mentions=AllowedMentions(users=True),
            )

        if msg.channel.category_id in MAP_ELEMENTS2 and "»〛" not in msg.channel.name:
            db2 = self.bot.mongo_db("RP Sessions")

            if isinstance(msg.channel, Thread):
                key = {
                    "category": msg.channel.category_id,
                    "thread": msg.channel.id,
                    "channel": msg.channel.parent_id,
                }
            else:
                key = {
                    "category": msg.channel.category_id,
                    "thread": None,
                    "channel": msg.channel.id,
                }

            if entry := await db2.find_one(key):
                message_id = entry["id"]
                await msg.channel.get_partial_message(message_id).delete(delay=0)
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
                log_w = await self.bot.webhook(1001125143071965204)
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
    @app_commands.choices(role=[Choice(name=k, value=str(v)) for k, (_, v) in RP_SEARCH_ROLES.items()])
    async def ping(self, interaction: Interaction, role: str, member: Optional[Member | User] = None):
        """Command used to ping roles, and even users.

        Parameters
        ----------
        interaction : Interaction
            Interaction
        role : str
            Role to ping
        member : Optional[Member | User], optional
            Member to ping
        """
        resp: InteractionResponse = interaction.response
        db = self.bot.mongo_db("Characters")
        guild = interaction.guild
        role: Role = guild.get_role(int(role))
        user = self.bot.supporting.get(interaction.user, interaction.user)
        ocs = [
            Character.from_mongo_dict(x)
            async for x in db.find(
                {
                    "author": user.id,
                    "server": guild.id,
                }
            )
        ]
        modal = RPModal(user=user, role=role, ocs=ocs, to_user=member)
        if await modal.check(interaction):
            await resp.send_modal(modal)

    async def check_afk(self, ctx: Interaction, member: Member):
        resp: InteractionResponse = ctx.response
        db = self.bot.mongo_db("AFK")
        if item := await db.find_one({"user": ctx.user.id}):
            current_date = ctx.created_at
            embed = Embed(title="AFK Schedule", timestamp=current_date, color=member.color)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
            if item2 := await db.find_one({"user": member.id}):
                tz1 = timezone(timedelta(hours=item["offset"]))
                tz2 = timezone(timedelta(hours=item2["offset"]))
                data = AFKSchedule(
                    [datetime.combine(current_date, time(hour=x), tz2).astimezone(tz1) for x in item["hours"]]
                )
                embed.description = data.text
                date = current_date.astimezone(tz2)
                text = quote_plus(f"{member.display_name}'s time is {date.strftime('%I:%M %p')}")
                embed.set_image(url=f"https://dummyimage.com/468x60/FFFFFF/000000&text={text}")
            else:
                embed.set_image(url=WHITE_BAR)
            await resp.send_message(embed=embed, ephemeral=True)
        else:
            modal = AFKModal()
            await resp.send_modal(modal)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def afk(self, ctx: Interaction, member: Optional[Member | User]):
        """Check users' AFK Schedule

        Parameters
        ----------
        ctx : Interaction
            Interaction
        member : Member
            User to Check
        """
        await self.check_afk(ctx, member or ctx.user)

    @commands.command()
    @commands.guild_only()
    @commands.check(lambda x: x.message.channel.category_id in MAP_ELEMENTS2 and "»〛" not in x.message.channel.name)
    async def finish(self, ctx: commands.Context):
        db1 = self.bot.mongo_db("RP Channels")
        db2 = self.bot.mongo_db("RP Sessions")

        await ctx.message.delete(delay=0)

        if isinstance(ctx.channel, Thread):
            key = {
                "category": ctx.channel.category_id,
                "thread": ctx.channel.id,
                "channel": ctx.channel.parent_id,
            }
        else:
            key = {
                "category": ctx.channel.category_id,
                "thread": None,
                "channel": ctx.channel.id,
            }

        if entry := await db2.find_one(key):
            message_id = entry["id"]
            if any([item.id == message_id async for item in ctx.channel.history(limit=1, before=ctx.message)]):
                return

            try:
                m = await ctx.channel.fetch_message(message_id)
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
            log_w = await self.bot.webhook(1001125143071965204)
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

        file = await ctx.author.display_avatar.to_file()

        embed.set_author(
            name=ctx.author.display_name,
            icon_url=f"attachment://{file.filename}",
        )

        message = await ctx.channel.send(embed=embed, view=view, file=file)

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
