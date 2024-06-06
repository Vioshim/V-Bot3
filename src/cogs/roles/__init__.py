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


from calendar import Month
from datetime import datetime, timedelta, timezone
from textwrap import TextWrapper
from typing import Optional

from discord import (
    AllowedMentions,
    AutoModRule,
    AutoModTrigger,
    Embed,
    EntityType,
    EventStatus,
    ForumChannel,
    Guild,
    Interaction,
    Member,
    Message,
    PrivacyLevel,
    RawReactionActionEvent,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get, snowflake_time

from src.cogs.roles.roles import BasicRoleSelect, RPModal, RPSearchManage, TimeArg
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR

__all__ = ("Roles", "setup")


class Roles(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.auto_mods: dict[int, Optional[AutoModRule]] = {}
        self.wrapper = TextWrapper(width=250, placeholder="", max_lines=10)
        self.no_ping_roles: dict[int, int | None] = {}
        self.ready = False

    async def fetch_no_ping_role(self, guild: Guild) -> Optional[int]:
        db = self.bot.mongo_db("Server")

        if guild.id not in self.no_ping_roles:
            self.no_ping_roles[guild.id] = None

            if item := await db.find_one(
                {
                    "id": guild.id,
                    "self_roles.no_ping": {"$exists": True},
                },
                {
                    "_id": 0,
                    "self_roles.no_ping": 1,
                },
            ):
                self.no_ping_roles[guild.id] = item["self_roles"]["no_ping"]

        return self.no_ping_roles[guild.id]

    async def fetch_automod(self, guild: Guild) -> Optional[AutoModRule]:
        db = self.bot.mongo_db("Server")

        if guild.id not in self.auto_mods:
            self.auto_mods[guild.id] = None

            if item := await db.find_one(
                {
                    "id": guild.id,
                    "self_roles.no_ping_automod": {"$exists": True},
                },
                {
                    "_id": 0,
                    "self_roles.no_ping_automod": 1,
                },
            ):
                rule_id = item["self_roles"]["no_ping_automod"]
                try:
                    self.auto_mods[guild.id] = await guild.fetch_automod_rule(rule_id)
                except Exception:
                    await db.update_one(
                        {"id": guild.id},
                        {"$unset": {"self_roles.no_ping_automod": ""}},
                    )
                    return

        return self.auto_mods[guild.id]

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")

        db = self.bot.mongo_db("Server")
        async for item in db.find({"self_roles": {"$exists": True}}):
            info = item.get("self_roles", {})
            channel = self.bot.get_partial_messageable(info["channel"], guild_id=item["id"])
            msg = channel.get_partial_message(info["message"])
            view = BasicRoleSelect(items=info.get("items", []))
            if webhook_id := item.get("webhook_id"):
                w = await self.bot.fetch_webhook(webhook_id)
                await w.edit_message(message_id=msg.id, view=view)
            else:
                await msg.edit(view=view)

        self.bot.logger.info("Finished loading Self Roles")

    @commands.Cog.listener()
    async def on_ready(self):
        if self.ready:
            return

        await self.load_self_roles()
        self.ready = True

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if (
            (role_id := await self.fetch_no_ping_role(after.guild))
            and (roles := set(before.roles) ^ set(after.roles))
            and (no_ping_role := get(roles, id=role_id))
            and (rule := await self.fetch_automod(after.guild))
        ):
            members_text = " ".join(str(x.id) for x in sorted(no_ping_role.members, key=lambda x: x.id))
            regex_patterns = [f"<@!?({line.replace(' ', '|')})>" for line in self.wrapper.wrap(members_text) if line]
            if rule.trigger.regex_patterns != regex_patterns:
                trigger = AutoModTrigger(regex_patterns=regex_patterns)
                rule = await rule.edit(
                    trigger=trigger,
                    name="No Ping Automod",
                    reason=f"Updated by {after}",
                    enabled=True,
                )
                self.auto_mods[after.guild.id] = rule

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if not all(
            (
                payload.guild_id,
                str(payload.emoji) == "\N{BELLHOP BELL}",
                (payload.member and not payload.member.bot),
            )
        ):
            return

        db = self.bot.mongo_db("Roleplayers")
        db1 = self.bot.mongo_db("Server")
        item = await db.find_one({"id": payload.message_id, "server": payload.guild_id})
        data = await db1.find_one(
            {
                "id": payload.guild_id,
                "rp_planning": {"$exists": True},
            },
            {"_id": 0, "rp_planning": 1},
        )

        if item and data:
            guild = payload.member.guild
            if thread := guild.get_thread(payload.channel_id):
                msg = thread.get_partial_message(payload.message_id)
                await msg.remove_reaction(emoji=payload.emoji, member=payload.member)

            if (author := guild.get_member(item["user"])) and author != payload.member:
                registered = get(guild.roles, name="Registered")
                if registered and get(payload.member.roles, name="Moderation") and registered not in author.roles:
                    return await author.add_roles(registered, reason=str(payload.member))

                if not (channel := guild.get_channel(data["rp_planning"])):
                    channel: ForumChannel = await guild.fetch_channel(data["rp_planning"])

                view = View()
                url = f"https://discord.com/channels/{payload.guild_id}/{payload.message_id}"
                view.add_item(Button(label="Your OCs", url=url))
                if item2 := await db.find_one({"user": payload.member.id, "server": payload.guild_id}):
                    url = f"https://discord.com/channels/{payload.guild_id}/{item2['id']}"
                    view.add_item(Button(label="User's OCs", url=url))

                embed = Embed(
                    title=f"Hello {author.display_name}",
                    description=f"{payload.member.display_name} is interested on Rping with your characters.",
                    color=payload.member.color,
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(text=guild.name, icon_url=guild.icon)
                base = await channel.create_thread(
                    name=f"▷{payload.member.display_name}",
                    content=f"{author.mention} {payload.member.mention}",
                    reason=str(payload.member),
                    embed=embed,
                    view=view,
                    allowed_mentions=AllowedMentions(users=[author, payload.member]),
                )
                await base.message.pin()

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.flags.ephemeral or not msg.guild or msg.webhook_id or msg.author.bot:
            return

        if not (users := {x for x in msg.mentions if x != msg.author and isinstance(x, Member)}):
            return

        no_ping_role = get(msg.guild.roles, name="Don't Ping Me")
        if (
            not (msg.author.guild_permissions.manage_messages or msg.author.guild_permissions.administrator)
            and no_ping_role
            and (no_ping_users := ", ".join(str(x) for x in users if no_ping_role in x.roles))
        ):
            await msg.reply("https://media.tenor.com/kJhT6VC2tzEAAAAC/pings-off-reply-pings-off.gif")
            await msg.author.timeout(timedelta(seconds=5), reason=f"Pinged {no_ping_users}")

        """
        db = self.bot.mongo_db("AFK")
        offline_users = [x.id for x in users if str(x.status) == "offline"]
        if not offline_users:
            return

        embeds = []
        if reference_tz := await db.find_one({"user": msg.author.id}):
            reference_tz: Optional[timezone] = timezone(offset=timedelta(hours=reference_tz["offset"]))

        async for item in db.find({"user": {"$in": offline_users}}):
            user = get(users, id=item["user"])
            tz = timezone(offset=timedelta(hours=item["offset"]))
            ref_date = msg.created_at.astimezone(tz)
            if ref_date.hour not in item["hours"]:
                continue

            embed = Embed(title=user.display_name, color=user.color, timestamp=ref_date)
            embed.set_thumbnail(url=user.display_avatar)
            text = quote_plus(f"User's time is {ref_date.strftime('%I:%M %p')}")
            embed.set_image(url=f"https://dummyimage.com/468x60/FFFFFF/000000&text={text}")
            user_data = [datetime.combine(msg.created_at, time(hour=x), tz) for x in item["hours"]]
            data1 = AFKSchedule(user_data)
            data2 = data1.astimezone(reference_tz) if reference_tz else data1
            desc1, desc2 = data1.text, data2.text
            if desc1 != desc2 and desc1 and desc2:
                embed.add_field(name="In user's timezone", value=desc1, inline=False)
                embed.add_field(name="In your timezone", value=desc2, inline=False)
            elif not reference_tz:
                embed.add_field(name="In user's timezone", value=desc1, inline=False)
            else:
                embed.description = desc1 or desc2
            embeds.append(embed)

        if embeds:
            await msg.channel.send(
                content=msg.author.mention,
                embeds=embeds[:10],
                delete_after=10,
                allowed_mentions=AllowedMentions(users=True),
            )
        """

    @commands.Cog.listener()
    async def on_ready(self):
        db = self.bot.mongo_db("RP Search")
        async for item in db.find({}):
            date = snowflake_time(item["id"])
            self.cool_down.setdefault(item["member"], date)
            self.role_cool_down.setdefault(item["role"], date)
            self.cool_down[item["member"]] = max(self.cool_down[item["member"]], date)
            self.role_cool_down[item["role"]] = max(self.role_cool_down[item["role"]], date)
            view = RPSearchManage(
                msg_id=item["id"], member_id=item["member"], ocs=item["ocs"], server_id=item["server"]
            )
            self.bot.add_view(view, message_id=item["id"])

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def ping(self, itx: Interaction[CustomBot], member: Member | User):
        """Command used to ping roles, and even users.

        Parameters
        ----------
        itx : Interaction[CustomBot],
            Interaction[CustomBot],
        member : Member | User
            Member to ping
        """
        db = self.bot.mongo_db("Characters")
        guild = itx.guild
        user = self.bot.supporting.get(itx.user, itx.user)
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": user.id, "server": guild.id})]
        modal = RPModal(user=user, ocs=ocs, to_user=member)
        if await modal.check(itx):
            await itx.response.send_modal(modal)

    @commands.hybrid_command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def birthday(
        self,
        ctx: commands.Context[CustomBot],
        month: Month,
        day: commands.Range[int, 1, 31],
        time: TimeArg,
    ):
        """Set your birthday

        Parameters
        ----------
        ctx : commands.Context[CustomBot]
            Context
        month : Month
            Month of the birthday
        day : commands.Range[int, 1, 31]
            Day of the birthday
        time : TimeArg
            Current time
        """
        db = self.bot.mongo_db("Birthday")
        user: Member = self.bot.supporting.get(ctx.author, ctx.author)

        date1, date2 = ctx.message.created_at, time
        diff_seconds = (date2 - date1).total_seconds()
        closest_half_hour = round(diff_seconds / 1800) * 1800
        offset = closest_half_hour / 3600
        tzinfo = timezone(offset=timedelta(hours=offset % 12))
        date = date1.replace(month=month, day=day, tzinfo=tzinfo, hour=0, minute=0, second=0, microsecond=1)

        if date <= date1:
            date = date.replace(year=date.year + 1)

        event = None
        image = await user.display_avatar.read()
        if info := await db.find_one({"user": user.id, "server": user.guild.id}):

            try:
                if not (event := ctx.guild.get_scheduled_event(info["id"])):
                    event = await ctx.guild.fetch_scheduled_event(info["id"])
            except Exception:
                await db.delete_one({"user": user.id, "server": user.guild.id})
                event = None

        if event:
            await event.edit(
                name=f"\N{BIRTHDAY CAKE} {user.display_name}",
                start_time=date,
                end_time=date + timedelta(days=1),
                status=EventStatus.scheduled,
                image=image,
                entity_type=EntityType.external,
                privacy_level=PrivacyLevel.guild_only,
                location="Birthday",
                description=user.mention,
            )
        else:
            event = await ctx.guild.create_scheduled_event(
                name=f"\N{BIRTHDAY CAKE} {user.display_name}",
                start_time=date,
                end_time=date + timedelta(days=1),
                image=image,
                entity_type=EntityType.external,
                privacy_level=PrivacyLevel.guild_only,
                location="Birthday",
                description=user.mention,
            )

            await db.replace_one(
                {
                    "user": user.id,
                    "server": user.guild.id,
                },
                {
                    "user": user.id,
                    "server": user.guild.id,
                    "id": event.id,
                },
                upsert=True,
            )

        view = View()
        view.add_item(Button(label="View Event", url=event.url))
        await ctx.send(f"Your birthday has been set to {date.strftime('%B %d, %Y')}", ephemeral=True, view=view)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
