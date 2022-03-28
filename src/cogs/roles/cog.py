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

from discord import Thread, Webhook, WebhookMessage
from discord.ext.commands import Cog

from src.cogs.roles.roles import (
    BasicRoles,
    ColorRoles,
    PronounRoles,
    RegionRoles,
    RPSearchRoles,
    RPThreadManage,
    RPThreadView,
)
from src.structures.bot import CustomBot

__all__ = ("Roles", "setup")


class Roles(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.last_claimer: dict[int, int] = {}
        self.webhook: Optional[Webhook] = None
        self.msgs: dict[int, WebhookMessage] = {}

    async def load_rp_searches(self):
        self.bot.logger.info("Loading existing RP Searches")
        async with self.bot.database() as db:
            async for item in db.cursor("SELECT * FROM RP_SEARCH;"):
                msg_id, member_id, role_id, server_id, created_at = (
                    item["id"],
                    item["member"],
                    item["role"],
                    item["server"],
                    item["created_at"],
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
                    view=RPThreadManage(
                        bot=self.bot,
                        role=role,
                        member=member,
                    ),
                    message_id=msg_id,
                )
        self.bot.logger.info("Finished loading existing RP Searches")

    @Cog.listener()
    async def on_ready(self):
        """Loads the views"""
        self.webhook = await self.bot.webhook(
            910914713234325504,
            reason="RP Pinging",
        )
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
            view=RegionRoles(bot=self.bot),
            message_id=956970863805231144,
        )
        w = await self.bot.webhook(910914713234325504)
        async for m in w.channel.history(limit=None):
            if m.webhook_id != w.id:
                continue

            if not (thread := w.channel.get_thread(m.id)):
                thread: Thread = await w.guild.fetch_channel(m.id)

            await w.edit_message(
                m.id,
                view=RPThreadView(
                    bot=self.bot,
                    cool_down=self.cool_down,
                    role_cool_down=self.role_cool_down,
                    last_claimer=self.last_claimer,
                    thread=thread,
                ),
            )

        await self.load_rp_searches()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Roles(bot))
