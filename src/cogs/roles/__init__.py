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


from datetime import datetime, time, timedelta, timezone
from typing import Optional
from urllib.parse import quote_plus

from discord import (
    AllowedMentions,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Object,
    RawReactionActionEvent,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, View

from src.cogs.roles.roles import (
    AFKModal,
    AFKSchedule,
    BasicRoleSelect,
    RPModal,
    TimezoneSelect,
)
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR

__all__ = ("Roles", "setup")


class Roles(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cool_down: dict[int, datetime] = {}
        self.role_cool_down: dict[int, datetime] = {}
        self.itx_menu1 = app_commands.ContextMenu(
            name="AFK Schedule",
            callback=self.check_afk,
            guild_ids=[719343092963999804],
        )

    async def cog_load(self):
        self.bot.tree.add_command(self.itx_menu1)
        await self.load_self_roles()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.itx_menu1.name, type=self.itx_menu1.type)

    async def check_afk(self, itx: Interaction[CustomBot], member: Member):
        db = self.bot.mongo_db("AFK")
        if item := await db.find_one({"user": itx.user.id}):
            current_date = itx.created_at
            embed = Embed(title="AFK Schedule", color=member.color)
            embed.set_author(name=member.display_name, icon_url=member.display_avatar)
            if item2 := await db.find_one({"user": member.id}):
                tz1 = timezone(timedelta(hours=item["offset"]))
                tz2 = timezone(timedelta(hours=item2["offset"]))
                user_data = [datetime.combine(current_date, time(hour=x), tz2) for x in item2["hours"]]

                data1 = AFKSchedule(user_data)
                data2 = data1.astimezone(tz1)
                desc1, desc2 = data1.text, data2.text
                if desc1 != desc2 and desc1 and desc2:
                    embed.add_field(name="In user's timezone", value=desc1, inline=False)
                    embed.add_field(name="In your timezone", value=desc2, inline=False)
                else:
                    embed.description = desc1 or desc2

                date = current_date.astimezone(tz2)
                text = f"User's time is {date.strftime('%I:%M %p')}"
            else:
                text = "No timezone associated to the account."
            embed.set_image(url=f"https://dummyimage.com/468x60/FFFFFF/000000&text={quote_plus(text)}")
            await itx.response.send_message(embed=embed, ephemeral=True)
        else:
            modal = AFKModal()
            await itx.response.send_modal(modal)

    async def load_self_roles(self):
        self.bot.logger.info("Loading Self Roles")
        channel = self.bot.get_partial_messageable(719709333369258015, guild_id=719343092963999804)
        msg1 = channel.get_partial_message(1059863286667038772)
        msg2 = channel.get_partial_message(1059863298285256864)
        await msg1.edit(view=BasicRoleSelect(timeout=None))
        await msg2.edit(view=TimezoneSelect(timeout=None))
        self.bot.logger.info("Finished loading Self Roles")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        member = payload.member
        if not all(
            (
                payload.guild_id,
                str(payload.emoji) == "\N{PUBLIC ADDRESS LOUDSPEAKER}",
                not member.bot,
            )
        ):
            return

        db = self.bot.mongo_db("Roleplayers")
        if item := await db.find_one({"id": payload.message_id, "server": payload.guild_id}):
            guild = member.guild
            if thread := guild.get_thread(payload.channel_id):
                msg = thread.get_partial_message(payload.message_id)
                await msg.remove_reaction(emoji=payload.emoji, member=payload.member)
            webhook = await self.bot.webhook(1061008601335992422, reason="Ping")
            view = View()
            url = f"https://discord.com/channels/{payload.guild_id}/{payload.message_id}"
            view.add_item(Button(label="Your OCs", url=url))
            if item2 := await db.find_one({"user": member.id, "server": payload.guild_id}):
                url = f"https://discord.com/channels/{payload.guild_id}/{item2['id']}"
                view.add_item(Button(label="User's OCs", url=url))

            if (author := guild.get_member(item["user"])) and author != member:
                embed = Embed(
                    title=f"Hello {author.display_name}",
                    description=f"{member.display_name} is interested on Rping with your characters.",
                    color=member.color,
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(text=guild.name, icon_url=guild.icon)
                await webhook.send(
                    content=f"{author.mention} pinged by {member.mention}",
                    allowed_mentions=AllowedMentions(users=True),
                    avatar_url=member.display_avatar.url,
                    username=member.display_name,
                    embed=embed,
                    view=view,
                    thread=Object(id=1061010425136828628),
                )

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        if msg.flags.ephemeral or not msg.guild or msg.webhook_id or msg.author.bot:
            return

        db = self.bot.mongo_db("AFK")
        users = {
            x.id: x for x in msg.mentions if x != msg.author and isinstance(x, Member) and str(x.status) == "offline"
        }
        if not users:
            return

        embeds = []
        if reference_tz := await db.find_one({"user": msg.author.id}):
            reference_tz: Optional[timezone] = timezone(offset=timedelta(hours=reference_tz["offset"]))

        async for item in db.find({"user": {"$in": [*users]}}):
            user = users[item["user"]]
            tz = timezone(offset=timedelta(hours=item["offset"]))
            ref_date = msg.created_at.astimezone(tz)
            if ref_date.hour not in item["hours"]:
                continue

            embed = Embed(title=user.display_name, color=user.color, timestamp=ref_date)
            embed.set_thumbnail(url=user.display_avatar)
            text = quote_plus(f"User's time is {ref_date.strftime('%I:%M %p')}")
            embed.set_image(url=f"https://dummyimage.com/468x60/FFFFFF/000000&text={text}")
            user_data = [datetime.combine(msg.created_at, time(hour=x), tz) for x in item["hours"]]
            data1 = AFKSchedule(user_data)
            data2 = data1.astimezone(reference_tz) if reference_tz else data1
            desc1, desc2 = data1.text, data2.text
            if desc1 != desc2 and desc1 and desc2:
                embed.add_field(name="In user's timezone", value=desc1, inline=False)
                embed.add_field(name="In your timezone", value=desc2, inline=False)
            elif not reference_tz:
                embed.add_field(name="In user's timezone", value=desc1, inline=False)
            else:
                embed.description = desc1 or desc2
            embeds.append(embed)

        if embeds:
            await msg.channel.send(
                content=msg.author.mention,
                embeds=embeds[:10],
                delete_after=10,
                allowed_mentions=AllowedMentions(users=True),
            )

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def ping(self, itx: Interaction[CustomBot], member: Member | User):
        """Command used to ping roles, and even users.

        Parameters
        ----------
        itx : Interaction[CustomBot],
            Interaction[CustomBot],
        member : Member | User
            Member to ping
        """
        db = self.bot.mongo_db("Characters")
        guild = itx.guild
        user = self.bot.supporting.get(itx.user, itx.user)
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": user.id, "server": guild.id})]
        modal = RPModal(user=user, ocs=ocs, to_user=member)
        if await modal.check(itx):
            await itx.response.send_modal(modal)

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    async def afk(self, itx: Interaction[CustomBot], member: Member | User):
        """Check users' AFK Schedule

        Parameters
        ----------
        itx : Interaction[CustomBot],
            Interaction[CustomBot],
        member : Member
            User to Check
        """
        await self.check_afk(itx, member)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Roles(bot))
