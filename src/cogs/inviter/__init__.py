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
    Object,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    Thread,
    Webhook,
    WebhookMessage,
)
from discord.ext import commands
from discord.ext.commands.converter import BadInviteArgument, InviteConverter
from discord.ui import Button, Select, View, button, select
from discord.utils import find, get, utcnow

from src.cogs.inviter.classifier import InviterView
from src.pagination.complex import Complex
from src.structures.bot import CustomBot
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
        super().__init__(timeout=None)
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
            sct.add_option(
                label=key,
                value=key,
                description=f"Adds {key} partnership",
            )

        if not sct.options:
            sct.add_option(label="NOTHING", value="NOTHING")
            sct.disabled = True
        else:
            sct.disabled = False

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if not interaction.user.guild_permissions.administrator:
            await resp.send_message("You are not an administrator", ephemeral=True)
            return False
        return True

    @select(placeholder="Select Category", custom_id="partner")
    async def process(self, inter: Interaction, sct: Select):
        member: Member = inter.user
        resp: InteractionResponse = inter.response
        w: Webhook = await inter.client.webhook(957602085753458708, reason="Partnership")
        self.embed.set_footer(text=sct.values[0])
        message = await w.send(
            content=self.invite.url,
            embed=self.embed,
            wait=True,
            thread=Object(id=957604961330561065),
            **self.kwargs,
        )
        self.data.setdefault(sct.values[0], set())
        self.data[sct.values[0]].add(message)
        await resp.pong()
        if partnered_role := get(member.guild.roles, name="Partners"):
            await self.author.add_roles(partnered_role)
        await inter.message.delete()
        self.stop()

    @button(
        label="Not interested...",
        style=ButtonStyle.red,
        row=0,
    )
    async def accident(
        self,
        inter: Interaction,
        btn: Button,
    ) -> None:
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
        self.message: Optional[WebhookMessage] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ready:
            thread: Thread = await self.bot.fetch_channel(957604961330561065)
            if thread.archived:
                await thread.edit(archived=False)
            messages = [m async for m in thread.history(limit=None, oldest_first=True)]
            w = await self.bot.webhook(thread)
            self.view = InviterView(messages)
            self.message = await w.edit_message(957604961330561065, view=self.view)
            self.ready = True

    @commands.Cog.listener()
    async def on_message(self, ctx: Message) -> None:
        """Discord invite detection

        Parameters
        ----------
        ctx: Message
            Message to be scanned
        """
        if not ctx.guild or ctx.author == self.bot.user or ctx.webhook_id or not (match := INVITE.search(ctx.content)):
            if isinstance(ctx.author, Member) and ctx.author.guild_permissions.administrator:
                return
            if ctx.channel.id == 957602085753458708:
                await ctx.delete()
            return

        context = await self.bot.get_context(ctx)

        try:
            invite = await self.adapt.convert(ctx=context, argument=match.group())
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
            description=ctx.clean_content[:2048],
            colour=Color.blurple(),
            timestamp=utcnow(),
        )

        files = []
        if (
            (icon := invite_guild.icon)
            and (icon_url := icon.with_size(4096).url)
            and (file := await self.bot.get_file(icon_url, "server_icon"))
        ):
            generator.set_thumbnail(url=f"attachment://{file.filename}")
            files.append(file)
        if attachments := ctx.attachments:
            file = await attachments[0].to_file(use_cached=True)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)
        elif (embeds := ctx.embeds) and (thumbnail := embeds[0].thumbnail):
            file = await self.bot.get_file(url=thumbnail.url)
            generator.set_image(url=f"attachment://{file.filename}")
            files.append(file)

        link_view = View()
        link_view.add_item(Button(label="Click Here to Join", url=invite.url))
        data = self.view.data
        if author.guild_permissions.administrator and ctx.channel.id == 957604961330561065:
            w = await self.bot.webhook(957602085753458708, reason="Partnership")
            message = await w.send(
                content=invite.url,
                embed=generator,
                wait=True,
                thread=Object(id=957604961330561065),
                view=link_view,
                files=files,
            )
            view: Complex[str] = Complex(
                member=author,
                values=data.keys(),
                target=ctx.channel,
                timeout=None,
            )

            async with view.send(title="Select Category", single=True) as choice:
                if choice:
                    generator.set_footer(text=choice)
                    if partnered_role := get(author.guild.roles, name="Partners"):
                        await author.add_roles(partnered_role)
                    await message.edit(embed=generator)
                    messages = self.view.messages
                    messages.append(message)
                    self.view.messages = messages
                    self.message = await self.message.edit(view=self.view)
                await ctx.delete()
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
            view = InviteView(
                invite,
                generator,
                ctx.author,
                data,
                view=link_view,
                files=files,
            )
            await mod_ch.send(
                content=invite.url,
                embed=embed,
                files=files_embed,
                view=view,
            )
            await ctx.delete()

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        if payload.channel_id != 957604961330561065:
            return
        messages = self.view.messages
        if any(x.id == payload.message_id for x in messages):
            messages = [x for x in messages if x.id != payload.message_id]
            self.view.messages = messages
            await self.message.edit(view=self.view)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        if payload.channel_id != 957604961330561065:
            return
        messages = self.view.messages
        if any(x.id in payload.message_ids for x in messages):
            messages = [x for x in messages if x.id not in payload.message_ids]
            self.view.messages = messages
            await self.message.edit(view=self.view)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Inviter(bot))
