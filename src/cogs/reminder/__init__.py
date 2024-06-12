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


from __future__ import annotations

from datetime import datetime
from typing import Optional, TypedDict

from apscheduler.triggers.date import DateTrigger
from bson import ObjectId
from dateparser import parse
from discord import (
    AllowedMentions,
    Color,
    Embed,
    Interaction,
    Object,
    Thread,
    app_commands,
)
from discord.ext import commands
from discord.utils import MISSING

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR


class ReminderPayload(TypedDict):
    _id: ObjectId
    author: int
    channel: int
    thread: Optional[int]
    message: str
    due: datetime


class Reminder(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    async def cog_load(self):
        remind = self.bot.mongo_db("Reminder")
        async for item in remind.find({}):
            await self.bot.scheduler.add_schedule(
                self.remind_action,
                trigger=DateTrigger(item["due"]),
                id=f"reminder-{item['_id']}",
                args=(item,),
            )

    async def remind_action(self, payload: ReminderPayload):
        remind = self.bot.mongo_db("Reminder")
        tupper_log = self.bot.mongo_db("Tupper-logs")

        author_id, channel_id, thread_id, text, due = (
            payload["author"],
            payload["channel"],
            payload["thread"],
            payload["message"],
            payload["due"],
        )

        embed = Embed(title="Reminder!", color=Color.blurple(), timestamp=due)
        embed.set_image(url=WHITE_BAR)

        if not (channel := self.bot.get_channel(channel_id)):
            channel = await self.bot.fetch_channel(channel_id)

        thread = Object(id=thread_id) if thread_id else MISSING

        webhook = await self.bot.webhook(channel)
        embed.description = text
        msg = await webhook.send(
            content=f"<@{author_id}>",
            username="Fennekin Reminder",
            avatar_url="https://hmp.me/dx4e",
            embed=embed,
            thread=thread,
            allowed_mentions=AllowedMentions(users=True),
            wait=True,
        )
        await tupper_log.insert_one(
            {
                "channel": msg.channel.id,
                "id": msg.id,
                "author": author_id,
            }
        )
        await remind.delete_one(
            {
                "author": author_id,
                "channel": channel_id,
                "thread": thread_id,
                "message": text,
            }
        )

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def remind(
        self,
        itx: Interaction[CustomBot],
        text: str,
        due: str,
    ):
        """Fennekin Reminder System

        Parameters
        ----------
        itx : Interaction[CustomBot]
            Interaction[CustomBot]
        text: str
            Message to remind
        due: str
            Time until notification, e.g. "in 5 hours", "tomorrow at 3pm", "next week", etc.
        """
        remind = self.bot.mongo_db("Reminder")

        try:
            until = itx.created_at + parse(due, settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc"))
        except Exception:
            return await itx.response.send_message("Invalid date format.", ephemeral=True)

        if until <= itx.created_at:
            return await itx.response.send_message("Invalid date, only future dates can be used.", ephemeral=True)

        if isinstance(itx.channel, Thread):
            channel_id, thread_id = itx.channel.parent_id, itx.channel.id
        else:
            channel_id, thread_id = itx.channel_id, None

        params = {
            "author": itx.user.id,
            "channel": channel_id,
            "thread": thread_id,
            "message": text,
            "due": until,
        }
        result = await remind.insert_one(params)
        params["_id"] = result.inserted_id
        await itx.response.send_message("Reminder has been created successfully.!", ephemeral=True)
        await self.bot.scheduler.add_schedule(
            self.remind_action,
            trigger=DateTrigger(until),
            id=f"reminder-{result.inserted_id}",
            args=(params,),
        )


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Reminder(bot))
