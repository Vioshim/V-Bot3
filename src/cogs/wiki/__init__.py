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
        self.order = TextInput(label="Order", required=False, default="0")
        self.tags = TextInput(label="Tags", style=TextStyle.paragraph, required=False)
        self.add_item(self.folder)
        self.add_item(self.redirect)
        self.add_item(self.order)
        self.add_item(self.tags)

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        path = self.folder.value
        try:
            await resp.defer(ephemeral=True, thinking=True)
            db: AsyncIOMotorCollection = interaction.client.mongo_db("Wiki")
            redirect_path = (self.redirect.value or path).removesuffix("/")
            content, embeds = self.message.content, self.message.embeds

            if not self.message.author.bot:
                embed = Embed(color=Color.blurple())
                embed.set_image(url=WHITE_BAR)
                split = content.split("\n")
                if len(split) < 2:
                    split = ["", content]
                embed.title = split[0]
                embed.description = "\n".join(split[1:])
                embed.set_image(url=WHITE_BAR)
                embeds = [embed]
                content = ""
                attachments = [x for x in self.message.attachments if x.content_type.startswith("image/")]
                if len(embeds) == len(attachments) == 1:
                    embed.set_image(url=attachments[0].url)
                elif attachments:
                    aux_embed = embed.copy()
                    aux_embed.title = ""
                    aux_embed.description = ""
                    embeds.extend(aux_embed.copy().set_image(url=x.url) for x in attachments)

            tags = [x.strip() for x in self.tags.value.split(",")]
            order = int(self.order.value) if self.order.value else 0
            entry = WikiEntry(path=redirect_path, content=content, embeds=embeds, tags=tags, order=order)
            await db.replace_one({"path": path.removesuffix("/")}, entry.simplified, upsert=True)
        except Exception as e:
            interaction.client.logger.exception(
                "Wiki(%s) had exception: %s",
                path,
                interaction.user.display_name,
                exc_info=e,
            )
        else:
            interaction.client.logger.info("Wiki(%s) modified by %s", path, interaction.user.display_name)
            embed = Embed(title=redirect_path, description="Modified successfully!", color=interaction.user.color)
            embed.set_image(url=WHITE_BAR)
            await interaction.followup.send(embed=embed, ephemeral=True)
        finally:
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
        if not (role and role in ctx.user.roles):
            return await resp.send_message("User hasn't been authorized for adding wiki entries", ephemeral=True)

        modal = WikiPathModal(msg)
        await resp.send_modal(modal)
        await modal.wait()

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def wiki(
        self,
        ctx: Interaction,
        group: Optional[WikiTreeArg],
        page: Optional[WikiNodeArg],
        search: Optional[str],
        tags: Optional[str],
    ):
        """Built-in server Wiki

        Parameters
        ----------
        ctx : Interaction
            Context
        group : WikiTreeArg
            Group
        page : WikiNodeArg
            Parameter
        search : str
            Lookup
        tags : str
            Tags separated by comma
        """
        page: Optional[WikiEntry] = page or group

        if not page:
            entries = await self.bot.mongo_db("Wiki").find({}).to_list(length=None)
            page = WikiEntry.from_list(entries)

        if tags:
            aux: set[str] = {x.strip().lower() for x in tags.split(",") if x.strip()}
            items = [item for item in page.flatten if aux.issubset(item.tags)]
            page = WikiEntry.from_list(items)

        if search:
            items = [item for item in page.flatten if item.contains(search)]
            page = WikiEntry.from_list(items)

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
