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


from __future__ import annotations

from contextlib import suppress
from dataclasses import astuple, dataclass

from discord import Embed, ForumChannel, NotFound
from discord.utils import get

from src.structures.bot import CustomBot


@dataclass(slots=True, unsafe_hash=True)
class Appeal:
    id: int = 0

    def __post_init__(self):
        self.id = int(self.id)

    def __hash__(self):
        return self.id >> 22

    def __eq__(self, other: Appeal):
        return isinstance(other, Appeal) and self.id == other.id

    @classmethod
    def from_values(cls, data: list[list[str]]):
        return {cls(*i[1:]) for i in data if i}


@dataclass(slots=True, unsafe_hash=True)
class BanAppeal(Appeal):
    ban_reason: str = ""
    unban_reason: str = ""

    def __eq__(self, other: BanAppeal):
        return self.id == other.id if isinstance(other, BanAppeal) else NotImplemented

    @classmethod
    async def appeal_check(cls, bot: CustomBot, responses: set[BanAppeal] = None):
        responses = set() if responses is None else responses

        with suppress(Exception):
            if not (channel := bot.get_channel(1094921401942687944)):
                channel: ForumChannel = await bot.fetch_channel(1094921401942687944)

            applied_tags = []
            if tag := get(channel.available_tags, name="Ban Appeal"):
                applied_tags.append(tag)

            storage = await bot.aiogoogle.discover("sheets", "v4")
            query = storage.spreadsheets.values.get(
                spreadsheetId="1OYI3sLKs9fFIoZ6v7RyM7KE7oFcbSOjffoMXFMVsC8s",
                range="Form Responses 1",
            )

            data = await bot.aiogoogle.as_service_account(query)
            responses = BanAppeal.from_values(data["values"][1:])
            db = bot.mongo_db("Ban Appeal")

            if new_reports := responses - responses:
                bot.logger.info(f"New Ban Appeals: {len(new_reports)}")
                responses |= new_reports

            for entry in new_reports:
                if await db.find_one({"id": entry.id}):
                    continue

                try:
                    ban_data = await channel.guild.fetch_ban(entry)
                except NotFound:
                    continue

                base_embed = (
                    Embed(title="Ban Appeal", color=0x2F3136)
                    .set_author(
                        name=ban_data.user.display_name,
                        icon_url=ban_data.user.display_avatar.url,
                    )
                    .set_footer(text=str(entry.id))
                )

                file = await ban_data.user.display_avatar.with_size(4096).to_file()
                tdata = await channel.create_thread(
                    name=str(ban_data.user),
                    content=f"Audit Logs' ban reason: {ban_data.reason or 'No Reason Provided.'}",
                    embeds=base_embed,
                    file=file,
                    applied_tags=applied_tags,
                )
                await tdata.message.pin()

                for title, answer in zip(data["values"][0][1:], astuple(entry)[1:]):
                    base_embed.title, base_embed.description = title, str(answer or "No Answer Provided.")[:4000]
                    await tdata.thread.send(embed=base_embed)

                await db.replace_one(
                    {"id": entry.id},
                    {"id": entry.id, "thread": tdata.thread.id},
                    upsert=True,
                )


@dataclass(slots=True, unsafe_hash=True)
class ModAppeal(Appeal):
    previous_experience: str = ""
    handling_disrespect: str = ""
    handling_racism: str = ""
    handling_trolls: str = ""
    handling_rpers: str = ""
    handling_biases: str = ""
    handling_lore: str = ""
    skills: str = ""

    def __eq__(self, other: ModAppeal):
        return self.id == other.id if isinstance(other, ModAppeal) else NotImplemented

    @classmethod
    async def appeal_check(cls, bot: CustomBot, responses: set[ModAppeal] = None):
        responses = set() if responses is None else responses
        if not (channel := bot.get_channel(1094921401942687944)):
            channel: ForumChannel = await bot.fetch_channel(1094921401942687944)

        applied_tags = []
        if tag := get(channel.available_tags, name="Mod Application"):
            applied_tags.append(tag)

        storage = await bot.aiogoogle.discover("sheets", "v4")
        query = storage.spreadsheets.values.get(
            spreadsheetId="19KUAlatwWoFcNB7fxS4lYa-sySrsBpJ50OfRxCy1R4E",
            range="Form Responses 1",
        )

        data = await bot.aiogoogle.as_service_account(query)
        new_responses = ModAppeal.from_values(data["values"][1:])
        db = bot.mongo_db("Mod Appeal")

        if new_reports := new_responses - responses:
            bot.logger.info(f"New Mod Applications: {len(new_reports)}")
            responses |= new_reports

        for entry in new_reports:
            if await db.find_one({"id": entry.id}):
                continue

            if not (member := channel.guild.get_member(entry.id)):
                try:
                    member = await channel.guild.fetch_member(entry.id)
                except NotFound:
                    continue

            if member.guild_permissions.manage_guild:
                continue

            base_embed = (
                Embed(
                    title="Mod Application",
                    color=member.color,
                    description="\n".join(x.mention for x in member.roles),
                    timestamp=member.joined_at,
                )
                .set_author(name=member.display_name, icon_url=member.display_avatar)
                .set_footer(text=str(entry.id))
            )

            file = await member.display_avatar.with_size(4096).to_file()

            tdata = await channel.create_thread(
                name=str(member),
                content=f"Mod application from {member.mention}",
                embed=base_embed,
                file=file,
                applied_tags=applied_tags,
            )
            await tdata.message.pin()

            for title, answer in zip(data["values"][0][1:], astuple(entry)[1:]):
                base_embed.title, base_embed.description = title, str(answer or "No Answer Provided.")[:4000]
                await tdata.thread.send(embed=base_embed)

            await db.replace_one(
                {"id": entry.id},
                {"id": entry.id, "thread": tdata.thread.id},
                upsert=True,
            )
