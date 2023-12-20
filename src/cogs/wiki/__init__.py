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


from discord.ext import commands

from src.pagination.wiki import WikiComplex, WikiEntry
from src.structures.bot import CustomBot


class Wiki(commands.Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot

    @commands.hybrid_command(name="help", aliases=["wiki"])
    async def help(self, ctx: commands.Context[CustomBot], search: str = ""):
        """Built-in Bot Wiki

        Parameters
        ----------
        ctx : commands.Context[CustomBot]
            Context
        search : str
            Lookup term
        """
        guild_id = ctx.guild.id if ctx.guild else None
        entries = await self.bot.mongo_db("Wiki").find({"server": guild_id}).to_list(length=None)
        data = page = WikiEntry.from_list(entries)

        if search:
            nodes = [item for item in page.flatten if item.contains(search)]
            data = WikiEntry.from_list(nodes, path="Search Results")
            data.parent = page
            page.add_node(data)

        edit_mode = await self.bot.is_owner(ctx.author)

        if ctx.guild and not edit_mode:
            edit_mode = ctx.permissions.administrator

        view = WikiComplex(tree=data, context=ctx, edit_mode=edit_mode)
        if search:
            data.embeds = [view.embed]
            data.embeds[0].title = f"Search: {search.title()}"

        await view.simple_send(ephemeral=True, embeds=data.embeds)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Wiki(bot))
