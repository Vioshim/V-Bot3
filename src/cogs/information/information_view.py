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

from discord import (
    CategoryChannel,
    Interaction,
    InteractionResponse,
    PermissionOverwrite,
)
from discord.ui import Button, View, button

from src.cogs.information.area_selection import AreaSelection
from src.structures.bot import CustomBot

__all__ = ("RegionView",)


class RegionView(View):
    def __init__(self, bot: CustomBot, cat_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.cat_id = cat_id
        self.unlock.custom_id = f"unlock-{cat_id}"
        self.lock.custom_id = f"lock-{cat_id}"
        self.read.custom_id = f"read-{cat_id}"

    async def interaction_check(self, interaction: Interaction) -> bool:
        """Check if the User is registered

        Parameters
        ----------
        interaction : Interaction
            interaction

        Returns
        -------
        bool
            valid user
        """
        resp: InteractionResponse = interaction.response
        registered = interaction.guild.get_role(719642423327719434)
        if registered not in interaction.user.roles:
            view = View()
            view.add_item(
                Button(
                    label="Create a Character",
                    url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
                )
            )
            await resp.send_message(
                f"In order to use this function, you need to have the role {registered.mention}",
                view=view,
                ephemeral=True,
            )
            return False
        return True

    async def perms_setter(self, ctx: Interaction, mode: bool) -> None:
        """Enable/Disable reading permissions

        Parameters
        ----------
        ctx : Interaction
            interaction
        mode : bool
            mode
        """
        cat: CategoryChannel = ctx.guild.get_channel(self.cat_id)
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        permissions = cat.overwrites
        perms = permissions.get(ctx.user, PermissionOverwrite())
        self.bot.logger.info(
            "%s reading permissions for %s at %s",
            "Enabling" if mode else "Disabling",
            str(ctx.user),
            cat.name,
        )
        perms.read_messages = mode
        await cat.set_permissions(target=ctx.user, overwrite=perms)
        await ctx.followup.send(
            "Permissions have been changed.",
            ephemeral=True,
        )

    @button(label="Obtain Access")
    async def unlock(self, _: Button, ctx: Interaction) -> None:
        await self.perms_setter(ctx, True)

    @button(label="Remove Acess")
    async def lock(self, _: Button, ctx: Interaction) -> None:
        await self.perms_setter(ctx, False)

    @button(label="More Information")
    async def read(self, _: Button, ctx: Interaction) -> None:
        """Read Information

        Parameters
        ----------
        btn : Button
            button
        ctx : Interaction
            interaction
        """
        category: CategoryChannel = ctx.guild.get_channel(self.cat_id)
        resp: InteractionResponse = ctx.response
        self.bot.logger.info(
            "%s is reading Map Information of %s",
            str(ctx.user),
            category.name,
        )
        await resp.defer(ephemeral=True)
        view = AreaSelection(bot=self.bot, cat=category, member=ctx.user)
        await ctx.followup.send(
            f"There's a total of {view.total:02d} OCs in {category.name}.",
            view=view,
            ephemeral=True,
        )
