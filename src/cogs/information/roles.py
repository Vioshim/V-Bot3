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

from typing import Iterable, Optional

from discord import (
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
)
from discord.ui import Button, Select, View, button, select

__all__ = ("PronounRoles", "BasicRoles", "ColorRoles", "RPSearchRoles")


async def role_menu(
    ctx: Interaction, roles: Iterable[Role], total: Iterable[Role]
):
    member: Member = ctx.user
    resp: InteractionResponse = ctx.response
    if remove := (set(total) - set(roles)) & set(member.roles):
        await member.remove_roles(*remove, reason="Self Roles")
    await member.add_roles(*roles, reason="Self Roles")
    await resp.send_message("Roles has been set!", ephemeral=True)


async def unique_role_button(
    ctx: Interaction, role: Optional[Role], roles: Iterable[int]
) -> None:
    """Button to add/remove roles. Removing its set

    Parameters
    ----------
    ctx: Interaction
        Discord Interaction
    role: Role
        Selected Role
    roles: Iterable[int]
        Role IDs from the group

    Returns
    -------

    """
    resp: InteractionResponse = ctx.response

    if role in ctx.user.roles:

        class Confirmation(View):
            @button(
                label="Keep role", emoji=":small_check_mark:811367963235713124"
            )
            async def keep(self, _: Button, inter: Interaction):
                await inter.response.send_message(
                    f"Role {role.mention} was not removed.", ephemeral=True
                )

            @button(
                label="Remove Role", emoji=":small_x_mark:811367596866797658"
            )
            async def remove(self, _: Button, inter: Interaction):
                await ctx.user.remove_roles(
                    role, reason="Self Roles interaction"
                )
                await inter.response.send_message(
                    f"Role {role.mention} was removed.", ephemeral=True
                )

        view = Confirmation()
        await resp.send_message(
            f"You have the role {role.mention} already",
            ephemeral=True,
            view=view,
        )
        return await view.wait()
    elif role:
        await ctx.user.add_roles(role, reason="Self Roles interaction")
        await resp.send_message(
            f"Role {role.mention} was added to your account.", ephemeral=True
        )
    if data := set(x.id for x in ctx.user.roles).intersection(roles):
        await ctx.user.remove_roles(
            *(
                role_item
                for item in data
                if (role_item := ctx.guild.get_role(item))
            ),
            reason="Self Roles",
        )


async def required_role_menu(
    ctx: Interaction, selected: Role, required: Role
) -> None:
    resp: InteractionResponse = ctx.response
    member: Member = ctx.user
    if required in ctx.user.roles:
        if selected in member.roles:
            await member.remove_roles(selected, reason="Self Roles")
            return await resp.send_message(
                f"Role {selected.mention} removed", ephemeral=True
            )
        else:
            await member.add_roles(selected, reason="Self Roles")
            return await resp.send_message(
                f"Role {selected.mention} added", ephemeral=True
            )
    return await resp.send_message(
        f"You need {required.mention} to use this role.", ephemeral=True
    )


PRONOUN_ROLES = dict(
    He=738230651840626708,
    She=738230653916807199,
    Them=874721683381030973,
)

BASIC_ROLES = {
    "PMDiscord": 729522869993734248,
    "Smash Events": 742820332477612062,
    "PMU": 750531846739198062,
    "Minecraft": 748584270011957252,
    "Roblox": 750395469280051260,
    "Radio": 805878418225889280,
    "Announcements": 908809235012419595,
}

COLOR_ROLES = dict(
    red=794274172813312000,
    crimson=794274956296847370,
    orange=794275894209282109,
    golden=794275428696064061,
    yellow=794274424777080884,
    green=794274561570504765,
    lime=794276035326902342,
    cyan=794276172762185799,
    light_blue=794274301707812885,
    deep_blue=794275553477394475,
    violet=794275765533278208,
    pink=794274741061025842,
    light_brown=794275107958292500,
    dark_brown=794275288271028275,
    silver=850018780762472468,
    gray=794273806176223303,
)

RP_SEARCH_ROLES = dict(
    Any=744841294869823578,
    Plot=744841357960544316,
    Casual=744841408539656272,
    Action=744842759004880976,
    GameMaster=808730687753420821,
)


class PronounButton(Button):
    async def callback(self, ctx: Interaction):
        role = ctx.guild.get_role(int(self.custom_id))
        return await unique_role_button(ctx, role, PRONOUN_ROLES.values())


class ColorButton(Button):
    async def callback(self, ctx: Interaction):
        guild: Guild = ctx.guild
        role = guild.get_role(int(self.custom_id))
        return await unique_role_button(ctx, role, COLOR_ROLES.values())


class RPSearchButton(Button):
    async def callback(self, ctx: Interaction):
        guild: Guild = ctx.guild
        role = guild.get_role(int(self.custom_id))
        if registered := guild.get_role(719642423327719434):
            await required_role_menu(ctx, role, registered)


COLORS = [
    ColorButton(
        emoji=":red:880796435048706099",
        custom_id="794274172813312000",
        row=0,
    ),
    ColorButton(
        emoji=":crimson:880796435161968681",
        custom_id="794274956296847370",
        row=0,
    ),
    ColorButton(
        emoji=":orange:880796435501678602",
        custom_id="794275894209282109",
        row=0,
    ),
    ColorButton(
        emoji=":golden:880796435291983902",
        custom_id="794275428696064061",
        row=0,
    ),
    ColorButton(
        emoji=":yellow:880796435325526047",
        custom_id="794274424777080884",
        row=1,
    ),
    ColorButton(
        emoji=":green:880796435329724446",
        custom_id="794274561570504765",
        row=1,
    ),
    ColorButton(
        emoji=":lime:880796435359080458",
        custom_id="794276035326902342",
        row=1,
    ),
    ColorButton(
        emoji=":cyan:880796435312967710",
        custom_id="794276172762185799",
        row=1,
    ),
    ColorButton(
        emoji=":light_blue:880796435065483306",
        custom_id="794274301707812885",
        row=2,
    ),
    ColorButton(
        emoji=":deep_blue:880796435229069323",
        custom_id="794275553477394475",
        row=2,
    ),
    ColorButton(
        emoji=":violet:880796435635904572",
        custom_id="794275765533278208",
        row=2,
    ),
    ColorButton(
        emoji=":pink:880796434989977601",
        custom_id="794274741061025842",
        row=2,
    ),
    ColorButton(
        emoji=":light_brown:880796435426201610",
        custom_id="794275107958292500",
        row=3,
    ),
    ColorButton(
        emoji=":dark_brown:880796435359092806",
        custom_id="794275288271028275",
        row=3,
    ),
    ColorButton(
        emoji=":silver:880796435409416202",
        custom_id="850018780762472468",
        row=3,
    ),
    ColorButton(
        emoji=":gray:880796435430395914",
        custom_id="794273806176223303",
        row=3,
    ),
]


class PronounRoles(View):

    # noinspection DuplicatedCode
    @select(
        placeholder="Select Pronoun/s",
        custom_id="pronouns",
        min_values=0,
        max_values=3,
        options=[
            SelectOption(
                label="He",
                value="738230651840626708",
                emoji="\N{MALE SIGN}️",
            ),
            SelectOption(
                label="She",
                value="738230653916807199",
                emoji="\N{FEMALE SIGN}️",
            ),
            SelectOption(
                label="Them",
                value="874721683381030973",
                emoji="🏳️‍🌈",
            ),
        ],
    )
    async def pronoun(self, _: Select, ctx: Interaction):
        data: list[str] = ctx.data.get("values", [])
        guild: Guild = ctx.guild
        roles: list[Role] = [
            role for item in data if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in PRONOUN_ROLES.values()
            if (role := guild.get_role(int(item)))
        ]
        return await role_menu(ctx, roles, total)


class ColorRoles(View):
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        for item in COLORS:
            self.add_item(item)


class BasicRoles(View):

    @select(
        placeholder="Select Basic Roles",
        min_values=0,
        max_values=6,
        custom_id="62a0a35098d0666728712d4f05a140d1",
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
    async def basic(self, _, ctx: Interaction):
        data: list[str] = ctx.data.get("values", [])
        guild: Guild = ctx.guild
        roles: list[Role] = [
            role for item in data if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in BASIC_ROLES.values()
            if (role := guild.get_role(int(item)))
        ]
        return await role_menu(ctx, roles, total)


class RPSearchRoles(View):
    @select(
        placeholder="Select RP Search Roles",
        custom_id="rp_search",
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
    async def rp_search(self, _: Select, ctx: Interaction):
        data: list[str] = ctx.data.get("values", [])
        guild: Guild = ctx.guild
        roles: list[Role] = [
            role for item in data if (role := guild.get_role(int(item)))
        ]
        total: list[Role] = [
            role
            for item in RP_SEARCH_ROLES.values()
            if (role := guild.get_role(int(item)))
        ]
        return await role_menu(ctx, roles, total)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        required: Role = interaction.guild.get_role(719642423327719434)
        if required in interaction.user.roles:
            return True
        await resp.send_message(
            f"You need {required.mention} to use this role.", ephemeral=True
        )
        return False
