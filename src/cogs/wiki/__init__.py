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


from typing import Optional

from discord import Interaction, app_commands
from discord.ext import commands

from src.cogs.wiki.wiki import WikiEntry, WikiNodeArg, WikiTreeArg
from src.structures.bot import CustomBot


class Wiki(commands.Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.tree: WikiEntry = WikiEntry()

    async def cog_load(self) -> None:
        items = await self.bot.mongo_db("Wiki").find({}).to_list(length=None)
        self.tree = WikiEntry.from_list(items)

    @app_commands.command()
    async def wiki(self, ctx: Interaction, group: WikiTreeArg, word: Optional[WikiNodeArg]):
        """Built-in server Wiki

        Parameters
        ----------
        ctx : Interaction
            Context
        group : WikiTreeArg
            Group
        word : WikiNodeArg
            Parameter
        """
        word = "/" if not word else word.route
        self.bot.logger.info("Test 1: %s - 2: %s", group.route, word)
        await ctx.response.send_message("This is a test", embeds=group.embeds, ephemeral=True)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Wiki(bot))
