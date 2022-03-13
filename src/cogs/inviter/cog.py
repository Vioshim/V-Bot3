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

from discord import (
    ButtonStyle,
    CategoryChannel,
    Color,
    DiscordException,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    SelectOption,
    Thread,
    Webhook,
)
from discord.ext.commands import Cog
from discord.ext.commands.converter import InviteConverter
from discord.ui import Button, Select, View, button, select
from discord.utils import find, get, utcnow

from src.structures.bot import CustomBot
from src.utils.matches import INVITE

__all__ = ("Inviter", "setup")


class InviteView(View):
    def __init__(
        self,
        handler,
        category: CategoryChannel,
        author: Member,
    ):
        super().__init__(timeout=None)
        self.category = category
        self.handler = handler
        self.author = author

        sct: Select = self.process
        items = []
        for channel in category.channels:
            try:
                emoji, name = channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = None, channel.name
            finally:
                name = name.replace("-", " ").title()
                items.append(
                    SelectOption(
                        label=name,
                        value=channel.id,
                        emoji=emoji,
                    )
                )

        sct.options = items

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if not interaction.user.guild_permissions.administrator:
            await resp.send_message(
                "You are not an administrator", ephemeral=True
            )
            return False
        return True

    @select(placeholder="Select Partnership Channel", custom_id="partner")
    async def process(self, sct: Select, inter: Interaction):
        member: Member = inter.user
        resp: InteractionResponse = inter.response
        thread: Thread = await self.handler(idx := int(sct.values[0]))
        await thread.add_user(member)
        await thread.add_user(self.author)
        await resp.send_message(
            f"<#{idx}> has been added by {member.display_name}"
        )
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
        btn: Button,
        inter: Interaction,
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
        await resp.send_message(
            f"{btn.label!r} has been chosen by {member.display_name}"
        )
        await inter.message.delete()
        self.stop()


class Inviter(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.adapt = InviteConverter()

    @Cog.listener()
    async def on_message(self, ctx: Message) -> None:
        """Discord invite detection

        Parameters
        ----------
        ctx: Message
            Message to be scanned
        """
        if (
            not ctx.guild
            or ctx.author == self.bot.user
            or ctx.webhook_id
            or not (match := INVITE.search(ctx.content))
        ):
            return

        context = await self.bot.get_context(ctx)

        invite = await self.adapt.convert(ctx=context, argument=match.group())

        guild: Guild = ctx.guild
        author: Member = ctx.author

        if not (invite_guild := invite.guild):
            return

        if not (category := ctx.channel.category):
            with suppress(DiscordException):
                await ctx.delete()
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

        link_view = View(Button(label="Click Here to Join", url=invite.url))

        async def handler(w: Webhook) -> Thread:
            """Inner function to add parameters

            Parameters
            ----------
            w : Webhook
                Webhook

            Returns
            -------
            Thread
                Resulting thread
            """
            if not isinstance(w, Webhook):
                w = await self.bot.webhook(w, reason="Partnership")

            msg = await w.send(
                content=invite.url,
                embed=generator,
                view=link_view,
                files=files,
                wait=True,
            )
            thread = await msg.create_thread(name=invite.guild.name)

            mentions = [
                member
                for x in ctx.mentions
                if (member := guild.get_member(x.id))
            ]
            if (inviter := invite.inviter) and (
                member := guild.get_member(inviter.id)
            ):
                mentions.append(member)

            for user in mentions:
                await thread.add_user(user)

            return thread

        if (
            author.guild_permissions.administrator
            and "partner" in category.name.lower()
        ):
            await handler(ctx.channel)
        else:
            generator.set_footer(
                text=author.display_name,
                icon_url=author.display_avatar.url,
            )
            embed = Embed(
                title="Server Invite Detected - Possible Partner/Advertiser",
                color=author.color,
                description=ctx.content,
                timestamp=utcnow(),
            )
            embed.set_author(
                name=author.display_name,
                icon_url=author.display_avatar.url,
            )
            if icon := invite_guild.icon:
                embed.set_footer(text=f"ID: {author.id}", icon_url=icon.url)
                embed.set_thumbnail(url=icon.url)
            else:
                embed.set_footer(text=f"ID: {author.id}")
            embed.add_field(name="Posted at", value=ctx.channel.mention)

            if user := invite.inviter:
                embed.add_field(
                    name=f"Invite creator - {user.name!r}",
                    value=user.mention,
                )

            if images := ctx.attachments:
                embed.set_image(url=images[0].proxy_url)

            files_embed, embed = await self.bot.embed_raw(embed=embed)
            view = InviteView(handler, category, ctx.author)
            await mod_ch.send(
                content=invite.url,
                embed=embed,
                files=files_embed,
                view=view,
            )
        await ctx.delete()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot

    Returns
    -------

    """
    bot.add_cog(Inviter(bot))
