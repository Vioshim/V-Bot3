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
        self.message: Optional[Message] = None

    async def load_partners(self):
        if not (channel := self.bot.get_channel(957602085753458708)):
            channel: TextChannel = await self.bot.fetch_channel(957602085753458708)

        if self.message is None:
            async for m in channel.history(limit=1, oldest_first=False):
                if m.embeds and m.author == self.bot.user and not m.content:
                    self.message = m

        guild = channel.guild
        view = InviterView(timeout=None)
        embed = Embed(title="Partnership Rules", description=channel.topic, color=Color.blurple())
        embed.set_footer(text=guild.name, icon_url=guild.icon)
        embed.set_thumbnail(url=guild.icon)
        embed.set_image(url="https://dummyimage.com/500x5/FFFFFF/000000&text=%20")

        if self.message:
            try:
                self.message = await self.message.edit(embed=embed, view=view)
            except DiscordException:
                self.message = await channel.send(embed=embed, view=view)
        else:
            self.message = await channel.send(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_partners()

    @commands.command()
    @commands.is_owner()
    @commands.guild_only()
    async def update(
        self,
        ctx: commands.Context,
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
        if not reference:
            reference = ctx.message.reference.resolved
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
            tags=sorted((msg.embeds[0].footer.text or "").split(", ")),
        )

        db = self.bot.mongo_db("Partnerships")
        await db.replace_one({"id": guild.id}, partner.data, upsert=True)
        await ctx.message.delete(delay=3)

    @commands.Cog.listener()
    async def on_message(self, ctx: Message):
        """Discord invite detection

        Parameters
        ----------
        ctx: Message
            Message to be scanned
        """
        if (
            ctx.flags.ephemeral
            or not self.message
            or not ctx.guild
            or not ctx.content
            or ctx.author == self.bot.user
            or ctx.channel.id == 1020157013126283284
        ):
            return

        context = await self.bot.get_context(ctx)

        if context.command:
            return

        if ctx.channel.id == 957602085753458708 and ctx.author == self.bot.user:
            if m := self.message:
                view = InviterView(timeout=None)
                self.message = await ctx.channel.send(embeds=m.embeds, view=view)
                await m.delete(delay=0)
            return

        if not (match := INVITE.search(ctx.content)):
            if ctx.channel.id == 957602085753458708:
                await ctx.delete(delay=0)
            return

        try:
            invite = await self.bot.fetch_invite(url=match.group(1))
        except DiscordException:
            return

        guild: Guild = ctx.guild
        author: Member = ctx.author

        if not isinstance(invite_guild := invite.guild, PartialInviteGuild) or invite_guild == guild:
            return

        partner_channel = ctx.guild.get_channel(957602085753458708)
        mod_ch = self.bot.get_partial_messageable(id=1020157013126283284, guild_id=guild.id)

        db = self.bot.mongo_db("Partnerships")

        if item := await db.find_one({"id": invite_guild.id}):
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
            description=ctx.clean_content[:4096],
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
        if attachments := [x for x in ctx.attachments if x.content_type.startswith("image/")]:
            file = await attachments[0].to_file(use_cached=True)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)
        elif (embeds := ctx.embeds) and (thumbnail := embeds[0].thumbnail):
            file = await self.bot.get_file(url=thumbnail.url)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)
        elif icon_banner := invite_guild.splash or invite_guild.banner:
            file = await icon_banner.with_size(4096).to_file()
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)

        link_view = View()
        link_view.add_item(Button(label="Click here to join", url=invite.url))

        pm_manager_role = guild.get_role(788215077336514570)
        if pm_manager_role and pm_manager_role in author.roles and ctx.channel.id == 957602085753458708:
            view_class, target = InviteComplex, ctx.channel
        else:
            view_class, target = InviteAdminComplex, mod_ch

        data = InviterView.group_method({Partner.from_mongo_dict(x) async for x in db.find()})
        view = view_class(invite=invite, member=ctx.author, tags=data, target=target)
        await ctx.delete(delay=0)
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

                if isinstance(view, InviteAdminComplex) and (partnered_role := get(ctx.guild.roles, name="Partners")):
                    await ctx.author.add_roles(partnered_role)

                partner = Partner(
                    id=invite_guild.id,
                    msg_id=message.id,
                    url=invite.id,
                    title=invite_guild.name,
                    content=message.embeds[0].description,
                    icon_url=message.embeds[0].thumbnail.url,
                    image_url=message.embeds[0].image.url,
                    tags=choices,
                )

                await db.replace_one({"id": invite_guild.id}, partner.data, upsert=True)
                if msg := self.message:
                    self.message = await msg.delete(delay=0)
                await self.load_partners()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        db = self.bot.mongo_db("Partnerships")
        if payload.channel_id == 957602085753458708:
            await db.delete_one({"msg_id": payload.message_id})

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        db = self.bot.mongo_db("Partnerships")
        if payload.channel_id == 957602085753458708:
            await db.delete_many({"msg_id": {"$in": list(payload.message_ids)}})


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Inviter(bot))
