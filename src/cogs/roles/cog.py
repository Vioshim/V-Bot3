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
    AllowedMentions,
    Embed,
    Member,
    Role,
    Webhook,
    WebhookMessage,
)
from discord.commands import (
    ApplicationContext,
    Option,
    OptionChoice,
    slash_command,
)
from discord.ext.commands import Cog, has_role
from discord.ui import Button, View
from discord.utils import utcnow

from src.cogs.roles.roles import (
    QUERIES,
    RP_SEARCH_ROLES,
    BasicRoles,
    ColorRoles,
    PronounRoles,
    RegionRoles,
    RoleManage,
    RoleView,
    RPSearchRoles,
    hours,
    seconds,
)
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR

__all__ = ("Roles", "setup")


class Roles(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.last_claimer: dict[int, int] = {}
        self.webhook: Optional[Webhook] = None
        self.msg: Optional[WebhookMessage] = None
        self.view: Optional[RoleView] = None

    async def load(self, rpers: dict[int, dict[int, Character]]):
        self.bot.logger.info("Loading existing RP Searches")
        async with self.bot.database() as db:
            for query in QUERIES:
                async for item in db.cursor(query):
                    msg_id, member_id, role_id, server_id, created_at = (
                        item["id"],
                        item["member"],
                        item["role"],
                        item["server"],
                        item["created_at"],
                    )

                    if not (guild := self.bot.get_guild(server_id)):
                        continue

                    if not (member := guild.get_member(member_id)):
                        continue

                    if not (role := guild.get_role(role_id)):
                        continue

                    if not (values := rpers.get(member.id, {}).values()):
                        continue

                    if (
                        item := self.role_cool_down.get(role_id, created_at)
                    ) >= created_at:
                        self.role_cool_down[role_id] = created_at
                        self.last_claimer[role_id] = member_id

                    if (
                        item := self.cool_down.get(member_id, created_at)
                    ) >= created_at:
                        self.cool_down[member_id] = created_at

                    view = RoleManage(
                        bot=self.bot,
                        role=role,
                        ocs=values,
                        member=member,
                    )
                    self.bot.add_view(view=view, message_id=msg_id)
        self.bot.logger.info("Finished loading existing RP Searches")
        w2 = await self.bot.webhook(910914713234325504, reason="RP Search")
        self.msg = await w2.fetch_message(910915102490910740)
        self.view = RoleView(
            bot=self.bot,
            cool_down=self.cool_down,
            webhook=self.webhook,
            role_cool_down=self.role_cool_down,
            last_claimer=self.last_claimer,
            msg=self.msg,
        )
        self.msg = await self.msg.edit(view=self.view)

    @slash_command(
        guild_ids=[719343092963999804],
        description="Allows to ping users for a specific kind of RP",
    )
    @has_role("Registered")
    async def ping(
        self,
        ctx: ApplicationContext,
        role_id: Option(
            str,
            description="Role to be pinged",
            choices=[
                OptionChoice(name=name, value=str(value))
                for name, value in RP_SEARCH_ROLES.items()
            ],
            required=True,
        ),
        member: Option(
            Member,
            description="Member to be pinged",
            required=False,
        ),
    ):
        if not member:
            member: Member = ctx.user
        if not self.webhook:
            await ctx.respond(
                "Bot is restarting, have patience.",
                ephemeral=True,
            )
            return
        role: Role = ctx.guild.get_role(int(role_id))
        cog = self.bot.get_cog(name="Submission")

        await ctx.defer(ephemeral=True)

        ocs = cog.rpers.get(member.id, {}).values()
        view = RoleManage(self.bot, role, ocs, member)

        embed = Embed(
            title=role.name,
            color=member.color,
            description=f"{member.display_name} is looking to RP with their registered character(s).",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)

        if member != ctx.user:
            embed.description = f"{ctx.user.display_name} is looking to RP with you, using their registered character(s)."
            await self.webhook.send(
                content=f"{member.mention} is being pinged by {ctx.user.mention}",
                embed=embed,
                allowed_mentions=AllowedMentions(users=True),
                view=view,
                username=ctx.user.display_name,
                avatar_url=ctx.user.url,
            )
            return

        if role not in member.roles:
            await member.add_roles(role, reason="Rp Searching")

        if self.last_claimer.get(role.id) == member.id:
            await ctx.send_followup(
                f"You're the last user that pinged {role.mention}, no need to keep pinging, just ask in the RP planning and discuss.",
                ephemeral=True,
            )
            return
        elif hours((val := self.cool_down.get(member.id))) < 2:
            s = 7200 - seconds(val)
            await ctx.send_followup(
                "You're in cool down, you pinged one of the roles recently."
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return
        elif hours((val := self.role_cool_down.get(role.id))) < 2:
            s = 7200 - seconds(val)
            await ctx.send_followup(
                f"{role.mention} is in cool down, check the latest ping at <#722617383738540092>."
                f"Or try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return

        msg = await self.webhook.send(
            content=f"{role.mention} is being pinged by {member.mention}",
            embed=embed,
            allowed_mentions=AllowedMentions(roles=True, users=True),
            view=view,
            username=member.display_name,
            avatar_url=member.default_avatar.url,
            wait=True,
        )
        self.cool_down[member.id] = utcnow()
        self.role_cool_down[role.id] = utcnow()
        self.last_claimer[role.id] = member.id
        view = View(Button(label="Jump URL", url=msg.jump_url))

        self.view.setup()
        self.msg = await self.msg.edit(view=self.view)
        async with self.bot.database() as db:
            await db.execute(
                """--sql
                INSERT INTO RP_SEARCH(ID, MEMBER, ROLE, SERVER)
                VALUES ($1, $2, $3, $4);
                """,
                msg.id,
                member.id,
                role.id,
                member.guild.id,
            )

            await ctx.send_followup(
                content="Ping has been done successfully.",
                ephemeral=True,
                view=view,
            )

    @Cog.listener()
    async def on_ready(self):
        """Loads the views"""
        self.webhook = await self.bot.webhook(
            722617383738540092,
            reason="RP Pinging",
        )
        self.roles = PronounRoles(timeout=None)
        self.basic = BasicRoles(timeout=None)
        self.color = ColorRoles(timeout=None)
        self.rp_search = RPSearchRoles(timeout=None)
        self.region = RegionRoles(self.bot)

        self.bot.add_view(view=self.roles, message_id=916482734933811232)
        self.bot.add_view(view=self.basic, message_id=916482736309534762)
        self.bot.add_view(view=self.color, message_id=916482737811120128)
        self.bot.add_view(view=self.rp_search, message_id=916482738876477483)
        self.bot.add_view(view=self.region, message_id=956970863805231144)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Roles(bot))
