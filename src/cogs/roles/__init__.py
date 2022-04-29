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

from discord import Interaction, InteractionResponse, Member, Role, app_commands
from discord.app_commands import Choice
from discord.ext.commands import Cog
from discord.utils import snowflake_time

from src.cogs.roles.roles import (
    RP_SEARCH_ROLES,
    BasicRoles,
    ColorRoles,
    PronounRoles,
    RegionRoles,
    RPModal,
    RPRolesView,
    RPSearchManage,
    RPSearchRoles,
    hours,
    seconds,
)
from src.structures.bot import CustomBot

__all__ = ("Roles", "setup")


class Roles(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.last_claimer: dict[int, int] = {}

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")
        self.bot.add_view(
            view=PronounRoles(timeout=None),
            message_id=962830900599603200,
        )
        self.bot.add_view(
            view=BasicRoles(timeout=None),
            message_id=962830903971827792,
        )
        self.bot.add_view(
            view=ColorRoles(timeout=None),
            message_id=962830941368246322,
        )
        self.bot.add_view(
            view=RegionRoles(timeout=None),
            message_id=962830944576864356,
        )
        self.bot.add_view(
            view=RPSearchRoles(timeout=None),
            message_id=962830949815554088,
        )
        self.bot.logger.info("Finished loading Self Roles")

    async def load_rp_searches(self):
        self.bot.logger.info("Loading existing RP Searches")
        async with self.bot.database() as db:
            async for item in db.cursor("SELECT * FROM RP_SEARCH;"):
                msg_id, member_id, role_id, server_id, aux, ocs = (
                    item["id"],
                    item["member"],
                    item["role"],
                    item["server"],
                    item["message"],
                    item["ocs"],
                )
                created_at = snowflake_time(msg_id)

                if not (guild := self.bot.get_guild(server_id)):
                    continue

                member = guild.get_member(member_id)
                role = guild.get_role(role_id)

                if not (member and role):
                    continue

                self.role_cool_down.setdefault(role_id, created_at)
                if self.role_cool_down[role_id] > created_at:
                    self.role_cool_down[role_id] = created_at
                    self.last_claimer[role_id] = member_id

                self.cool_down.setdefault(member_id, created_at)
                if self.cool_down[member_id] > created_at:
                    self.cool_down[member_id] = created_at

                self.bot.add_view(
                    view=RPSearchManage(member=member, ocs=ocs),
                    message_id=msg_id,
                )
                self.bot.add_view(
                    view=RPSearchManage(member=member, ocs=ocs),
                    message_id=aux,
                )

        self.bot.add_view(
            view=RPRolesView(timeout=None),
            message_id=962727445096714240,
        )
        self.bot.logger.info("Finished loading existing RP Searches")

    @Cog.listener()
    async def on_ready(self):
        """Loads the views"""
        await self.load_self_roles()
        await self.load_rp_searches()

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.choices(
        role=[Choice(name=k, value=str(v)) for k, v in RP_SEARCH_ROLES.items()],
    )
    async def ping(
        self,
        interaction: Interaction,
        role: str,
        member: Optional[Member] = None,
    ):
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
        user: Member = interaction.user
        guild = interaction.guild
        role: Role = guild.get_role(int(role))
        reference = member or role
        if self.last_claimer.get(reference.id) == user.id:
            return await resp.send_message(
                f"You're the last user that pinged {reference.mention}, no need to keep pinging, just ask in the RP planning and discuss.",
                ephemeral=True,
            )
        if hours((val := self.cool_down.get(user.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                "You're in cool down, you pinged one of the roles recently.\n"
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        if hours((val := self.role_cool_down.get(reference.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                "Thread is in cool down, check the pings at <#958122815171756042>.\n"
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        cog = interaction.client.get_cog("Submission")
        ocs = [oc for oc in cog.ocs.values() if oc.author == user.id]
        await resp.send_modal(
            RPModal(
                user=user,
                role=role,
                ocs=ocs,
                to_user=member,
            )
        )


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
