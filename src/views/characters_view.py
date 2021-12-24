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
from discord.ui import Button, Select, View, button

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR

__all__ = ("CharactersView", "PingView")


class PingView(View):
    def __init__(self, oc: Character, deleter: bool = False):
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
        await resp.send_message("You don't have registered role", ephemeral=True)
        return False

    @button(label="Ping to RP with the OC")
    async def ping(self, _: Button, ctx: Interaction) -> None:
        member = ctx.guild.get_member(self.oc.author)
        resp: InteractionResponse = ctx.response
        if ctx.user == member:
            await resp.send_message("You can't ping yourself", ephemeral=True)
            return
        try:
            channel: TextChannel = ctx.guild.get_channel(740568087820238919)
            view = View()
            view.add_item(Button(label="Character", url=self.oc.jump_url))
            await channel.send(
                f"Hello {member.mention}!\n\n"
                f"{ctx.user.mention} is interested on RPing with {self.oc.name}.",
                view=view,
                allowed_mentions=AllowedMentions(users=True),
            )
        finally:
            self.stop()

    @button(
        label="Delete Character",
        style=ButtonStyle.red,
    )
    async def delete(self, _: Button, ctx: Interaction) -> None:
        resp: InteractionResponse = ctx.response
        member = ctx.guild.get_member(self.oc.author)
        if ctx.user != member:
            await resp.send_message("This is not yours", ephemeral=True)
            return
        try:
            await resp.send_message("Deleted character", ephemeral=True)
            thread = await ctx.guild.fetch_channel(self.oc.thread_id)
            message = await thread.fetch_message(self.oc.id)
            await message.delete()
        except DiscordException:
            pass
        finally:
            self.stop()


class CharactersView(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        ocs: set[Character],
    ):
        super(CharactersView, self).__init__(
            bot=bot,
            member=member,
            target=target,
            values=ocs,
            timeout=None,
            title="Select a character",
            parser=lambda x: (x.name, repr(x)),
            image=WHITE_BAR,
        )

    async def custom_choice(self, _: Select, ctx: Interaction):
        response: InteractionResponse = ctx.response
        for index in ctx.data.get("values", []):  # type: str
            try:
                amount = self.entries_per_page * self._pos
                chunk = self.values[amount : amount + self.entries_per_page]
                item: Character = chunk[int(index)]
                if item := self._choice:
                    view = PingView(item, ctx.user.id == item.author)
                    await response.send_message(
                        embed=item.embed,
                        view=view,
                        ephemeral=True,
                    )
            except Exception as e:
                self.bot.logger.exception("Type: %s, Str: %s", type(item), str(item), exc_info=e)
            finally:
                await self.edit(ctx, self._pos)

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
