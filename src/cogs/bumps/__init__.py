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
        self.bump_pings: dict[int, Message] = {}
        self.bump_notifs: dict[int, Message] = {}

    @Cog.listener()
    async def on_message(self, message: Message):
        """Upon message detects if it's a successful bump for reminding purposes.

        Parameters
        ----------
        message: Message
            Message with possible bump information

        Returns
        -------

        """
        if message.author == self.bot.user:
            return

        if not message.author.bot or not message.embeds or not (item := BumpBot.get(id=message.author.id)):
            return

        self.bot.msg_cache_add(message)
        w = await self.bot.webhook(message.channel)
        bump = PingBump(after=message, data=item, webhook=w, bumps=self.bump_pings)

        if bump.valid:
            if msg := self.bump_pings.pop(message.author.id, None):
                await msg.delete(delay=0)

            if msg := self.bump_notifs.pop(message.author.id, None):
                await msg.delete(delay=0)

            await message.delete(delay=0)

        elif timedelta := bump.timedelta:
            await sleep(timedelta.total_seconds())

        self.bump_notifs[message.author.id] = await bump.send(timeout=False)
        await bump.wait()
        self.bump_pings[message.author.id] = await bump.send(timeout=True)

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

        self.bot.msg_cache_add(after)
        w = await self.bot.webhook(after.channel)
        bump = PingBump(before=before, after=after, data=item, webhook=w, bumps=self.bump_pings)
        if bump.valid:
            if msg := self.bump_pings.pop(after.author.id, None):
                await msg.delete(delay=0)

            if msg := self.bump_notifs.pop(after.author.id, None):
                await msg.delete(delay=0)

            await after.delete(delay=0)

        elif timedelta := bump.timedelta:
            await sleep(timedelta.total_seconds())

        self.bump_notifs[after.author.id] = await bump.send(timeout=False)
        await bump.wait()
        self.bump_pings[after.author.id] = await bump.send(timeout=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Bump(bot))
