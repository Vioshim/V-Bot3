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
from abc import ABCMeta, abstractmethod
from collections import OrderedDict
from datetime import datetime
from difflib import get_close_matches
from logging import getLogger, setLoggerClass
from time import mktime
from typing import Iterable, Optional

from discord import (
    AllowedMentions,
    ButtonStyle,
    CategoryChannel,
    Color,
    Embed,
    File,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    TextStyle,
    Webhook,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import get, utcnow

from src.cogs.roles.area_selection import AreaSelection
from src.structures.character import Character
from src.structures.logger import ColoredLogger
from src.utils.etc import MAP_ELEMENTS, MAP_ELEMENTS2, SETTING_EMOJI, WHITE_BAR, MapPair
from src.utils.imagekit import Fonts, ImageKit
from src.views.characters_view import CharactersView

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


__all__ = (
    "PronounRoles",
    "BasicRoles",
    "ColorRoles",
    "RPSearchRoles",
    "RPSearchManage",
    "RPRolesView",
)


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


RP_SEARCH_ROLES = dict(
    Any=962719564167254077,
    Plot=962719564863508510,
    Action=962719565182271590,
    Narrated=962719566402813992,
    Romance=962719567149408256,
    Drama=962719567694659604,
    Literate=962719568172814368,
    Horror=962719570148331560,
)


class RoleSelect(View, metaclass=ABCMeta):
    @abstractmethod
    async def choice(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        guild = ctx.guild

        def get_role(items: Iterable):
            for x in items:
                if isinstance(x, SelectOption):
                    x = x.value
                if role := guild.get_role(int(x)):
                    yield role

        roles = set(get_role(sct.values))
        total = set(get_role(sct.options))

        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(
            title=sct.placeholder.removeprefix("Select "),
            color=Color.blurple(),
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        if add := set(roles) - set(member.roles):
            embed.add_field(
                name="**__Roles Added__**",
                value="\n".join(f"> • {role.mention}" for role in add),
                inline=False,
            )
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            embed.add_field(
                name="**__Roles Removed__**",
                value="\n".join(f"> • {role.mention}" for role in remove),
                inline=False,
            )
            await member.remove_roles(*remove)

        await ctx.followup.send(embed=embed, ephemeral=True)


class PronounRoles(RoleSelect):
    @select(
        placeholder="Select Pronoun Roles",
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
    async def choice(self, ctx: Interaction, sct: Select):
        await super(PronounRoles, self).choice(ctx, sct)


class ColorRoles(RoleSelect):
    @select(
        placeholder="Select Color Roles",
        custom_id="colors",
        options=[
            SelectOption(
                label="Red",
                value="794274172813312000",
                emoji=":red:952523311395528728",
            ),
            SelectOption(
                label="Crimson",
                value="794274956296847370",
                emoji=":crimson:952523311680745492",
            ),
            SelectOption(
                label="Orange",
                value="794275894209282109",
                emoji=":orange:952523311756218428",
            ),
            SelectOption(
                label="Golden",
                emoji=":golden:952523311429074966",
                value="794275428696064061",
            ),
            SelectOption(
                label="Yellow",
                emoji=":yellow:952523311697494086",
                value="794274424777080884",
            ),
            SelectOption(
                label="Green",
                emoji=":green:952523311890452520",
                value="794274561570504765",
            ),
            SelectOption(
                label="Lime",
                emoji=":lime:952523311865270302",
                value="794276035326902342",
            ),
            SelectOption(
                label="Cyan",
                emoji=":cyan:952523311735255100",
                value="794276172762185799",
            ),
            SelectOption(
                label="Light Blue",
                emoji=":light_blue:952523313794670622",
                value="794274301707812885",
            ),
            SelectOption(
                label="Deep Blue",
                emoji=":deep_blue:952523311680725013",
                value="794275553477394475",
            ),
            SelectOption(
                label="Violet",
                emoji=":violet:952523311743660052",
                value="794275765533278208",
            ),
            SelectOption(
                label="Pink",
                emoji=":pink:952523311743635486",
                value="794274741061025842",
            ),
            SelectOption(
                label="Light Brown",
                emoji=":light_brown:952523311764627536",
                value="794275107958292500",
            ),
            SelectOption(
                label="Dark Brown",
                emoji=":dark_brown:952523311642972200",
                value="794275288271028275",
            ),
            SelectOption(
                label="Silver",
                emoji=":silver:952523311680745532",
                value="850018780762472468",
            ),
            SelectOption(
                label="Gray",
                emoji=":gray:952523311714295898",
                value="794273806176223303",
            ),
        ],
        min_values=0,
    )
    async def choice(self, ctx: Interaction, sct: Select):
        await super(ColorRoles, self).choice(ctx, sct)


class BasicRoles(RoleSelect):
    @select(
        placeholder="Select Basic Roles",
        custom_id="basic",
        min_values=0,
        max_values=2,
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
    async def choice(self, ctx: Interaction, sct: Select):
        await super(BasicRoles, self).choice(ctx, sct)


class RPSearchRoles(RoleSelect):
    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        role = get(interaction.guild.roles, name="Registered")
        if role and role not in member.roles:
            view = View()
            view.add_item(
                Button(
                    label="OC Submissions",
                    url="https://discord.com/channels/719343092963999804/852180971985043466/961345742222536744",
                    emoji="\N{OPEN BOOK}",
                )
            )

            await resp.send_message(
                "In order to use this function, you have to make a character.",
                view=view,
                ephemeral=True,
            )
            return False
        return True

    @select(
        placeholder="Select RP Search Roles",
        custom_id="rp-search",
        min_values=0,
        max_values=len(RP_SEARCH_ROLES),
        options=[
            SelectOption(
                label=f"{key} RP Search",
                emoji="💠",
                value=str(item),
                description=f"Enables {key} RP search ping notifications.",
            )
            for key, item in RP_SEARCH_ROLES.items()
        ],
    )
    async def choice(self, ctx: Interaction, sct: Select):
        await super(RPSearchRoles, self).choice(ctx, sct)


class RegionView(View):
    def __init__(self, info: MapPair):
        super(RegionView, self).__init__(timeout=None)
        self.info = info
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
        await resp.edit_message(view=self)
        if spectator in ctx.user.roles:
            await ctx.user.remove_roles(spectator)
        if btn.label == "Obtain Access":
            await ctx.user.add_roles(role)
            word = "Enabling"
        else:
            await ctx.user.remove_roles(role)
            word = "Disabling"
        ctx.client.logger.info(
            "%s reading permissions for %s at %s",
            word,
            str(ctx.user),
            role.name,
        )

    @button(label="Obtain Access", custom_id="unlock")
    async def unlock(self, ctx: Interaction, btn: Button) -> None:
        await self.perms_setter(ctx, btn)

    @button(label="Remove Access", custom_id="lock")
    async def lock(self, ctx: Interaction, btn: Button) -> None:
        await self.perms_setter(ctx, btn)

    @button(label="More Information", custom_id="read")
    async def read(self, ctx: Interaction, _: Button) -> None:
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
        logger.info(
            "%s is reading Map Information of %s",
            str(ctx.user),
            category.name,
        )
        view = AreaSelection(bot=ctx.client, cat=category, member=ctx.user)
        await resp.send_message(
            content=f"There's a total of {view.total:02d} OCs in {category.name}.",
            view=view,
            ephemeral=True,
        )


class RegionRoles(RoleSelect):
    @select(
        placeholder="Select Map Roles",
        custom_id="region",
        row=0,
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
    async def choice(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        all_roles = {role for x in MAP_ELEMENTS if (role := ctx.guild.get_role(x.role))}
        spectator: Role = ctx.guild.get_role(957069729741287434)
        if len(sct.values) == 1:
            info = MAP_ELEMENTS2[int(sct.values[0])]
            view = RegionView(info=info)
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
            role for x in map(int, sct.values) if (role := ctx.guild.get_role(MAP_ELEMENTS2[x].role))
        }:
            if all_roles != choosen_roles:
                if removed_roles := (all_roles - choosen_roles) | {spectator}:
                    await ctx.user.remove_roles(*removed_roles)
                await ctx.user.add_roles(*choosen_roles)
            else:
                await ctx.user.remove_roles(*all_roles)
                if spectator not in ctx.user.roles:
                    await ctx.user.add_roles(spectator)
        else:
            all_roles.add(spectator)
            await ctx.user.remove_roles(*all_roles)

        if not resp.is_done():
            await ctx.followup.send("Roles have been set", ephemeral=True)

    @button(label="Obtain all Map Roles", custom_id="region-all", row=1)
    async def region_all(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        spectator = ctx.guild.get_role(957069729741287434)
        if roles := [
            role for role in map(lambda x: ctx.guild.get_role(x.role), MAP_ELEMENTS) if role in ctx.user.roles
        ]:
            await ctx.user.remove_roles(*roles)
        if spectator in ctx.user.roles:
            await ctx.followup.send("You already have the Spectator role.", ephemeral=True)
        else:
            await ctx.user.add_roles(spectator)
            await ctx.followup.send("Roles added.", ephemeral=True)

    @button(label="Remove all Map Roles", custom_id="region-none", row=1)
    async def region_none(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        spectator = ctx.guild.get_role(957069729741287434)
        if roles := [
            role for role in map(lambda x: ctx.guild.get_role(x.role), MAP_ELEMENTS) if role in ctx.user.roles
        ]:
            await ctx.user.remove_roles(*roles)
        if spectator in ctx.user.roles:
            await ctx.user.remove_roles(spectator)
        await ctx.followup.send("Roles removed.", ephemeral=True)


class RPSearchManage(View):
    def __init__(
        self,
        member_id: int | Member,
        ocs: set[int | Character] = None,
    ):
        super(RPSearchManage, self).__init__(timeout=None)
        if not isinstance(member_id, int):
            member_id = member_id.id
        self.member_id = member_id
        self.ocs = ocs

    @button(
        label="Click to Read User's OCs.",
        row=1,
        custom_id="check_ocs",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
    )
    async def check_ocs(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        cog = ctx.client.get_cog("Submission")
        if not self.ocs or not (ocs := [x for item in self.ocs if isinstance(x := cog.ocs.get(item, item), Character)]):
            ocs: list[Character] = [oc for oc in cog.ocs.values() if oc.author == self.member_id]
        view = CharactersView(
            member=ctx.user,
            target=ctx,
            ocs=ocs,
            keep_working=True,
        )
        embed = view.embed
        if member := ctx.guild.get_member(self.member_id) or ctx.client.get_user(self.member_id):
            embed.set_author(
                name=member.display_name,
                icon_url=member.display_avatar.url,
            )
        else:
            member = f"User(ID={self.member_id})"
        async with view.send(ephemeral=True, single=True) as data:
            if isinstance(data, Character):
                logger.info(
                    "User %s is currently reading %s's character %s [%s]",
                    str(ctx.user),
                    str(member),
                    data.name,
                    repr(data),
                )


class RPModal(Modal):
    def __init__(
        self,
        user: Member,
        role: Role,
        ocs: set[Character],
        to_user: Optional[Member] = None,
    ) -> None:
        super().__init__(title=f"Pinging {role.name}")
        self.user = user
        self.role = role
        self.ocs = ocs
        self.to_user = to_user
        text = "\n".join(f"- {x.species.name} | {x.name}" for x in ocs)
        if len(text) > 4000:
            text = "\n".join(f"- {x.name}" for x in ocs)
        self.names = TextInput(
            style=TextStyle.paragraph,
            label="Characters you have free (Will show in order)",
            placeholder="Character names go here separated by commas, if empty, all ocs will be used.",
            required=False,
            default=text,
        )
        self.message = TextInput(
            style=TextStyle.paragraph,
            label="Message",
            placeholder=f"Describe what you're looking for in this {self.role.name} (Optional)",
            default=f"{user.display_name} is looking to RP with their registered characters.",
            required=False,
        )
        self.add_item(self.names)
        self.add_item(self.message)

    async def on_submit(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        info = {x.name.title(): x for x in self.ocs}
        data = self.names.value or ""
        items: list[Character] = []
        for item in data.split("\n"):
            item = item.removeprefix("-").strip().title()
            item = item.split("|")[-1].strip()
            if oc := info.get(item):
                items.append(oc)
            elif elements := get_close_matches(item, info, n=1, cutoff=0.85):
                items.append(info[elements[0]])
        member: Member = interaction.user
        embed = Embed(
            title=self.role.name,
            color=member.color,
            description=self.message.value,
        )
        guild: Guild = member.guild
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        items = list(OrderedDict.fromkeys(items))
        kit = ImageKit(base="OC_list_9a1DZPDet.png", width=1500, height=1000)
        for index, oc in enumerate(items[:6]):
            x = 500 * (index % 3) + 25
            y = 500 * int(index / 3) + 25
            kit.add_image(image=oc.image_url, height=450, width=450, x=x, y=y)
            for index, item in enumerate(oc.types):
                kit.add_image(image=item.icon, width=200, height=44, x=250 + x, y=y + 44 * index)
            kit.add_text(
                text=oc.name,
                width=330,
                x=x,
                y=y + 400,
                background=0xFFFFFF,
                background_transparency=70,
                font=Fonts.Whitney_Black,
                font_size=36,
            )
            if oc.pronoun.image:
                kit.add_image(image=oc.pronoun.image, height=120, width=120, x=x + 325, y=y + 325)
        file: File = await interaction.client.get_file(kit.url)
        embed.set_image(url=f"attachment://{file.filename}")
        reference = self.role
        channel = 958122815171756042
        name = f"{self.role.name} - {self.user.display_name}"
        if self.to_user:
            channel = 740568087820238919
            reference = self.to_user
            name += f" - {self.to_user.display_name}"
        elif self.role not in self.user.roles:
            await self.user.add_roles(self.role)

        webhook: Webhook = await interaction.client.webhook(channel, reason="RP Search")
        embed.set_image(url="attachment://image.png")

        kwargs = dict(
            content=reference.mention,
            allowed_mentions=AllowedMentions(roles=True, users=True),
            embed=embed,
            view=RPSearchManage(member, items),
            username=member.display_name,
            avatar_url=member.display_avatar.url,
            file=file,
        )
        msg1 = await webhook.send(wait=True, **kwargs)
        thread = await msg1.create_thread(name=name)
        kwargs["thread"] = thread
        del kwargs["content"]
        embed.set_image(url=WHITE_BAR)
        msg2 = await webhook.send(wait=True, **kwargs)
        await thread.add_user(self.user)
        cog0 = interaction.client.get_cog("Submission")
        cog1 = interaction.client.get_cog("Roles")
        cog1.cool_down[reference.id] = utcnow()
        cog1.role_cool_down[reference.id] = utcnow()
        cog1.last_claimer[reference.id] = member.id
        ocs = [oc for oc in cog0.ocs.values() if oc.author == member.id]
        ocs = [] if len(ocs) == self.ocs else [oc.id for oc in self.ocs]
        async with interaction.client.database() as db:
            await db.execute(
                """
                INSERT INTO RP_SEARCH(ID, MEMBER, ROLE, SERVER, MESSAGE, OCS)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                msg1.id,
                member.id,
                reference.id,
                member.guild.id,
                msg2.id,
                ocs,
            )
            await interaction.followup.send(
                content="Ping has been done successfully.",
                ephemeral=True,
            )


class RPRolesView(View):
    @select(
        placeholder="Select a role to Ping",
        custom_id="rp-view",
        options=[
            SelectOption(
                label=f"{key} RP Search",
                emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
                value=str(item),
                description=f"Pings {key} RP search.",
            )
            for key, item in RP_SEARCH_ROLES.items()
        ],
    )
    async def choice(self, interaction: Interaction, sct: Select):
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        cog = interaction.client.get_cog("Roles")
        role: Role = interaction.guild.get_role(int(sct.values[0]))
        if cog.last_claimer.get(role.id) == member.id:
            return await resp.send_message(
                "You're the last user that pinged this role, no need to keep pinging, just ask in the RP planning and discuss.",
                ephemeral=True,
            )
        if hours((val := cog.cool_down.get(member.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                "You're in cool down, you pinged one of the roles recently.\n"
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        if hours((val := cog.role_cool_down.get(role.id))) < 2:
            s = 7200 - seconds(val)
            return await resp.send_message(
                "Thread is in cool down, check the ping at <#958122815171756042>.\n"
                f"Try again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds",
                ephemeral=True,
            )
        cog = interaction.client.get_cog("Submission")
        ocs = [oc for oc in cog.ocs.values() if oc.author == member.id]
        await resp.send_modal(
            RPModal(
                user=member,
                role=role,
                ocs=ocs,
            )
        )
