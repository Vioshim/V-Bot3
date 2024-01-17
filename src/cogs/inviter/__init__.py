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
from dataclasses import asdict
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    Guild,
    Invite,
    Member,
    Message,
    PartialInviteGuild,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    TextChannel,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import get, utcnow

from src.cogs.inviter.classifier import (
    InviteAdminComplex,
    InviteComplex,
    InviterView,
    Partner,
)
from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.matches import INVITE

__all__ = ("Inviter", "setup")


class Inviter(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.partnerships_messages: dict[int, Message] = {}
        self.partnerships_channels: dict[int, int] = {}
        self.partnerships_notifis: dict[int, int] = {}

    async def load_partners(self, **partnerships: int | list[int]):
        channel_id = partnerships.get("channel")
        if not (channel := self.bot.get_channel(channel_id)):
            channel: TextChannel = await self.bot.fetch_channel(channel_id)

        self.partnerships_channels[channel.guild.id] = channel.id
        self.partnerships_notifis[channel.guild.id] = partnerships.get("notification")

        guild = channel.guild
        if not self.partnerships_messages.get(guild.id):
            async for m in channel.history(limit=1, oldest_first=False):
                if m.embeds and m.author == self.bot.user and not m.content:
                    self.partnerships_messages[guild.id] = m

        view = InviterView(timeout=None)
        embed = Embed(title="Partnership Rules", description=channel.topic, color=Color.blurple())
        embed.set_footer(text=guild.name, icon_url=guild.icon)
        embed.set_thumbnail(url=guild.icon)
        embed.set_image(url="https://dummyimage.com/500x5/FFFFFF/000000&text=%20")

        if msg := self.partnerships_messages.get(guild.id):
            try:
                message = await msg.edit(embed=embed, view=view)
            except DiscordException:
                message = await channel.send(embed=embed, view=view)
        else:
            message = await channel.send(embed=embed, view=view)

        self.partnerships_messages[guild.id] = message

    @commands.Cog.listener()
    async def on_ready(self):
        db = self.bot.mongo_db("InfoData")
        async for item in db.find(
            {"partnerships": {"$exists": True, "$ne": None}},
            {"partnerships.channel": {"$exists": True, "$ne": None}},
            {"_id": 0, "partnerships": 1},
        ):
            await self.load_partners(**item["partnerships"])

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def update(
        self,
        ctx: commands.Context[CustomBot],
        invite: Optional[Invite] = None,
        reference: Optional[Message] = None,
    ):
        """Update Invite command

        Parameters
        ----------
        ctx : commands.Context
            Context
        invite : Optional[Invite], optional
            Invite to update, by default None
        reference : Optional[Message], optional
            Message reference, by default None
        """

        reference = reference or (ctx.message.reference and ctx.message.reference.resolved)

        if not reference:
            return await ctx.reply("No message reference", delete_after=2)

        if not invite and (invite_url := INVITE.search(reference.content) or INVITE.search(ctx.message.content)):
            with suppress(DiscordException):
                invite = await self.bot.fetch_invite(url=invite_url.group(1))

        if invite is None:
            return await ctx.reply("Invalid URL", delete_after=2)

        view = View()
        view.add_item(Button(label="Click here to join", url=invite.url))

        guild: PartialInviteGuild = invite.guild

        if guild.icon:
            attachments, embed = await self.bot.embed_raw(reference.embeds[0], "thumbnail")
            fmt = "gif" if guild.icon.is_animated() else "png"
            icon = guild.icon.with_size(4096).with_format(fmt)
            file = await icon.to_file(filename=f"{guild.id}.{fmt}")
            attachments.append(file)
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        else:
            attachments, embed = await self.bot.embed_raw(reference.embeds[0])

        embed.title = f"__**{ctx.guild.name} is now officially partnered with {guild.name}**__"
        embed.description = INVITE.sub(invite.url, embed.description)

        if (not embed.image or embed.image.url == WHITE_BAR) and (icon_banner := guild.splash or guild.banner):
            file = await icon_banner.with_size(4096).to_file()
            embed.set_image(url=f"attachment://{file.filename}")
            attachments.append(file)

        msg = await reference.edit(content=invite.url, attachments=attachments, embed=embed, view=view)

        partner = Partner(
            id=guild.id,
            msg_id=msg.id,
            url=invite.id,
            title=guild.name,
            content=msg.embeds[0].description,
            icon_url=msg.embeds[0].thumbnail.url,
            image_url=msg.embeds[0].image.url,
            tags=sorted(x for x in (msg.embeds[0].footer.text or "").split(", ") if x),
        )

        db = self.bot.mongo_db("Partnerships")
        await db.replace_one({"id": guild.id, "server": ctx.guild.id}, asdict(partner), upsert=True)
        await ctx.message.delete(delay=3)

    @commands.Cog.listener()
    async def on_message(self, msg: Message):
        """Discord invite detection

        Parameters
        ----------
        msg: Message
            Message to be scanned
        """
        if not msg.guild:
            return

        channel_id, message, notif_id = (
            self.partnerships_channels.get(msg.guild.id),
            self.partnerships_messages.get(msg.guild.id),
            self.partnerships_notifis.get(msg.guild.id),
        )
        if not (channel_id and message and notif_id):
            return

        if (
            msg.flags.ephemeral
            or not message
            or not msg.content
            or msg.author == self.bot.user
            or msg.channel.id == channel_id
        ):
            return

        context = await self.bot.get_context(msg)

        if context.command:
            return

        if msg.channel.id == channel_id and msg.author == self.bot.user:
            if m := self.message:
                view = InviterView(timeout=None)
                self.message = await msg.channel.send(embeds=m.embeds, view=view)
                await m.delete(delay=0)
            return

        if not (match := INVITE.search(msg.content)):
            if msg.channel.id == channel_id:
                await msg.delete(delay=0)
            return

        try:
            invite = await self.bot.fetch_invite(url=match.group(1))
        except DiscordException:
            return

        guild: Guild = msg.guild
        author: Member = msg.author
        invite_guild = invite.guild

        if invite_guild.id == guild.id:
            return

        partner_channel = msg.guild.get_channel(channel_id)
        mod_ch = self.bot.get_partial_messageable(id=notif_id, guild_id=guild.id)

        db = self.bot.mongo_db("Partnerships")

        if item := await db.find_one({"id": invite_guild.id, "server": guild.id}):
            url = partner_channel.get_partial_message(item["msg_id"]).jump_url
            view = View()
            view.add_item(Button(label="Jump URL", url=url))
            with suppress(DiscordException):
                await context.reply(
                    content="We are partnered with this server.",
                    view=view,
                    allowed_mentions=AllowedMentions(users=True),
                    delete_after=3,
                )
            return

        generator = Embed(
            title=f"__**{guild.name} is now officially partnered with {invite_guild.name}**__",
            description=msg.clean_content[:4096],
            colour=Color.blurple(),
            timestamp=utcnow(),
        )

        files = []
        if (
            (icon := invite_guild.icon)
            and (icon_url := icon.with_size(4096).url)
            and (file := await self.bot.get_file(icon_url, str(invite_guild.id)))
        ):
            generator.set_thumbnail(url=f"attachment://{file.filename}")
            files.append(file)
        if attachments := [x for x in msg.attachments if x.content_type.startswith("image/")]:
            file = await attachments[0].to_file(use_cached=True)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)
        elif (embeds := msg.embeds) and (thumbnail := embeds[0].thumbnail):
            file = await self.bot.get_file(url=thumbnail.url)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)
        elif icon_banner := invite_guild.splash or invite_guild.banner:
            file = await icon_banner.with_size(4096).to_file()
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)

        link_view = View()
        link_view.add_item(Button(label="Click here to join", url=invite.url))

        pm_manager_role = get(guild.roles, name="Recruiter")
        if pm_manager_role and pm_manager_role in author.roles and msg.channel.id == channel_id:
            view_class, target = InviteComplex, msg.channel
        else:
            view_class, target = InviteAdminComplex, mod_ch

        data = InviterView.group_method({Partner(**x) async for x in db.find({}, {"_id": 0})})
        view = view_class(invite=invite, member=msg.author, tags=data, target=target)
        await msg.delete(delay=0)
        async with view.send(description=generator.description) as choices:
            if choices:
                generator.set_footer(text=", ".join(choices))
                if partnered_role := get(author.guild.roles, name="Partners"):
                    await author.add_roles(partnered_role)

                message = await partner_channel.send(
                    content=invite.url,
                    embed=generator,
                    view=link_view,
                    files=files,
                )

                if isinstance(view, InviteAdminComplex) and (partnered_role := get(msg.guild.roles, name="Partners")):
                    await msg.author.add_roles(partnered_role)

                partner = Partner(
                    id=invite_guild.id,
                    msg_id=message.id,
                    url=invite.id,
                    title=invite_guild.name,
                    content=message.embeds[0].description,
                    icon_url=message.embeds[0].thumbnail.url,
                    image_url=message.embeds[0].image.url,
                    tags=sorted(choices),
                )

                await db.replace_one({"id": invite_guild.id, "server": guild.id}, asdict(partner), upsert=True)
                if msg := self.message:
                    self.message = await msg.delete(delay=0)
                await self.load_partners()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if self.partnerships_channels.get(payload.guild_id) != payload.channel_id:
            return

        db = self.bot.mongo_db("Partnerships")
        await db.delete_one({"msg_id": payload.message_id, "server": payload.guild_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        if self.partnerships_channels.get(payload.guild_id) != payload.channel_id:
            return

        db = self.bot.mongo_db("Partnerships")
        await db.delete_many({"msg_id": {"$in": list(payload.message_ids)}, "server": payload.guild_id})


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Inviter(bot))
