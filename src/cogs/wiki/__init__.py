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

from discord import Interaction, InteractionResponse, Message, app_commands
from discord.ext import commands

from src.cogs.wiki.wiki import WikiComplex, WikiEntry, WikiNodeArg, WikiTreeArg
from src.structures.bot import CustomBot


class Wiki(commands.Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Add to Wiki",
            callback=self.wiki_add,
            guild_ids=[719343092963999804],
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def wiki_add(self, ctx: Interaction, msg: Message):
        resp: InteractionResponse = ctx.response
        if ctx.user.id != 678374009045254198:
            return await resp.send_message("User hasn't been authorized for adding wiki entries", ephemeral=True)
        path = msg.embeds[-1].footer.text
        entry = WikiEntry(path=path, content=msg.content, embeds=msg.embeds)
        await self.bot.mongo_db("Wiki").replace_one({"path": path}, entry.simplified, upsert=True)
        await resp.send_message(f"{path!r} added/modified.!", ephemeral=True)

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
        page: WikiEntry = group or word
        view = WikiComplex(tree=page, target=ctx)
        async with view.send(ephemeral=True, embeds=page.embeds, content=page.content):
            self.bot.logger.info("%s is reading wiki's page: %s", ctx.user.display_name, page.path)

    @commands.command()
    async def wiki_remove(self, ctx: commands.Context, path: str):
        item = await self.bot.mongo_db("Wiki").delete_one({"path": path})
        if item.deleted_count:
            await ctx.reply("Path has been deleted!", delete_after=3)
        else:
            await ctx.reply("Path does not exist!", delete_after=3)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Wiki(bot))
