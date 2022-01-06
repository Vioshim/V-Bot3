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

from typing import Iterable, Optional

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    User,
)
from discord.ui import Button, Select, View, button, select

__all__ = ("SelfRoles",)


class SelfRoles(View):
    def __init__(self, member: Member | User):
        super(SelfRoles, self).__init__(timeout=None)
        if isinstance(member, User):
            guild = member.mutual_guilds[0]
            member = guild.get_member(member.id)
        self.guild = member.guild
        self.member = member
        required: Role = member.guild.get_role(719642423327719434)
        if required not in member.roles:
            self.rp_search.disabled = True
            self.add_item(
                Button(
                    label="Go to OC-Submission in order to get access to the RP.",
                    url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
                    emoji="\N{OPEN BOOK}",
                    row=4,
                )
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        return interaction.user == self.member

    async def role_menu(
        self,
        ctx: Interaction,
        roles: Iterable[Role],
        total: Iterable[Role],
    ):
        """Method to add/remove multiple roles.

        Parameters
        ----------
        ctx: Interaction
            Discord Interaction
        roles: Iterable[Role]
            Selected Roles
        total: Iterable[int]
            Role IDs from the group
        """
        resp: InteractionResponse = ctx.response
        if remove := (set(total) - set(roles)) & set(self.member.roles):
            await self.member.remove_roles(*remove, reason="Self Roles")
        await self.member.add_roles(*roles, reason="Self Roles")
        await resp.send_message("Roles has been set!", ephemeral=True)

    async def unique_role_button(
        self,
        ctx: Interaction,
        role: Optional[Role],
        roles: Iterable[Role],
    ) -> None:
        """Method to add/remove a single role.

        Parameters
        ----------
        ctx: Interaction
            Discord Interaction
        role: Role
            Selected Role
        roles: Iterable[Role]
            Role IDs from the group
        """
        resp: InteractionResponse = ctx.response
        member = self.member
        if role in member.roles:
            await member.remove_roles(role, reason="Self Roles interaction")
            await resp.send_message(
                f"Role {role.mention} was removed from your account.",
                ephemeral=True,
            )
        elif role:
            await member.add_roles(role, reason="Self Roles interaction")
            await resp.send_message(
                f"Role {role.mention} was added to your account.",
                ephemeral=True,
            )
        if data := set(member.roles).intersection(roles):
            await member.remove_roles(
                *(
                    role_item
                    for item in data
                    if (role_item := ctx.guild.get_role(item))
                ),
                reason="Self Roles",
            )

    @select(
        placeholder="Select Pronoun/s",
        min_values=0,
        max_values=3,
        options=[
            SelectOption(
                label="He",
                value="738230651840626708",
                emoji="\N{MALE SIGN}",
            ),
            SelectOption(
                label="She",
                value="738230653916807199",
                emoji="\N{FEMALE SIGN}",
            ),
            SelectOption(
                label="Them",
                value="874721683381030973",
                emoji="🏳️‍🌈",
            ),
        ],
    )
    async def pronoun(self, sct: Select, interaction: Interaction):
        guild = self.guild
        roles: list[Role] = [
            role for item in sct.values if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in sct.options
            if (role := guild.get_role(int(item.value)))
        ]
        return await self.role_menu(interaction, roles, total)

    @select(
        placeholder="Select Basic Roles",
        min_values=0,
        max_values=6,
        options=[
            SelectOption(
                label="Smash Events",
                emoji="💠",
                value="742820332477612062",
                description="Lets you get pinged for Smash Events",
            ),
            SelectOption(
                label="Pokemon",
                emoji="💠",
                value="750531846739198062",
                description="To ping for Pokemon Games",
            ),
            SelectOption(
                label="Minecraft",
                emoji="💠",
                value="748584270011957252",
                description="Allows you to get notified for playing together.",
            ),
            SelectOption(
                label="Roblox",
                emoji="💠",
                value="750395469280051260",
                description="Helps you to get pinged for Roblox Events",
            ),
            SelectOption(
                label="Radio",
                emoji="💠",
                value="805878418225889280",
                description="Get pinged each time Reshy streams in radio.",
            ),
            SelectOption(
                label="Announcements",
                emoji="💠",
                value="908809235012419595",
                description="Get pinged during announcements.",
            ),
        ],
    )
    async def basic(self, sct: Select, interaction: Interaction):
        guild = self.guild
        roles: list[Role] = [
            role for item in sct.values if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in sct.options
            if (role := guild.get_role(int(item.value)))
        ]
        return await self.role_menu(interaction, roles, total)

    @select(
        placeholder="Select Color Roles",
        options=[
            SelectOption(
                label="Red",
                emoji=":red:880796435048706099",
                value="794274172813312000",
                description="Select to add or remove red color role",
            ),
            SelectOption(
                label="Crimson",
                emoji=":crimson:880796435161968681",
                value="794274956296847370",
                description="Select to add or remove crimson color role",
            ),
            SelectOption(
                label="Orange",
                emoji=":orange:880796435501678602",
                value="794275894209282109",
                description="Select to add or remove orange color role",
            ),
            SelectOption(
                label="Golden",
                emoji=":golden:880796435291983902",
                value="794275428696064061",
                description="Select to add or remove golden color role",
            ),
            SelectOption(
                label="Yellow",
                emoji=":yellow:880796435325526047",
                value="794274424777080884",
                description="Select to add or remove yellow color role",
            ),
            SelectOption(
                label="Green",
                emoji=":green:880796435329724446",
                value="794274561570504765",
                description="Select to add or remove green color role",
            ),
            SelectOption(
                label="Lime",
                emoji=":lime:880796435359080458",
                value="794276035326902342",
                description="Select to add or remove lime color role",
            ),
            SelectOption(
                label="Cyan",
                emoji=":cyan:880796435312967710",
                value="794276172762185799",
                description="Select to add or remove cyan color role",
            ),
            SelectOption(
                label="Light Blue",
                emoji=":light_blue:880796435065483306",
                value="794274301707812885",
                description="Select to add or remove light blue color role",
            ),
            SelectOption(
                label="Deep Blue",
                emoji=":deep_blue:880796435229069323",
                value="794275553477394475",
                description="Select to add or remove deep blue color role",
            ),
            SelectOption(
                label="Violet",
                emoji=":violet:880796435635904572",
                value="794275765533278208",
                description="Select to add or remove violet color role",
            ),
            SelectOption(
                label="Pink",
                emoji=":pink:880796434989977601",
                value="794274741061025842",
                description="Select to add or remove pink color role",
            ),
            SelectOption(
                label="Light Brown",
                emoji=":light_brown:880796435426201610",
                value="794275107958292500",
                description="Select to add or remove light brown color role",
            ),
            SelectOption(
                label="Dark Brown",
                emoji=":dark_brown:880796435359092806",
                value="794275288271028275",
                description="Select to add or remove dark brown color role",
            ),
            SelectOption(
                label="Silver",
                emoji=":silver:880796435409416202",
                value="850018780762472468",
                description="Select to add or remove silver color role",
            ),
            SelectOption(
                label="Gray",
                emoji=":gray:880796435430395914",
                value="794273806176223303",
                description="Select to add or remove gray color role",
            ),
        ],
    )
    async def color_roles(self, sct: Select, interaction: Interaction):
        guild = self.guild
        if role := guild.get_role(int(sct.values[0])):
            total: list[Role] = [
                role
                for item in sct.options
                if (role := guild.get_role(int(item.value)))
            ]
            return await self.unique_role_button(interaction, role, total)

    @select(
        placeholder="Select RP Search Roles",
        min_values=0,
        max_values=5,
        options=[
            SelectOption(
                label="Any",
                description="Used for getting any kind of RP.",
                value="744841294869823578",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
            SelectOption(
                label="Plot",
                description="Used for getting arcs in RP.",
                value="744841357960544316",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
            SelectOption(
                label="Casual",
                description="Used for getting random meetings in RP.",
                value="744841408539656272",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
            SelectOption(
                label="Action",
                description="Used for getting battle/tension related RPs.",
                value="744842759004880976",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
            SelectOption(
                label="GameMaster",
                description="Used for getting help with narration.",
                value="808730687753420821",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
        ],
    )
    async def rp_search(self, sct: Select, interaction: Interaction):
        guild = self.guild
        roles: list[Role] = [
            role for item in sct.values if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in sct.options
            if (role := guild.get_role(int(item.value)))
        ]
        return await self.role_menu(interaction, roles, total)
