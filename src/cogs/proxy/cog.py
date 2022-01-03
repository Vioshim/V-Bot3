# Copyright 2021 Vioshim
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
    DiscordException,
    Message,
    NotFound,
    RawReactionActionEvent,
    TextChannel,
    Thread,
)
from discord.ext.commands import Cog, command, guild_only
from discord.ui import Button, View

from src.context import Context
from src.structures.bot import CustomBot
from src.structures.converters import SpeciesCall

NPCLog = namedtuple("NPCLog", "channel_id message_id")


class Proxy(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.npc_info: dict[NPCLog, int] = {}

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
        if isinstance(channel, Thread):
            if registered not in channel.parent.overwrites:
                pass
        elif isinstance(channel, TextChannel):
            if registered not in channel.overwrites:
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
                        view = View()
                        view.add_item(Button(label="Jump URL", url=message.jump_url))
                        text = f"That message was sent by {user.mention} (tag: {user} - id: {user.id})."
                        with suppress(DiscordException):
                            await payload.member.send(text, view=view)
            except NotFound:
                await payload.member.send(
                    "That proxy was sent by an user who is no longer in discord."
                )

    async def handler(self, ctx: Context, name: str, avatar_url: str, content: str):
        webhook = await self.bot.webhook(ctx.channel, reason="NPC")
        message: Message = ctx.message
        view = View()
        if reference := message.reference:
            view.add_item(item=Button(label="Replying to", url=reference.jump_url))

        data = dict(
            username=name,
            avatar_url=avatar_url,
            content=content,
            files=[await item.to_file() for item in message.attachments],
            view=view,
            wait=True,
        )

        if isinstance(ctx.channel, Thread):
            data["thread"] = ctx.channel

        proxy_msg = await webhook.send(**data)

        self.npc_info[
            NPCLog(channel_id=ctx.channel.id, message_id=proxy_msg.id)
        ] = ctx.author.id

        self.bot.msg_cache.add(message.id)
        with suppress(DiscordException):
            if message.mentions:
                await message.delete(delay=300)
            else:
                await message.delete()

    @guild_only()
    @command()
    async def npc(self, ctx: Context, species: SpeciesCall, *, content: str):
        webhook = await self.bot.webhook(ctx.channel, reason="NPC")
        message: Message = ctx.message
        view = View()
        if reference := message.reference:
            item = Button(label="Replying to", url=reference.jump_url)
            view.add_item(item=item)

        data = dict(
            username=f"NPC〕{species.name} ",
            avatar_url=species.base_image,
            content=content,
            files=[await item.to_file() for item in message.attachments],
            view=view,
            wait=True,
        )

        if isinstance(ctx.channel, Thread):
            data["thread"] = ctx.channel

        proxy_msg = await webhook.send(**data)

        key = NPCLog(channel_id=ctx.channel.id, message_id=proxy_msg.id)
        self.npc_info[key] = ctx.author.id

        self.bot.msg_cache.add(message.id)
        with suppress(DiscordException):
            if message.mentions:
                await message.delete(delay=300)
            else:
                await message.delete()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Proxy(bot))
