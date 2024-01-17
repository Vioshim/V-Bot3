# Copyright 2023 Vioshim
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
from itertools import chain, groupby
from time import mktime
from typing import Iterable, Optional

from dateparser import parse
from discord import (
    AllowedMentions,
    ButtonStyle,
    Color,
    Embed,
    ForumChannel,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Role,
    SelectOption,
    TextStyle,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import utcnow
from rapidfuzz import process

from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import DEFAULT_TIMEZONE, LINK_EMOJI, SETTING_EMOJI, WHITE_BAR
from src.utils.functions import chunks_split, safe_username
from src.views.characters_view import CharactersView

__all__ = ("RoleSelect", "RPSearchManage", "hours", "seconds")


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
        return AFKSchedule(frozenset(x.astimezone(tz) for x in self.hours))

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
    def __init__(self, hours: Optional[list[int]] = None, offset: int = 0) -> None:
        super(AFKModal, self).__init__(timeout=None)
        date = utcnow().astimezone(timezone(offset=timedelta(hours=offset)))
        text = date.strftime("%I:%M %p")

        data = TextInput(
            label="What time it is for you?",
            max_length=8,
            placeholder=text,
            default=text,
        )
        items = []
        if hours:
            items.extend(map(int, hours))
        self.hours: list[int] = items
        self.hours.sort()
        self.offset = offset
        self.data = data
        self.add_item(data)

    async def on_error(self, itx: Interaction[CustomBot], error: Exception, /) -> None:
        itx.client.logger.error("Ignoring exception in modal %r", self, exc_info=error)

    async def on_submit(self, itx: Interaction[CustomBot]) -> None:
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        current_date = itx.created_at
        member = itx.client.supporting.get(itx.user, itx.user)
        date1 = current_date.astimezone(DEFAULT_TIMEZONE)
        date2 = (parse(self.data.value, settings=dict(TIMEZONE="utc")) or date1).astimezone(DEFAULT_TIMEZONE)
        ref = abs(date1 - date2).seconds
        self.offset = min(range(0, 48 * 1800 + 1, 1800), key=lambda x: abs(x - ref)) / 3600
        if date1 > date2:
            self.offset = -self.offset

        tz = timezone(timedelta(hours=self.offset))
        data = AFKSchedule(frozenset(datetime.combine(current_date, time(hour=x), tz) for x in self.hours))

        embed = Embed(
            title="AFK Schedule",
            description=data.text or "All schedules were removed.",
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(
            text="Command /afk will show your afk schedule.\npings when you're offline will notify of it during them.",
        )

        await itx.followup.send(embed=embed)

        db = itx.client.mongo_db("AFK")
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


class RoleSelect(Select):
    async def role_choice(self, itx: Interaction[CustomBot]):
        resp: InteractionResponse = itx.response
        member: Member = itx.client.supporting.get(itx.user, itx.user)
        guild: Guild = itx.guild

        roles: set[Role] = set(get_role(self.values, guild))
        total: set[Role] = set(get_role(self.options, guild))

        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(
            title=self.placeholder and self.placeholder.removeprefix("Select "),
            color=Color.blurple(),
            timestamp=itx.created_at,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon)

        if add := set(roles) - set(member.roles):
            text = "\n".join(f"* {role.mention}" for role in add)
            embed.add_field(name="**__Roles Added__**", value=text, inline=False)
            await member.add_roles(*add)
        if remove := (total - roles) & set(member.roles):
            text = "\n".join(f"* {role.mention}" for role in remove)
            embed.add_field(name="**__Roles Removed__**", value=text, inline=False)
            await member.remove_roles(*remove)

        await itx.followup.send(embed=embed, ephemeral=True)

        return roles


class BasicRoleSelect(View):
    def __init__(self, items: list[dict[str, str]]) -> None:
        super(BasicRoleSelect, self).__init__(timeout=None)
        for index, item in enumerate(items):
            self.add_item(
                RoleSelect(
                    placeholder=item.get("placeholder"),
                    custom_id=item.get("custom_id"),
                    row=index,
                    options=[
                        SelectOption(
                            label=option.get("label"),
                            value=option.get("value"),
                            description=option.get("description", ""),
                            emoji=option.get("emoji"),
                        )
                        for option in item.get("options", [])
                    ],
                    min_values=item.get("min_values", 1),
                    max_values=item.get("max_values", 1),
                )
            )

    async def on_error(self, itx: Interaction[CustomBot], error: Exception, item, /) -> None:
        itx.client.logger.error("Ignoring exception in view %r for item %r", self, item, exc_info=error)

    @select(
        placeholder="AFK Schedule",
        custom_id="afk",
        min_values=0,
        max_values=24,
        row=3,
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
    async def afk_schedule(self, itx: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = itx.response
        db = itx.client.mongo_db("AFK")
        member: Member = itx.client.supporting.get(itx.user, itx.user)
        if item := await db.find_one({"user": member.id}):
            modal = AFKModal(hours=sct.values, offset=item["offset"])
        else:
            modal = AFKModal(hours=sct.values)
        await resp.send_modal(modal)

    @button(
        label="Set Timezone. What time it is?",
        custom_id="timezone",
        style=ButtonStyle.blurple,
        emoji="\N{TIMER CLOCK}",
        row=4,
    )
    async def tz_schedule(self, itx: Interaction[CustomBot], _: Button):
        resp: InteractionResponse = itx.response
        db = itx.client.mongo_db("AFK")
        member: Member = itx.client.supporting.get(itx.user, itx.user)
        if item := await db.find_one({"user": member.id}):
            modal = AFKModal(hours=item["hours"], offset=item["offset"])
        else:
            modal = AFKModal()
        await resp.send_modal(modal)


class RPSearchManage(View):
    def __init__(
        self,
        msg_id: int,
        member_id: int | Member,
        ocs: set[int | Character] = None,
        server_id: int = None,
    ):
        super(RPSearchManage, self).__init__(timeout=None)
        if not isinstance(member_id, int):
            member_id = member_id.id
        self.server_id = server_id
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
    async def check_ocs(self, itx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        db = itx.client.mongo_db("Characters")
        items = [x.id if isinstance(x, Character) else x for x in self.ocs]

        key = {
            "author": self.member_id,
            "server": self.server_id or itx.guild_id,
        }

        if not (ocs := [Character.from_mongo_dict(x) async for x in db.find({"id": {"$in": items}} | key)]):
            ocs = [Character.from_mongo_dict(x) async for x in db.find(key)]

        view = CharactersView(
            member=itx.user,
            target=itx,
            ocs=ocs,
            keep_working=True,
            msg_id=int(btn.custom_id) if btn.custom_id.isdigit() else None,
        )
        embed = view.embed
        if member := itx.guild.get_member(self.member_id) or itx.client.get_user(self.member_id):
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        else:
            member = f"User(ID={self.member_id})"
        async with view.send(ephemeral=True, single=True) as data:
            if isinstance(data, Character):
                itx.client.logger.info(
                    "User %s is currently reading %s's character %s [%s]",
                    str(itx.user),
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
    async def conclude(self, itx: Interaction[CustomBot], _: Button):
        if itx.user.id != self.member_id and not itx.user.guild_permissions.moderate_members:
            return await itx.response.send_message(f"Only <@{self.member_id}> can archive it", ephemeral=True)
        await itx.response.send_message("Archiving thread...", ephemeral=True)
        await itx.channel.edit(archived=True)


def time_message(msg: str, s: int):
    return f"{msg}\nTry again in {s // 3600:02} Hours, {s % 3600 // 60:02} Minutes, {s % 60:02} Seconds"


class RPModal(Modal):
    def __init__(
        self,
        user: Member,
        ocs: Iterable[Character],
        to_user: Optional[Member | Role] = None,
        mobile: bool = True,
    ) -> None:
        super(RPModal, self).__init__(title="Pinging")
        self.user = user
        self.ocs = sorted(ocs, key=lambda x: x.last_used or x.id, reverse=True)
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
            placeholder="Describe what you're looking for in this RP (Optional)",
            default=f"{user.display_name} is looking to RP with their registered characters.",
            required=False,
        )
        if isinstance(to_user, Member) and self.message.default:
            # fmt: off
            self.message.default = (
                self.message.default
                .replace("their", f"{to_user.display_name}'s")
                .replace("s's", "s'")
            )
            # fmt: on
        self.add_item(self.message)

        placeholder = "Select Characters"
        self.select_ocs1 = Select(placeholder=placeholder, min_values=0)
        self.select_ocs2 = Select(placeholder=placeholder, min_values=0)
        self.select_ocs3 = Select(placeholder=placeholder, min_values=0)
        self.select_ocs4 = Select(placeholder=placeholder, min_values=0)
        self.select_ocs_group = (
            self.select_ocs1,
            self.select_ocs2,
            self.select_ocs3,
            self.select_ocs4,
        )

        if mobile:
            text = "\n".join(f"- {x.species.name} | {x.name}" for x in self.ocs if x.species)
            if len(text) > 4000:
                text = "\n".join(f"- {x.name}" for x in self.ocs)[:4000]
            self.names.default = text
            self.add_item(self.names)
        elif self.ocs:
            oc_chunks = iter(chunks_split(self.ocs, 25))
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

    async def on_error(self, itx: Interaction[CustomBot], error: Exception, /) -> None:
        itx.client.logger.error("Ignoring exception in Modal %r", self, exc_info=error)

    async def check(self, itx: Interaction[CustomBot]) -> bool:
        resp: InteractionResponse = itx.response
        cog = itx.client.get_cog("Roles")
        if (val := cog.cool_down.get(self.user.id)) and hours(val) < 1:  # type: ignore
            msg = f"{self.user.mention} is in cool down, user pinged one recently."
            await resp.send_message(time_message(msg, 3600 - seconds(val)), ephemeral=True)
            return False
        user = self.to_user or self.user
        if (val := cog.role_cool_down.get(user.id)) and hours(val) < 1:  # type: ignore
            msg = f"Pinging {user.mention} is in cool down, check the pings at RP-Planning."
            await resp.send_message(time_message(msg, 3600 - seconds(val)), ephemeral=True)
            return False
        return True

    async def on_submit(self, itx: Interaction[CustomBot]):
        resp: InteractionResponse = itx.response
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

        cog1 = itx.client.get_cog("Roles")
        db = itx.client.mongo_db("Characters")
        items.extend(
            [
                Character.from_mongo_dict(x)
                async for x in db.find(
                    {
                        "id": {
                            "$in": [
                                int(item)
                                for item in chain(
                                    self.select_ocs1.values,
                                    self.select_ocs2.values,
                                    self.select_ocs3.values,
                                    self.select_ocs4.values,
                                )
                                if item.isdigit()
                            ]
                        },
                        "author": self.user.id,
                        "server": itx.guild_id,
                    }
                )
            ]
        )

        db1 = itx.client.mongo_db("Server")
        server_info = await db1.find_one({"id": itx.guild_id})
        server_info = server_info or {}

        if isinstance(item := self.to_user, Role):
            name, reference_name = item.name, f"{self.user.display_name}▷{item.name}"
        elif isinstance(item, Member):
            name, reference_name = item.display_name, f"▷{self.to_user.display_name}"
        else:
            item = itx.guild.get_role(server_info.get("looking_for_rp")) or self.user
            name, reference_name = "Looking for RP", f"{self.user.display_name}▷"

        embed = Embed(
            title=name,
            color=self.user.color,
            description=self.message.value,
            timestamp=itx.created_at,
        )
        guild: Guild = self.user.guild
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        items = sorted(set(items or self.ocs), key=lambda x: x.last_used or x.id, reverse=True)

        rp_planning_id = server_info.get("rp_planning")
        if not (channel := guild.get_channel(rp_planning_id)):
            channel: ForumChannel = await guild.fetch_channel(rp_planning_id)

        base = await channel.create_thread(
            name=safe_username(reference_name),
            content=f"{self.user.mention} is looking to RP with {item.mention}!",
            allowed_mentions=AllowedMentions(users=True, roles=True),
            embed=embed,
        )
        await base.message.pin()

        view = RPSearchManage(base.thread.id, self.user, items)
        for idx, x in enumerate(items[:6]):
            view.add_item(Button(label=x.name[:80], emoji=x.emoji, url=x.jump_url, row=idx // 3))

        cog1.cool_down[self.user.id] = itx.created_at
        cog1.role_cool_down[item.id] = itx.created_at

        aux_embed = RP_SEARCH_EMBED.copy()
        aux_embed.clear_fields()
        aux_embed.title = "Ping has been done successfully!"

        aux_view = View()
        aux_view.add_item(Button(label="Go to Ping", emoji=LINK_EMOJI, url=base.message.jump_url))
        await itx.followup.send(embed=aux_embed, ephemeral=True, view=aux_view)

        db = itx.client.mongo_db("OC Background")
        if img := await db.find_one({"author": self.user.id, "server": guild.id}):
            img = img["image"]

        if oc_file := await itx.client.get_file(Character.collage(items, background=img)):
            embed.set_image(url=f"attachment://{oc_file.filename}")
            await base.message.edit(embed=embed, attachments=[oc_file], view=view)
        else:
            await base.message.edit(view=view)
            itx.client.logger.info("Error Image Parsing OCs: %s", ", ".join(str(x.id) for x in items))

        db = itx.client.mongo_db("RP Search")
        await db.insert_one(
            {
                "id": base.thread.id,
                "member": self.user.id,
                "role": item.id,
                "server": itx.guild and itx.guild.id,
                "ocs": [x.id for x in items] if len(items) != len(self.ocs) else [],
            }
        )

        self.stop()
