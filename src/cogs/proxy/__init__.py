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


from typing import NamedTuple, Optional

from discord import (
    Attachment,
    DiscordException,
    Interaction,
    InteractionResponse,
    Message,
    RawReactionActionEvent,
    Thread,
    WebhookMessage,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View
from discord.utils import MISSING
from rapidfuzz import process

from src.cogs.pokedex.search import DefaultSpeciesArg
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.pronouns import Pronoun
from src.structures.species import Species

__all__ = ("Proxy", "setup")


class NPC(NamedTuple):
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


class Proxy(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    async def proxy_handler(self, npc: NPC, message: Message, text: str = None):
        webhook = await self.bot.webhook(message.channel, reason="NPC")
        text = text or "\u200b"
        thread = view = MISSING
        if reference := message.reference:
            view = View().add_item(Button(label="Replying to", url=reference.jump_url))
        if isinstance(message.channel, Thread):
            thread = message.channel
        proxy_msg: WebhookMessage = await webhook.send(
            username=npc.name,
            avatar_url=npc.avatar,
            content=text,
            files=[await item.to_file() for item in message.attachments],
            wait=True,
            view=view,
            thread=thread,
        )
        await self.bot.mongo_db("Tupper-logs").insert_one(
            {
                "channel": message.channel.id,
                "id": proxy_msg.id,
                "author": message.author.id,
            }
        )
        await message.delete(delay=300 if message.mentions else 0)

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
        image = image.proxy_url if image else None
        if pokemon and not name:
            name = f"NPC〕{pokemon.name}"

        if pokemon and not image:
            image = pokemon.image(shiny=shiny, gender=pronoun)

        if not name:
            modal = NameModal(timeout=None)
            await resp.send_modal(modal)
            await modal.wait()
            name = modal.name.value

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
        db = self.bot.mongo_db("Characters")
        member = self.bot.supporting.get(ctx.author, ctx.author)
        if mon := Species.single_deduce(pokemon):
            npc = NPC(name=f"NPC〕{mon.name}", avatar=mon.base_image)
        elif (ocs := [Character.from_mongo_dict(x) async for x in db.find({"author": member.id})]) and (
            options := process.extractOne(
                pokemon, choices=ocs, score_cutoff=60, processor=lambda x: getattr(x, "name", x)
            )
        ):
            oc = options[0]
            npc = NPC(name=oc.name, avatar=oc.image_url)
        else:
            npc = NPC(name=pokemon)
        await self.proxy_handler(npc=npc, message=ctx.message, text=text)

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
        if (ocs := [Character.from_mongo_dict(x) async for x in db.find({"author": member.id})]) and (
            options := process.extractOne(
                pokemon, choices=ocs, score_cutoff=60, processor=lambda x: getattr(x, "name", x)
            )
        ):
            oc = options[0]
            npc = NPC(name=oc.name, avatar=oc.image_url)
        elif mon := Species.single_deduce(pokemon):
            npc = NPC(name=f"NPC〕{mon.name}", avatar=mon.base_image)
        else:
            npc = NPC(name=pokemon)
        await self.proxy_handler(npc=npc, message=ctx.message, text=text)

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
        else:
            npc = NPC()
        await self.proxy_handler(npc=npc, message=ctx.message, text=text)

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
            try:
                await payload.member.send(text, view=view)
            except DiscordException:
                pass


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Proxy(bot))
