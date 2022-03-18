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

from collections import namedtuple
from contextlib import suppress
from typing import Union

from discord import (
    ApplicationContext,
    DiscordException,
    Member,
    Message,
    NotFound,
    Option,
    RawReactionActionEvent,
    TextChannel,
    Thread,
    WebhookMessage,
)
from discord.ext.commands import (
    Cog,
    Context,
    command,
    guild_only,
    slash_command,
)
from discord.ui import Button, View
from discord.utils import get

from src.cogs.pokedex.search import default_species_autocomplete
from src.cogs.submission.cog import Submission, oc_autocomplete
from src.structures.bot import CustomBot
from src.structures.species import Fusion, Species

NPC = namedtuple("NPC", "name avatar")
NPCLog = namedtuple("NPCLog", "channel_id message_id")
MALE = "\N{MALE SIGN}"
FEMALE = "\N{FEMALE SIGN}"


class Proxy(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.npc_info: dict[NPCLog, int] = {}
        self.current: dict[int, NPC] = {}

    async def proxy_handler(
        self,
        npc: NPC,
        message: Message,
        text: str = None,
    ):
        webhook = await self.bot.webhook(message.channel, reason="NPC")
        text = text or "\u200b"

        data = dict(
            username=npc.name,
            avatar_url=npc.avatar,
            content=text,
            files=[await item.to_file() for item in message.attachments],
            wait=True,
        )

        if reference := message.reference:
            data["view"] = View(
                Button(
                    label="Replying to",
                    url=reference.jump_url,
                )
            )

        if isinstance(message.channel, Thread):
            data["thread"] = message.channel

        proxy_msg: WebhookMessage = await webhook.send(**data)
        proxy_msg.channel = message.channel

        item = NPCLog(
            channel_id=message.channel.id,
            message_id=proxy_msg.id,
        )
        self.npc_info[item] = message.author.id

        self.bot.msg_cache.add(message.id)
        with suppress(DiscordException):
            if message.mentions:
                await message.delete(delay=300)
            else:
                await message.delete()

    @slash_command(name="npc", guild_ids=[719343092963999804])
    async def slash_npc(
        self,
        ctx: ApplicationContext,
        pokemon: Option(
            str,
            description="Species to use",
            autocomplete=default_species_autocomplete,
            required=False,
        ),
        shiny: Option(
            bool,
            description="If Shiny",
            required=False,
        ),
        gender: Option(
            str,
            choices=["Male", "Female"],
            description="Sprite to use",
            required=False,
        ),
        character: Option(
            str,
            description="Character to Use",
            autocomplete=oc_autocomplete,
            required=False,
        ),
    ):
        """Slash command for NPC Narration

        Parameters
        ----------
        ctx : ApplicationContext
            Context
        pokemon : str, optional
            Pokemon, by default None
        shiny : bool, optional
            if shiny, by default None
        gender : str, optional
            pronoun, by default None
        character : str, optional
            character id, by default None
        """
        cog = self.bot.get_cog("Submission")
        if (character or "").isdigit() and (oc := cog.ocs.get(int(character))):
            self.current[ctx.author.id] = NPC(
                name=oc.name,
                avatar=oc.image,
            )
            await ctx.respond(
                f"NPC has been set as {oc.name}, now send the message.",
                ephemeral=True,
            )
            return
        if mon := Species.single_deduce(pokemon):
            name = mon.name
            if shiny:
                name = f"Shiny {name}"
                if gender == "Female":
                    avatar = mon.female_image_shiny
                else:
                    avatar = mon.base_image_shiny
            elif gender == "Female":
                avatar = mon.female_image
            else:
                avatar = mon.base_image

            if gender == "Male":
                name = f"NPC〕{name} {MALE}"
            elif gender == "Female":
                name = f"NPC〕{name} {FEMALE}"
            else:
                name = f"NPC〕{name}"

            self.current[ctx.author.id] = NPC(
                name=name,
                avatar=avatar,
            )

            await ctx.respond(
                "NPC has been set, now send the message.",
                ephemeral=True,
            )
        else:
            await ctx.respond(
                f"{pokemon} was not found, try again.",
                ephemeral=True,
            )

    @command(name="npc")
    @guild_only()
    async def cmd_npc(
        self,
        ctx: Context,
        pokemon: str,
        *,
        text: str = None,
    ):
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
        if mon := Species.single_deduce(pokemon):
            npc = NPC(name=f"NPC〕{mon.name}", avatar=mon.base_image)
        else:
            member: Member = ctx.author
            cog: Submission = self.bot.get_cog("Submission")
            ocs = cog.rpers.get(member.id, {}).values()
            if ocs := [
                x
                for x in ocs
                if pokemon.lower() in x.name.lower()
                or x.name.lower() in pokemon.lower()
            ]:
                oc = ocs[0]
                npc = NPC(name=oc.name, avatar=oc.image)
            else:
                npc = NPC(
                    name=f"NPC〕{member.display_name}",
                    avatar=member.display_avatar.url,
                )
        await self.proxy_handler(
            npc=npc,
            message=ctx.message,
            text=text,
        )

    @Cog.listener()
    async def on_message(self, message: Message):
        member: Member = message.author
        if not message.guild or member.bot or member.id not in self.current:
            return

        ctx = await self.bot.get_context(message)

        if ctx.command:
            return

        if npc := self.current.pop(member.id, None):
            await self.proxy_handler(
                npc=npc,
                message=message,
                text=message.content,
            )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        """On raw reaction added

        Parameters
        ----------
        payload : RawReactionActionEvent
            Reaction added
        """
        if not payload.guild_id:
            return
        if payload.member.bot:
            return

        if (emoji := str(payload.emoji)) not in [
            "\N{CROSS MARK}",
            "\N{BLACK QUESTION MARK ORNAMENT}",
        ]:
            return

        guild = self.bot.get_guild(payload.guild_id)
        registered = get(guild.roles, name="Registered")
        if not registered:
            return

        channel: Union[Thread, TextChannel] = await self.bot.fetch_channel(
            payload.channel_id
        )
        reference: TextChannel = getattr(channel, "parent", channel)
        if registered not in reference.overwrites:
            return

        key = NPCLog(channel_id=channel.id, message_id=payload.message_id)
        if data := self.npc_info.get(key):
            message = await channel.fetch_message(payload.message_id)
            try:
                if emoji == "\N{CROSS MARK}" and data == payload.member.id:
                    await message.delete()
                elif emoji == "\N{BLACK QUESTION MARK ORNAMENT}":
                    await message.clear_reaction(emoji=emoji)
                    if user := guild.get_member(data):
                        view = View(
                            Button(label="Jump URL", url=message.jump_url)
                        )
                        text = f"That message was sent by {user.mention} (tag: {user} - id: {user.id})."
                        with suppress(DiscordException):
                            await payload.member.send(text, view=view)
            except NotFound:
                await payload.member.send(
                    "That proxy was sent by an user who is no longer in discord."
                )


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Proxy(bot))
