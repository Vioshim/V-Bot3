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


from contextlib import suppress
from dataclasses import dataclass
from typing import NamedTuple, Optional

from discord import (
    Attachment,
    DiscordException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Object,
    RawReactionActionEvent,
    TextChannel,
    TextStyle,
    Thread,
    Webhook,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View
from discord.utils import MISSING, find, get
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.cogs.pokedex.search import DefaultSpeciesArg
from src.cogs.proxy.proxy import ProxyVariantArg
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.pronouns import Pronoun
from src.structures.proxy import Proxy
from src.structures.species import Species
from src.utils.etc import LINK_EMOJI

__all__ = ("Proxy", "setup")


@dataclass(unsafe_hash=True, slots=True)
class NPC:
    name: str = "Narrator"
    avatar: str = "https://hmp.me/dx4a"


class NameModal(Modal, title="NPC Name"):
    name = TextInput(label="Name", placeholder="Name", default="Narrator", required=True)

    async def on_submit(self, interaction: Interaction):
        """This is a function that handles the submission of the name.

        Parameters
        ----------
        interaction : Interaction
            Interaction that triggered the submission
        """
        resp: InteractionResponse = interaction.response
        await resp.pong()
        self.stop()


class ProxyModal(Modal, title="Edit Proxy Message"):
    def __init__(self, msg: Message, data: dict[str, int]) -> None:
        super(ProxyModal, self).__init__(timeout=None)
        self.text = TextInput(
            label="Message (Empty = Delete)",
            placeholder="Once you press submit, the message will be deleted.",
            default=msg.content,
            style=TextStyle.paragraph,
            required=False,
            max_length=2000,
        )
        self.add_item(self.text)
        self.msg = msg
        self.data = data

    async def on_error(self, interaction: Interaction, error: Exception, /) -> None:
        interaction.client.logger.error("Ignoring exception in modal %r:", self, exc_info=error)

    async def on_submit(self, interaction: Interaction, /) -> None:
        resp: InteractionResponse = interaction.response
        if not self.text.value:
            await self.msg.delete(delay=0)
            return await resp.send_message("Message has been deleted.", ephemeral=True, delete_after=3)

        db: AsyncIOMotorCollection = interaction.client.mongo_db("Tupper-logs")
        w: Webhook = await interaction.client.webhook(self.msg.channel)
        thread = self.msg.channel if isinstance(self.msg.channel, Thread) else MISSING
        try:
            await w.edit_message(self.msg.id, content=self.text.value, thread=thread)
            await resp.send_message("Message has been edited successfully.", ephemeral=True, delete_after=3)
        except DiscordException:
            await db.delete_one(self.data)


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

    async def msg_proxy(self, ctx: Interaction, msg: Message):
        db1 = self.bot.mongo_db("Tupper-logs")
        db2 = self.bot.mongo_db("RP Logs")
        entry: Optional[dict[str, int]] = await db1.find_one({"channel": msg.channel.id, "id": msg.id})
        member: Member = self.bot.supporting.get(ctx.user, ctx.user)

        self.bot.logger.info("User %s is checking proxies at %s", str(ctx.user), msg.jump_url)

        if entry and member.id == entry["author"]:
            return await ctx.response.send_modal(ProxyModal(msg, entry))

        await ctx.response.defer(ephemeral=True, thinking=True)

        view = View()
        view.add_item(Button(label="Jump URL", url=msg.jump_url))
        text = "Current associated information to the message."

        if item := await db2.find_one(
            {
                "$or": [
                    {"id": msg.id, "channel": msg.channel.id},
                    {"log": msg.id, "log-channel": msg.channel.id},
                ]
            }
        ):
            if not entry:
                entry = await db1.find_one({"channel": item["log-channel"], "id": item["log"]})
            ch: TextChannel = ctx.guild.get_channel_or_thread(item["log-channel"])
            with suppress(DiscordException):
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

    async def proxy_handler(self, npc: NPC, message: Message, text: str = None):
        webhook = await self.bot.webhook(message.channel, reason="NPC")
        text = text or "\u200b"
        thread = view = MISSING
        if reference := message.reference:
            view = View().add_item(Button(label="Replying", url=reference.jump_url, emoji=LINK_EMOJI))
        if isinstance(message.channel, Thread):
            thread = message.channel

        author_id, npc.name = message.author.id, Proxy.clyde(npc.name)

        if data := self.last_names.get(message.channel.id):
            alternate = Proxy.alternate(npc.name)
            if data[0] == author_id:
                npc.name = data[-1] if alternate == data[-1] else npc.name
            elif data[-1] == npc.name:
                npc.name = alternate

        proxy_msg = await webhook.send(
            username=npc.name[:80],
            avatar_url=npc.avatar,
            content=text,
            files=[await item.to_file() for item in message.attachments],
            wait=True,
            view=view,
            thread=thread,
        )
        self.last_names[message.channel.id] = (message.author.id, proxy_msg.author.display_name)
        await self.bot.mongo_db("Tupper-logs").insert_one(
            {
                "channel": message.channel.id,
                "id": proxy_msg.id,
                "author": author_id,
            }
        )
        await message.delete(delay=300 if message.mentions else 0)

    @app_commands.command(description="Proxy management")
    @app_commands.guilds(719343092963999804)
    async def proxy(
        self,
        ctx: Interaction,
        oc: CharacterArg,
        variant: Optional[ProxyVariantArg],
        image: Optional[Attachment],
        prefix: Optional[str] = "",
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
        prefix : Optional[str], optional
            Must include word text
        delete : bool, optional
            If deleting proxy/variant
        """

        await ctx.response.defer(ephemeral=True, thinking=True)

        if prefix and "text" not in prefix:
            await ctx.followup.send("Invalid Prefix", ephemeral=True)

        member: Member = self.bot.supporting.get(ctx.user, ctx.user)
        db = self.bot.mongo_db("Proxy")
        if image and image.content_type.startswith("image/"):
            w = await self.bot.webhook(1020151767532580934)
            file = await image.to_file()
            m = await w.send(
                f"{oc.name} - {variant}",
                file=file,
                wait=True,
                thread=Object(id=1045687852069040148),
                username=ctx.user.display_name,
                avatar_url=ctx.user.display_avatar.url,
            )
            image_url = m.attachments[0].url
        else:
            image_url = oc.image_url

        key = {"id": oc.id, "server": ctx.guild_id, "author": member.id}

        if data := await db.find_one(key):
            proxy = Proxy.from_mongo_dict(data)
            var_proxy = get(proxy.extras, name=variant)
        else:
            proxy = var_proxy = None

        if prefix:
            prefix_data = Proxy.prefix_handle(prefix)
            prefix_text = "text".join(prefix_data)
            prefixes_arg = frozenset({prefix_data})
        else:
            prefix_data, prefix_text, prefixes_arg = None, "", frozenset()

        if not proxy:  # No Proxy Found
            message = "No proxy for the character was previously created."
            if not delete:
                if variant:  # Creating w/ Variant
                    proxy = Proxy(id=oc.id, author=oc.author, server=oc.server, image=oc.image_url)
                    proxy.append_extra(name=variant, image=image_url, prefixes=prefixes_arg)
                    message = f"Created Proxy {proxy.name} - {variant}"
                else:  # Creating without Variant
                    proxy = Proxy(id=oc.id, author=oc.author, server=oc.server, image=image_url, prefixes=prefixes_arg)
                    message = f"Created Proxy {proxy.name}"
        elif var_proxy:  # Variant Found
            var_proxy.image = image_url
            message = f"Updating {oc.name} - {variant}"
            if delete:  # Remove Variant
                message = f"Removed variant {variant}"
                proxy.extras = proxy.extras.difference({var_proxy})
            elif find(lambda x: x == prefix_data, var_proxy.prefixes):
                message = f"Removed prefix {prefix_text} to {variant}"
                var_proxy.remove_prefixes(prefix_data)
            elif prefix_data:
                message = f"Added prefix {prefix_text} to {variant}"
                var_proxy.append_prefixes(prefix_data)
        elif variant:  # No variant was found. Adding one
            message = f"Proxy didn't have variant {variant}"
            if not delete:
                message = f"Added Variant {variant}, prefix is {prefix_text}"
                proxy.append_extra(name=variant, image=image_url, prefixes=prefixes_arg)
        else:
            proxy.image = image_url
            message = f"Updating Proxy for {oc.name}"

            if delete:
                await db.delete_one(key)
                message = f"Deleted Proxy for {oc.name}"
            elif find(lambda x: x == prefix_data, proxy.prefixes):
                message = f"Removed prefix {prefix_text}"
                proxy.remove_prefixes(prefix_data)
            elif prefix_data:
                message = f"Added prefix {prefix_text}"
                proxy.append_prefixes(prefix_data)

        if not delete:
            proxy.name = oc.name
            await db.replace_one(key, proxy.to_dict(), upsert=True)

        await ctx.followup.send(message, ephemeral=True)

    @app_commands.command(name="npc", description="Slash command for NPC Narration")
    @app_commands.guilds(719343092963999804)
    async def slash_npc(
        self,
        ctx: Interaction,
        name: Optional[str],
        pokemon: Optional[DefaultSpeciesArg],
        shiny: Optional[bool],
        pronoun: Optional[Pronoun],
        character: Optional[CharacterArg],
        image: Optional[Attachment],
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
        resp: InteractionResponse = ctx.response
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
                thread=Object(id=1045687852069040148),
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

        npc = NPC(name, image) if image else NPC(name)
        await self.bot.mongo_db("NPC").replace_one(
            {"author": ctx.user.id},
            {"author": ctx.user.id, "name": npc.name, "avatar": npc.avatar},
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
            npc = NPC(name=f"NPC〕{mon.name}", avatar=mon.base_image)
            await self.proxy_handler(npc=npc, message=ctx.message, text=text)
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
        db = self.bot.mongo_db("Characters")
        member = self.bot.supporting.get(ctx.author, ctx.author)
        if options := process.extractOne(
            pokemon,
            choices=[
                Character.from_mongo_dict(x)
                async for x in db.find(
                    {
                        "author": member.id,
                        "server": ctx.guild.id,
                    }
                )
            ],
            score_cutoff=60,
            processor=lambda x: getattr(x, "name", x),
        ):
            oc: Character = options[0]
            npc = NPC(name=oc.name, avatar=oc.image_url)
            await self.proxy_handler(npc=npc, message=ctx.message, text=text)
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
            npc = NPC(name=entry["name"], avatar=entry["avatar"])
            await self.proxy_handler(npc=npc, message=ctx.message, text=text)
        else:
            await ctx.message.delete(delay=0)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
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

            with suppress(DiscordException):
                await payload.member.send(text, view=view)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(ProxyCog(bot))
