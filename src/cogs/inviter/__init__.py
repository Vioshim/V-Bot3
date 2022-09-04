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


from typing import Optional

from discord import (
    ButtonStyle,
    Color,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Invite,
    Member,
    Message,
    PartialEmoji,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    TextChannel,
)
from discord.ext import commands
from discord.ext.commands.converter import BadInviteArgument, InviteConverter
from discord.ui import Button, Select, View, button, select
from discord.utils import find, get, utcnow

from src.cogs.inviter.classifier import InviterView
from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR
from src.utils.matches import INVITE

__all__ = ("Inviter", "setup")


class InviteView(View):
    def __init__(
        self,
        invite: Invite,
        embed: Embed,
        author: Member,
        data: dict[str, set[Message]],
        **kwargs,
    ):
        super(InviteView, self).__init__(timeout=None)
        self.invite = invite
        self.embed = embed
        self.author = author
        self.data = data
        self.kwargs = kwargs
        self.setup()

    def setup(self):
        sct: Select = self.process
        sct.options.clear()
        for key in self.data:
            sct.add_option(label=key, value=key, description=f"Adds {key} partnership")

        if not sct.options:
            sct.add_option(label="NOTHING", value="NOTHING")
            sct.disabled = True
        else:
            sct.disabled = False

        sct.max_values = len(sct.values)

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if not interaction.user.guild_permissions.administrator:
            await resp.send_message("You are not an administrator", ephemeral=True)
            return False
        return True

    @select(placeholder="Select Tags", custom_id="partner")
    async def process(self, inter: Interaction, sct: Select):
        member: Member = inter.user
        resp: InteractionResponse = inter.response
        channel = inter.guild.get_channel(957602085753458708)
        self.embed.set_footer(text=", ".join(sct.values))
        message = await channel.send(content=self.invite.url, embed=self.embed, **self.kwargs)
        for tag in sct.values:
            self.data.setdefault(tag, set())
            self.data[tag].add(message)
        await resp.pong()
        if partnered_role := get(member.guild.roles, name="Partners"):
            await self.author.add_roles(partnered_role)
        await inter.message.delete()
        self.stop()

    @button(label="Not interested...", style=ButtonStyle.red, row=0)
    async def accident(self, inter: Interaction, btn: Button) -> None:
        """Conclude Partnership

        Parameters
        ----------
        btn: Button
            Button
        inter: Interaction
            Interaction
        """
        member: Member = inter.user
        resp: InteractionResponse = inter.response
        await resp.send_message(f"{btn.label!r} has been chosen by {member.display_name}")
        await inter.message.delete()
        self.stop()


class Inviter(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.adapt = InviteConverter()
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
    async def update(self, ctx: commands.Context, invite: Invite, reference: Optional[Message] = None):
        if not reference:
            reference = ctx.message.reference.resolved

        view = View()
        view.add_item(Button(label="Click Here to Join", url=invite.url))

        guild = invite.guild
        if guild.icon:
            attachments, embed = await self.bot.embed_raw(reference.embeds[0], "thumbnail")
            fmt = "gif" if guild.icon.is_animated() else "png"
            icon = guild.icon.with_size(4096).with_format(fmt)
            file = await icon.to_file(filename=f"{guild.id}.{fmt}")
            attachments.append(file)
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        else:
            attachments, embed = await self.bot.embed_raw(reference.embeds[0])

        embed.description = INVITE.sub(invite.url, embed.description)
        if not embed.image or embed.image.url == WHITE_BAR and (icon := guild.discovery_splash or guild.banner):
            file = await guild.banner.with_size(4096).to_file()
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
        if ctx.flags.ephemeral or not self.message or not ctx.guild or not ctx.content:
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

        context = await self.bot.get_context(ctx)

        try:
            invite = await self.adapt.convert(ctx=context, argument=match.group(1))
        except BadInviteArgument:
            return

        guild: Guild = ctx.guild
        author: Member = ctx.author

        if not (invite_guild := invite.guild) or invite_guild == guild:
            return

        mod_ch = find(lambda x: "mod-chat" in x.name, guild.channels)
        if not mod_ch:
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
        elif icon := invite_guild.discovery_splash or invite_guild.banner:
            file = await guild.banner.with_size(4096).to_file()
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)

        link_view = View()
        link_view.add_item(Button(label="Click Here to Join", url=invite.url))
        data = self.view.data
        pm_manager_role = guild.get_role(788215077336514570)
        if pm_manager_role and pm_manager_role in author.roles and ctx.channel.id == 957602085753458708:
            view: Complex[str] = Complex(
                member=author,
                values=data.keys(),
                max_values=len(data),
                parser=lambda x: (x, None),
                target=ctx.channel,
                timeout=None,
                emoji_parser=PartialEmoji(name="MessageLink", id=778925231506587668),
            )
            await ctx.delete(delay=0)
            async with view.send(title="Select Category") as choices:
                if choices:
                    generator.set_footer(text=", ".join(choices))
                    if partnered_role := get(author.guild.roles, name="Partners"):
                        await author.add_roles(partnered_role)
                    message = await ctx.channel.send(
                        content=invite.url,
                        embed=generator,
                        view=link_view,
                        files=files,
                    )
                    self.view.append(message)
                    self.message = await self.message.edit(view=self.view)
        else:
            generator.set_footer(text=author.display_name, icon_url=author.display_avatar.url)
            embed = Embed(
                title="Server Invite Detected - Possible Partner/Advertiser",
                color=author.color,
                description=ctx.content,
                timestamp=utcnow(),
            )
            embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
            if icon := invite_guild.icon:
                embed.set_footer(text=f"ID: {author.id}", icon_url=icon.url)
                embed.set_thumbnail(url=icon.url)
            else:
                embed.set_footer(text=f"ID: {author.id}")
            embed.add_field(name="Posted at", value=ctx.channel.mention)

            if user := invite.inviter:
                embed.add_field(name=f"Invite creator - {user.name!r}", value=user.mention)

            if images := ctx.attachments:
                embed.set_image(url=images[0].proxy_url)

            files_embed, embed = await self.bot.embed_raw(embed=embed)
            view = InviteView(invite, generator, ctx.author, data, view=link_view, files=files)
            await mod_ch.send(content=invite.url, embed=embed, files=files_embed, view=view)
            await ctx.delete(delay=0)

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
