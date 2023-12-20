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


from asyncio import sleep

from discord import Message
from discord.ext.commands import Cog

from src.cogs.bumps.bumps import BumpBot, PingBump
from src.structures.bot import CustomBot

__all__ = ("Bump", "setup")


class Bump(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.bump_pings: dict[tuple[int, int], Message] = {}
        self.bump_notifs: dict[tuple[int, int], Message] = {}

    @Cog.listener()
    async def on_message(self, message: Message):
        """Upon message detects if it's a successful bump for reminding purposes.

        Parameters
        ----------
        message: Message
            Message with possible bump information
        """
        if not (
            message.guild
            and message.author != self.bot.user
            and message.author.bot
            and message.embeds
            and (item := BumpBot.get(id=message.author.id))
        ):
            return

        key = message.guild.id, message.author.id
        self.bot.msg_cache_add(message)
        w = await self.bot.webhook(message.channel)
        bump = PingBump(after=message, data=item, webhook=w)

        if not bump.valid:
            return

        if msg := self.bump_pings.pop(key, None):
            await msg.delete(delay=0)

        if msg := self.bump_notifs.pop(key, None):
            await msg.delete(delay=0)

        await message.delete(delay=0)
        self.bump_notifs[key] = await bump.send(timeout=False)
        await sleep(bump.timedelta.total_seconds())
        self.bump_pings[key] = await bump.send(timeout=True)

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        """Bump handler for message editing bots

        Parameters
        ----------
        before : Message
            Message before editing
        after : Message
            Message after editing
        """
        if (after.author == self.bot.user or not after.author.bot or not after.embeds) or not (
            item := BumpBot.get(id=after.author.id)
        ):
            return

        key = before.guild.id, after.author.id
        self.bot.msg_cache_add(after)
        w = await self.bot.webhook(after.channel)
        bump = PingBump(before=before, after=after, data=item, webhook=w)

        if not bump.valid:
            return

        if msg := self.bump_pings.pop(key, None):
            await msg.delete(delay=0)

        if msg := self.bump_notifs.pop(key, None):
            await msg.delete(delay=0)

        await after.delete(delay=0)
        self.bump_notifs[key] = await bump.send(timeout=False)
        await sleep(bump.timedelta.total_seconds())
        self.bump_pings[key] = await bump.send(timeout=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Bump(bot))
