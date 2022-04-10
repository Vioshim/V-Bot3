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

from discord import Webhook
from discord.ext.commands import Cog

from src.cogs.roles.roles import (
    BasicRoles,
    ColorRoles,
    PronounRoles,
    RegionRoles,
    RPRolesView,
    RPSearchManage,
    RPSearchRoles,
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
                msg_id, member_id, role_id, server_id, created_at, aux = (
                    item["id"],
                    item["member"],
                    item["role"],
                    item["server"],
                    item["created_at"],
                    item["message"],
                )

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
                    view=RPSearchManage(member=member),
                    message_id=msg_id,
                )
                self.bot.add_view(
                    view=RPSearchManage(member=member),
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


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
