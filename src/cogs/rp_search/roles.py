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

from datetime import datetime
from time import mktime

from discord import (
    AllowedMentions,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    TextChannel,
)
from discord.ui import Button, View, button
from discord.utils import utcnow

from src.structures.bot import CustomBot
from src.structures.character import Character
from src.views.characters_view import CharactersView

__all__ = (
    "RoleView",
    "QUERIES",
)

RP_SEARCH_ROLES = dict(
    Any=744841294869823578,
    Plot=744841357960544316,
    Casual=744841408539656272,
    Action=744842759004880976,
    GameMaster=808730687753420821,
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
        self.ocs = set(ocs)
        self.member = member
        self.role_add.label = f"Get {role.name} Role"
        self.role_remove.label = f"Remove {role.name} Role"

    @button(emoji="\N{WHITE HEAVY CHECK MARK}", row=0, custom_id="role_add")
    async def role_add(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if self.role in member.roles:
            await resp.send_message("You already have the role", ephemeral=True)
            return
        await member.add_roles(self.role)
        await resp.send_message(
            "Role added, you'll get pinged next time.", ephemeral=True
        )

    @button(emoji="\N{CROSS MARK}", row=0, custom_id="role_remove")
    async def role_remove(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if self.role in member.roles:
            await member.remove_roles(self.role, reason="RP Search")
            await resp.send_message("Role removed successfully", ephemeral=True)
            return
        await resp.send_message("You don't have that role.", ephemeral=True)

    @button(
        label="Click here to view all the user's characters.",
        row=1,
        custom_id="check_ocs",
    )
    async def check_ocs(self, _: Button, ctx: Interaction):
        view = CharactersView(
            bot=self.bot,
            member=ctx.user,
            target=ctx,
            ocs=self.ocs,
        )
        embed = view.embed
        embed.set_author(name=self.member.display_name)
        embed.set_thumbnail(url=self.member.display_avatar.url)
        async with view.send(ephemeral=True, single=True) as data:
            if isinstance(data, Character):
                self.bot.logger.info(
                    "User %s is currently reading %s's character %s [%s]",
                    str(ctx.user),
                    str(self.member),
                    data.name,
                    repr(data),
                )


class RoleView(View):
    __slots__ = ("cool_down", "role_time", "bot")

    def __init__(
        self,
        bot: CustomBot,
        cool_down: dict[int, datetime],
        role_cool_down: dict[int, datetime],
    ):
        """Init Method
        Parameters
        ----------
        bot: CustomBot
            Bot
        cool_down: dict[int, datetime]
            cool down per user
        role_cool_down: dict[int, datetime]
            cool down per role
        """
        super().__init__(timeout=None)
        self.cool_down: dict[int, datetime] = cool_down
        self.role_cool_down: dict[int, datetime] = role_cool_down
        self.bot = bot

    async def process(self, btn: Button, ctx: Interaction):
        role: Role = ctx.guild.get_role(int(btn.custom_id))
        member: Member = ctx.user
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)

        if role not in member.roles:
            await member.add_roles(role, reason="RP searching")

        cog = self.bot.get_cog(name="Submission")
        channel: TextChannel = self.bot.get_channel(722617383738540092)

        characters = cog.rpers.get(member.id, {}).values()
        view = RoleManage(self.bot, role, characters, member)

        embed = Embed(
            title=role.name,
            color=ctx.user.color,
            description=f"{ctx.user.display_name} is looking "
            "to RP with their registered character(s).",
            timestamp=utcnow(),
        )
        embed.set_thumbnail(url=ctx.user.avatar.url)
        msg = await channel.send(
            content=f"{role.mention} is being pinged by {ctx.user.mention}",
            embed=embed,
            allowed_mentions=AllowedMentions(roles=True, users=True),
            view=view,
        )
        self.cool_down[member.id] = utcnow()
        self.role_cool_down[role.id] = utcnow()

        view = View()
        view.add_item(Button(label="Jump URL", url=msg.jump_url))

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

    @button(label="Any", custom_id="744841294869823578")
    async def rp_search_1(self, btn: Button, interaction: Interaction):
        await self.process(btn, interaction)

    @button(label="Plot", custom_id="744841357960544316")
    async def rp_search_2(self, btn: Button, interaction: Interaction):
        await self.process(btn, interaction)

    @button(label="Casual", custom_id="744841408539656272")
    async def rp_search_3(self, btn: Button, interaction: Interaction):
        await self.process(btn, interaction)

    @button(label="Action", custom_id="744842759004880976")
    async def rp_search_4(self, btn: Button, interaction: Interaction):
        await self.process(btn, interaction)

    @button(label="GameMaster", custom_id="808730687753420821")
    async def rp_search_5(self, btn: Button, interaction: Interaction):
        await self.process(btn, interaction)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if hours((val := self.cool_down.get(interaction.user.id))) < 2:
            s = 7200 - seconds(val)
            await resp.send_message(
                "You're in cool down, you pinged one of the roles recently."
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return False
        custom_id: int = int(interaction.data.get("custom_id"))
        if hours((val := self.role_cool_down.get(custom_id))) < 2:
            s = 7200 - seconds(val)
            await resp.send_message(
                f"<@&{custom_id}> is in cool down, check the latest ping at <#722617383738540092>."
                f"Or try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
            return False
        return True
