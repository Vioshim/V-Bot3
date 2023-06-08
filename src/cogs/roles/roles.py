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
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import utcnow
from rapidfuzz import process

from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.pronouns import Pronoun
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
    def __init__(self, hours: list[int] = None, offset: int = 0) -> None:
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
        member: Member = itx.client.supporting.get(itx.user, itx.user)
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


class RoleSelect(View):
    async def on_error(self, itx: Interaction[CustomBot], error: Exception, item, /) -> None:
        itx.client.logger.error("Ignoring exception in view %r for item %r", self, item, exc_info=error)

    @staticmethod
    async def choice(itx: Interaction[CustomBot], sct: Select, remove_all: bool = False):
        resp: InteractionResponse = itx.response
        member: Member = itx.client.supporting.get(itx.user, itx.user)
        guild = itx.guild

        roles: set[Role] = set() if remove_all else set(get_role(sct.values, guild))
        total: set[Role] = set(get_role(sct.options, guild))

        await resp.defer(ephemeral=True, thinking=True)

        embed = Embed(
            title=sct.placeholder.removeprefix("Select "),
            color=Color.blurple(),
            timestamp=itx.created_at,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

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
    async def pronouns_choice(self, itx: Interaction[CustomBot], sct: Select):
        await self.choice(itx, sct)

    @select(
        placeholder="Select Color Roles",
        custom_id="colors",
        options=[
            SelectOption(
                label="Red",
                emoji=":red:952523311395528728",
                value="794274172813312000",
                description="#FF3C28",
            ),
            SelectOption(
                label="Crimson",
                emoji=":crimson:952523311680745492",
                value="794274956296847370",
                description="#E10F00",
            ),
            SelectOption(
                label="Orange",
                emoji=":orange:952523311756218428",
                value="794275894209282109",
                description="#FAA005",
            ),
            SelectOption(
                label="Golden",
                emoji=":golden:952523311429074966",
                value="794275428696064061",
                description="#1EDC00",
            ),
            SelectOption(
                label="Yellow",
                emoji=":yellow:952523311697494086",
                value="794274424777080884",
                description="#E6FF00",
            ),
            SelectOption(
                label="Green",
                emoji=":green:952523311890452520",
                value="794274561570504765",
                description="#1EDC00",
            ),
            SelectOption(
                label="Lime",
                emoji=":lime:952523311865270302",
                value="794276035326902342",
                description="#82FF96",
            ),
            SelectOption(
                label="Cyan",
                emoji=":cyan:952523311735255100",
                value="794276172762185799",
                description="#96F5F5",
            ),
            SelectOption(
                label="Light Blue",
                emoji=":light_blue:952523313794670622",
                value="794274301707812885",
                description="#0AB9E6",
            ),
            SelectOption(
                label="Deep Blue",
                emoji=":deep_blue:952523311680725013",
                value="794275553477394475",
                description="#4655F5",
            ),
            SelectOption(
                label="Violet",
                emoji=":violet:952523311743660052",
                value="794275765533278208",
                description="#B400E6",
            ),
            SelectOption(
                label="Pink",
                emoji=":pink:952523311743635486",
                value="794274741061025842",
                description="#FF3278",
            ),
            SelectOption(
                label="Light Brown",
                emoji=":light_brown:952523311764627536",
                value="794275107958292500",
                description="#D7AA73",
            ),
            SelectOption(
                label="Dark Brown",
                emoji=":dark_brown:952523311642972200",
                value="794275288271028275",
                description="#C88D32",
            ),
            SelectOption(
                label="Silver",
                emoji=":silver:952523311680745532",
                value="850018780762472468",
                description="#C0C0C0",
            ),
            SelectOption(
                label="Gray",
                emoji=":gray:952523311714295898",
                value="794273806176223303",
                description="#828282",
            ),
        ],
        min_values=0,
    )
    async def colors_choice(self, itx: Interaction[CustomBot], sct: Select):
        await self.choice(itx, sct)

    @select(
        placeholder="Select Basic Roles",
        custom_id="basic",
        min_values=0,
        max_values=5,
        options=[
            SelectOption(
                label="Announcements",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="908809235012419595",
                description="Get pinged during announcements.",
            ),
            SelectOption(
                label="Bump Reminder",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="1008443862559240312",
                description="Reminds you to bump the server",
            ),
            SelectOption(
                label="RP Events",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="805878418225889280",
                description="Get informed of RP Events, Missions and Storylines.",
            ),
            SelectOption(
                label="Don't Ping Me!",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="1092498088347844649",
                description="Warns people not to ping you.",
            ),
            SelectOption(
                label="Looking for RP",
                emoji="\N{DIAMOND SHAPE WITH A DOT INSIDE}",
                value="1110599604090716242",
                description="Lets people know you're looking for RP.",
            ),
        ],
    )
    async def basic_choice(self, itx: Interaction[CustomBot], sct: Select):
        await self.choice(itx, sct)

    @select(
        placeholder="AFK Schedule",
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
    async def check_ocs(self, itx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        db = itx.client.mongo_db("Characters")
        if not (
            ocs := [
                Character.from_mongo_dict(x)
                async for x in db.find({"id": {"$in": [x.id if isinstance(x, Character) else x for x in self.ocs]}})
            ]
        ):
            ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": self.member_id})]

        view = CharactersView(
            member=itx.user,
            target=itx,
            ocs=ocs,
            keep_working=True,
            msg_id=int(btn.custom_id) if btn.custom_id.isdigit() else None,
        )
        embed = view.embed
        if member := itx.guild.get_member(self.member_id) or itx.client.get_user(self.member_id):
            embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
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
    async def conclude(self, itx: Interaction[CustomBot], btn: Button):
        db = itx.client.mongo_db("RP Search")
        resp: InteractionResponse = itx.response
        if itx.user.id != self.member_id and not itx.user.guild_permissions.moderate_members:
            return await resp.send_message(
                f"Only <@{self.member_id}> can archive it",
                ephemeral=True,
            )
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)
        await resp.pong()
        if (message := itx.message) and (
            item := await db.find_one_and_delete(
                {
                    "server": itx.guild_id,
                    "id": message.id,
                }
            )
        ):
            channel = itx.guild.get_channel(958122815171756042)
            message = channel.get_partial_message(item["id"])
            await message.delete(delay=0)
            if thread := itx.guild.get_thread(item["id"]):
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
        ocs: set[Character],
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
        if isinstance(to_user, Member):
            # fmt: off
            self.message.default = (
                self.message.default
                .replace("their", f"{to_user.display_name}'s")
                .replace("s's", "s'")
            )
            # fmt: on
        self.add_item(self.message)

        self.select_ocs1 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs2 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs3 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs4 = Select(placeholder="Select Characters", min_values=0)
        self.select_ocs_group = (
            self.select_ocs1,
            self.select_ocs2,
            self.select_ocs3,
            self.select_ocs4,
        )

        if mobile:
            text = "\n".join(f"- {x.species.name} | {x.name}" for x in self.ocs)
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
        if (val := cog.cool_down.get(self.user.id)) and hours(val) < 1:
            msg = f"{self.user.mention} is in cool down, user pinged one recently."
            await resp.send_message(time_message(msg, 3600 - seconds(val)), ephemeral=True)
            return False
        user = self.to_user or self.user
        if (val := cog.role_cool_down.get(user.id)) and hours(val) < 1:
            msg = f"Pinging {user.mention} is in cool down, check the pings at <#1061008601335992422>."
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
                        }
                    }
                )
            ]
        )

        if isinstance(item := self.to_user, Role):
            name, reference_name = item.name, f"{self.user.display_name}▷{item.name}"
        elif isinstance(item, Member):
            name, reference_name = item.display_name, f"▷{self.to_user.display_name}"
        else:
            item = itx.guild.get_role(1110599604090716242) or self.user
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

        if not (channel := guild.get_channel(1061008601335992422)):
            channel: ForumChannel = await guild.fetch_channel(1061008601335992422)

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
        if img := await db.find_one({"author": self.user.id}):
            img = img["image"]

        if file := await itx.client.get_file(Character.collage(items, background=img)):
            embed.set_image(url=f"attachment://{file.filename}")
            await base.message.edit(embed=embed, attachments=[file], view=view)
        else:
            await base.message.edit(view=view)
            itx.client.logger.info("Error Image Parsing OCs: %s", ", ".join(str(x.id) for x in items))

        db = itx.client.mongo_db("RP Search")
        await db.insert_one(
            {
                "id": base.thread.id,
                "member": self.user.id,
                "role": item.id,
                "server": itx.guild.id,
                "ocs": [x.id for x in items] if len(items) != len(self.ocs) else [],
            }
        )

        self.stop()
