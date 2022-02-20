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
from io import StringIO
from os import getenv
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    File,
    Guild,
    HTTPException,
    Member,
    Message,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    TextChannel,
    Webhook,
    WebhookMessage,
)
from discord.ext.commands import (
    CheckFailure,
    Cog,
    CommandError,
    CommandNotFound,
    CommandOnCooldown,
    Context,
    DisabledCommand,
    MaxConcurrencyReached,
    UserInputError,
)
from discord.ui import Button, View
from discord.utils import format_dt, utcnow
from yaml import dump

from src.cogs.information.information_view import RegionView
from src.structures.bot import CustomBot
from src.utils.etc import MAP_ELEMENTS, WHITE_BAR
from src.utils.functions import message_line
from src.utils.imagekit import ImageKit

__all__ = ("Information", "setup")


channels = {
    766018765690241034: "Question",
    918703451830100028: "Poll",
    728800301888307301: "Suggestion",
    769304918694690866: "Story",
    903627523911458816: "Storyline",
}

TENOR_API = getenv("TENOR_API")
GIPHY_API = getenv("GIPHY_API")


class Information(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.join: dict[Member, Message] = {}
        self.log: Optional[Webhook] = None
        self.info_msg: Optional[WebhookMessage] = None

    @Cog.listener()
    async def on_message(self, message: Message):

        if not (message.content and message.channel.id in channels):
            return

        if message.webhook_id:
            await message.delete()
            return

        if message.author.bot:
            return

        context = await self.bot.get_context(message)

        if context.command:
            return

        member: Member = message.author
        guild: Guild = member.guild
        self.bot.msg_cache_add(message)

        word = channels.get(message.channel.id, "Question")

        embed = Embed(
            title=word,
            description=message.content,
            timestamp=message.created_at,
            colour=message.author.colour,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        embeds = [embed]
        files = []
        for item in message.attachments:
            if len(embeds) < 10 and item.content_type.startswith("image/"):
                if embeds[0].image.url == WHITE_BAR:
                    aux = embed
                else:
                    aux = Embed(color=message.author.colour)
                    embeds.append(aux)
                aux.set_image(url=f"attachments://{item.filename}")
                file = await item.to_file()
                files.append(file)

        msg = await message.channel.send(embeds=embeds, files=files)

        thread = await msg.create_thread(name=f"{word} {msg.id}")

        await thread.add_user(member)

        if word == "Poll":
            await msg.add_reaction("\N{THUMBS UP SIGN}")
            await msg.add_reaction("\N{THUMBS DOWN SIGN}")

        if "RP" in word and (tupper := guild.get_member(431544605209788416)):
            await thread.add_user(tupper)

        await message.delete()

    async def member_count(self):
        """Function which updates the member count and the Information's view"""
        if not self.info_msg:
            return
        guild = self.info_msg.guild
        members = len([m for m in guild.members if not m.bot])
        total = len(guild.members)
        embed = self.info_msg.embeds[0].copy()
        data: dict[str, int] = {}
        if cog := self.bot.get_cog("Submission"):
            ocs = [oc for oc in cog.ocs.values() if guild.get_member(oc.author)]
            data["Characters"] = len(ocs)

        data["Members   "] = members
        data["Bots      "] = total - members
        data["Total     "] = total

        text = "\n".join(f"{key}: {value:03d}" for key, value in data.items())
        text = f"```yaml\n{text}\n```"

        if self.info_msg.embeds[0].description != text:
            embed.description = text
            await self.info_msg.edit(embed=embed)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        await self.member_count()
        if msg := self.join.get(member):
            with suppress(DiscordException):
                await msg.delete()
        guild: Guild = member.guild
        roles = member.roles[:0:-1]
        embed = Embed(
            title="Member Left - Roles",
            description="The user did not have any roles.",
            color=Color.red(),
            timestamp=utcnow(),
        )
        if text := "\n".join(f"> **•** {role.mention}" for role in roles):
            embed.description = text
        embed.set_footer(text=f"ID: {member.id}", icon_url=guild.icon.url)
        embed.set_image(url=WHITE_BAR)
        view = View()
        if value := self.bot.get_cog("Submission").oc_list.get(member.id):
            view.add_item(
                Button(
                    label="Characters",
                    url=f"https://discord.com/channels/719343092963999804/919277769735680050/{value}",
                )
            )

        asset = member.display_avatar.replace(format="png", size=4096)
        if file := await self.bot.get_file(
            asset.url,
            filename=str(member.id),
        ):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            await self.log.send(
                file=file,
                embed=embed,
                view=view,
                username=member.display_name,
                avatar_url=member.display_avatar.url,
            )

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await self.member_count()
        guild: Guild = member.guild
        welcome_channel: TextChannel = guild.get_channel(719343092963999807)
        if not welcome_channel:
            return
        embed = Embed(
            title="Member Joined",
            colour=Color.green(),
            description=f"{member.mention} - {member}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {member.id}")
        asset = member.display_avatar.replace(format="png", size=512)
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(
                name="Account Age",
                value=format_dt(member.created_at, style="R"),
            )
            if value := self.bot.get_cog("Submission").oc_list.get(member.id):
                view = View(
                    Button(
                        label="User Characters",
                        url=f"https://discord.com/channels/719343092963999804/919277769735680050/{value}",
                    )
                )
            else:
                view = View()
            message = await self.log.send(
                embed=embed, file=file, view=view, wait=True
            )
            image = ImageKit(
                base="welcome_TW8HUQOuU.png", weight=1920, height=1080
            )
            image.add_text(
                font="unifont_HcfNyZlJoK.otf",
                text=member.display_name,
                font_size=120,
                color=0xFFFFFF,
                x=180,
                y=480,
            )
            image.add_image(
                image=message.embeds[0].thumbnail.url,
                height=548,
                weight=548,
                x=1308,
                y=65,
            )
            if file := await self.bot.get_file(
                image.url, filename=str(member.id)
            ):
                embed = Embed(
                    color=Color.blurple(),
                    timestamp=utcnow(),
                )
                embed.set_footer(text=guild.name, icon_url=guild.icon.url)
                embed.set_image(url=f"attachment://{file.filename}")

                view.add_item(
                    Button(
                        label="See Information & Rules",
                        url="https://discord.com/channels/719343092963999804/860590339327918100/913555643699458088",
                    )
                )

                with suppress(DiscordException):
                    self.join[member] = await member.send(
                        content=member.mention,
                        embed=embed,
                        file=file,
                        view=view,
                        allowed_mentions=AllowedMentions(users=True),
                    )

    @Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.premium_since == now.premium_since:
            return
        if past.premium_since and not now.premium_since:
            embed = Embed(
                title="Has un-boosted the Server!",
                colour=Color.red(),
                timestamp=utcnow(),
            )
        else:
            embed = Embed(
                title="Has boosted the Server!",
                colour=Color.brand_green(),
                timestamp=utcnow(),
            )
        embed.set_image(url=WHITE_BAR)
        asset = now.display_avatar.replace(format="png", size=4096)
        embed.set_thumbnail(url=asset.url)
        if guild := now.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        await self.log.send(content=now.mention, embed=embed)

    @Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ) -> None:
        """This coroutine triggers upon raw bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        if not (self.log and payload.guild_id):
            return
        if messages := [
            message
            for message in payload.cached_messages
            if message.id not in self.bot.msg_cache
            and message.webhook_id != self.log.id
        ]:
            msg = messages[0]
            fp = StringIO()
            fp.write(dump(list(map(message_line, messages))))
            fp.seek(0)
            file = File(fp=fp, filename="Bulk.yaml")
            embed = Embed(title="Bulk Message Delete", timestamp=utcnow())
            embed.set_footer(text=f"Deleted {len(messages)} messages")
            embed.set_image(url=WHITE_BAR)
            try:
                emoji, name = msg.channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = None, msg.channel.name

            view = View(
                Button(
                    emoji=emoji,
                    label=name.replace("-", " ").title(),
                    url=msg.jump_url,
                )
            )
            await self.log.send(embeds=embed, files=file, view=view)

        self.bot.msg_cache -= payload.message_ids

    async def tenor_fetch(self, image_id: str):
        URL = f"https://g.tenor.com/v1/gifs?ids={image_id}&key={TENOR_API}"
        with suppress(Exception):
            async with self.bot.session.get(url=URL) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["results"][0]
                    media = result["media"][0]
                    title: str = (
                        result["title"] or result["content_description"]
                    )
                    url: str = result["itemurl"]
                    image: str = media["gif"]["url"]
                    return title, url, image

    async def giphy_fetch(self, image_id: str):
        URL = f"https://api.giphy.com/v1/gifs/{image_id}?api_key={GIPHY_API}"
        with suppress(Exception):
            async with self.bot.session.get(url=URL) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["data"]
                    title: str = result["title"]
                    url: str = result["url"]
                    image: str = result["images"]["original"]["url"]
                    return title, url, image

    @Cog.listener()
    async def on_raw_message_delete(
        self,
        payload: RawMessageDeleteEvent,
    ) -> None:
        """Message deleted detection

        Parameters
        ----------
        payload: RawMessageDeleteEvent
            Deleted Message Event
        """
        if not (ctx := payload.cached_message):
            self.bot.msg_cache -= {payload.message_id}
            return

        user: Member = ctx.author

        if (
            not ctx.guild
            or not self.log
            or ctx.webhook_id == self.log.id
            or self.bot.user.id == user.id
            or user.id == self.bot.owner_id
            or user.id in self.bot.owner_ids
        ):
            return

        if ctx.id in self.bot.msg_cache:
            self.bot.msg_cache.remove(ctx.id)
        else:
            embed = Embed(
                title="Message Deleted",
                description=ctx.content,
                color=Color.blurple(),
                timestamp=utcnow(),
            )
            embed.set_image(url=WHITE_BAR)
            text = f"Embeds: {len(ctx.embeds)}, Attachments: {len(ctx.attachments)}"
            embed.set_footer(text=text, icon_url=ctx.guild.icon.url)
            files = []

            embeds: list[Embed] = [embed]

            for item in ctx.embeds:
                if (
                    item.type == "gifv"
                    and isinstance(url := item.url, str)
                    and (items := url.split("-"))
                ):

                    image_id = items[-1]
                    method = None

                    if url.startswith("https://tenor.com/"):
                        method = self.tenor_fetch
                    elif url.startswith("https://giphy.com/"):
                        method = self.giphy_fetch

                    if method and (data := await method(image_id=image_id)):
                        gif_title, gif_url, gif_image = data
                        if embed.title == "GIF Deleted":
                            aux = Embed(color=Color.blurple())
                            embeds.append(aux)
                        else:
                            aux = embed
                            aux.description = embed.Empty

                        aux.title = "GIF Deleted"
                        aux.url = gif_url
                        aux.set_image(url=gif_image)
                        aux.add_field(name="GIF Title", value=gif_title)
                else:
                    embeds.append(item)

            for item in ctx.attachments:
                with suppress(HTTPException):
                    file = await item.to_file(use_cached=True)
                    if item.content_type.startswith("image/"):
                        if embed.image.url == WHITE_BAR:
                            aux = embed
                        else:
                            aux = Embed(color=Color.blurple())
                            embeds.append(aux)
                        aux.set_image(url=f"attachment://{item.filename}")
                    files.append(file)

            try:
                emoji, name = ctx.channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = None, ctx.channel.name

            view = View(
                Button(
                    emoji=emoji,
                    label=name.replace("-", " ").title(),
                    url=ctx.jump_url,
                )
            )

            username: str = user.display_name
            if user.bot and "〕" not in username:
                name = f"Bot〕{username}"
            elif not user.bot:
                embed.title = f"{embed.title} (User: {user.id})"

            await self.log.send(
                embeds=embeds[:10],
                files=files,
                view=view,
                username=username,
                avatar_url=user.display_avatar.url,
            )

    @Cog.listener()
    async def on_command(self, ctx: Context) -> None:
        """This allows me to check when commands are being used.

        Parameters
        ----------
        ctx: Context
            Context
        """
        guild: Optional[Guild] = ctx.guild
        if guild:
            self.bot.logger.info(
                "%s > %s > %s",
                guild.name,
                ctx.author,
                ctx.command.qualified_name,
            )
        else:
            self.bot.logger.info(
                "Private message > %s > %s",
                ctx.author,
                ctx.command.qualified_name,
            )

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError) -> None:
        """Command error handler

        Parameters
        ----------
        ctx: Context
            Context
        error: CommandError
            Error
        """
        error = getattr(error, "original", error)

        if isinstance(error, CommandNotFound):
            return

        if isinstance(
            error,
            (
                CheckFailure,
                UserInputError,
                CommandOnCooldown,
                MaxConcurrencyReached,
                DisabledCommand,
            ),
        ):
            await ctx.send(
                embed=Embed(
                    color=Color.red(),
                    title=f"Error - {ctx.command.qualified_name}",
                    description=str(error),
                )
            )
            return

        if hasattr(ctx.command, "on_error"):
            return

        if (cog := ctx.cog) and cog._get_overridden_method(
            cog.cog_command_error
        ):
            return

        if error_cause := error.__cause__:
            await ctx.send(
                embed=Embed(
                    color=Color.red(),
                    title=f"Unexpected error - {ctx.command.qualified_name}",
                    description=f"```py\n{type(error_cause).__name__}: {error_cause}\n```",
                )
            )

        self.bot.logger.error(
            "Command Error(%s, %s)",
            ctx.command.qualified_name,
            ", ".join(f"{k}={v!r}" for k, v in ctx.kwargs.items()),
            exc_info=error,
        )

    @Cog.listener()
    async def on_ready(self):
        """Loads the program in the scheduler"""
        for item in MAP_ELEMENTS:
            view = RegionView(bot=self.bot, cat_id=item.category)
            self.bot.add_view(view, message_id=item.message)
        await self.member_count()
        self.log = await self.bot.fetch_webhook(943493074162700298)
        w = await self.bot.fetch_webhook(860606374488047616)
        self.info_msg = await w.fetch_message(913555643699458088)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot

    Returns
    -------

    """
    bot.add_cog(Information(bot))
