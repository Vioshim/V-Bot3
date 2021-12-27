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

from datetime import datetime

from discord import AllowedMentions, Embed, Message, Role, TextChannel
from discord.commands import (
    ApplicationContext,
    Option,
    OptionChoice,
    slash_command,
)
from discord.ext.commands import Cog, MemberConverter, has_role
from discord.ui import Button, View
from discord.utils import utcnow

from src.cogs.roles.roles import (
    QUERIES,
    RP_SEARCH_ROLES,
    BasicRoles,
    ColorRoles,
    PronounRoles,
    RoleManage,
    RoleView,
    RPSearchRoles,
    hours,
    seconds,
)
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.functions import text_check

__all__ = ("Roles", "setup")


class Roles(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}

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

                    if item := self.role_cool_down.get(role_id):
                        if item < created_at:
                            self.role_cool_down[role_id] = created_at
                    else:
                        self.role_cool_down[role_id] = created_at

                    if item := self.cool_down.get(member_id):
                        if item < created_at:
                            self.cool_down[member_id] = created_at
                    else:
                        self.cool_down[member_id] = created_at

                    view = RoleManage(
                        bot=self.bot, role=role, ocs=values, member=member
                    )
                    self.bot.add_view(view=view, message_id=msg_id)
        self.bot.logger.info("Finished loading existing RP Searches")

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
    ):
        role: Role = ctx.guild.get_role(int(role_id))
        cog = self.bot.get_cog(name="Submission")
        channel: TextChannel = ctx.channel
        await ctx.defer(ephemeral=True)
        if channel.permissions_for(ctx.user).manage_messages:
            await ctx.respond("Provide the user pinging", ephemeral=True)
            m: Message = await self.bot.wait_for(
                "message",
                check=text_check(ctx),
            )
            ctx = await self.bot.get_context(m)
            member = await MemberConverter().convert(ctx, m.content)
        else:
            member = ctx.user

        if role not in member.roles:
            await member.add_roles(role, reason="Rp Searching")

        if hours((val := self.cool_down.get(member.id))) < 2:
            s = 7200 - seconds(val)
            await ctx.respond(
                "You're in cool down, you pinged one of the roles recently."
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return
        elif hours((val := self.role_cool_down.get(role.id))) < 2:
            s = 7200 - seconds(val)
            await ctx.respond(
                f"{role.mention} is in cool down, check the latest ping at <#722617383738540092>."
                f"Or try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )

        channel = self.bot.get_channel(722617383738540092)

        ocs = cog.rpers.get(ctx.user.id, {}).values()
        view = RoleManage(self.bot, role, ocs, member)

        embed = Embed(
            title=role.name,
            color=member.color,
            description=f"{member.display_name} is looking "
            "to RP with their registered character(s).",
            timestamp=utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        msg = await channel.send(
            content=f"{role.mention} is being pinged by {member.mention}",
            embed=embed,
            allowed_mentions=AllowedMentions(roles=True, users=True),
            view=view,
        )
        self.cool_down[member.id] = utcnow()
        self.role_cool_down[role.id] = utcnow()
        view = View()
        view.add_item(Button(label="Jump URL", url=msg.jump_url))

        async with self.bot.database() as db:
            await db.execute(
                "INSERT INTO RP_SEARCH(ID, MEMBER, ROLE, SERVER) VALUES ($1, $2, $3, $4)",
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
        self.bot.add_view(
            view=PronounRoles(timeout=None),
            message_id=916482734933811232,
        )
        self.bot.add_view(
            view=BasicRoles(timeout=None),
            message_id=916482736309534762,
        )
        self.bot.add_view(
            view=ColorRoles(timeout=None),
            message_id=916482737811120128,
        )
        self.bot.add_view(
            view=RPSearchRoles(timeout=None),
            message_id=916482738876477483,
        )
        self.bot.add_view(
            view=RoleView(
                bot=self.bot,
                cool_down=self.cool_down,
                role_cool_down=self.role_cool_down,
            ),
            message_id=910915102490910740,
        )


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot

    Returns
    -------

    """
    bot.add_cog(Roles(bot))
