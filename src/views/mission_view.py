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

from discord import AllowedMentions, ButtonStyle, Interaction, Member, TextChannel
from discord.ui import Button, View, button

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mission import Mission

__all__ = ("MissionView",)


class MissionView(View):
    def __init__(self, bot: CustomBot, mission: Mission):
        super(MissionView, self).__init__(timeout=None)
        self.bot = bot
        self.mission = mission
        self.claim.disabled = bool(mission.claimed)

    @button(label="Claim Mission", custom_id="claim")
    async def claim(self, btn: Button, interaction: Interaction):
        # noinspection PyTypeChecker
        cog = self.bot.get_cog("Submission")
        member: Member = interaction.user
        if not (ocs := cog.oc_slots.get(member.id, set())):
            await interaction.response.send_message("You don't have registered characters", ephemeral=True)
            return

        async with self.bot.database() as db:

            if await db.fetchval("SELECT COUNT(*) > 1 FROM MISSIONS WHERE CLAIMED = $1;", member.id):
                await interaction.response.send_message("You are already doing a mission.", ephemeral=True)
                return

        view_select = Complex(
            bot=self.bot,
            member=member,
            target=interaction,
            values=ocs,
            parser=lambda x: (x.name, repr(x)),
        )

        choice: Character
        async with view_select.send(
            title="Mission Claiming",
            description="Select who is taking the mission",
        ) as choice:

            if not choice:
                return

            async with self.bot.database() as db:

                w2 = await self.bot.webhook(interaction.channel_id, reason="Missions")

                btn.label = "See Claim"
                btn.custom_id = None
                btn.style = ButtonStyle.link
                btn.url = choice.jump_url

                await w2.edit_message(interaction.message.id, view=self)

                w3 = await self.bot.webhook(740568087820238919, reason="Mission Claim")

                self.mission.claimed = member.id
                await self.mission.upsert(connection=db)
                view = View()
                view.add_item(Button(label="Character", url=choice.jump_url))
                view.add_item(Button(label="Mission", url=self.mission.jump_url))

                if author := w3.guild.get_member(self.mission.author):
                    await w3.send(
                        content=f"{member.mention} has claimed {author.mention}'s mission.",
                        view=view,
                        allowed_mentions=AllowedMentions(users=True),
                    )
                else:
                    await w3.send(
                        content=f"{member.mention} has claimed a mission ~~whose author left~~.",
                        view=view,
                        allowed_mentions=AllowedMentions(users=True),
                    )

    # noinspection PyTypeChecker
    @button(label="Remove Mission", custom_id="remove")
    async def remove(self, _: Button, interaction: Interaction):
        member: Member = interaction.user
        ch: TextChannel = interaction.channel
        if not ch.permissions_for(member).manage_messages:
            if member.id != self.mission.author:
                await interaction.response.send_message("It's not yours.", ephemeral=True)
                return
        async with self.bot.database() as db:
            await self.mission.remove(db)
            await interaction.message.delete()
        await interaction.response.send_message("Mission has been removed.", ephemeral=True)
