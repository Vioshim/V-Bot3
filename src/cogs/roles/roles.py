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
from difflib import get_close_matches
from time import mktime
from typing import Optional

from discord import (
    AllowedMentions,
    ButtonStyle,
    CategoryChannel,
    Embed,
    Guild,
    InputTextStyle,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    Thread,
    WebhookMessage,
)
from discord.ui import Button, InputText, Modal, Select, View, button, select
from discord.utils import utcnow

from src.cogs.roles.area_selection import AreaSelection
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import MAP_ELEMENTS, MAP_ELEMENTS2, WHITE_BAR, MapPair
from src.views.characters_view import CharactersView

__all__ = (
    "PronounRoles",
    "BasicRoles",
    "ColorRoles",
    "RPThreadView",
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
                emoji=None,
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
        emoji=":red:952523311395528728",
        custom_id="794274172813312000",
        row=0,
    ),
    ColorButton(
        emoji=":crimson:952523311680745492",
        custom_id="794274956296847370",
        row=0,
    ),
    ColorButton(
        emoji=":orange:952523311756218428",
        custom_id="794275894209282109",
        row=0,
    ),
    ColorButton(
        emoji=":golden:952523311429074966",
        custom_id="794275428696064061",
        row=0,
    ),
    ColorButton(
        emoji=":yellow:952523311697494086",
        custom_id="794274424777080884",
        row=1,
    ),
    ColorButton(
        emoji=":green:952523311890452520",
        custom_id="794274561570504765",
        row=1,
    ),
    ColorButton(
        emoji=":lime:952523311865270302",
        custom_id="794276035326902342",
        row=1,
    ),
    ColorButton(
        emoji=":cyan:952523311735255100",
        custom_id="794276172762185799",
        row=1,
    ),
    ColorButton(
        emoji=":light_blue:952523313794670622",
        custom_id="794274301707812885",
        row=2,
    ),
    ColorButton(
        emoji=":deep_blue:952523311680725013",
        custom_id="794275553477394475",
        row=2,
    ),
    ColorButton(
        emoji=":violet:952523311743660052",
        custom_id="794275765533278208",
        row=2,
    ),
    ColorButton(
        emoji=":pink:952523311743635486",
        custom_id="794274741061025842",
        row=2,
    ),
    ColorButton(
        emoji=":light_brown:952523311764627536",
        custom_id="794275107958292500",
        row=3,
    ),
    ColorButton(
        emoji=":dark_brown:952523311642972200",
        custom_id="794275288271028275",
        row=3,
    ),
    ColorButton(
        emoji=":silver:952523311680745532",
        custom_id="850018780762472468",
        row=3,
    ),
    ColorButton(
        emoji=":gray:952523311714295898",
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
        max_values=2,
        custom_id="62a0a35098d0666728712d4f05a140d1",
        options=[
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


class RegionView(View):
    def __init__(self, bot: CustomBot, info: MapPair, ctx: Interaction):
        super(RegionView, self).__init__(timeout=None)
        self.bot = bot
        self.info = info
        self.ctx = ctx
        self.unlock.custom_id = f"unlock-{info.category}"
        self.lock.custom_id = f"lock-{info.category}"
        self.read.custom_id = f"read-{info.category}"

    async def perms_setter(self, ctx: Interaction, btn: Button) -> None:
        """Enable/Disable reading permissions

        Parameters
        ----------
        ctx : Interaction
            interaction
        btn : Button
            button
        """
        resp: InteractionResponse = ctx.response
        role: Role = ctx.guild.get_role(self.info.role)
        btn.disabled = True
        spectator = ctx.guild.get_role(957069729741287434)
        await resp.pong()
        await self.ctx.edit_original_message(view=self)
        if spectator in ctx.user.roles:
            await ctx.user.remove_roles(spectator)
        if btn.label == "Obtain Access":
            await ctx.user.add_roles(role)
            word = "Enabling"
        else:
            await ctx.user.remove_roles(role)
            word = "Disabling"
        self.bot.logger.info(
            "%s reading permissions for %s at %s",
            word,
            str(ctx.user),
            role.name,
        )

    @button(label="Obtain Access", custom_id="unlock")
    async def unlock(self, btn: Button, ctx: Interaction) -> None:
        await self.perms_setter(ctx, btn)

    @button(label="Remove Access", custom_id="lock")
    async def lock(self, btn: Button, ctx: Interaction) -> None:
        await self.perms_setter(ctx, btn)

    @button(label="More Information", custom_id="read")
    async def read(self, _: Button, ctx: Interaction) -> None:
        """Read Information

        Parameters
        ----------
        btn : Button
            button
        ctx : Interaction
            interaction
        """
        category: CategoryChannel = ctx.guild.get_channel(self.info.category)
        resp: InteractionResponse = ctx.response
        self.bot.logger.info(
            "%s is reading Map Information of %s",
            str(ctx.user),
            category.name,
        )
        await resp.pong()
        view = AreaSelection(bot=self.bot, cat=category, member=ctx.user)
        await self.ctx.edit_original_message(
            content=f"There's a total of {view.total:02d} OCs in {category.name}.",
            view=view,
        )


class RegionRoles(View):
    def __init__(self, bot: CustomBot):
        super().__init__(timeout=None)
        self.bot = bot

    @select(
        placeholder="Select Map Roles",
        custom_id="region",
        row=0,
        min_values=0,
        max_values=len(MAP_ELEMENTS),
        options=[
            SelectOption(
                label=item.name,
                description=(item.short_desc or item.desc)[:100],
                value=item.category,
                emoji=item.emoji,
            )
            for item in MAP_ELEMENTS
        ],
    )
    async def region(self, sct: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        all_roles = {
            role for x in MAP_ELEMENTS if (role := ctx.guild.get_role(x.role))
        }
        spectator: Role = ctx.guild.get_role(957069729741287434)
        if len(sct.values) == 1:
            info = MAP_ELEMENTS2[int(sct.values[0])]
            view = RegionView(bot=self.bot, info=info, ctx=ctx)
            role: Role = ctx.guild.get_role(info.role)
            view.unlock.disabled = role in ctx.user.roles
            view.lock.disabled = role not in ctx.user.roles
            embed = Embed(
                title=info.name,
                description=info.desc,
                timestamp=utcnow(),
                color=ctx.user.color,
            )
            embed.set_image(url=info.image or WHITE_BAR)
            if icon := ctx.guild.icon:
                embed.set_footer(
                    text=ctx.guild.name,
                    icon_url=icon.url,
                )
            else:
                embed.set_footer(
                    text=ctx.guild.name,
                )
            await ctx.followup.send(
                view=view,
                embed=embed,
                ephemeral=True,
            )
        elif choosen_roles := {
            role
            for x in map(int, sct.values)
            if (role := ctx.guild.get_role(MAP_ELEMENTS2[x].role))
        }:
            if all_roles != choosen_roles:
                if removed_roles := (all_roles - choosen_roles) | {spectator}:
                    await ctx.user.remove_roles(*removed_roles)
                await ctx.user.add_roles(*choosen_roles)
            else:
                await ctx.user.remove_roles(*all_roles)
                if spectator not in ctx.user.roles:
                    await ctx.user.add_roles(spectator)
            await ctx.followup.send("Roles have been set", ephemeral=True)
        else:
            all_roles.add(spectator)
            await ctx.user.remove_roles(*all_roles)
            await ctx.followup.send("Roles have been set", ephemeral=True)

    @button(label="Obtain all Map Roles", custom_id="region-all", row=1)
    async def region_all(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        spectator = ctx.guild.get_role(957069729741287434)
        if roles := [
            role
            for role in map(lambda x: ctx.guild.get_role(x.role), MAP_ELEMENTS)
            if role in ctx.user.roles
        ]:
            await ctx.user.remove_roles(*roles)
        if spectator in ctx.user.roles:
            await ctx.followup.send(
                "You already have the Spectator role.", ephemeral=True
            )
        else:
            await ctx.user.add_roles(spectator)
            await ctx.followup.send("Roles added.", ephemeral=True)

    @button(label="Remove all Map Roles", custom_id="region-none", row=1)
    async def region_none(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        spectator = ctx.guild.get_role(957069729741287434)
        if roles := [
            role
            for role in map(lambda x: ctx.guild.get_role(x.role), MAP_ELEMENTS)
            if role in ctx.user.roles
        ]:
            await ctx.user.remove_roles(*roles)
        if spectator in ctx.user.roles:
            await ctx.user.remove_roles(spectator)
        await ctx.followup.send("Roles removed.", ephemeral=True)


class RPThreadManage(View):
    def __init__(
        self,
        bot: CustomBot,
        thread: Thread,
        member: Member,
        ocs: set[Character] = None,
    ):
        super(RPThreadManage, self).__init__(timeout=None)
        self.bot = bot
        self.thread = thread
        self.member = member
        self.ocs = ocs

    @button(
        label="Click here to view all the user's characters.",
        row=1,
        custom_id="check_ocs",
    )
    async def check_ocs(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        cog = self.bot.get_cog("Submission")
        if not (ocs := self.ocs):
            ocs = cog.rpers.get(self.member.id, {}).values()
        view = CharactersView(
            bot=self.bot,
            member=ctx.user,
            target=ctx,
            ocs=ocs,
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


class RPModal(Modal):

    def __init__(
        self,
        bot: CustomBot,
        cool_down: dict[int, datetime],
        role_cool_down: dict[int, datetime],
        last_claimer: dict[int, int],
        thread: Thread,
        ocs: set[Character]
    ) -> None:
        super().__init__(title="Pinging a RP Search")
        self.bot = bot
        self.cool_down = cool_down
        self.role_cool_down = role_cool_down
        self.last_claimer = last_claimer
        self.thread = thread
        self.ocs = ocs
        if len(text := "\n".join(f"- {x.species.name} | {x.name}" for x in ocs)) > 4000:
            text = "\n".join(f"- {x.name}" for x in ocs)
        self.add_item(
            InputText(
                style=InputTextStyle.paragraph,
                label="Characters you have free (Will show in order)",
                placeholder="Character names go here separated by commas, if empty, all ocs will be used.",
                required=False,
                value=text,
            )
        )

    async def callback(self, interaction: Interaction):
        info = {x.name.title(): x for x in self.ocs}
        data = self.children[0].value or ""
        items: list[Character] = []
        for item in data.split("\n"):
            item = item.removeprefix("-").strip().title()
            item = item.split("|")[-1].strip()
            if oc := info.get(item):
                items.append(oc)
            elif elements := get_close_matches(item, info, n=1):
                items.append(elements[0])
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        embed = Embed(title=self.thread.name, color=member.color)
        guild: Guild = member.guild
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        webhook = await self.bot.webhook(910914713234325504, reason="RP Search")
        msg: WebhookMessage = await webhook.send(
            content="@here",
            allowed_mentions=AllowedMentions(everyone=True),
            embed=embed,
            view=RPThreadManage(self.bot, self.thread, member, items),
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            wait=True,
            thread=self.thread,
        )
        self.cool_down[member.id] = utcnow()
        self.role_cool_down[self.thread.id] = utcnow()
        self.last_claimer[self.thread.id] = member.id
        async with self.bot.database() as db:
            await db.execute(
                "INSERT INTO RP_SEARCH(ID, MEMBER, ROLE, SERVER) VALUES ($1, $2, $3, $4)",
                msg.id,
                member.id,
                self.thread.id,
                member.guild.id,
            )
            await resp.send_message(
                content="Ping has been done successfully.",
                ephemeral=True,
            )


class RPThreadView(View):
    def __init__(
        self,
        bot: CustomBot,
        cool_down: dict[int, datetime],
        role_cool_down: dict[int, datetime],
        last_claimer: dict[int, int],
        thread: Thread,
    ):
        super(RPThreadView, self).__init__(timeout=None)
        self.bot = bot
        self.cool_down = cool_down
        self.role_cool_down = role_cool_down
        self.last_claimer = last_claimer
        self.thread = thread

    @button(
        label="Ping Role",
        custom_id="ping-role",
        emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def ping(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if self.last_claimer.get(self.thread.id) == member.id:
            return await resp.send_message(
                "You're the last user that pinged this thread, no need to keep pinging, just ask in the RP planning and discuss.",
                ephemeral=True,
            )
        if hours((val := self.cool_down.get(member.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                "You're in cool down, you pinged one of the threads recently."
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        if hours((val := self.role_cool_down.get(self.thread.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                f"Thread is in cool down, check the latest thread at <#{self.thread.id}>."
                f"Or try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        await resp.send_modal(
            RPModal(
                bot=self.bot,
                cool_down=self.cool_down,
                role_cool_down=self.role_cool_down,
            )
        )

    @button(
        label="Enable Pings",
        custom_id="obtain-role",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def get_role(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await self.thread.add_user(interaction.user)
        await resp.send_message("Access granted.", ephemeral=True)

    @button(
        label="Disable Pings",
        custom_id="remove-role",
        style=ButtonStyle.blurple,
        row=0,
    )
    async def remove_role(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await self.thread.remove_user(interaction.user)
        await resp.send_message("Access removed.", ephemeral=True)
