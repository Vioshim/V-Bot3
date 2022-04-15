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

from logging import getLogger, setLoggerClass
from typing import Optional, Union

from discord import (
    AllowedMentions,
    ButtonStyle,
    DiscordException,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    TextChannel,
    Webhook,
)
from discord.ui import Button, Select, View, button, select

from src.pagination.complex import Complex
from src.structures.character import Character
from src.structures.logger import ColoredLogger

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

__all__ = ("CharactersView", "PingView")


class PingView(View):
    def __init__(
        self,
        oc: Character,
        deleter: bool = False,
    ):
        super(PingView, self).__init__(timeout=None)
        self.oc = oc
        self.ping.label = f"Ping to RP with {oc.name}"
        if not deleter:
            self.remove_item(self.delete)

    async def interaction_check(self, interaction: Interaction) -> bool:
        guild: Guild = interaction.guild
        resp: InteractionResponse = interaction.response
        registered = guild.get_role(719642423327719434)
        if registered in interaction.user.roles:
            if guild.get_member(self.oc.author):
                return True
            await resp.send_message("Owner of the OC is no longer in the Server", ephemeral=True)
            return False
        await resp.send_message(
            "You don't have registered role",
            ephemeral=True,
        )
        return False

    @button(label="Ping to RP with the OC")
    async def ping(self, ctx: Interaction, _: Button) -> None:
        member = ctx.guild.get_member(self.oc.author)
        resp: InteractionResponse = ctx.response
        if ctx.user == member:
            await resp.send_message(
                "You can't ping yourself",
                ephemeral=True,
            )
            return
        try:
            if isinstance(channel := ctx.channel, TextChannel):
                channel = ctx.guild.get_channel(740568087820238919) or channel
            view = View()
            view.add_item(Button(label="Character", url=self.oc.jump_url))
            await channel.send(
                f"Hello {member.mention}!\n\n"
                f"{ctx.user.mention} is interested on RPing with your OC {self.oc.name}.",
                view=view,
                allowed_mentions=AllowedMentions(users=True),
            )
        finally:
            self.stop()

    @button(
        label="Delete Character",
        style=ButtonStyle.red,
    )
    async def delete(self, ctx: Interaction, _: Button) -> None:
        resp: InteractionResponse = ctx.response
        member = ctx.guild.get_member(self.oc.author)
        if ctx.user != member:
            await resp.send_message("This is not yours", ephemeral=True)
            return
        try:
            await resp.send_message("Deleted character", ephemeral=True)
            thread = await ctx.guild.fetch_channel(self.oc.thread)
            message = await thread.fetch_message(self.oc.id)
            await message.delete()
        except DiscordException:
            pass
        finally:
            self.stop()


class CharactersView(Complex):
    def __init__(
        self,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        ocs: set[Character],
        keep_working: bool = False,
    ):
        super(CharactersView, self).__init__(
            member=member,
            target=target,
            values=ocs,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
            sort_key=lambda x: x.name,
        )
        self.embed.title = "Select a character"

    @select(
        row=1,
        placeholder="Select the elements",
        custom_id="selector",
    )
    async def select_choice(
        self,
        interaction: Interaction,
        sct: Select,
    ) -> None:
        response: InteractionResponse = interaction.response
        item: Character = self.current_choice
        embed = item.embed
        guild: Guild = self.member.guild
        if author := guild.get_member(item.author):
            embed.set_author(
                name=author.display_name,
                icon_url=author.display_avatar.url,
            )
        view = PingView(
            oc=item,
            deleter=interaction.user.id == item.author,
        )
        await response.send_message(
            embed=embed,
            view=view,
            ephemeral=True,
        )
        await super(CharactersView, self).select_choice(interaction, sct)

    @property
    def choice(self) -> Optional[Character]:
        """Method Override

        Returns
        -------
        set[Move]
            Desired Moves
        """
        if value := super(CharactersView, self).choice:
            return value
