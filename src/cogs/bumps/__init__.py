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

    @Cog.listener()
    async def on_message(self, ctx: Message):
        """Upon message detects if it's a successful bump for reminding purposes.

        Parameters
        ----------
        ctx: Message
            Message with possible bump information

        Returns
        -------

        """
        if ctx.author == self.bot.user:
            return

        if not (ctx.author.bot and ctx.embeds):
            return

        if item := BumpBot.get(id=ctx.author.id):
            self.bot.msg_cache_add(ctx)
            w = await self.bot.webhook(ctx.channel)
            bump = PingBump(after=ctx, data=item, webhook=w)
            if bump.valid:
                await ctx.delete(delay=0)
            elif timedelta := bump.timedelta:
                await sleep(timedelta.total_seconds())
            await bump.send()

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
        if (
            after.author == self.bot.user
            or not after.author.bot
            or not after.embeds
        ):
            return

        if item := BumpBot.get(id=after.author.id):
            self.bot.msg_cache_add(after)
            w = await self.bot.webhook(after.channel)
            bump = PingBump(before=before, after=after, data=item, webhook=w)
            if bump.valid:
                await after.delete(delay=0)
            elif timedelta := bump.timedelta:
                await sleep(timedelta.total_seconds())
            await bump.send()


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Bump(bot))
