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


import random
import re
from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass
from typing import Optional

import d20
from discord import (
    Attachment,
    DiscordException,
    Embed,
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
from discord.utils import MISSING, get
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.cogs.pokedex.search import DefaultSpeciesArg
from src.cogs.proxy.proxy import ProxyVariantArg
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.pronouns import Pronoun
from src.structures.proxy import Proxy, ProxyExtra
from src.structures.species import Species
from src.utils.etc import LINK_EMOJI

__all__ = ("Proxy", "setup")

PARSER = re.compile(r"\{\{([^\{\}]+)\}\}")


@dataclass(unsafe_hash=True, slots=True)
class NPC:
    name: str = "Narrator"
    image: str = "https://hmp.me/dx4a"

    def __post_init__(self):
        self.name = self.name or "Narrator"
        self.image = self.image or "https://hmp.me/dx4a"


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


class ProxyFunction(ABC):
    aliases: list[str]

    @classmethod
    def lookup(cls, npc: NPC | Proxy | ProxyExtra, text: str):
        items = {alias: item for item in cls.__subclasses__() for alias in item.aliases}
        aux_text = text.split(":")[0]
        if x := process.extractOne(aux_text, choices=list(items), score_cutoff=60):
            return items[x[0]].parse(
                npc,
                text.removeprefix(aux_text).strip().removeprefix(":").strip(),
            )

    @classmethod
    @abstractmethod
    def parse(
        cls,
        npc: NPC | Proxy | ProxyExtra,
        text: str,
    ) -> Optional[tuple[NPC | Proxy | ProxyExtra, str, Optional[Embed]]]:
        """This is the abstract parsing methods

        Parameters
        ----------
        npc : NPC | Proxy | ProxyExtra
            NPC to keep or replace
        text : str
            Text to evaluate

        Returns
        -------
        Optional[tuple[NPC | Proxy | ProxyExtra, str, Optional[Embed]]]
            Result
        """


class MoveFunction(ProxyFunction):
    aliases = ["Move"]

    @classmethod
    def parse(cls, npc: NPC | Proxy | ProxyExtra, text: str) -> Optional[tuple[str, Optional[Embed]]]:
        match text.split(":"):
            case [move]:
                if not (item := Move.deduce(move)):
                    return
                return npc, f"{item.emoji}`{item.name}`", item.embed
            case [move, move_type]:
                if not (item := Move.deduce(move)):
                    return
                move_type = TypingEnum.deduce(move_type) or item.type
                embed = item.embed
                embed.color = move_type.color
                if item.type != move_type:
                    embed.set_author(name=f"Originally {item.type.name} Type ", icon_url=item.type.emoji.url)
                embed.set_thumbnail(url=move_type.emoji.url)
                return npc, f"{move_type.emoji}`{item.name}`", item.embed


class MetronomeFunction(ProxyFunction):
    aliases = ["Metronome"]

    @classmethod
    def parse(cls, npc: NPC | Proxy | ProxyExtra, text: str):
        item = random.choice([x for x in Move.all(banned=False, shadow=False) if x.metronome])
        if "mute" in text.lower():
            name, embed = f"{item.emoji}`{item.name}`", None
        else:
            name, embed = f"`{item.name}`", item.embed
        return npc, name, embed


class TypeFunction(ProxyFunction):
    aliases = ["Type"]

    @classmethod
    def parse(cls, npc: NPC | Proxy | ProxyExtra, text: str):
        if item := TypingEnum.deduce(text):
            return npc, str(item.emoji), None


class MoodFunction(ProxyFunction):
    aliases = ["Mood", "Mode"]

    @classmethod
    def parse(cls, npc: NPC | Proxy | ProxyExtra, text: str):
        if isinstance(npc, Proxy) and (
            o := process.extractOne(
                text.strip(),
                choices=npc.extras,
                score_cutoff=60,
                processor=lambda x: getattr(x, "name", x),
            )
        ):
            if len(username := f"{npc.name} ({o[0].name})") > 80:
                username = o[0].name
            return NPC(name=username, image=o[0].image or npc.image), "", None


class RollFunction(ProxyFunction):
    aliases = ["Roll"]

    @classmethod
    def parse(cls, npc: NPC | Proxy | ProxyExtra, text: str):
        with suppress(Exception):
            value = d20.roll(expr=text.strip() or "d20", allow_comments=True)
            if len(value.result) > 4096:
                d20.utils.simplify_expr(value.expr)
            return npc, Embed(description=value.result), f"`🎲{value.total}`"


class ProxyMessageModal(Modal, title="Edit Proxy Message"):
    def __init__(self, msg: Message, data: dict[str, int]) -> None:
        super(ProxyMessageModal, self).__init__(timeout=None)
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


class ProxyModal(Modal, title="Prefixes"):
    def __init__(
        self,
        oc: Character,
        proxy: Optional[Proxy],
        variant: Optional[ProxyExtra | str],
        image_url: Optional[str] = None,
    ) -> None:
        super(ProxyModal, self).__init__(timeout=None)
        self.oc = oc
        self.proxy = (
            proxy
            if proxy
            else Proxy(
                id=oc.id,
                author=oc.author,
                server=oc.author,
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
            label=proxy.name[:45],
            placeholder="Each line must include word text",
            default="\n".join(map("text".join, self.proxy.prefixes)),
            style=TextStyle.paragraph,
            required=False,
        )
        self.add_item(self.proxy1_data)
        self.proxy2_data = TextInput(
            label="Variant",
            placeholder="Each line must include word text",
            required=False,
            style=TextStyle.paragraph,
        )
        if variant:
            self.proxy2_data.label = variant.name[:45]
            self.proxy2_data.default = "\n".join(map("text".join, variant.prefixes))
            self.add_item(self.proxy2_data)
        self.variant = variant

    async def on_submit(self, ctx: Interaction):
        """This is a function that handles the submission of the name.

        Parameters
        ----------
        interaction : Interaction
            Interaction that triggered the submission
        """
        resp: InteractionResponse = ctx.response
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Proxy")
        self.proxy.prefixes = frozenset(
            (o[0].strip(), o[-1].strip()) for x in self.proxy1_data.value.split("\n") if len(o := x.split("text")) > 1
        )
        if self.variant:
            self.variant.prefixes = frozenset(
                (o[0].strip(), o[-1].strip())
                for x in self.proxy2_data.value.split("\n")
                if len(o := x.split("text")) > 1
            )
            self.proxy.extras |= {self.variant}
            await resp.send_message(embeds=[self.proxy.embed, self.variant.embed], ephemeral=True)
        else:
            await resp.send_message(embed=self.proxy.embed, ephemeral=True)

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

    async def on_proxy_message(self, message: Message):
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
            await self.proxy_handler(npc, message, text, attachments=index == 0, deleting=False)
        if deleting:
            await message.delete(delay=300 if message.mentions else 0)

    @commands.Cog.listener()
    async def on_message_edit(self, previous: Message, current: Message):
        if not (
            previous.webhook_id or previous.author.bot or not previous.guild or previous.content == current.content
        ):
            await self.on_proxy_message(current)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not (message.webhook_id or message.author.bot or not message.guild):
            await self.on_proxy_message(message)

    async def msg_proxy(self, ctx: Interaction, msg: Message):
        db1 = self.bot.mongo_db("Tupper-logs")
        db2 = self.bot.mongo_db("RP Logs")
        entry: Optional[dict[str, int]] = await db1.find_one({"channel": msg.channel.id, "id": msg.id})
        member: Member = self.bot.supporting.get(ctx.user, ctx.user)

        self.bot.logger.info("User %s is checking proxies at %s", str(ctx.user), msg.jump_url)

        if entry and member.id == entry["author"]:
            return await ctx.response.send_modal(ProxyMessageModal(msg, entry))

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

    async def proxy_handler(
        self,
        npc: Character | NPC | Proxy | ProxyExtra,
        message: Message,
        text: str = None,
        attachments: bool = True,
        deleting: bool = True,
    ):
        webhook = await self.bot.webhook(message.channel, reason="NPC")
        db = self.bot.mongo_db("Characters")
        oc: Optional[Character] = None
        if isinstance(npc, Character):
            oc = npc
            npc = NPC(name=npc.name, image=npc.image_url)
        elif isinstance(npc, Proxy) and (oc_data := await db.find_one({"id": npc.id, "author": npc.author})):
            oc = Character.from_mongo_dict(oc_data)

        text = (text.strip() if text else None) or "\u200b"
        original_text = text
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

        embeds = []
        for item in PARSER.finditer(text):
            if proxy_data := ProxyFunction.lookup(npc, aux := item.group(1)):
                npc, data_text, data_embed = proxy_data
                if data_embed is None or len(embeds) < 10:
                    text = text.replace("{{" + aux + "}}", data_text, 1)
                    if data_embed:
                        data_embed.color = data_embed.color or message.author.color
                        embeds.append(data_embed)

        if attachments:
            files = [await item.to_file() for item in message.attachments]
        else:
            files = []

        proxy_msg = await webhook.send(
            username=npc.name[:80],
            avatar_url=npc.image,
            embeds=embeds,
            content=text or "\u200b",
            files=files,
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
        if deleting:
            await message.delete(delay=300 if message.mentions else 0)
        if original_text != proxy_msg.content and oc:
            await self.bot.get_cog("Submission").on_message_tupper(
                message=proxy_msg,
                user=message.author,
                kwargs=oc,
            )

    @app_commands.command(description="Proxy management")
    @app_commands.guilds(719343092963999804)
    async def proxy(
        self,
        ctx: Interaction,
        oc: CharacterArg,
        variant: Optional[ProxyVariantArg],
        image: Optional[Attachment],
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
        member: Member = self.bot.supporting.get(ctx.user, ctx.user)
        db = self.bot.mongo_db("Proxy")
        key = {"id": oc.id, "server": ctx.guild_id, "author": member.id}
        data = await db.find_one(key)
        proxy = Proxy.from_mongo_dict(data) if data else None
        var_proxy = get(proxy.extras, name=variant) if proxy else variant

        if delete:
            if proxy is None:
                embed = Embed(title="Proxy not found")
                embed.set_author(name=oc.name, url=oc.jump_url, icon_url=oc.image_url)
            elif isinstance(var_proxy, ProxyExtra):
                proxy.remove_extra(var_proxy)
                embed = var_proxy.embed.set_footer(text="Proxy's Variant was removed")
                await db.update_one(key, proxy.to_dict(), upsert=True)
            elif variant:
                embed = Embed(title="Proxy's Variant not Found", description=variant)
                embed.set_author(name=proxy.name, icon_url=proxy.image)
            else:
                embed = proxy.embed.set_footer(text="Proxy was removed")
                await db.delete_one(key)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

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
            modal = ProxyModal(oc, proxy, var_proxy or variant, m.attachments[0].url)
        else:
            modal = ProxyModal(oc, proxy, var_proxy or variant)
        await ctx.response.send_modal(modal)

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
            await self.proxy_handler(npc=ocs[options[0]], message=ctx.message, text=text)
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
