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

from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
)
from discord.ui import Button, View, button
from discord.utils import utcnow

from src.structures.bot import CustomBot

__all__ = ("RPView",)


class RPView(View):
    def __init__(
        self,
        bot: CustomBot,
        member_id: int,
        oc_list: dict[int, int],
        server: int = 719343092963999804,
    ):
        super(RPView, self).__init__(timeout=None)
        self.bot = bot
        self.member_id = member_id
        self.last_ping = None
        self.oc_list = oc_list
        self.server = server
        self.url = f"https://discord.com/channels/{server}/{oc_list[member_id]}/"
        btn = Button(label="Check User's OCs", url=self.url)
        self.add_item(btn)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        registered = interaction.guild.get_role(719642423327719434)
        if interaction.user.id == self.member_id:
            await resp.send_message("Can't ping yourself", ephemeral=True)
            return False
        if registered not in interaction.user.roles:
            await resp.send_message("Only registered users can ping", ephemeral=True)
            return False
        if not (member := interaction.guild.get_member(self.member_id)):
            await resp.send_message("User isn't here anymore.", ephemeral=True)
            return False
        if registered not in member:
            await resp.send_message("User is no longer registered.", ephemeral=True)
            return False

        return True

    @button(label="Mention the User", style=ButtonStyle.green, custom_id="ping")
    async def ping(self, _: Button, interaction: Interaction):
        member: Member = interaction.user
        guild = interaction.guild
        webhook = await self.bot.webhook(740568087820238919, reason="Ping")
        embed = Embed(title="User has pinged you.", timestamp=utcnow(), color=member.color)
        embed.set_author(name=member.display_name)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        view = View()
        view.add_item(Button(label="Your OCs", url=self.url))
        if thread_id := self.oc_list.get(member.id):
            view.add_item(
                Button(
                    label="User's OCs",
                    url=f"https://discord.com/channels/{self.server}/{thread_id}/",
                )
            )
        author = interaction.guild.get_member(self.member_id)
        await webhook.send(
            f"Hello {author.mention}\n\n{member.mention} is interested on Rping with your characters.",
            embed=embed,
            view=view,
            allowed_mentions=AllowedMentions(users=True),
        )
