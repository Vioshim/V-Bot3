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

from datetime import datetime, timedelta
from logging import getLogger, setLoggerClass
from time import mktime
from typing import Iterable, Optional

from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
    DiscordException,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    PartialMessage,
    Role,
    SelectOption,
    TextStyle,
    Thread,
    Webhook,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import get, time_snowflake, utcnow
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.pagination.complex import Complex
from src.structures.character import Character
from src.structures.logger import ColoredLogger
from src.utils.etc import MOBILE_EMOJI, SETTING_EMOJI, WHITE_BAR
from src.utils.functions import chunks_split
from src.views.characters_view import CharactersView

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


__all__ = (
    "RoleSelect",
    "RPSearchManage",
    "RPRolesView",
    "hours",
    "seconds",
)

INTERVAL = timedelta(hours=12)
RP_SEARCH_EMBED = (
    Embed(
        description="This is the section where RP Search roles get pinged, and don't worry even if you don't have the role, it will get assigned to you when you use the options",
        color=Color.blurple(),
    )
    .add_field(
        name="Recommendations",
        value="In order to get the most out of this, when you make a ping, try to write in the message what you're looking for. From defining the OCs you'd like to use, to simply stating the kind of RP that you're looking for.\n\nKeep in mind as well that the idea of this channel is to help you find a RP, but you can try to find RPs naturally by interacting with people within the RP itself.",
        inline=False,
    )
    .add_field(
        name="Note",
        value="If you're experiencing bugs, use the Mobile version.",
        inline=False,
    )
    .set_image(url=WHITE_BAR)
)


def hours(test: datetime) -> int:
    """A function which returns the time between a date and today

    Parameters
    ----------
    test: datetime
        Time

    Returns
    -------
    Time in between
    """
    today = utcnow()
    data = mktime(today.timetuple()) - mktime(test.timetuple())
    return int(data // 3600)


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
    Any=("Useful for finding Any kind of RP", 962719564167254077),
    Plot=("If you need a hand with an Arc or plot.", 962719564863508510),
    Action=("Encounters that involve action such as battles, thievery, etc.", 962719565182271590),
    Narrated=("Narrate for others or get narrated.", 962719566402813992),
    Romance=("Useful for long term planned ships, not instantaneous.", 962719567149408256),
    Drama=("RPs that present a problem for OCs to solve.", 962719567694659604),
    Literate=("Be descriptive and detailed as possible", 962719568172814368),
    Horror=("Scary or mysterious RPs for OCs", 962719570148331560),
)


def get_role(items: Iterable, guild: Guild):
    for x in items:
        if isinstance(x, SelectOption):
            x = x.value
        if role := guild.get_role(int(x)):
            yield role


class RoleSelect(View):
    async def choice(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        guild = ctx.guild

        roles: set[Role] = set(get_role(sct.values, guild))
        total: set[Role] = set(get_role(sct.options, guild))

        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(
            title=sct.placeholder.removeprefix("Select "),
            color=Color.blurple(),
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        if add := set(roles) - set(member.roles):
            text = "\n".join(f"> • {role.mention}" for role in add)
            embed.add_field(name="**__Roles Added__**", value=text, inline=False)
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            text = "\n".join(f"> • {role.mention}" for role in remove)
            embed.add_field(name="**__Roles Removed__**", value=text, inline=False)
            await member.remove_roles(*remove)

        await ctx.followup.send(embed=embed, ephemeral=True)

    @select(
        placeholder="Select Pronoun Roles",
        custom_id="pronouns",
        min_values=0,
        max_values=3,
        options=[
            SelectOption(label="He", value="738230651840626708", emoji="\N{MALE SIGN}"),
            SelectOption(label="She", value="738230653916807199", emoji="\N{FEMALE SIGN}"),
            SelectOption(label="Them", value="874721683381030973", emoji=None),
        ],
    )
    async def pronouns_choice(self, ctx: Interaction, sct: Select):
        await self.choice(ctx, sct)

    @select(
        placeholder="Select Color Roles",
        custom_id="colors",
        options=[
            SelectOption(label="Red", emoji=":red:952523311395528728", value="794274172813312000"),
            SelectOption(label="Crimson", emoji=":crimson:952523311680745492", value="794274956296847370"),
            SelectOption(label="Orange", emoji=":orange:952523311756218428", value="794275894209282109"),
            SelectOption(label="Golden", emoji=":golden:952523311429074966", value="794275428696064061"),
            SelectOption(label="Yellow", emoji=":yellow:952523311697494086", value="794274424777080884"),
            SelectOption(label="Green", emoji=":green:952523311890452520", value="794274561570504765"),
            SelectOption(label="Lime", emoji=":lime:952523311865270302", value="794276035326902342"),
            SelectOption(label="Cyan", emoji=":cyan:952523311735255100", value="794276172762185799"),
            SelectOption(label="Light Blue", emoji=":light_blue:952523313794670622", value="794274301707812885"),
            SelectOption(label="Deep Blue", emoji=":deep_blue:952523311680725013", value="794275553477394475"),
            SelectOption(label="Violet", emoji=":violet:952523311743660052", value="794275765533278208"),
            SelectOption(label="Pink", emoji=":pink:952523311743635486", value="794274741061025842"),
            SelectOption(label="Light Brown", emoji=":light_brown:952523311764627536", value="794275107958292500"),
            SelectOption(label="Dark Brown", emoji=":dark_brown:952523311642972200", value="794275288271028275"),
            SelectOption(label="Silver", emoji=":silver:952523311680745532", value="850018780762472468"),
            SelectOption(label="Gray", emoji=":gray:952523311714295898", value="794273806176223303"),
        ],
        min_values=0,
    )
    async def colors_choice(self, ctx: Interaction, sct: Select):
        await self.choice(ctx, sct)

    @select(
        placeholder="Select Basic Roles",
        custom_id="basic",
        min_values=0,
        max_values=4,
        options=[
            SelectOption(
                label="Radio",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="805878418225889280",
                description="Get pinged each time Reshy streams in radio.",
            ),
            SelectOption(
                label="Announcements",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="908809235012419595",
                description="Get pinged during announcements.",
            ),
            SelectOption(
                label="MysteryCord",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="974410022845038673",
                description="Gives access to PMDiscord's category.",
            ),
            SelectOption(
                label="Art Fight",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="998937033068253309",
                description="Enables PVP ON (Art Fight wise)",
            ),
            SelectOption(
                label="Bump Reminder",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="1008443862559240312",
                description="Reminds you to bump the server",
            ),
        ],
    )
    async def basic_choice(self, ctx: Interaction, sct: Select):
        await self.choice(ctx, sct)

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
                description=desc,
            )
            for key, (desc, item) in RP_SEARCH_ROLES.items()
        ],
    )
    async def rp_search_choice(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        role = get(ctx.guild.roles, name="Registered")
        if role and role not in member.roles:
            view = View()
            view.add_item(
                Button(
                    label="OC Submissions",
                    url="https://canary.discord.com/channels/719343092963999804/852180971985043466/1005387453055639612",
                    emoji="\N{OPEN BOOK}",
                )
            )
            await resp.send_message(
                f"In order to use this function, you need to have {role.mention}",
                view=view,
                ephemeral=True,
            )
        else:
            await self.choice(ctx, sct)


class RPSearchManage(View):
    def __init__(self, member_id: int | Member, ocs: set[int | Character] = None):
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
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        cog = ctx.client.get_cog("Submission")
        if not (ocs := [x for item in self.ocs if isinstance(x := cog.ocs.get(item, item), Character)]):
            ocs: list[Character] = [oc for oc in cog.ocs.values() if oc.author == self.member_id]
        view = CharactersView(member=ctx.user, target=ctx, ocs=ocs, keep_working=True)
        embed = view.embed
        if member := ctx.guild.get_member(self.member_id) or ctx.client.get_user(self.member_id):
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
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


def time_message(msg: str, s: int):
    return f"{msg}\nTry again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds"


class RPModal(Modal):
    def __init__(
        self,
        user: Member,
        role: Role,
        ocs: set[Character],
        to_user: Optional[Member] = None,
        mobile: bool = False,
    ) -> None:
        super(RPModal, self).__init__(title=f"Pinging {role.name}")
        self.user = user
        self.role = role
        self.ocs = ocs
        self.to_user = to_user

        self.names = TextInput(
            style=TextStyle.paragraph,
            label="Characters you have free (Will show in order)",
            placeholder="Character names go here separated by commas, if empty, all ocs will be used.",
            required=False,
        )
        self.message = TextInput(
            style=TextStyle.paragraph,
            label="Message",
            placeholder=f"Describe what you're looking for in this {self.role.name} (Optional)",
            default=f"{user.display_name} is looking to RP with their registered characters.",
            required=False,
        )
        if isinstance(to_user, Member):
            self.message.default = self.message.default.replace("their", f"{to_user.display_name}'s ")
        self.add_item(self.message)

        self.select_ocs1 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs2 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs3 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs4 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs_group = self.select_ocs1, self.select_ocs2, self.select_ocs3, self.select_ocs4

        if mobile:
            text = "\n".join(f"- {x.species.name} | {x.name}" for x in ocs)
            if len(text) > 4000:
                text = "\n".join(f"- {x.name}" for x in ocs)
            self.names.default = text
            self.add_item(self.names)
        elif ocs:
            oc_chunks = iter(chunks_split(ocs, 25))
            for item in self.select_ocs_group:
                if characters := next(oc_chunks, []):
                    item.options = [
                        SelectOption(
                            label=oc.name[:100],
                            value=str(oc.id),
                            description=f"{oc!r}"[:100],
                            emoji=oc.pronoun.emoji,
                        )
                        for oc in characters
                    ]
                    item.max_values = len(characters)
                    self.add_item(item)

    async def check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        cog = interaction.client.get_cog("Roles")
        reference = self.to_user or self.role
        if (val := cog.cool_down.get(self.user.id)) and hours(val) < 1:
            msg = f"{self.user.mention} is in cool down, user pinged one recently."
            await resp.send_message(time_message(msg, 3600 - seconds(val)), ephemeral=True)
            return False
        if (val := cog.role_cool_down.get(reference.id)) and hours(val) < 1:
            msg = f"Pinging {reference.mention} is in cool down, check the pings at <#958122815171756042>."
            await resp.send_message(time_message(msg, 3600 - seconds(val)), ephemeral=True)
            return False
        return True

    async def on_submit(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        if isinstance(interaction.channel, Thread) and interaction.channel.archived:
            await interaction.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        info = {x.name.title(): x for x in self.ocs}
        info_ids = {str(x.id): x for x in self.ocs}
        interaction.client.get_cog("Submission")

        items: list[Character] = []

        if data := self.names.value:

            for item in data.split("\n"):
                item = item.removeprefix("-").strip().title()
                item = item.split("|")[-1].strip()
                if oc := info.get(item):
                    items.append(oc)
                elif data := process.extractOne(item, info, score_cutoff=85):
                    items.append(info[data[0]])

        for item in self.select_ocs_group:
            items.extend(map(lambda x: info_ids[x], item.values))

        embed = Embed(title=self.role.name, color=self.user.color, description=self.message.value)
        guild: Guild = self.user.guild
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        if not items:
            items = sorted(self.ocs, key=lambda x: x.name)
        items = set(items)

        reference = self.role
        name = f"{self.role.name} - {self.user.display_name}"
        if self.to_user:
            reference = self.to_user
            name += f" - {self.to_user.display_name}"
        webhook: Webhook = await interaction.client.webhook(958122815171756042, reason="RP Search")
        kwargs = dict(
            content=reference.mention,
            allowed_mentions=AllowedMentions(roles=True),
            embed=embed,
            view=RPSearchManage(self.user, items),
            username=self.user.display_name,
            avatar_url=self.user.display_avatar.url,
        )
        msg1 = await webhook.send(wait=True, **kwargs)
        thread = await msg1.create_thread(name=name)
        kwargs["thread"] = thread
        del kwargs["content"]
        embed.set_image(url=WHITE_BAR)
        msg2 = await webhook.send(wait=True, **kwargs)
        await thread.add_user(self.user)
        if isinstance(reference, Member):
            await thread.add_user(reference)
        cog0 = interaction.client.get_cog("Submission")
        cog1 = interaction.client.get_cog("Roles")
        cog1.cool_down[reference.id] = utcnow()
        cog1.role_cool_down[reference.id] = utcnow()
        ocs = {oc.id for oc in cog0.ocs.values() if oc.author == self.user.id}
        if ocs == {x.id if isinstance(x, Character) else x for x in self.ocs}:
            ocs = set()

        db: AsyncIOMotorCollection = interaction.client.mongo_db("RP Search")
        await db.insert_one(
            {
                "id": msg1.id,
                "member": self.user.id,
                "role": reference.id,
                "server": self.user.guild.id,
                "message": msg2.id,
                "ocs": list(ocs),
            }
        )

        aux_embed = RP_SEARCH_EMBED.copy()
        aux_embed.clear_fields()
        aux_embed.title = "Ping has been done successfully!"
        await interaction.followup.send(embed=aux_embed, ephemeral=True)

        db: AsyncIOMotorCollection = interaction.client.mongo_db("OC Background")
        if img := await db.find_one({"author": self.user.id}):
            img = img["image"]

        if file := await interaction.client.get_file(Character.collage(items, background=img)):
            embed.set_image(url=f"attachment://{file.filename}")
            await msg1.edit(embed=embed, attachments=[file])
        elif text := ", ".join(str(x.id) for x in items):
            interaction.client.logger.info("Error Image Parsing OCs: %s", text)
        await cog1.view_load(interaction.channel)
        self.stop()


class RPSearchComplex(Complex[Member]):
    def __init__(
        self,
        member: Member,
        values: Iterable[Member],
        target: Interaction,
        role: Role,
    ):
        super(RPSearchComplex, self).__init__(
            member=member,
            values=values,
            target=target,
            timeout=None,
            parser=lambda x: (x.display_name, "Click to Ping"),
            sort_key=lambda x: x.display_name,
            silent_mode=True,
        )
        self.embed = RP_SEARCH_EMBED.copy()
        self.embed.title = role.name
        self.role = role
        if role in member.roles:
            self.ping_mode.label, self.ping_mode.style, self.ping_mode.emoji = (
                f"Remove {role.name} Role",
                ButtonStyle.red,
                "\N{BELL WITH CANCELLATION STROKE}",
            )
        elif role:
            self.ping_mode.label = f"Add {role.name} Role"

    async def method(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        cog = ctx.client.get_cog("Submission")
        member: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        ocs = [oc for oc in cog.ocs.values() if oc.author == member.id]
        modal = RPModal(
            user=member,
            role=self.role,
            ocs=ocs,
            mobile=(btn.emoji == MOBILE_EMOJI),
        )
        if await modal.check(ctx):
            await resp.send_modal(modal)
            await modal.wait()
            self.stop()

    @button(emoji="\N{BELL}", style=ButtonStyle.blurple, row=4)
    async def ping_mode(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        match btn.style:
            case ButtonStyle.blurple:
                btn.label, btn.style, btn.emoji = (
                    f"Remove {self.role.name} Role",
                    ButtonStyle.red,
                    "\N{BELL WITH CANCELLATION STROKE}",
                )
                await ctx.user.add_roles(self.role)
            case ButtonStyle.red:
                btn.label, btn.style, btn.emoji = (
                    f"Add {self.role.name} Role",
                    ButtonStyle.blurple,
                    "\N{BELL}",
                )
                await ctx.user.remove_roles(self.role)
        await resp.edit_message(view=self)

    @button(label="New Ping", style=ButtonStyle.blurple, emoji=MOBILE_EMOJI, row=4)
    async def mobile_pinging(self, ctx: Interaction, btn: Button):
        await self.method(ctx, btn)

    @button(label="New Ping", emoji="\N{DESKTOP COMPUTER}", style=ButtonStyle.blurple, row=4)
    async def pinging(self, ctx: Interaction, btn: Button):
        await self.method(ctx, btn)


class RPRolesView(View):
    @select(
        placeholder="Make a new Ping",
        custom_id="rp-view",
        options=[
            SelectOption(
                label=f"{key} RP Search",
                emoji="\N{LEFT-POINTING MAGNIFYING GLASS}",
                value=str(item),
                description=desc,
            )
            for key, (desc, item) in RP_SEARCH_ROLES.items()
        ],
    )
    async def choice(self, interaction: Interaction, sct: Select):
        guild: Guild = interaction.guild
        role: Role = interaction.guild.get_role(int(sct.values[0]))
        db: AsyncIOMotorCollection = interaction.client.mongo_db("RP Search")
        user: Member = interaction.client.supporting.get(interaction.user, interaction.user)
        key = {
            "$and": [
                {"role": role.id},
                {"id": {"$gte": time_snowflake(interaction.created_at - INTERVAL)}},
                {"member": {"$ne": user.id}},
            ]
        }
        cog = interaction.client.get_cog("Submission")
        data: list[dict[str, int]] = await db.find(key, sort=[("id", -1)]).to_list(length=None)
        entries = {
            m: item["id"]
            for item in data
            if (m := guild.get_member(item["member"])) and ({x for x in cog.ocs.values() if x.author == user.id})
        }
        member: Member = interaction.client.supporting.get(interaction.user, interaction.user)
        view = RPSearchComplex(member=member, values=entries.keys(), target=interaction, role=role)
        async with view.send(ephemeral=True, single=True) as choice:
            if thread_id := entries.get(choice):
                if not (thread := guild.get_channel_or_thread(thread_id)):
                    thread = await guild.fetch_channel(thread)
                if thread.archived:
                    await thread.edit(archived=False)
                await thread.add_user(member)
                await thread.add_user(choice)

    @button(label="Existing RP Pings", style=ButtonStyle.blurple, custom_id="rp-pings")
    async def rp_pings(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        date = time_snowflake(ctx.created_at - INTERVAL)
        cog = ctx.client.get_cog("Submission")
        user: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        db: AsyncIOMotorCollection = ctx.client.mongo_db("RP Search")
        key = {"$and": [{"id": {"$gte": date}}, {"member": {"$ne": user.id}}]}
        items = [
            (
                (
                    f"{role.name} - {member}",
                    f"{member.display_name} w/ {len(ocs)} OCs",
                ),
                PartialMessage(channel=ctx.channel, id=item["id"]),
            )
            async for item in db.find(key, sort=[("id", -1)])
            if (role := ctx.guild.get_role(item["role"]))
            and (member := ctx.guild.get_member(item["member"]))
            and (
                ocs := {oc for x in item["ocs"] if isinstance(oc := cog.ocs.get(x), Character)}
                or {x for x in cog.ocs.values() if x.author == member.id}
            )
        ]
        view = Complex(
            member=ctx.user,
            target=ctx,
            values=items,
            parser=lambda x: x[0],
            silent_mode=True,
        )
        async with view.send(ephemeral=True, single=True) as choice:
            if not choice:
                return
            msg: PartialMessage = choice[1]

            try:
                msg = await msg.fetch()
                aux = View()
                aux.add_item(Button(label="Jump URL", url=msg.jump_url))
                await view.message.edit(embed=msg.embeds[0], view=aux)
            except DiscordException:
                await db.delete_one({"id": msg.id})
