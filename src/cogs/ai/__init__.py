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

from discord import DiscordException, Embed, Message, TextChannel, Thread
from discord.ext import commands
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

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def ai_load_samples(self, ctx: commands.Context, cache: bool = True):
        channels: set[TextChannel | Thread] = set()
        if cache and self.msg_cache:
            msgs = list(self.msg_cache.values())
        else:
            for channel in filter(
                lambda x: isinstance(x, TextChannel)
                and not x.name.endswith("-ooc")
                and x.category
                and x.category.id not in IDS,
                ctx.guild.channels,
            ):
                channels.add(channel)
                channels.update([x async for x in channel.archived_threads(limit=None)])
                channels.update(channel.threads)

            msgs = []
            for channel in channels:
                msgs.extend(
                    [
                        msg
                        async for msg in channel.history(limit=None, oldest_first=True)
                        if (msg.content and msg.webhook_id and msg.author != self.bot.user)
                    ]
                )

        for msg in sorted(msgs, key=lambda x: x.id):
            await self.process(msg)

        await ctx.reply("Finished Scan")

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def ai_solve_samples(self, ctx: commands.Context, caching: bool = True):
        db = self.bot.mongo_db("RP Samples")
        if not (caching and self.msg_cache and self.cache):
            async for item in db.find({"ocs": {"$exists": True}}):
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
                    self.cache[msg.id] = item

        values: list[Message] = [m for k, v in self.cache.items() if "ocs" in v and (m := self.msg_cache.get(k))]

        view = Complex[Message](
            member=ctx.author,
            values=values,
            target=ctx.channel,
            parser=lambda x: (x.author.name, f"Written in {x.channel}"),
        )

        async with view.send(single=True) as msg:
            if isinstance(msg, Message):
                cog = self.bot.get_cog("Submission")
                ocs = [o for x in self.cache[msg.id].get("ocs", []) if (o := cog.ocs.get(x))]

                embed = Embed(title=msg.author.name, description=msg.content)
                embed.set_image(url=msg.author.display_avatar.with_size(4096))
                embed.add_field(name="mention", value=msg.channel.mention)

                view2 = CharactersView(member=ctx.author, target=ctx.channel, ocs=ocs)
                async with view2.send(embed=embed, single=True) as oc:
                    if isinstance(oc, Character):
                        data = message_parse(msg)
                        data["oc"] = oc.id
                        await db.replace_one({"id": msg.id}, data, upsert=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(AiCog(bot))
