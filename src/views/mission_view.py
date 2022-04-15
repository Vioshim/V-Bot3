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

from discord import Interaction, InteractionResponse, Member, TextChannel, Thread
from discord.ui import Button, View, button
from discord.utils import format_dt, utcnow

from src.pagination.complex import Complex
from src.structures.character import Character
from src.structures.mission import Mission

__all__ = ("MissionView",)


class MissionView(View):
    def __init__(
        self,
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
        self.mission = mission
        self.mission_claimers = mission_claimers
        self.mission_cooldown = mission_cooldown
        self.supporting = supporting

    @button(label="Join Mission", custom_id="claim")
    async def claim(self, interaction: Interaction, btn: Button) -> None:
        """Claim Mission

        Parameters
        ----------
        btn : Button
            Button
        interaction : Interaction
            Interaction
        """
        resp: InteractionResponse = interaction.response
        cog = interaction.client.get_cog("Submission")
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
            if not btn.disabled:
                btn.disabled = True
                await interaction.message.edit(view=self)
            await resp.send_message(
                f"The limited mission has already been claimed by {limit:02d} characters.",
                ephemeral=True,
            )
            return

        if items := [oc for oc in ocs if oc.id in self.mission.ocs]:
            oc = items[0]
            view = View()
            view.add_item(Button(label="Jump URL", url=oc.jump_url))
            await resp.send_message(
                f"Your character {oc.name!r} is already participating in the mission.",
                view=view,
                ephemeral=True,
            )
            return

        if (time := self.mission_cooldown.get(member.id)) and (reference_time := time + timedelta(days=3)) >= utcnow():
            time: str = format_dt(reference_time, style="R")
            await resp.send_message(
                f"You are in cool down: {time}.",
                ephemeral=True,
            )
            return

        view_select = Complex(
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

            async with interaction.client.database() as db:

                assigned_at = await self.mission.upsert_oc(connection=db, oc_id=choice.id)
                self.mission_cooldown[member.id] = assigned_at
                embed = self.mission.embed
                if limit and len(self.mission.ocs) >= limit:
                    btn.disabled = True
                await interaction.message.edit(embed=embed, view=self)

                thread: Thread = await interaction.client.fetch_channel(self.mission.msg_id)
                view = View()
                view.add_item(Button(label="Jump URL", url=choice.jump_url))
                await thread.add_user(member)
                await thread.send(
                    f"{member} joined with {choice.name} `{choice!r}` as character for this mission.",
                    view=view,
                )

    # noinspection PyTypeChecker
    @button(label="Conclude Mission", custom_id="remove")
    async def remove(self, interaction: Interaction, btn: Button):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        ch: TextChannel = interaction.channel
        await resp.defer(ephemeral=True)
        if member.id == self.mission.author or ch.permissions_for(member).manage_messages:
            self.claim.disabled = True
            btn.disabled = True
            async with interaction.client.database() as db:
                await self.mission.remove(db)
                await interaction.message.delete()
                if not (thread := member.guild.get_thread(self.mission.msg_id)):
                    thread: Thread = await interaction.client.fetch_channel(self.mission.msg_id)
                await thread.edit(
                    archived=False,
                    locked=True,
                    reason=f"{member} concluded the mission.",
                )
                await thread.send(embed=self.mission.embed)
            await interaction.followup.send(
                "Mission has been concluded.",
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                "It's not yours.",
                ephemeral=True,
            )
