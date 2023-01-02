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


from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from itertools import groupby
from time import mktime
from typing import Iterable, Optional

from dateparser import parse
from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
    DiscordException,
    Embed,
    ForumChannel,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    TextStyle,
    Thread,
    Webhook,
    WebhookMessage,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import get, utcnow
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.pagination.view_base import Basic
from src.structures.character import Character
from src.structures.pronouns import Pronoun
from src.utils.etc import DEFAULT_TIMEZONE, SETTING_EMOJI, WHITE_BAR
from src.utils.functions import chunks_split
from src.views.characters_view import CharactersView

__all__ = (
    "RoleSelect",
    "RPSearchManage",
    "RPRolesView",
    "hours",
    "seconds",
)


INTERVAL = timedelta(days=3)
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
    Casual=("Ideal for Slice of Life RP", 1017897677423378512),
    Plot=("If you need a hand with an Arc or plot.", 962719564863508510),
    Action=("Encounters that involve action such as battles, thievery, etc.", 962719565182271590),
    Narrated=("Narrate for others or get narrated.", 962719566402813992),
    Drama=("RPs that present a problem for OCs to solve.", 962719567694659604),
    Literate=("Be descriptive and detailed as possible", 962719568172814368),
    Horror=("Scary or mysterious RPs for OCs", 962719570148331560),
)


def get_role(items: Iterable[SelectOption | str], guild: Guild):
    for x in items:
        if isinstance(x, SelectOption):
            x = x.value
        if role := guild.get_role(int(x)):
            yield role


@dataclass(unsafe_hash=True, slots=True)
class AdjacentTimeState:
    key: int = 0
    previous: float = float("nan")

    def __call__(self, value: datetime):
        adjacent = value.hour - self.previous == 1
        wraps_around = value.hour == 0 and self.previous == 23
        if not adjacent and not wraps_around:
            self.key += 1
        self.previous = value.hour
        return self.key


@dataclass(unsafe_hash=True, slots=True)
class AFKSchedule:
    hours: frozenset[datetime] = field(default_factory=frozenset)

    def astimezone(self, tz: timezone):
        return AFKSchedule([x.astimezone(tz) for x in self.hours])

    @property
    def pairs(self):
        # find all consecutive runs
        hours = sorted(self.hours, key=lambda x: x.hour)
        runs = [list(group) for _, group in groupby(hours, key=AdjacentTimeState())]

        # check wrap-around
        if len(runs) >= 2:
            (first_time, *_), *_, (*_, last_time) = runs
            if first_time.hour - last_time.hour == 1 or first_time.hour == 0 and last_time.hour == 23:
                runs[0] = runs[-1] + runs[0]
                del runs[-1]

        return sorted((run[0].time(), run[-1].time()) for run in runs)

    @property
    def text(self):
        return "\n".join(f"• {x.strftime('%I:00 %p')} - {y.strftime('%I:59 %p')}" for x, y in self.pairs)


class AFKModal(Modal, title="Current Time"):
    def __init__(self, hours: list[int] = None) -> None:
        super(AFKModal, self).__init__(timeout=None)

        data = TextInput(
            label="What time is for you?",
            max_length=8,
            placeholder="01:00 PM",
        )
        self.hours = [*map(int, hours or [])]
        self.hours.sort()
        data.placeholder = data.default = utcnow().strftime("%I:00 %p")
        self.offset: int = 0
        self.data = data
        self.add_item(data)

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        interaction.client.logger.error("Ignoring exception in modal %r", self, exc_info=error)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        current_date = interaction.created_at
        member: Member = interaction.client.supporting.get(interaction.user, interaction.user)
        date1 = current_date.astimezone(DEFAULT_TIMEZONE)
        date2 = (parse(self.data.value, settings=dict(TIMEZONE="utc")) or date1).astimezone(DEFAULT_TIMEZONE)
        ref = abs(date1 - date2).seconds
        self.offset = min(range(0, 48 * 1800 + 1, 1800), key=lambda x: abs(x - ref)) / 3600
        if date1 > date2:
            self.offset = -self.offset

        tz = timezone(timedelta(hours=self.offset))
        data = AFKSchedule([datetime.combine(current_date, time(hour=x), tz) for x in self.hours])

        embed = Embed(
            title="AFK Schedule",
            description=data.text or "All schedules were removed.",
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(
            text="Command /afk will show your afk schedule.\npings when you're offline will notify of it during them.",
        )

        await interaction.followup.send(embed=embed)

        db: AsyncIOMotorCollection = interaction.client.mongo_db("AFK")
        await db.replace_one(
            {"user": member.id},
            {
                "user": member.id,
                "hours": sorted(self.hours),
                "offset": float(self.offset),
            },
            upsert=True,
        )

        self.stop()


class RoleSelect(View):
    async def on_error(self, interaction: Interaction, error: Exception, item, /) -> None:
        interaction.client.logger.error("Ignoring exception in view %r for item %r", self, item, exc_info=error)

    @staticmethod
    async def choice(ctx: Interaction, sct: Select, remove_all: bool = False):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        guild = ctx.guild

        roles: set[Role] = set() if remove_all else set(get_role(sct.values, guild))
        total: set[Role] = set(get_role(sct.options, guild))

        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(
            title=sct.placeholder.removeprefix("Select "),
            color=Color.blurple(),
            timestamp=ctx.created_at,
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

        return roles


class BasicRoleSelect(RoleSelect):
    @select(
        placeholder="Select Pronoun Roles",
        custom_id="pronouns",
        min_values=0,
        max_values=len(Pronoun),
        options=[
            SelectOption(
                label=pronoun.name,
                value=str(pronoun.role_id),
                description=f"Adds {pronoun.name} as pronoun in roles.",
                emoji=pronoun.emoji,
            )
            for pronoun in Pronoun
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
        max_values=7,
        options=[
            SelectOption(
                label="Archive",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="1051564303901261934",
                description="Read RPs from 2020 - 2022",
            ),
            SelectOption(
                label="RP Events",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="805878418225889280",
                description="Get informed of RP Events, Missions and Storylines.",
            ),
            SelectOption(
                label="Supporter",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="967980442919784488",
                description="Get pings when people need a hand.",
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
        max_values=5,
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
        roles = await self.choice(ctx, sct)
        member: Member = ctx.client.supporting.get(ctx.user, ctx.user)
        roles = [x.name.removesuffix(" RP Search") for x in roles]
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Roleplayers")
        if item := await db.find_one({"user": member.id}):
            if not (channel := ctx.guild.get_channel_or_thread(item["id"])):
                channel: Thread = await ctx.guild.fetch_channel(item["id"])
            forum: ForumChannel = channel.parent
            tags = [o for x in roles if (o := get(forum.available_tags, name=x))][:5]
            tags.sort(key=lambda x: x.name)
            if set(channel.applied_tags) != set(tags):
                await channel.edit(archived=False, applied_tags=tags)

    @select(
        placeholder="AFK Schedule (No timezone)",
        custom_id="afk",
        min_values=0,
        max_values=24,
        options=[
            SelectOption(
                label=lapse.strftime("%I:00 %p"),
                value=str(lapse.hour),
                description=lapse.strftime("From %I:00 %p to %I:59 %p"),
                emoji="\N{SLEEPING SYMBOL}",
            )
            for lapse in map(time, range(24))
        ],
    )
    async def afk_schedule(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        modal = AFKModal(hours=sct.values)
        await resp.send_modal(modal)


class RPSearchManage(View):
    def __init__(self, msg_id: int, member_id: int | Member, ocs: set[int | Character] = None):
        super(RPSearchManage, self).__init__(timeout=None)
        if not isinstance(member_id, int):
            member_id = member_id.id
        self.member_id = member_id
        self.check_ocs.custom_id = str(msg_id)
        self.ocs = ocs

    @button(
        label="Click to Read User's OCs.",
        row=4,
        custom_id="check_ocs",
        style=ButtonStyle.blurple,
        emoji=SETTING_EMOJI,
    )
    async def check_ocs(self, ctx: Interaction, btn: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Characters")
        if not (
            ocs := [
                Character.from_mongo_dict(x)
                async for x in db.find({"id": {"$in": [x.id if isinstance(x, Character) else x for x in self.ocs]}})
            ]
        ):
            ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": self.member_id})]

        view = CharactersView(
            member=ctx.user,
            target=ctx,
            ocs=ocs,
            keep_working=True,
            msg_id=int(btn.custom_id) if btn.custom_id.isdigit() else None,
        )
        embed = view.embed
        if member := ctx.guild.get_member(self.member_id) or ctx.client.get_user(self.member_id):
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        else:
            member = f"User(ID={self.member_id})"
        async with view.send(ephemeral=True, single=True) as data:
            if isinstance(data, Character):
                ctx.client.logger.info(
                    "User %s is currently reading %s's character %s [%s]",
                    str(ctx.user),
                    str(member),
                    data.name,
                    repr(data),
                )

    @button(
        label="Archive Thread",
        row=4,
        custom_id="archive_thread",
        style=ButtonStyle.red,
    )
    async def conclude(self, ctx: Interaction, btn: Button):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("RP Search")
        resp: InteractionResponse = ctx.response
        if ctx.user.id != self.member_id and not ctx.user.guild_permissions.moderate_members:
            return await resp.send_message(
                f"Only <@{self.member_id}> can archive it",
                ephemeral=True,
            )
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        await resp.pong()
        if (message := ctx.message) and (
            item := await db.find_one_and_delete(
                {
                    "server": ctx.guild_id,
                    "$or": [{"id": message.id}, {"message": message.id}],
                }
            )
        ):
            channel = ctx.guild.get_channel(958122815171756042)
            message = channel.get_partial_message(item["id"])
            await message.delete(delay=0)
            if thread := ctx.guild.get_thread(item["id"]):
                message = thread.get_partial_message(item["message"])
                try:
                    await message.edit(view=None)
                except DiscordException:
                    await message.delete(delay=0)

                await thread.edit(archived=True, locked=True)


def time_message(msg: str, s: int):
    return f"{msg}\nTry again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds"


class RPModal(Modal):
    def __init__(
        self,
        user: Member,
        role: Role,
        ocs: set[Character],
        to_user: Optional[Member] = None,
        mobile: bool = True,
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
                            emoji=oc.emoji,
                        )
                        for oc in characters
                    ]
                    item.max_values = len(characters)
                    self.add_item(item)

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        interaction.client.logger.error("Ignoring exception in Modal %r", self, exc_info=error)

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
        await resp.defer(ephemeral=True, thinking=True)

        items = [
            data[0]
            for item in map(
                lambda x: x.removeprefix("-").strip(),
                self.names.value.title().split("\n"),
            )
            if (
                data := process.extractOne(
                    item.split("|")[-1].strip(),
                    self.ocs,
                    score_cutoff=85,
                    processor=lambda x: getattr(x, "name", x),
                )
            )
        ]

        cog1 = interaction.client.get_cog("Roles")
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        data = [
            Character.from_mongo_dict(x)
            async for x in db.find(
                {"id": {"$in": [int(value) for item in self.select_ocs_group for value in item.values]}}
            )
        ]
        items.extend(data)

        embed = Embed(title=self.role.name, color=self.user.color, description=self.message.value)
        guild: Guild = self.user.guild
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        if not items:
            items = self.ocs
        items = sorted(set(items), key=lambda x: x.name)

        reference = self.role
        name = f"{self.role.name} - {self.user.display_name}"
        if self.to_user:
            reference = self.to_user
            name += f" - {self.to_user.display_name}"
        webhook: Webhook = await interaction.client.webhook(958122815171756042, reason="RP Search")
        msg1: WebhookMessage = await webhook.send(
            content=reference.mention,
            allowed_mentions=AllowedMentions(roles=True),
            embed=embed,
            username=self.user.display_name,
            avatar_url=self.user.display_avatar.url,
            wait=True,
        )
        thread = await msg1.create_thread(name=name)
        embed.set_image(url=WHITE_BAR)
        view = RPSearchManage(msg1.id, self.user, items)
        for idx, x in enumerate(items[:6]):
            view.add_item(Button(label=x.name[:80], emoji=x.emoji, url=x.jump_url, row=idx // 3))
        msg2 = await thread.send(
            content=reference.mention,
            allowed_mentions=AllowedMentions(users=True),
            embed=embed,
            view=view,
        )
        await thread.add_user(self.user)

        cog1.cool_down[reference.id] = interaction.created_at
        cog1.role_cool_down[reference.id] = interaction.created_at

        ocs = {x["id"] async for x in db.find({"author": self.user.id, "server": guild.id})}
        ocs2 = {x.id if isinstance(x, Character) else x for x in self.ocs}
        if ocs == ocs2:
            ocs2 = set()

        ocs = ocs2

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
            await msg1.edit(embed=embed, attachments=[file], view=view)
        elif text := ", ".join(str(x.id) for x in items):
            interaction.client.logger.info("Error Image Parsing OCs: %s", text)
        self.stop()


class RPRolesView(Basic):
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
        role: Role = interaction.guild.get_role(int(sct.values[0]))
        resp: InteractionResponse = interaction.response
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Characters")
        user: Member = interaction.client.supporting.get(interaction.user, interaction.user)
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": user.id, "server": interaction.guild_id})]
        modal = RPModal(user=user, role=role, ocs=ocs)
        if await modal.check(interaction):
            await resp.send_modal(modal)
            await modal.wait()
