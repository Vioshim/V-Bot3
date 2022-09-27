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


from contextlib import suppress
from datetime import datetime
from typing import Optional

from dateparser import parse
from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    Interaction,
    Object,
    TextStyle,
    Thread,
    app_commands,
)
from discord.ext import commands
from discord.ext.tasks import loop
from discord.ui import Modal, TextInput
from discord.utils import MISSING

from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR


class ReminderModal(Modal, title="Reminder"):
    due = TextInput(
        label="Due (When should I notify you?)",
        placeholder="In 1 hour",
    )
    message = TextInput(
        label="Message",
        style=TextStyle.paragraph,
        placeholder="This is what I'll be reminding you of.",
    )

    @classmethod
    async def send(cls, interaction: Interaction, date: Optional[str], message: str):
        bot: CustomBot = interaction.client
        await interaction.response.defer(ephemeral=True)
        embed = Embed(title="Reminder Command", color=Color.blurple())
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=interaction.guild.name, icon_url=interaction.guild.icon)
        date = parse(date or "", settings=dict(PREFER_DATES_FROM="future", TIMEZONE="utc"))
        if not date or date <= interaction.created_at:
            embed.description = "Invalid date, unable to identify. Only future dates can be used."
        else:
            embed.timestamp = date
            embed.description = "Reminder has been created successfully.!"
            channel, thread = interaction.channel, None
            if isinstance(channel, Thread):
                thread = channel.id
                channel = channel.parent
            await bot.mongo_db("Reminder").insert_one(
                {
                    "author": interaction.user.id,
                    "channel": channel.id,
                    "thread": thread,
                    "message": message,
                    "due": date,
                }
            )
        await interaction.followup.send(embed=embed, ephemeral=True)

    async def on_submit(self, interaction: Interaction) -> None:
        await self.send(interaction, self.due.value, self.message.value)
        self.stop()


class Reminder(commands.Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.remind_action.start()

    async def cog_unload(self) -> None:
        self.remind_action.stop()

    @loop(seconds=1)
    async def remind_action(self):
        remind = self.bot.mongo_db("Reminder")
        tupper_log = self.bot.mongo_db("Tupper-logs")
        condition = {"due": {"$lte": datetime.utcnow()}}
        embed = Embed(title="Reminder!", color=Color.blurple())
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text="You can react with ❌ to delete this message.")

        async for item in remind.find(condition):
            author_id, channel_id, thread_id, message = (
                item["author"],
                item["channel"],
                item["thread"],
                item["message"],
            )
            channel = self.bot.get_channel(channel_id)
            thread = Object(id=thread_id) if thread_id else MISSING
            if not channel:
                continue
            guild = channel.guild
            member = guild.get_member(author_id)
            if not member:
                continue
            webhook = await self.bot.webhook(channel)
            embed.description = message
            with suppress(DiscordException):
                msg = await webhook.send(
                    content=member.mention,
                    username="Fennekin Reminder",
                    avatar_url="https://hmp.me/dx4e",
                    embed=embed,
                    thread=thread,
                    allowed_mentions=AllowedMentions(users=True),
                    wait=True,
                )
                await msg.add_reaction("\N{CROSS MARK}")
                await tupper_log.insert_one({"channel": msg.channel.id, "id": msg.id, "author": author_id})

        await remind.delete_many(condition)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def remind(self, ctx: Interaction, message: Optional[str], due: Optional[str]):
        """Fennekin Reminder System

        Parameters
        ----------
        ctx : Interaction
            Interaction
        message : str
            Message to remind
        due : str
            Time until notification
        """
        if message and due:
            await ReminderModal.send(ctx, due, message)
        else:
            modal = ReminderModal(timeout=None)
            await ctx.response.send_modal(modal)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Reminder(bot))
