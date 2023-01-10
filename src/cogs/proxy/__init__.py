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


import asyncio
from contextlib import suppress
from textwrap import wrap
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View
from discord.utils import MISSING, get
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.cogs.pokedex.search import DefaultSpeciesArg
from src.cogs.proxy.proxy import ProxyFunction, ProxyVariantArg
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.pronouns import Pronoun
from src.structures.proxy import NPC, Proxy, ProxyExtra
from src.structures.species import Species
from src.utils.etc import LINK_EMOJI, WHITE_BAR
from src.utils.matches import BRACKETS_PARSER, EMOJI_REGEX

__all__ = ("Proxy", "setup")


class NameModal(Modal, title="NPC Name"):
    name = TextInput(label="Name", placeholder="Name", default="Narrator", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        """This is a function that handles the submission of the name.

        Parameters
        ----------
        interaction : Interaction
            Interaction that triggered the submission
        """
        resp = interaction.response
        await resp.pong()
        self.stop()


class ProxyMessageModal(Modal, title="Edit Proxy Message"):
    def __init__(self, msg: discord.Message, data: dict[str, int]) -> None:
        super(ProxyMessageModal, self).__init__(timeout=None)
        self.text = TextInput(
            label="Message (Empty = Delete)",
            placeholder="Once you press submit, the message will be deleted.",
            default=msg.content,
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=2000,
        )
        self.add_item(self.text)
        self.msg = msg
        self.data = data

    async def on_error(self, interaction: discord.Interaction, error: Exception, /) -> None:
        interaction.client.logger.error("Ignoring exception in modal %r:", self, exc_info=error)

    async def on_submit(self, interaction: discord.Interaction, /) -> None:
        resp = interaction.response
        db: AsyncIOMotorCollection = interaction.client.db("Tupper-logs")

        if not self.text.value:
            try:
                await self.msg.delete()
                await resp.send_message("Message has been deleted.", ephemeral=True, delete_after=3)
                await db.delete_one(self.data)
            except discord.Forbidden as e:
                await resp.send_message(str(e), ephemeral=True)
            except discord.NotFound:
                await resp.send_message("Message has been deleted.", ephemeral=True, delete_after=3)
                await db.delete_one(self.data)
            except discord.HTTPException as e:
                await resp.send_message(str(e), ephemeral=True)
            return

        w: discord.Webhook = await interaction.client.webhook(self.msg.channel)
        if not isinstance(thread := self.msg.channel, discord.Thread):
            thread = MISSING

        try:
            await w.edit_message(self.msg.id, content=self.text.value, thread=thread)
            await resp.send_message("Message has been edited successfully.", ephemeral=True, delete_after=3)
        except discord.Forbidden:
            await resp.send_message(
                "Webhooks restart when bot is re-added. Can't edit this message.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            await resp.send_message(str(e), ephemeral=True)


class ProxyModal(Modal, title="Prefixes"):
    def __init__(
        self,
        oc: Character,
        proxy: Optional[Proxy],
        variant: Optional[ProxyExtra | str],
        image_url: Optional[discord.Attachment] = None,
    ) -> None:
        super(ProxyModal, self).__init__(timeout=None)
        self.oc = oc
        self.proxy = (
            proxy
            if proxy
            else Proxy(
                id=oc.id,
                author=oc.author,
                server=oc.server,
                image=oc.image_url,
            )
        )
        self.proxy.name = oc.name
        if isinstance(variant, str):
            variant = ProxyExtra(name=variant, image=image_url or oc.image_url)
        elif isinstance(variant, ProxyExtra):
            self.proxy.remove_extra(variant)
            if image_url:
                variant.image = image_url
        elif image_url:
            self.proxy.image = image_url

        self.proxy1_data = TextInput(
            label=self.proxy.name[:45],
            placeholder="Each line must include word text",
            default="\n".join(map("text".join, self.proxy.prefixes)),
            style=discord.TextStyle.paragraph,
            required=False,
        )
        self.add_item(self.proxy1_data)
        self.proxy2_name = TextInput(
            label="Name",
            placeholder="Psst, ending with * makes bot only use this name.",
            required=False,
            max_length=80,
        )
        self.proxy2_data = TextInput(
            label="Variant",
            placeholder="Each line must include word text",
            required=False,
            style=discord.TextStyle.paragraph,
        )
        if variant:
            self.proxy2_name.default = variant.name[:80] or oc.name
            self.proxy2_data.default = "\n".join(map("text".join, variant.prefixes))
            self.add_item(self.proxy2_name)
            self.add_item(self.proxy2_data)
        self.variant = variant

    async def on_submit(self, ctx: discord.Interaction):
        """This is a function that handles the submission of the name.

        Parameters
        ----------
        interaction : Interaction
            Interaction that triggered the submission
        """
        resp = ctx.response
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Proxy")
        self.proxy.prefixes = frozenset(
            (o[0].strip(), o[-1].strip()) for x in self.proxy1_data.value.split("\n") if len(o := x.split("text")) > 1
        )

        image: Optional[discord.Attachment] = None
        phrase = f"{self.oc.name}"
        if item := self.variant:
            item.name = self.proxy2_name.value
            self.variant.prefixes = frozenset(
                (o[0].strip(), o[-1].strip())
                for x in self.proxy2_data.value.split("\n")
                if len(o := x.split("text")) > 1
            )
            self.proxy.extras |= {self.variant}
            if isinstance(self.variant.image, discord.Attachment):
                image = self.variant.image
                phrase = f"{phrase} - {self.variant.name}"
        elif isinstance(image := self.proxy.image, discord.Attachment):
            item = self.proxy

        if isinstance(image, discord.Attachment) and item:
            w: discord.Webhook = await ctx.client.webhook(1020151767532580934)
            file = await image.to_file()
            m = await w.send(
                phrase,
                file=file,
                wait=True,
                thread=discord.Object(id=1045687852069040148),
                username=ctx.user.display_name,
                avatar_url=ctx.user.display_avatar.url,
            )
            item.image = m.attachments[0].url

        embeds = [self.proxy.embed]
        if item := self.variant:
            embeds.append(item.embed)

        await resp.send_message(embeds=embeds, ephemeral=True)

        await db.replace_one(
            {
                "id": self.oc.id,
                "server": self.oc.server,
                "author": self.oc.author,
            },
            self.proxy.to_dict(),
            upsert=True,
        )
        self.stop()


class ProxyCog(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ctx_menu1 = app_commands.ContextMenu(
            name="Proxy",
            callback=self.msg_proxy,
            guild_ids=[719343092963999804],
        )
        self.last_names: dict[int, tuple[int, str]] = {}

    async def cog_load(self):
        self.bot.tree.add_command(self.ctx_menu1)

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu1.name, type=self.ctx_menu1.type)

    async def on_proxy_message(self, message: discord.Message):
        db = self.bot.mongo_db("Proxy")
        deleting: bool = False
        for index, (npc, text) in enumerate(
            Proxy.lookup(
                [
                    Proxy.from_mongo_dict(x)
                    async for x in db.find({"server": message.guild.id, "author": message.author.id})
                ],
                message.content,
            )
        ):
            deleting = True
            ctx = await self.bot.get_context(message)
            await self.proxy_handler(npc, ctx, text, attachments=index == 0, deleting=False)
        if deleting:
            await message.delete(delay=300 if message.mentions else 0)

    @commands.Cog.listener()
    async def on_message_edit(self, previous: discord.Message, current: discord.Message):
        if not (
            previous.webhook_id or previous.author.bot or not previous.guild or previous.content == current.content
        ):
            await self.on_proxy_message(current)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not (message.webhook_id or message.author.bot or not message.guild):
            await self.on_proxy_message(message)

    async def msg_proxy(self, ctx: discord.Interaction, msg: discord.Message):
        db1 = self.bot.mongo_db("Tupper-logs")
        db2 = self.bot.mongo_db("RP Logs")
        entry: Optional[dict[str, int]] = await db1.find_one({"channel": msg.channel.id, "id": msg.id})
        item: Optional[dict[str, int]] = await db2.find_one(
            {
                "$or": [
                    {"id": msg.id, "channel": msg.channel.id},
                    {"log": msg.id, "log-channel": msg.channel.id},
                ]
            }
        )
        member: discord.Member = self.bot.supporting.get(ctx.user, ctx.user)

        self.bot.logger.info("User %s is checking proxies at %s", str(ctx.user), msg.jump_url)

        if entry and member.id == entry["author"] and not (item and item["log-channel"] == ctx.channel_id):
            return await ctx.response.send_modal(ProxyMessageModal(msg, entry))

        await ctx.response.defer(ephemeral=True, thinking=True)

        view = View()
        view.add_item(Button(label="Jump URL", url=msg.jump_url))
        text = "Current associated information to the message."

        if item:
            if not entry:
                entry = await db1.find_one({"channel": item["log-channel"], "id": item["log"]})
            ch: discord.TextChannel = ctx.guild.get_channel_or_thread(item["log-channel"])
            with suppress(discord.DiscordException):
                aux_msg = await ch.fetch_message(item["log"])
                view = View.from_message(aux_msg)

        if not entry:
            text = "No information associated to the message."
        else:
            if not (user := ctx.guild.get_member(entry["author"])):
                user = await self.bot.get_or_fetch_user(entry["author"])

            if user:
                text = f"That message was sent by {user.mention} (tag: {user} - id: {user.id})."
            else:
                text = f"That message was sent by a Deleted User (id: {entry['author']})."

        await ctx.followup.send(text, view=view, ephemeral=True)

    async def proxy_handler(
        self,
        npc: Character | NPC | list[Proxy | ProxyExtra],
        ctx: commands.Context,
        text: str = None,
        attachments: bool = True,
        deleting: bool = True,
    ):
        webhook = await self.bot.webhook(ctx.channel, reason="NPC")

        if isinstance(npc, list):
            try:
                npc, extra = npc
            except ValueError:
                npc, extra = npc[0], None

            if isinstance(npc, Proxy) and isinstance(extra, ProxyExtra):
                username = f"{npc.name} ({extra.name})" if npc.name != extra.name else npc.name
                if extra.name.endswith("*") or len(username) > 80:
                    username = extra.name.removesuffix("*") or npc.name
                npc = NPC(name=username, image=extra.image or npc.image)

        if isinstance(npc, Character):
            npc = NPC(name=npc.name, image=npc.image_url)

        text = (text.strip() if text else None) or "\u200b"
        thread = view = MISSING
        if reference := ctx.message.reference:
            view = View().add_item(Button(label="Replying", url=reference.jump_url, emoji=LINK_EMOJI))
        if isinstance(ctx.channel, discord.Thread):
            thread = ctx.channel

        author_id, npc.name = ctx.author.id, Proxy.clyde(npc.name)

        if data := self.last_names.get(ctx.channel.id):
            alternate = Proxy.alternate(npc.name)
            if data[0] == author_id:
                npc.name = data[-1] if alternate == data[-1] else npc.name
            elif data[-1] == npc.name:
                npc.name = alternate

        embeds = []
        for item in BRACKETS_PARSER.finditer(text):
            aux = item.group(1)
            try:
                if proxy_data := await ProxyFunction.lookup(ctx, npc, aux):
                    npc, data_text, data_embed = proxy_data
                    if data_embed is None or len(embeds) < 10:
                        text = text.replace("{{" + aux + "}}", data_text, 1)
                        if data_embed:
                            data_embed.color = data_embed.color or ctx.author.color
                            embeds.append(data_embed)
            except Exception as e:
                self.bot.logger.exception("Failed to parse %s", aux, exc_info=e)
                continue

        for item in EMOJI_REGEX.finditer(text):
            match item.groupdict():
                case {"animated": "a", "name": name, "id": id}:
                    if id.isdigit() and not self.bot.get_emoji(int(id)):
                        url = f"[{name}](https://cdn.discordapp.com/emojis/{id}.gif?size=60&quality=lossless)"
                        text = EMOJI_REGEX.sub(url, text)
                case {"name": name, "id": id}:
                    if id.isdigit() and not self.bot.get_emoji(int(id)):
                        url = f"[{name}](https://cdn.discordapp.com/emojis/{id}.webp?size=60&quality=lossless)"
                        text = EMOJI_REGEX.sub(url, text)

        if ctx.message.attachments and attachments:
            files = [await item.to_file() for item in ctx.message.attachments]
        else:
            files = []

        for paragraph in wrap(
            text or "\u200b",
            2000,
            replace_whitespace=False,
            placeholder="",
        ):
            await asyncio.sleep(0.5)
            proxy_msg = await webhook.send(
                username=npc.name[:80],
                avatar_url=npc.image,
                embeds=embeds,
                content=paragraph.strip() or "\u200b",
                files=files,
                wait=True,
                view=view,
                thread=thread,
            )
            self.last_names[ctx.channel.id] = (ctx.author.id, proxy_msg.author.display_name)
            await self.bot.mongo_db("Tupper-logs").insert_one(
                {
                    "channel": ctx.channel.id,
                    "id": proxy_msg.id,
                    "author": author_id,
                }
            )
            if deleting:
                await ctx.message.delete(delay=300 if ctx.message.mentions else 0)

    @app_commands.command(description="Proxy management")
    @app_commands.guilds(719343092963999804)
    async def proxy(
        self,
        ctx: discord.Interaction,
        oc: CharacterArg,
        variant: Optional[ProxyVariantArg],
        image: Optional[discord.Attachment],
        delete: bool = False,
    ):
        """Proxy Command

        Parameters
        ----------
        ctx : Interaction
            Context
        oc : CharacterArg
            Chaaracter
        variant : Optional[ProxyVariantArg]
            Emotion Variant
        image : Optional[Attachment]
            Image
        delete : bool, optional
            If deleting proxy/variant
        """
        db = self.bot.mongo_db("Proxy")
        key = {"id": oc.id, "server": oc.server, "author": oc.author}
        member = self.bot.supporting.get(ctx.user, ctx.user)
        data = await db.find_one(key)
        proxy = Proxy.from_mongo_dict(data) if data else None
        var_proxy = get(proxy.extras, name=variant) if proxy else variant

        if delete:
            if proxy is None:
                embed = discord.Embed(title="Proxy not found")
                embed.set_author(name=oc.name, url=oc.jump_url, icon_url=oc.image_url)
            elif isinstance(var_proxy, ProxyExtra):
                proxy.remove_extra(var_proxy)
                embed = var_proxy.embed.set_footer(text="Proxy's Variant was removed")
                await db.replace_one(key, proxy.to_dict(), upsert=True)
            elif variant:
                embed = discord.Embed(title="Proxy's Variant not Found", description=variant)
                embed.set_author(name=proxy.name, icon_url=proxy.image)
            else:
                embed = proxy.embed.set_footer(text="Proxy was removed")
                await db.delete_one(key)
            embed.color, embed.timestamp = member.color, ctx.created_at
            embed.set_image(url=WHITE_BAR)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        if not (image and image.content_type.startswith("image/")):
            image = None

        modal = ProxyModal(oc, proxy, var_proxy or variant, image)
        await ctx.response.send_modal(modal)

    @app_commands.command(name="npc", description="Slash command for NPC Narration")
    @app_commands.guilds(719343092963999804)
    async def slash_npc(
        self,
        ctx: discord.Interaction,
        name: Optional[str],
        pokemon: Optional[DefaultSpeciesArg],
        shiny: Optional[bool],
        pronoun: Optional[Pronoun],
        character: Optional[CharacterArg],
        image: Optional[discord.Attachment],
    ):
        """Slash command for NPC Narration

        Parameters
        ----------
        ctx : ApplicationContext
            Context
        name : Optional[str]
            Name of the NPC
        pokemon : str, optional
            Species to use
        shiny : bool, optional
            If Shiny
        pronoun : str, optional
            Sprite to use
        character : str, optional
            Character
        image : Optional[Attachment]
            Image to use
        """
        resp = ctx.response
        name = character.name if character else name

        if pokemon and pokemon.banned:
            pokemon = None

        if pokemon and not name:
            name = f"NPC〕{pokemon.name}"

        if not name:
            modal = NameModal(timeout=None)
            await resp.send_modal(modal)
            await modal.wait()
            name = modal.name.value

        if image and image.content_type.startswith("image/"):
            w = await self.bot.webhook(1020151767532580934)
            file = await image.to_file()
            m = await w.send(
                name,
                file=file,
                wait=True,
                thread=discord.Object(id=1045687852069040148),
                username=ctx.user.display_name,
                avatar_url=ctx.user.display_avatar.url,
            )
            image = m.attachments[0].url
        else:
            image = None

        if pokemon and not image:
            image = pokemon.image(shiny=shiny, gender=pronoun)

        if resp.is_done():
            context = ctx.followup.send
        else:
            context = resp.send_message

        npc = NPC(name, image)
        await self.bot.mongo_db("NPC").replace_one(
            {"author": ctx.user.id},
            {"author": ctx.user.id, "name": npc.name, "image": npc.image},
            upsert=True,
        )
        await context(
            content=f'NPC has been set as `{npc.name}`, you can now use it with `?npci`. Example ?npci "Hello".',
            ephemeral=True,
        )

    @commands.command(name="npc")
    @commands.guild_only()
    async def cmd_npc(self, ctx: commands.Context, pokemon: str, *, text: str = None):
        """Inplace NPC Narration

        Parameters
        ----------
        ctx : commands.Context
            _description_
        text : str, optional
            _description_, by default None
        """
        if (mon := Species.single_deduce(pokemon)) and not mon.banned:
            npc = NPC(name=f"NPC〕{mon.name}", image=mon.base_image)
            await self.proxy_handler(npc=npc, ctx=ctx, text=text)
        else:
            await ctx.message.delete(delay=0)

    @commands.command(name="pc")
    @commands.guild_only()
    async def cmd_pc(self, ctx: commands.Context, pokemon: str, *, text: str = None):
        """Inplace PC Narration

        Parameters
        ----------
        ctx : commands.Context
            _description_
        text : str, optional
            _description_, by default None
        """
        db1 = self.bot.mongo_db("Characters")
        db2 = self.bot.mongo_db("Proxy")
        member = self.bot.supporting.get(ctx.author, ctx.author)
        key = {"author": member.id, "server": ctx.guild.id}
        ocs = [Character.from_mongo_dict(x) async for x in db1.find(key)]
        ocs = {oc.name: oc for oc in ocs}
        async for x in db2.find(key):
            proxy = Proxy.from_mongo_dict(x)
            ocs[proxy.name] = proxy

        if options := process.extractOne(pokemon, choices=list(ocs), score_cutoff=60):
            await self.proxy_handler(npc=ocs[options[0]], ctx=ctx, text=text)
        else:
            await ctx.message.delete(delay=0)

    @commands.command(name="npci")
    @commands.guild_only()
    async def cmd_npci(self, ctx: commands.Context, *, text: str = None):
        """Command for NPCs

        Parameters
        ----------
        ctx : Context
            Context
        pokemon : SpeciesCall
            Species
        text : str, optional
            Text, by default None
        """
        if entry := await self.bot.mongo_db("NPC").find_one({"author": ctx.author.id}):
            npc = NPC(name=entry["name"], image=entry["avatar"] if "avatar" in entry else entry["image"])
            await self.proxy_handler(npc=npc, ctx=ctx, text=text)
        else:
            await ctx.message.delete(delay=0)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """On raw reaction added

        Parameters
        ----------
        payload : RawReactionActionEvent
            Reaction added
        """
        guild = self.bot.get_guild(payload.guild_id)

        if not guild:
            return

        if payload.member.bot:
            return

        if (emoji := str(payload.emoji)) not in ["\N{CROSS MARK}", "\N{BLACK QUESTION MARK ORNAMENT}"]:
            return

        db = self.bot.mongo_db("Tupper-logs")
        entry: Optional[dict[str, str]] = await db.find_one(
            {
                "channel": payload.channel_id,
                "id": payload.message_id,
            }
        )
        if not entry:
            return

        if not (channel := guild.get_channel_or_thread(payload.channel_id)):
            channel = await self.bot.fetch_channel(payload.channel_id)

        message = await channel.fetch_message(payload.message_id)
        author_id: int = entry["author"]

        if emoji == "\N{CROSS MARK}" and author_id == payload.member.id:
            await message.delete(delay=0)
            await db.delete_one(entry)
        elif emoji == "\N{BLACK QUESTION MARK ORNAMENT}":
            await message.clear_reaction(emoji=payload.emoji)
            if not (user := guild.get_member(author_id)):
                user = await self.bot.get_or_fetch_user(author_id)

            view = View()
            view.add_item(Button(label="Jump URL", url=message.jump_url))

            if user:
                text = f"That message was sent by {user.mention} (tag: {user} - id: {user.id})."
            else:
                text = f"That message was sent by a Deleted User (id: {author_id})."

            with suppress(discord.DiscordException):
                await payload.member.send(text, view=view)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(ProxyCog(bot))
