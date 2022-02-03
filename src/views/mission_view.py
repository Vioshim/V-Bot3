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

from datetime import datetime, timedelta

from discord import (
    Color,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Thread,
)
from discord.ui import Button, View, button
from discord.utils import format_dt

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mission import Mission

__all__ = ("MissionView",)


class MissionView(View):
    def __init__(
        self,
        bot: CustomBot,
        mission: Mission,
        mission_claimers: dict[int, set[int]],
        mission_cooldown: dict[int, datetime],
        supporting: dict[Member, Member],
    ):
        """Init Method

        Parameters
        ----------
        bot : CustomBot
            Bot Instance
        mission : Mission
            Mission
        mission_claimers : dict[int, datetime]
            Members with their last claim date
        mission_cooldown : dict[int, set[int]]
            mission id and the ocs that claim it
        """
        super(MissionView, self).__init__(timeout=None)
        self.bot = bot
        self.mission = mission
        self.mission_claimers = mission_claimers
        self.mission_cooldown = mission_cooldown
        self.supporting = supporting

    @button(label="Join Mission", custom_id="claim")
    async def claim(self, btn: Button, interaction: Interaction) -> None:
        """Claim Mission

        Parameters
        ----------
        btn : Button
            Button
        interaction : Interaction
            Interaction
        """
        resp: InteractionResponse = interaction.response
        cog = self.bot.get_cog("Submission")
        member: Member = self.supporting.get(interaction.user, interaction.user)

        ocs: list[Character] = list(cog.rpers.get(member.id, {}).values())

        if not ocs:
            await resp.send_message(
                "You don't have registered characters",
                ephemeral=True,
            )
            return

        limit = self.mission.max_amount
        if limit and len(self.mission.ocs) >= limit:
            await resp.send_message(
                f"The limited mission has already been claimed by {limit:02d} characters.",
                ephemeral=True,
            )
            return

        if items := [oc for oc in ocs if oc.id in self.mission.ocs]:
            oc = items[0]
            await resp.send_message(
                f"Your character {oc.name!r} is already participating in the mission.",
                view=View(Button(label="Jump URL", url=oc.jump_url)),
                ephemeral=True,
            )
            return

        if (time := self.mission_cooldown.get(member.id)) and (
            reference_time := time + timedelta(days=3)
        ) >= datetime.now():
            time: str = format_dt(reference_time, style="R")
            await resp.send_message(
                f"You are in cool down: {time}.",
                ephemeral=True,
            )
            return

        view_select = Complex(
            bot=self.bot,
            member=interaction.user,
            target=interaction,
            values=ocs,
            sort_key=lambda x: x.name,
        )

        choice: Character
        async with view_select.send(
            title="Mission Claiming",
            description="Select who is taking the mission",
            single=True,
            ephemeral=True,
        ) as choice:

            if choice is None:
                return

            async with self.bot.database() as db:

                assigned_at = await self.mission.upsert_oc(
                    connection=db, oc_id=choice.id
                )
                self.mission_cooldown[member.id] = assigned_at
                embed = self.mission.embed
                if limit and self.mission.ocs >= limit:
                    btn.disabled = True
                await interaction.message.edit(embed=embed, view=self)

                thread: Thread = await self.bot.fetch_channel(
                    self.mission.msg_id
                )
                await thread.add_user(member)
                await thread.send(
                    f"{member} joined with {choice.name} `{choice!r}` as character for this mission.",
                    view=View(Button(label="Jump URL", url=choice.jump_url)),
                )

    # noinspection PyTypeChecker
    @button(label="Conclude Mission", custom_id="remove")
    async def remove(self, btn: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        ch: TextChannel = interaction.channel
        await resp.defer(ephemeral=True)
        if (
            member.id == self.mission.author
            or ch.permissions_for(member).manage_messages
        ):
            self.claim.disabled = True
            btn.disabled = True
            async with self.bot.database() as db:
                await self.mission.remove(db)
                embed = self.mission.embed
                embed.color = Color.red()
                await interaction.message.edit(embed=embed, view=self)
                thread: Thread = await self.bot.fetch_channel(
                    self.mission.msg_id
                )
                await thread.edit(
                    locked=True,
                    reason=f"{member} concluded the mission.",
                )
            await interaction.followup.send(
                "Mission has been concluded.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "It's not yours.",
                ephemeral=True,
            )
