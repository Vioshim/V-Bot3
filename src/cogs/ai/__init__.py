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


from discord import (
    Embed,
    Message,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    RawThreadDeleteEvent,
    TextChannel,
    Thread,
)
from discord.ext import commands
from openai import Completion
from rapidfuzz import process

from src.structures.bot import CustomBot
from src.structures.character import Character

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


def ai_completition(prompt: str):
    if not prompt.endswith("."):
        prompt += "."
    resp = Completion.create(
        prompt=prompt,
        engine="text-davinci-002",
        max_tokens=4000 - len(prompt),
        temperature=0.7,
        top_p=1,
        stop=None,
        presence_penalty=0,
        frequency_penalty=0,
        echo=False,
        n=1,
        stream=False,
        logprobs=None,
        best_of=1,
        logit_bias={},
    )
    return "\n".join(choice.text.strip() for choice in resp.choices)


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
        db2 = self.bot.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(x) async for x in db2.find({})]
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
    @commands.guild_only()
    @commands.has_any_role("Booster", "Moderation")
    async def ai(self, ctx: commands.Context, *, text: str):
        """OpenAI Generator

        Parameters
        ----------
        ctx : commands.Context
            Context
        text : str
            Text
        """
        if len(text := await self.bot.loop.run_in_executor(None, ai_completition, text)) <= 2000:
            await ctx.reply(content=text or "\u200b")
        else:
            await ctx.reply(embed=Embed(description=text[:4096]))


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(AiCog(bot))
