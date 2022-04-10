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


ROLE_VIEWS = {
    916482734933811232: PronounRoles(timeout=None),
    916482736309534762: BasicRoles(timeout=None),
    916482737811120128: ColorRoles(timeout=None),
    956970863805231144: RegionRoles(timeout=None),
    962732430832304178: RPSearchRoles(timeout=None),
}


class Roles(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.last_claimer: dict[int, int] = {}

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")
        w = await self.bot.webhook(719709333369258015)
        vio = w.guild.get_member(self.bot.owner_id)
        for msg_id, view in ROLE_VIEWS.items():
            # self.bot.add_view(view=view, message_id=msg_id)
            m = await w.fetch_message(msg_id)
            files, embed = await self.bot.embed_raw(m.embeds[0])
            await w.send(
                files=files,
                embed=embed,
                username=vio.display_name,
                avatar_url=vio.display_avatar.url,
                view=view,
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

        view = RPRolesView(timeout=None)
        w = await self.bot.webhook(910914713234325504, reason="RP Search")
        await w.edit_message(962727445096714240, view=view)
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
