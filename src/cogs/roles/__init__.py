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
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Role,
    app_commands,
)
from discord.app_commands import Choice
from discord.ext.commands import Cog
from discord.utils import snowflake_time

from src.cogs.roles.roles import (
    RP_SEARCH_ROLES,
    RoleSelect,
    RPModal,
    RPRolesView,
    RPSearchManage,
)
from src.structures.bot import CustomBot

__all__ = ("Roles", "setup")

IMAGE = "https://cdn.discordapp.com/attachments/748384705098940426/990454127639269416/unknown.png"


class Roles(Cog):
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

    @Cog.listener()
    async def on_ready(self):
        if not self.ref_msg:
            channel = self.bot.get_channel(958122815171756042)
            async for m in channel.history(limit=1):
                view = RPRolesView(timeout=None)
                if m.author == self.bot.user and not m.webhook_id:
                    self.ref_msg = await m.edit(content=IMAGE, view=view)
                else:
                    self.ref_msg = await channel.send(content=IMAGE, view=view)

    @Cog.listener()
    async def on_message(self, msg: Message):
        if msg.flags.ephemeral:
            return
        if msg.webhook_id and msg.channel.id == 958122815171756042:
            view = RPRolesView(timeout=None)
            if m := self.ref_msg:
                await m.delete(delay=0)
            self.ref_msg = await msg.channel.send(content=IMAGE, view=view)

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


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
