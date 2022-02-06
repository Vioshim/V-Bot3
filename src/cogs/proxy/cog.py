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
from discord.ext.commands import Cog, slash_command
from discord.ui import Button, View

from src.cogs.pokedex.search import default_species_autocomplete
from src.structures.bot import CustomBot
from src.structures.species import Fusion, Species

NPC = namedtuple("NPC", "name avatar")
NPCLog = namedtuple("NPCLog", "channel_id message_id")


class Proxy(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.npc_info: dict[NPCLog, int] = {}
        self.current: dict[int, NPC] = {}

    @slash_command(guild_ids=[719343092963999804])
    async def npc(
        self,
        ctx: ApplicationContext,
        pokemon: Option(
            str,
            description="Species to use",
            autocomplete=default_species_autocomplete,
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
    ):

        if (mon := Species.from_ID(pokemon)) and not isinstance(mon, Fusion):
            image = mon.base_image
            if shiny:
                image = mon.base_image_shiny
                if gender == "Female":
                    if shiny:
                        image = mon.female_image_shiny
                    else:
                        image = mon.female_image

            self.current[ctx.author.id] = NPC(name=mon.name, image=image)

            await ctx.respond(
                "NPC has been set, now send the message.",
                ephemeral=True,
            )
        else:
            await ctx.respond(
                f"{pokemon} was not found, try again.",
                ephemeral=True,
            )

    @Cog.listener()
    async def on_message(self, message: Message):
        member: Member = message.author
        if not message.guild or member.bot:
            return
        if npc := self.current.pop(member.id, None):
            webhook = await self.bot.webhook(message.channel, reason="NPC")

            data = dict(
                username=f"NPC〕{npc.name} ",
                avatar_url=npc.avatar,
                content=message.content,
                files=[await item.to_file() for item in message.attachments],
                wait=True,
            )

            if reference := message.reference:
                data["view"] = View(
                    Button(label="Replying to", url=reference.jump_url)
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
        registered = guild.get_role(719642423327719434)
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
