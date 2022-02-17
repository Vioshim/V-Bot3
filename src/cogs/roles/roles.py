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
from time import mktime
from typing import Optional

from discord import (
    AllowedMentions,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    Webhook,
)
from discord.ui import Button, Select, View, button, select
from discord.utils import utcnow

from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR
from src.views.characters_view import CharactersView

__all__ = (
    "PronounRoles",
    "BasicRoles",
    "ColorRoles",
    "RPSearchRoles",
    "RoleView",
    "QUERIES",
)

QUERIES = [
    """--sql
DELETE FROM RP_SEARCH
WHERE (CREATED_AT + INTERVAL '1 day') <= CURRENT_TIMESTAMP
RETURNING *;
""",
    """--sql
SELECT * FROM RP_SEARCH;
""",
]


def hours(test: datetime = None) -> int:
    """A function which returns the time between a date and today, with 2 hours as max

    Parameters
    ----------
    test: datetime
        Time

    Returns
    -------
    Time in between
    """
    if test:
        today = utcnow()
        data = mktime(today.timetuple()) - mktime(test.timetuple())
        return int(data // 3600)
    return 2


def seconds(test: datetime) -> int:
    """A function which returns the difference between a date and the current in seconds.

    Parameters
    ----------
    test: datetime
        Datetime parameter

    Returns
    -------
    Difference in seconds
    """
    return int((utcnow() - test).total_seconds())


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
    Narrated=808730687753420821,
)


class PronounRoles(View):
    @select(
        placeholder="Select Pronoun/s",
        custom_id="pronouns",
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
    async def pronoun(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        guild: Guild = ctx.guild
        roles = {item for x in sct.values if (item := guild.get_role(int(x)))}
        total = {
            item for x in sct.options if (item := guild.get_role(int(x.value)))
        }
        if add := roles - set(member.roles):
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            await member.remove_roles(*remove)
        text: str = ", ".join(role.mention for role in roles)
        await resp.send_message(f"Roles [{text}] has been set!", ephemeral=True)


class Confirmation(View):
    def __init__(self, role: Role):
        super().__init__()
        self.role = role

    @button(
        label="Keep role",
        emoji=":small_check_mark:811367963235713124",
    )
    async def keep(self, _: Button, inter: Interaction):
        await inter.response.send_message(
            f"Role {self.role.mention} was not removed.",
            ephemeral=True,
        )
        self.stop()

    @button(
        label="Remove Role",
        emoji=":small_x_mark:811367596866797658",
    )
    async def remove(self, _: Button, inter: Interaction):
        await inter.user.remove_roles(self.role)
        await inter.response.send_message(
            f"Role {self.role.mention} was removed.",
            ephemeral=True,
        )
        self.stop()


class ColorButton(Button):
    async def callback(self, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        guild = ctx.guild
        role = guild.get_role(int(self.custom_id))
        total = set(map(guild.get_role, COLOR_ROLES.values()))
        total.remove(role)
        if role in ctx.user.roles:
            view = Confirmation(role)
            await resp.send_message(
                f"You have the role {role.mention} already",
                ephemeral=True,
                view=view,
            )
        elif role:
            await resp.send_message(
                f"Role {role.mention} is being added to your account.",
                ephemeral=True,
            )
            await ctx.user.add_roles(role)
        if data := set(ctx.user.roles).intersection(total):
            await ctx.user.remove_roles(*data)


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


class ColorRoles(View):
    def __init__(self, timeout: Optional[float] = None):
        super().__init__(*COLORS, timeout=timeout)


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
    async def basic(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        guild: Guild = ctx.guild
        roles = {item for x in sct.values if (item := guild.get_role(int(x)))}
        total = {
            item for x in sct.options if (item := guild.get_role(int(x.value)))
        }
        if add := roles - set(member.roles):
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            await member.remove_roles(*remove)
        if text := ", ".join(role.mention for role in roles):
            await resp.send_message(
                f"Roles [{text}] has been set!",
                ephemeral=True,
            )
        else:
            await resp.send_message(
                "Roles unset!",
                ephemeral=True,
            )


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
                label="Narrated",
                description="Used for getting help with narration.",
                value="808730687753420821",
                emoji="\N{RIGHT-POINTING MAGNIFYING GLASS}",
            ),
        ],
    )
    async def rp_search(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        guild: Guild = ctx.guild
        roles = {item for x in sct.values if (item := guild.get_role(int(x)))}
        total = {
            item for x in sct.options if (item := guild.get_role(int(x.value)))
        }
        if add := roles - set(member.roles):
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            await member.remove_roles(*remove)
        if text := ", ".join(role.mention for role in roles):
            await resp.send_message(
                f"Roles [{text}] has been set!",
                ephemeral=True,
            )
        else:
            await resp.send_message(
                "Roles unset!",
                ephemeral=True,
            )

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        required: Role = interaction.guild.get_role(719642423327719434)
        if required in interaction.user.roles:
            return True
        await resp.send_message(
            f"You need {required.mention} to use this role.",
            ephemeral=True,
        )
        return False


class RoleManage(View):
    def __init__(
        self,
        bot: CustomBot,
        role: Role,
        ocs: set[Character],
        member: Member,
    ):
        super(RoleManage, self).__init__(timeout=None)
        self.bot = bot
        self.role = role
        self.ocs = list(ocs)
        self.member = member
        self.role_add.label = f"Get {role.name} Role"
        self.role_remove.label = f"Remove {role.name} Role"

    @button(emoji="\N{WHITE HEAVY CHECK MARK}", row=0, custom_id="role_add")
    async def role_add(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if self.role in member.roles:
            await resp.send_message(
                "You already have the role",
                ephemeral=True,
            )
            return
        await member.add_roles(self.role)
        await resp.send_message(
            "Role added, you'll get pinged next time.",
            ephemeral=True,
        )

    @button(emoji="\N{CROSS MARK}", row=0, custom_id="role_remove")
    async def role_remove(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role, reason="RP Search")
            await resp.send_message(
                "Role removed successfully",
                ephemeral=True,
            )
            return
        await resp.send_message(
            "You don't have that role.",
            ephemeral=True,
        )

    @button(
        label="Click here to view all the user's characters.",
        row=1,
        custom_id="check_ocs",
    )
    async def check_ocs(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        view = CharactersView(
            bot=self.bot,
            member=ctx.user,
            target=ctx,
            ocs=self.ocs,
            keep_working=True,
        )
        embed = view.embed
        embed.set_author(
            name=self.member.display_name,
            icon_url=self.member.display_avatar.url,
        )
        async with view.send(ephemeral=True, single=True) as data:
            if isinstance(data, Character):
                self.bot.logger.info(
                    "User %s is currently reading %s's character %s [%s]",
                    str(ctx.user),
                    str(self.member),
                    data.name,
                    repr(data),
                )


class RoleButton(Button):
    def __init__(
        self,
        bot: CustomBot,
        webhook: Webhook,
        cool_down: dict[int, datetime],
        role_cool_down: dict[int, datetime],
        last_claimer: dict[int, int],
        label: str,
        custom_id: str,
    ):
        super().__init__(label=label, custom_id=custom_id)
        self.cool_down = cool_down
        self.role_cool_down = role_cool_down
        self.last_claimer = last_claimer
        self.webhook = webhook
        self.bot = bot

    async def callback(self, ctx: Interaction):
        role: Role = ctx.guild.get_role(int(self.custom_id))
        member: Member = ctx.user
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)

        if role not in member.roles:
            await member.add_roles(role, reason="RP searching")

        cog = self.bot.get_cog(name="Submission")
        characters = cog.rpers.get(member.id, {}).values()
        view = RoleManage(self.bot, role, characters, member)
        embed = Embed(
            title=role.name,
            color=member.color,
            description=f"{member.display_name} is looking "
            "to RP with their registered character(s).",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        msg = await self.webhook.send(
            content=f"{role.mention} is being pinged by {member.mention}",
            embed=embed,
            allowed_mentions=AllowedMentions(roles=True, users=True),
            view=view,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            wait=True,
        )
        self.cool_down[member.id] = utcnow()
        self.role_cool_down[role.id] = utcnow()
        self.last_claimer[role.id] = member.id
        view = View(Button(label="Jump URL", url=msg.jump_url))
        async with self.bot.database() as db:
            await db.execute(
                "INSERT INTO RP_SEARCH(ID, MEMBER, ROLE, SERVER) VALUES ($1, $2, $3, $4)",
                msg.id,
                member.id,
                role.id,
                member.guild.id,
            )
            await ctx.followup.send(
                content="Ping has been done successfully.",
                view=view,
                ephemeral=True,
            )


class RoleView(View):
    def __init__(
        self,
        bot: CustomBot,
        webhook: Webhook,
        cool_down: dict[int, datetime],
        role_cool_down: dict[int, datetime],
        last_claimer: dict[int, int],
    ):
        buttons = [
            RoleButton(
                bot=bot,
                webhook=webhook,
                cool_down=cool_down,
                role_cool_down=role_cool_down,
                last_claimer=last_claimer,
                label=k,
                custom_id=str(v),
            )
            for k, v in RP_SEARCH_ROLES.items()
        ]
        super().__init__(*buttons, timeout=None)
        self.cool_down = cool_down
        self.role_cool_down = role_cool_down
        self.last_claimer = last_claimer

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        custom_id: int = int(interaction.data.get("custom_id"))
        role: Role = interaction.guild.get_role(custom_id)
        if self.last_claimer.get(custom_id) == interaction.user.id:
            await resp.send_message(
                f"You're the last user that pinged {role.mention}, no need to keep pinging, just ask in the RP planning and discuss.",
                ephemeral=True,
            )
            return False
        if hours((val := self.cool_down.get(interaction.user.id))) < 2:
            s = 7200 - seconds(val)
            await resp.send_message(
                "You're in cool down, you pinged one of the roles recently."
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return False
        if hours((val := self.role_cool_down.get(custom_id))) < 2:
            s = 7200 - seconds(val)
            await resp.send_message(
                f"{role.mention} is in cool down, check the latest ping at <#722617383738540092>."
                f"Or try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return False
        return True
