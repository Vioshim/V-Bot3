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

from src.cogs.inviter.classifier import InviteAdminComplex, InviteComplex, InviterView
from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.matches import INVITE

__all__ = ("Inviter", "setup")


class Inviter(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready = False
        self.message: Optional[Message] = None
        self.view: Optional[InviterView] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            if not (channel := self.bot.get_channel(957602085753458708)):
                channel: TextChannel = await self.bot.fetch_channel(957602085753458708)

            messages: list[Message] = []
            async for m in channel.history(limit=None, oldest_first=True):
                if m.embeds and m.author == self.bot.user:
                    if m.content:
                        messages.append(m)
                    else:
                        self.message = m

            guild = channel.guild
            self.view = InviterView()
            self.view.group_method(messages)
            embed = Embed(title="Partnership Rules", description=channel.topic, color=Color.blurple())
            embed.set_footer(text=guild.name, icon_url=guild.icon)
            embed.set_thumbnail(url=guild.icon)
            embed.set_image(url="https://dummyimage.com/500x5/FFFFFF/000000&text=%20")
            msg = self.message
            if not msg or messages[-1].created_at > msg.created_at:
                if msg:
                    await msg.delete(delay=0)
                msg = await channel.send(embed=embed, view=self.view)
            else:
                msg = await self.message.edit(embed=embed, view=self.view)
            self.message = msg
            self.ready = True

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
        view.add_item(Button(label="Click Here to Join", url=invite.url))

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
        msgs = [x for x in self.view.messages if x.id != reference.id]
        msgs.append(reference)
        self.view.messages = msgs

        await reference.edit(content=invite.url, attachments=attachments, embed=embed, view=view)
        await ctx.message.delete(delay=3)

    @commands.Cog.listener()
    async def on_message(self, ctx: Message) -> None:
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
                self.message = await ctx.channel.send(embeds=m.embeds, view=self.view)
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

        mod_ch = self.bot.get_partial_messageable(id=1020157013126283284, guild_id=guild.id)

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
        link_view.add_item(Button(label="Click Here to Join", url=invite.url))

        pm_manager_role = guild.get_role(788215077336514570)
        if pm_manager_role and pm_manager_role in author.roles and ctx.channel.id == 957602085753458708:
            view_class, target = InviteComplex, ctx.channel
        else:
            view_class, target = InviteAdminComplex, mod_ch

        view = view_class(invite=invite, member=ctx.author, tags=self.view.data, target=target)
        await ctx.delete(delay=0)
        async with view.send(description=generator.description) as choices:
            if choices:
                generator.set_footer(text=", ".join(choices))
                if partnered_role := get(author.guild.roles, name="Partners"):
                    await author.add_roles(partnered_role)
                channel = ctx.guild.get_channel(957602085753458708)
                message = await channel.send(
                    content=invite.url,
                    embed=generator,
                    view=link_view,
                    files=files,
                )
                self.view.append(message)
                self.message = await self.message.edit(view=self.view)
                if isinstance(view, InviteAdminComplex) and (partnered_role := get(ctx.guild.roles, name="Partners")):
                    await ctx.author.add_roles(partnered_role)

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        if payload.channel_id != 957602085753458708:
            return
        if view := self.view:
            messages = view.messages
            if any(x.id == payload.message_id for x in messages):
                messages = [x for x in messages if x.id != payload.message_id]
                view.group_method(messages)
                self.message = await self.message.edit(view=view)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        if payload.channel_id != 957602085753458708:
            return
        if view := self.view:
            messages = view.messages
            if any(x.id in payload.message_ids for x in messages):
                messages = [x for x in messages if x.id not in payload.message_ids]
                view.group_method(messages)
                self.message = await self.message.edit(view=view)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Inviter(bot))
