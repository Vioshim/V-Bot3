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

from discord import (
    Color,
    Embed,
    Interaction,
    InteractionResponse,
    Message,
    TextStyle,
    app_commands,
)
from discord.ext import commands
from discord.ui import Modal, TextInput
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.wiki.wiki import WikiEntry, WikiNodeArg, WikiTreeArg
from src.cogs.wiki.wiki_complex import WikiComplex
from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR


class WikiPathModal(Modal, title="Wiki Path"):
    def __init__(self, message: Message) -> None:
        super(WikiPathModal, self).__init__(timeout=None)
        self.message = message
        self.folder = TextInput(label="Path", style=TextStyle.paragraph, required=True, default="/")
        self.redirect = TextInput(label="Change", style=TextStyle.paragraph, required=False)
        self.add_item(self.folder)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        path = self.folder.value
        db: AsyncIOMotorCollection = interaction.client.mongo_db("Wiki")
        redirect_path = self.redirect.value or path
        content, embeds = self.message.content, self.message.embeds

        if not self.message.author.bot:
            embeds = []

        embed = Embed(color=Color.blurple())
        embed.set_image(url=WHITE_BAR)
        if content and not embeds:
            split = content.split("\n")
            if len(split) < 2:
                split = ["", content]
            embed.title = split[0]
            embed.description = "\n".join(split[1:])
            embed.set_image(url=WHITE_BAR)
            embeds = [embed]
            content = ""
        elif stickers := self.message.stickers:
            embed.title = stickers[0].name
            embed.set_image(url=stickers[0].url)

        if attachments := [x for x in self.message.attachments if x.content_type.startswith("image/")]:
            if len(embeds) == len(attachments) == 1:
                embed.set_image(url=attachments[0].url)
            else:
                aux_embed = embed.copy()
                aux_embed.title = ""
                aux_embed.description = ""
                embeds.extend(aux_embed.copy().set_image(url=x.url) for x in attachments)

        entry = WikiEntry(path=redirect_path, content=content, embeds=embeds)
        await db.replace_one({"path": path}, entry.simplified, upsert=True)
        interaction.client.logger.info("Wiki(%s) modified by %s", path, interaction.user.display_name)
        embed = Embed(title=redirect_path, description="Modified successfully!", color=interaction.user.color)
        embed.set_image(url=WHITE_BAR)
        await resp.send_message(embed=embed, ephemeral=True)
        self.stop()


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
        role = ctx.guild.get_role(996542547155497082)
        if role and role in ctx.user.roles:
            await resp.send_modal(WikiPathModal(msg))
        else:
            return await resp.send_message("User hasn't been authorized for adding wiki entries", ephemeral=True)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def wiki(self, ctx: Interaction, group: Optional[WikiTreeArg], page: Optional[WikiNodeArg]):
        """Built-in server Wiki

        Parameters
        ----------
        ctx : Interaction
            Context
        group : WikiTreeArg
            Group
        page : WikiNodeArg
            Parameter
        """
        page: Optional[WikiEntry] = page or group

        if not page:
            entries = await self.bot.mongo_db("Wiki").find({}).to_list(length=None)
            page = WikiEntry.from_list(entries)

        view = WikiComplex(tree=page, target=ctx)
        async with view.send(ephemeral=True, embeds=page.embeds, content=page.content):
            self.bot.logger.info("%s is reading wiki's page: %s", ctx.user.display_name, page.path)

    @commands.command()
    async def wiki_remove(self, ctx: commands.Context, *, path: str):
        class WikiModal(Modal, title="Wiki Route"):
            def __init__(self, tree: WikiEntry) -> None:
                super(WikiModal, self).__init__(timeout=None)
                self.tree = tree
                self.folder = TextInput(
                    label="Wiki Folder",
                    style=TextStyle.paragraph,
                    required=True,
                    default=tree.route,
                )
                self.add_item(self.folder)

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
