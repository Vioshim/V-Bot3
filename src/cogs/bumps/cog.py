# Copyright 2021 Vioshim
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

from discord import Message
from discord.ext.commands import Cog

from src.cogs.bumps.bumps import BumpsEnum, PingBump
from src.structures.bot import CustomBot


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
        if not (ctx.author.bot and ctx.embeds):
            return

        for item in BumpsEnum:
            if item.on_message(ctx):
                bump = PingBump(ctx, item.value)
                self.bot.msg_cache_add(ctx)
                await ctx.delete()
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

        if not (after.author.bot and after.embeds):
            return

        for item in BumpsEnum:
            if item.on_message_edit(before, after):
                bump = PingBump(after, item.value)
                self.bot.msg_cache_add(after)
                await after.delete()
                await bump.send()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Bump(bot))
