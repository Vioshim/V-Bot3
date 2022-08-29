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
from typing import Any

from discord import (
    DiscordException,
    Embed,
    Message,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    RawThreadDeleteEvent,
    TextChannel,
    Thread,
)
from discord.ext import commands
from frozendict import frozendict
from rapidfuzz import process

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.views.characters_view import CharactersView

IDS = [
    788172543273598976,
    719663307526504468,
    740550068922220625,
    740552350703550545,
    720107294838227034,
    974362077445640252,
    719343092963999805,
    740567496721039401,
]


def message_parse(message: Message):
    if isinstance(channel := message.channel, Thread):
        thread_id, channel_id = channel.id, channel.parent_id
    else:
        thread_id, channel_id = None, channel.id

    return {
        "id": message.id,
        "text": message.content,
        "category": message.channel.category_id,
        "thread": thread_id,
        "channel": channel_id,
        "server": message.guild.id,
        "created_at": message.created_at,
    }


class AiCog(commands.Cog):
    def __init__(self, bot: CustomBot) -> None:
        self.bot = bot
        self.cache: dict[int, dict] = {}
        self.msg_cache: dict[int, Message] = {}

    async def process(self, message: Message):
        db = self.bot.mongo_db("RP Samples")

        ocs: list[Character] = list(self.bot.get_cog("Submission").ocs.values())
        if items := process.extract(
            message.author.display_name,
            ocs,
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=85,
        ):
            data = message_parse(message)
            if len(ocs := [x[0] for x in items]) == 1:
                data["oc"] = ocs[0].id
            else:
                data["ocs"] = [x.id for x in ocs]

            self.cache[message.id] = data
            self.msg_cache[message.id] = message

            await db.replace_one({"id": message.id}, data, upsert=True)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: RawThreadDeleteEvent):
        db = self.bot.mongo_db("RP Samples")
        await db.delete_many({"thread": payload.thread_id})

    @commands.Cog.listener()
    async def on_channel_delete(self, channel: TextChannel):
        if isinstance(channel, TextChannel):
            db = self.bot.mongo_db("RP Samples")
            await db.delete_many({"channel": channel.id})

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        db = self.bot.mongo_db("RP Samples")
        self.cache.pop(payload.message_id, None)
        self.msg_cache.pop(payload.message_id, None)
        await db.delete_one({"id": payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        db = self.bot.mongo_db("RP Samples")
        await db.delete_many({"id": {"$in": list(payload.message_ids)}})
        for item in payload.message_ids:
            self.cache.pop(item, None)
            self.msg_cache.pop(item, None)

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def ai_solve_samples(self, ctx: commands.Context, caching: bool = True, fetching: bool = False):
        db = self.bot.mongo_db("RP Samples")
        if not (caching and self.msg_cache and self.cache):
            async for item in db.find({"ocs": {"$exists": True}}):
                self.cache[item["id"]] = item
                if not fetching:
                    continue

                with suppress(DiscordException):
                    if not (guild := self.bot.get_guild(item["server"])):
                        continue

                    if not (channel := guild.get_channel(item["channel"])):
                        continue

                    if thread_id := item["thread"]:
                        if not (thread := channel.get_thread(thread_id)):
                            thread = await guild.fetch_channel(thread_id)
                    else:
                        thread = channel

                    msg = await thread.fetch_message(item["id"])
                    self.msg_cache[msg.id] = msg

        values = {x["id"]: x for x in self.cache.values() if "ocs" in x}

        def parser(o: str):
            x = values[o]
            if o := self.msg_cache.get(x["id"]):
                return o.author.display_name, f"Written in {o.channel}"
            o = self.bot.get_channel(x["channel"])
            return f"Message {x['id']}", f"Written in {o}"

        view = Complex[frozendict[str, Any]](
            member=ctx.author,
            values=values.keys(),
            target=ctx.channel,
            parser=parser,
        )

        async with view.send(single=True) as raw:
            if raw := values.get(raw):
                cog = self.bot.get_cog("Submission")
                ocs = [o for x in self.cache[raw["id"]].get("ocs", []) if (o := cog.ocs.get(x))]

                if not (msg := self.msg_cache.get(raw["id"])):
                    if channel := self.bot.get_channel(raw["channel"]):
                        if raw["thread"]:
                            if not (thread := channel.guild.get_thread(raw["thread"])):
                                thread = channel.guild.fetch_channel(raw["thread"])
                            channel = thread
                        msg = await channel.fetch_message(raw["id"])
                        self.msg_cache[msg.id] = msg
                    else:
                        return

                embed = Embed(title=msg.author.name, description=msg.content, url=msg.jump_url)
                embed.set_image(url=msg.author.display_avatar.with_size(4096))
                embed.add_field(name="mention", value=msg.channel.mention)

                view2 = CharactersView(member=ctx.author, target=ctx.channel, ocs=ocs)
                async with view2.send(embed=embed, single=True) as oc:
                    if isinstance(oc, Character):
                        data = message_parse(msg)
                        data["oc"] = oc.id
                        self.cache[msg.id] = data
                        await db.replace_one({"id": msg.id}, data, upsert=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(AiCog(bot))
