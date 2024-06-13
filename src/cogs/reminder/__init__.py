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
from discord import AllowedMentions, Color, Embed, Interaction, app_commands
from discord.ext import commands

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

        author_id, channel_id, text, due = (
            payload["author"],
            payload["channel"],
            payload["message"],
            payload["due"],
        )

        embed = Embed(title="Reminder!", color=Color.blurple(), timestamp=due)
        embed.set_image(url=WHITE_BAR)
        embed.set_thumbnail(
            url="https://cdn.discordapp.com/attachments/1196879060232573021/1250846338728333422/Fennekin.png"
        )

        if not (channel := self.bot.get_channel(channel_id)):
            channel = await self.bot.fetch_channel(channel_id)

        embed.description = text
        await channel.send(
            content=f"<@{author_id}>",
            embed=embed,
            allowed_mentions=AllowedMentions(users=True),
        )
        await remind.delete_one({"_id": payload["_id"]})

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def remind(self, itx: Interaction[CustomBot], text: str, due: str):
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
            until = parse(due, settings=dict(PREFER_DATES_FROM="future", RELATIVE_BASE=itx.created_at))
            if not until:
                raise Exception
            until = until.astimezone(itx.created_at.tzinfo)
        except Exception:
            return await itx.response.send_message("Invalid date format.", ephemeral=True)

        if not until or until <= itx.created_at:
            return await itx.response.send_message("Invalid date, only future dates can be used.", ephemeral=True)

        params = {
            "author": itx.user.id,
            "channel": itx.channel_id,
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
