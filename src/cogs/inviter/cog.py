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
    ButtonStyle,
    Color,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    PartialInviteGuild,
    TextChannel,
    Thread,
    Webhook,
)
from discord.ext.commands import Cog
from discord.ext.commands.converter import InviteConverter
from discord.ui import Button, View, button
from discord.utils import utcnow

from src.structures.bot import CustomBot
from src.utils.matches import INVITE

__all__ = ("Inviter", "setup")


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
        if not isinstance(invite_guild := invite.guild, PartialInviteGuild):
            return
        partnered_role = guild.get_role(725582056620294204)
        mod_ch: TextChannel = self.bot.get_channel(877376320093425685)

        generator = Embed(
            title=f"__**{guild.name} is now officially partnered with {invite_guild.name}**__",
            description=ctx.clean_content[:2048],
            colour=Color.blurple(),
            timestamp=utcnow(),
        )
        files = []
        if (icon := invite_guild.icon) and (
            file := await self.bot.get_file(
                icon.with_size(4096).url,
                "server_icon",
            )
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
            and ctx.channel.category_id == 735900056946868335
        ):
            await handler(ctx.channel)
        else:
            generator.set_footer(
                text=author.display_name,
                icon_url=author.avatar.url,
            )
            embed = Embed(
                title="Server Invite Detected - Possible Partner/Advertiser",
                color=author.color,
                description=ctx.content,
                timestamp=utcnow(),
            )
            embed.set_author(
                name=author.display_name,
                icon_url=author.avatar.url,
            )
            embed.set_footer(
                text=f"ID: {author.id}",
                icon_url=invite_guild.icon.url,
            )
            embed.add_field(
                name="Posted at",
                value=ctx.channel.mention,
            )
            if user := invite.inviter:
                embed.add_field(
                    name=f"Invite creator - {user.name!r}",
                    value=user.mention,
                )
            embed.set_thumbnail(url=invite_guild.icon.url)

            if images := ctx.attachments:
                embed.set_image(url=images[0].proxy_url)

            class InviteView(View):
                async def interaction_check(
                    self,
                    interaction: Interaction,
                ) -> bool:
                    resp: InteractionResponse = interaction.response
                    if not interaction.user.guild_permissions.administrator:
                        await resp.send_message(
                            "You are not an administrator",
                            ephemeral=True,
                        )
                        return False
                    return True

                async def process(
                    self,
                    btn: Button,
                    inter: Interaction,
                ):
                    """Process Partnership

                    Parameters
                    ----------
                    btn: Button
                        Button
                    inter: Interaction
                        Interaction
                    """
                    member: Member = inter.user
                    resp: InteractionResponse = inter.response
                    thread = await handler(int(btn.custom_id))
                    thread.add_user(ctx.author)
                    thread.add_user(member)
                    await resp.send_message(
                        f"{btn.label} has been added by {member.display_name}"
                    )
                    await author.add_roles(partnered_role)
                    await inter.message.delete()
                    self.stop()

                @button(
                    label="Pokemon Partnership",
                    style=ButtonStyle.green,
                    row=0,
                    custom_id="855197800907407360",
                )
                async def partner1(self, btn, inter) -> None:
                    await self.process(btn, inter)

                @button(
                    label="Standard Partnership",
                    style=ButtonStyle.green,
                    row=0,
                    custom_id="855199463978041355",
                )
                async def partner2(self, btn, inter):
                    await self.process(btn, inter)

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

            files_embed, embed = await self.bot.embed_raw(embed=embed)
            view = InviteView(timeout=None)
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
