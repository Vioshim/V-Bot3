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
from textwrap import TextWrapper
from typing import Optional
from urllib.parse import quote_plus
from contextlib import suppress
from discord import (
    AllowedMentions,
    AutoModTrigger,
    Embed,
    ForumChannel,
    Interaction,
    Member,
    Message,
    RawReactionActionEvent,
    User,
    app_commands,
    AutoModRule,
    Guild,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get, snowflake_time

from src.cogs.roles.roles import (
    AFKModal,
    AFKSchedule,
    BasicRoleSelect,
    RPModal,
    RPSearchManage,
)
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
        self.itx_menu1 = app_commands.ContextMenu(name="AFK Schedule", callback=self.check_afk)
        self.wrapper = TextWrapper(width=250, placeholder="", max_lines=10)

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

    async def cog_load(self):
        self.bot.tree.add_command(self.itx_menu1)
        await self.load_self_roles()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.itx_menu1.name, type=self.itx_menu1.type)

    async def check_afk(self, itx: Interaction[CustomBot], member: Member):
        db = self.bot.mongo_db("AFK")
        if item := await db.find_one({"user": itx.user.id}):
            current_date = itx.created_at
            embed = Embed(title="AFK Schedule", color=member.color)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
            if item2 := await db.find_one({"user": member.id}):
                tz1 = timezone(timedelta(hours=item["offset"]))
                tz2 = timezone(timedelta(hours=item2["offset"]))
                user_data = [datetime.combine(current_date, time(hour=x), tz2) for x in item2["hours"]]

                data1 = AFKSchedule(user_data)
                data2 = data1.astimezone(tz1)
                desc1, desc2 = data1.text, data2.text
                if desc1 != desc2 and desc1 and desc2:
                    embed.add_field(name="In user's timezone", value=desc1, inline=False)
                    embed.add_field(name="In your timezone", value=desc2, inline=False)
                else:
                    embed.description = desc1 or desc2

                date = current_date.astimezone(tz2)
                text = f"User's time is {date.strftime('%I:%M %p')}"
            else:
                text = "No timezone associated to the account."
            embed.set_image(url=f"https://dummyimage.com/468x60/FFFFFF/000000&text={quote_plus(text)}")
            await itx.response.send_message(embed=embed, ephemeral=True)
        else:
            modal = AFKModal()
            await itx.response.send_modal(modal)

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")

        db = self.bot.mongo_db("Server")
        async for item in db.find({"self_roles": {"$exists": True}}):
            info = item.get("self_roles", {})
            channel = self.bot.get_partial_messageable(info["channel"], guild_id=item["id"])
            msg = channel.get_partial_message(info["message"])
            await msg.edit(view=BasicRoleSelect(items=info.get("items", [])))

        self.bot.logger.info("Finished loading Self Roles")

    @commands.Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if (
            (roles := set(before.roles) ^ set(after.roles))
            and (no_ping_role := get(roles, name="Don't Ping Me"))
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

        db = self.bot.mongo_db("AFK")
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

    @app_commands.command()
    async def afk(self, itx: Interaction[CustomBot], member: Member | User):
        """Check users' AFK Schedule

        Parameters
        ----------
        itx : Interaction[CustomBot],
            Interaction[CustomBot],
        member : Member
            User to Check
        """
        await self.check_afk(itx, member)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
