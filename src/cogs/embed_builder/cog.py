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


from contextlib import asynccontextmanager, suppress
from typing import Union

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    Emoji,
    Guild,
    Member,
    Message,
    PartialEmoji,
    PartialMessage,
    TextChannel,
    Thread,
    User,
    Webhook,
    WebhookMessage,
)
from discord.ext.commands import (
    Cog,
    CommandError,
    MessageConverter,
    PartialMessageConverter,
    group,
    has_guild_permissions,
    is_owner,
)
from discord.ui import Button, View
from discord.utils import MISSING, utcnow

from src.context import Context
from src.structures.bot import CustomBot
from src.structures.converters import AfterDateCall
from src.utils.etc import RAINBOW, WHITE_BAR
from src.utils.functions import embed_handler

__all__ = ("EmbedBuilder", "setup")


class EmbedBuilder(Cog):
    """Cog for embed building based on webhooks"""

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cache: dict[tuple[int, int], WebhookMessage] = {}
        self.blame: dict[WebhookMessage, tuple[int, int]] = {}
        self.loaded: bool = False
        self.converter: MessageConverter = MessageConverter()

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        """Removes messages from the user in the current guild

        Parameters
        ----------
        member: Member
            User who left

        Returns
        -------

        """
        if data := self.cache.pop((member.id, member.guild.id), None):
            self.blame.pop(data, None)

    @Cog.listener()
    async def on_message(self, message: Message):

        if not message.guild or message.author.bot or not message.content:
            return

        try:
            (
                guild_id,
                message_id,
                channel_id,
            ) = PartialMessageConverter._get_id_matches(message.content)
            if guild := self.bot.get_guild(guild_id):
                if not (channel := guild.get_channel_or_thread(channel_id)):
                    channel = await guild.fetch_channel(channel_id)
            elif not (channel := self.bot.get_channel(channel_id)):
                channel = await self.bot.fetch_channel(channel_id)
            reference = await channel.fetch_message(message_id)
            member: Member = message.author
            author: User = reference.author
            embed = Embed(
                colour=member.colour,
                timestamp=reference.created_at,
            )
            if content := reference.content:
                embed.title = "Content"
                embed.description = content

            embed.set_author(
                name=f"Quoting {author}",
                icon_url=author.display_avatar.url,
            )
            embed.set_footer(
                text=f"Requested by {member}",
                icon_url=member.display_avatar.url,
            )
            view = View(Button(label="Jump URL", url=reference.jump_url))
            target: TextChannel = message.channel
            await target.send(embed=embed, view=view)
            for item in reference.embeds:
                files, embed_item = await self.bot.embed_raw(embed=item)
                await target.send(embed=embed_item, files=files)

            if not reference.embeds and reference.attachments:
                embed.title = embed.Empty
                embed.description = embed.Empty
                files = []
                embeds = []
                for item in reference.attachments:
                    if item.content_type.startswith("image/"):
                        aux = embed.copy()
                        file = await item.to_file()
                        aux.set_image(url=f"attachment://{file.filename}")
                        embeds.append(aux)
                        files.append(file)

                await target.send(embed=embeds[:10], file=files[:10])
        except Exception:
            return

    @Cog.listener()
    async def on_message_delete(self, ctx: Message):
        """Checks if a message got deleted in order to remove it from DB

        Parameters
        ----------
        ctx: Message
            Message that got deleted

        Returns
        -------

        """
        if (
            ctx.webhook_id
            and (
                items := [
                    item
                    for item in self.blame
                    if not (ctx.channel == item.channel and ctx.id == item.id)
                ]
            )
            and (data := self.blame.pop(items[0], None))
        ):
            self.cache.pop(data, None)

    def write(self, message: WebhookMessage, author: Member):
        """A method for adding webhook messages to the database

        Parameters
        ----------
        message: Message
            Message to be uploaded
        author: Member
            Author who sent the message
        """
        self.cache[(author.id, author.guild.id)] = message
        self.blame[message] = (author.id, author.guild.id)

    @asynccontextmanager
    async def edit(self, ctx: Context, delete: bool = True):
        """Functions which edits and embed along its files

        Parameters
        ----------
        ctx: Context
            Context
        delete: bool = True
            If this should delete a message

        Returns
        -------

        """
        item_cache = (ctx.author.id, ctx.guild.id)
        try:
            embed = Embed()
            if (message := self.cache.get(item_cache)) and (
                embeds := message.embeds
            ):
                embed = embeds[0]
            yield embed
        finally:
            try:
                if ctx.message.attachments:
                    files, embed = await self.bot.embed_raw(embed)
                    await message.edit(files=files, embed=embed, attachments=[])
                elif message:
                    embed = embed_handler(message, embed)
                    await message.edit(embed=embed)

                if delete:
                    self.bot.msg_cache.add(ctx.message.id)
                    await ctx.message.delete()
            except DiscordException as e:
                self.bot.logger.exception(
                    "exception while editing an embed", exc_info=e
                )
                if item := self.cache.pop(item_cache, None):
                    del self.blame[item]

    @group(name="embed", aliases=["e"], invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed(self, ctx: Context):
        """Shows stored embed's location

        Parameters
        ----------
        ctx: Context
            Message's Context

        Returns
        -------

        """
        embed = Embed(
            title="Embed Builder",
            color=ctx.author.color,
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
        )
        embed.set_footer(
            text=ctx.guild.name,
            icon_url=ctx.guild.icon,
        )
        if data := self.cache.get((ctx.author.id, ctx.guild.id)):
            try:
                emoji, name = data.channel.name.split("〛")
                emoji = emoji[0]
            except Exception:
                name = data.channel.name
                emoji = None

            view = View(Button(label=name, emoji=emoji, url=data.jump_url))
            await ctx.reply(embed=embed, view=view)
        else:
            await ctx.reply(embed=embed)

    @embed.command(name="new", aliases=["create"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_new(
        self, ctx: Context, title: str = "", *, description: str = ""
    ):
        """Allows to create discord embeds

        Parameters
        ----------
        ctx: Context
            Context
        title: str = ""
            Title of the embed. Defaults to None
        description: str = ""
            Description of the embed. Defaults to None

        Returns
        -------

        """
        embed = Embed(title=title, description=description)
        webhook = await self.bot.webhook(
            ctx.channel.id, reason="Created by Embed Builder"
        )
        author: Member = ctx.author

        if not isinstance(thread := ctx.channel, Thread):
            thread = MISSING

        if attachment := ctx.message.attachments:
            file = await attachment[0].to_file()
            embed.set_image(url=f"attachment://{file.filename}")
            message: WebhookMessage = await webhook.send(
                embed=embed,
                wait=True,
                username=author.display_name,
                avatar_url=author.display_avatar.url,
                file=file,
                thread=thread,
            )
        else:
            message: WebhookMessage = await webhook.send(
                embed=embed,
                wait=True,
                username=author.display_name,
                avatar_url=author.display_avatar.url,
                thread=thread,
            )
        message.channel = ctx.channel
        self.write(message, author)
        await ctx.message.delete()

    @embed.command(name="set")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_set(self, ctx: Context, *, message: Message = None):
        """Allows to set a new editable Embed out of an existing message

        Parameters
        ----------
        ctx: Context
            Context
        message: Message
            Provided Message

        Returns
        -------

        """
        guild: Guild = ctx.guild
        if reference := ctx.message.reference:
            if isinstance(reference.resolved, Message):
                message = reference.resolved
            else:
                channel: Union[
                    Thread, TextChannel
                ] = guild.get_channel_or_thread(reference.channel_id)
                message = await channel.fetch_message(reference.message_id)

        if isinstance(message, Message):
            if webhook_id := message.webhook_id:
                try:
                    webhook = await self.bot.fetch_webhook(webhook_id)
                    if isinstance(channel := message.channel, Thread):
                        thread_id = channel.id
                    else:
                        thread_id = None
                    message: WebhookMessage = await webhook.fetch_message(
                        message.id, thread_id=thread_id
                    )
                    message.channel = channel
                    self.write(message, ctx.author)
                    await ctx.reply("Message has been set", delete_after=3)
                except DiscordException:
                    await ctx.reply("Message can't be set", delete_after=3)
            else:
                await ctx.reply(
                    "I can't use that message for embedding purposes",
                    delete_after=3,
                )
        else:
            await ctx.reply("No message was found.", delete_after=3)

    @embed.group(name="post", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_post(self, ctx: Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            webhook: Webhook = await ctx.bot.webhook(ctx.channel)

            if not isinstance(thread := ctx.channel, Thread):
                thread = MISSING

            message = await webhook.send(
                embed=embed,
                username=ctx.author.display_name,
                avatar_url=ctx.author.display_avatar.url,
                thread=thread,
                wait=True,
            )
            self.write(message, ctx.author)

    @embed_post.command(name="raw")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_post_raw(self, ctx: Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            files, embed_aux = await self.bot.embed_raw(embed)
            webhook: Webhook = await ctx.bot.webhook(ctx.channel)

            if not isinstance(thread := ctx.channel, Thread):
                thread = MISSING

            message = await webhook.send(
                files=files,
                embed=embed_aux,
                username=ctx.author.display_name,
                avatar_url=ctx.author.display_avatar.url,
                thread=thread,
                wait=True,
            )
            self.write(message, ctx.author)

    @embed.command(name="announce")
    @is_owner()
    async def embed_announce(self, ctx: Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            webhook: Webhook = await ctx.bot.webhook(ctx.channel)
            message = await webhook.send(
                content="@everyone",
                embed=embed,
                allowed_mentions=AllowedMentions(everyone=True),
                wait=True,
            )
            self.write(message, ctx.author)

    @embed.command(name="unset")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_unset(self, ctx: Context):
        """Allows to remove the stored embed

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        if message := self.cache.pop((ctx.author.id, ctx.guild.id), None):
            del self.blame[message]
            view = View(Button(label="Jump URL", url=message.jump_url))
            await ctx.reply("Removed stored embed.", view=view)
        else:
            await ctx.reply("No stored embed to remove.")

    @embed.command(name="title", aliases=["t"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_title(self, ctx: Context, *, title: str = ""):
        """Allows to edit the embed's title

        Parameters
        ----------
        ctx: Context
            Context
        title: str = ""
            Title of the embed. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.title = title

    @embed.command(name="description", aliases=["desc", "d", "text", "content"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_description(self, ctx: Context, *, description: str = ""):
        """Allows to edit the embed's description

        Parameters
        ----------
        ctx: Context
            Context
        description: str = ""
            Description of the embed. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.description = description

    @embed.command(name="color", aliases=["colour"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_color(self, ctx: Context, *, color: Color = None):
        """Allows to edit the embed's color

        Parameters
        ----------
        ctx: Context
            Context
        color: Color = None
            Color of the embed. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.colour = color or Color.default()

    @embed.group(
        name="timestamp", aliases=["date", "time"], invoke_without_command=True
    )
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_timestamp(
        self, ctx: Context, *, date: AfterDateCall = None
    ):
        """Allows to edit the embed's timestamp

        Parameters
        ----------
        ctx: Context
            Context
        date: datetime = None
            A specified Date. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.timestamp = date or embed.Empty

    @embed_timestamp.command(name="now")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_timestamp_now(self, ctx: Context):
        """Allows to edit the embed's timestamp

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.timestamp = utcnow()

    @embed.command(name="url", aliases=["link"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_url(self, ctx: Context, *, url: str = ""):
        """Allows to edit the embed's url

        Parameters
        ----------
        ctx: Context
            Context
        url: str = ""
            Url of the embed. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.url = url

    @embed.group(name="author", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_author(self, ctx: Context, *, author: str = ""):
        """Allows to add author to an embed

        Parameters
        ----------
        ctx: Context
            Context
        author: str = ""
            Embed's Author name. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if author:
                embed.set_author(
                    name=author,
                    url=embed.author.url,
                    icon_url=embed.author.icon_url,
                )
            else:
                embed.remove_author()

    @embed_author.command(name="user")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_author_user(
        self, ctx: Context, *, author: Union[Member, User] = None
    ):
        """Allows to set an user as author of an embed

        Parameters
        ----------
        ctx: Context
            Context
        author: User
            Discord User

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            author = author or ctx.author  # type: Union[Member, User]
            embed.set_author(
                name=author.display_name,
                url=embed.author.url,
                icon_url=author.display_avatar.url,
            )

    @embed_author.command(name="guild", aliases=["server"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_author_guild(self, ctx: Context, *, guild: Guild = None):
        """Allows to set the specified guild as Author of the embed

        Parameters
        ----------
        ctx: Context
            Context
        guild: Guild
            Guild. Defaults to Current

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            guild = guild or ctx.guild
            embed.set_author(
                name=guild.name,
                url=embed.author.url,
                icon_url=guild.icon.url,
            )

    @embed_author.command(name="url", aliases=["link"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_author_url(self, ctx: Context, *, url: str = ""):
        """Allows to set URL to an embed's author

        Parameters
        ----------
        ctx: Context
            Context
        url: str = ""
            URL string

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if author := embed.author:
                embed.set_author(
                    name=author.name,
                    url=url or author.url,
                    icon_url=author.icon_url,
                )

    @embed_author.command(name="icon")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_author_icon(
        self, ctx: Context, *, icon: Union[Emoji, PartialEmoji, str] = None
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context (Possible with Attachment or message reference with an Attachment)
        icon: Union[Emoji, PartialEmoji, str] = None
            Emoji or URL. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if author := embed.author:
                if attachments := ctx.message.attachments:
                    embed.set_author(
                        name=author.name,
                        url=author.url,
                        icon_url=attachments[-1].proxy_url,
                    )
                elif isinstance(icon, (Emoji, PartialEmoji)):
                    embed.set_author(
                        name=author.name, url=author.url, icon_url=icon.url
                    )
                elif icon:
                    embed.set_author(
                        name=author.name, url=author.url, icon_url=icon
                    )
                else:
                    embed.set_author(name=author.name, url=author.url)

    @embed.group(name="footer", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_footer(self, ctx: Context, *, footer: str = ""):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context
        footer: str = ""
            Footer's text. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if footer:
                embed.set_footer(text=footer, icon_url=embed.footer.icon_url)
            else:
                embed.remove_footer()

    @embed_footer.command(name="user")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_footer_user(
        self, ctx: Context, *, user: Union[Member, User] = None
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context
        user: User
            User as Footer. Defaults to Self

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author
            embed.set_footer(
                text=user.display_name, icon_url=user.display_avatar.url
            )

    @embed_footer.command(name="guild", aliases=["server"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_footer_guild(self, ctx: Context, *, guild: Guild = None):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context
        guild: Guild
            Guild as Footer. Defaults to Self

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            guild = guild or ctx.guild
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)

    @embed_footer.command(name="icon")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_footer_icon(
        self, ctx: Context, *, icon: Union[Emoji, PartialEmoji, str] = None
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context
        icon: Union[Emoji, PartialEmoji, str] = None
            Footer Icon URL. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if footer := embed.footer:
                if attachments := ctx.message.attachments:
                    embed.set_footer(
                        text=footer.text,
                        icon_url=attachments[-1].proxy_url,
                    )
                elif isinstance(icon, (Emoji, PartialEmoji)):
                    embed.set_footer(
                        text=footer.text,
                        icon_url=icon.url,
                    )
                elif icon:
                    embed.set_footer(
                        text=footer.text,
                        icon_url=icon,
                    )
                else:
                    embed.set_footer(
                        text=footer.text,
                    )

        async with self.edit(ctx) as embed:
            if footer := embed.footer:
                icon = icon or footer.icon_url  # type: str
                if attachments := ctx.message.attachments:
                    file = await attachments[-1].to_file()
                    setattr(embed, "file", file)
                    embed.set_footer(
                        text=footer.text,
                        icon_url=f"attachment://{file.filename}",
                    )
                elif icon:
                    embed.set_footer(
                        text=footer.text,
                        icon_url=icon,
                    )
                else:
                    embed.set_footer(
                        text=footer.text,
                    )

    @embed.group(name="thumbnail", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_thumbnail(
        self, ctx: Context, *, thumbnail: Union[Emoji, PartialEmoji, str] = None
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: Context
            Context
        thumbnail: Union[Emoji, PartialEmoji, str] = None
            Embed's thumbnail. Defaults to None

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if attachments := ctx.message.attachments:
                embed.set_thumbnail(url=attachments[-1].proxy_url)
            elif isinstance(thumbnail, Emoji):
                embed.set_thumbnail(url=thumbnail.url)
            elif isinstance(thumbnail, PartialEmoji):
                embed.set_thumbnail(url=thumbnail.url)
            elif thumbnail:
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.remove_thumbnail()

    @embed_thumbnail.group(name="user", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_thumbnail_user(
        self, ctx: Context, *, user: Union[Member, User] = None
    ):
        """Allows to edit an embed's thumbnail by an user

        Parameters
        ----------
        ctx: Context
            Context
        user: User
            User for embed. Defaults to self
        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author  # type: User
            embed.set_thumbnail(url=user.display_avatar.url)

    @embed_thumbnail.group(
        name="guild", aliases=["server"], invoke_without_command=True
    )
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_thumbnail_guild(self, ctx: Context, *, guild: Guild = None):
        """Allows to edit an embed's thumbnail by an user

        Parameters
        ----------
        ctx: Context
            Context
        guild: Guild
            Guild for embed. Defaults to self
        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_thumbnail(url=guild.icon.url)

    @embed.group(name="image", invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_image(
        self, ctx: Context, *, image: Union[Emoji, PartialEmoji, str] = None
    ):
        """Allows to edit an embed's image

        Parameters
        ----------
        ctx: Context
            Context (w/ attachment or reference to one)
        image: Union[Emoji, PartialEmoji, str] = None
            URL. Defaults to None
        Returns
        -------

        """
        method = self.edit(ctx)
        async with method as embed:
            if attachments := ctx.message.attachments:
                embed.set_image(url=attachments[-1].proxy_url)
            elif isinstance(image, (Emoji, PartialEmoji)):
                embed.set_image(url=image.url)
            elif image:
                embed.set_image(url=image)
            else:
                embed.set_image(url=embed.Empty)

    @embed_image.command(name="user")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_image_user(
        self, ctx: Context, *, user: Union[Member, User] = None
    ):
        """Allows to edit an embed's image based on an user

        Parameters
        ----------
        ctx: Context
            Context
        user: User
            User to take as reference. Defaults to self

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author  # type: User
            embed.set_image(url=user.display_avatar.url)

    @embed_image.command(name="guild", aliases=["server"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_image_guild(self, ctx: Context, *, guild: Guild = None):
        """Allows to edit an embed's image based on an user

        Parameters
        ----------
        ctx: Context
            Context
        guild: Guild = None
            Guild to take as reference. Defaults to current

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_image(url=guild.icon.url)

    @embed_image.command(name="rainbow")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_image_rainbow(self, ctx: Context):
        """Allows to add a rainbow line as placeholder in embed images

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.set_image(url=RAINBOW)

    @embed_image.command(name="whitebar")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def embed_image_whitebar(self, ctx: Context):
        """Allows to add a whitebar line as placeholder in embed images

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.set_image(url=WHITE_BAR)

    @group(name="fields", aliases=["field", "f"], invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields(self, ctx: Context):
        """Outputs the fields that the current embed has

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if content := "\n".join(
                f"• {i}){f.name} > {f.value}"
                for i, f in enumerate(embed.fields)
            ):
                await ctx.send(f"```yaml\n{content}\n```")

    @fields.command(name="add", aliases=["a"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_add(self, ctx: Context, name: str, *, value: str):
        """Allows to add a field to an embed, given some parameters

        Parameters
        ----------
        ctx: Context
            Context
        name: str
            Field's name
        value: str
            Field's value

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.add_field(name=name, value=value)

    @fields.command(name="name", aliases=["n"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_name(self, ctx: Context, before: str, *, after: str):
        """Allows to rename fields with same names

        Parameters
        ----------
        ctx: Context
            Context
        before: str
            Current Name
        after: str
            Name to be changed as

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            for index, field in enumerate(embed.fields):
                if field.name == before:
                    embed.set_field_at(
                        index,
                        name=after,
                        value=field.value,
                        inline=field.inline,
                    )

    @fields.command(name="value")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_value(self, ctx: Context, name: str, *, value: str):
        """Allows to edit values of fields with same name

        Parameters
        ----------
        ctx: Context
            Context
        name: str
            Field's Name
        value: str
            Field's Value

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            for index, field in enumerate(embed.fields):
                if field.name == name:
                    embed.set_field_at(
                        index,
                        name=field.name,
                        value=value,
                        inline=field.inline,
                    )

    @fields.command(name="inline")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_inline(self, ctx: Context, *, name: str):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: Context
            Context
        name: str
            Field's Name

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            for index, field in enumerate(embed.fields):
                if field.name == name:
                    embed.set_field_at(
                        index,
                        name=field.name,
                        value=field.value,
                        inline=not field.inline,
                    )

    @fields.group(name="delete", invoke_without_command=True, aliases=["d"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_delete(self, ctx: Context, *, name: str):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: Context
            Context
        name: str
            Field's name

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            setattr(
                embed,
                "_fields",
                [
                    dict(
                        name=field.name, value=field.value, inline=field.inline
                    )
                    for field in embed.fields
                    if field.name != name
                ],
            )

    @fields_delete.command(name="all")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_delete_all(self, ctx: Context):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.clear_fields()

    @fields.group(name="index", aliases=["i"], invoke_without_command=True)
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index(self, ctx: Context):
        """Outputs the amount of fields that the current embed has

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            if fields := embed.fields:
                await ctx.reply(f"There's {len(fields)} fields in the embed")
            else:
                await ctx.reply("There's no fields in the embed")

    @fields_index.command(name="add", aliases=["a"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index_add(
        self, ctx: Context, index: int, name: str, *, value: str
    ):
        """Allows to insert a field to an embed based on its index

        Parameters
        ----------
        ctx: Context
            Context
        index: int
            Integer Index
        name: str
            Field's Name
        value: str
            Field's Value

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.insert_field_at(index, name=name, value=value)

    @fields_index.command(name="name", aliases=["n"])
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index_name(self, ctx: Context, index: int, *, name: str):
        """Allows to rename a field in an embed based on its index

        Parameters
        ----------
        ctx: Context
            Context
        index: int
            Integer Index
        name: str
            Field's new name

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            field = embed.fields[index]
            embed.set_field_at(
                index, name=name, value=field.value, inline=field.inline
            )

    @fields_index.command(name="value")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index_value(self, ctx: Context, index: int, *, value: str):
        """Allows to edit a field's value in an embed based on its index

        Parameters
        ----------
        ctx: Context
            Context
        index: int
            Integer Index
        value: str
            Field's new value

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            aux = embed.fields[index]
            embed.set_field_at(
                index, name=aux.name, value=value, inline=aux.inline
            )

    @fields_index.command(name="inline")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index_inline(self, ctx: Context, *, index: int):
        """Allows to enable/disable inline of embed fields based on its index

        Parameters
        ----------
        ctx: Context
            Context
        index: int
            Integer Index

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            field = embed.fields[index]
            embed.set_field_at(
                index,
                name=field.name,
                value=field.value,
                inline=not field.inline,
            )

    @fields_index.command(name="delete")
    @has_guild_permissions(
        manage_messages=True, send_messages=True, embed_links=True
    )
    async def fields_index_delete(self, ctx: Context, *, index: int):
        """Allows to delete embed fields based on their index

        Parameters
        ----------
        ctx: Context
            Context
        index: int
            Integer Index

        Returns
        -------

        """
        async with self.edit(ctx) as embed:
            embed.remove_field(index)

    @Cog.listener()
    async def on_cog_command_error(self, ctx: Context, error: CommandError):
        """Error handler for this class.

        Parameters
        ----------
        ctx: Context
            Context
        error: CommandError
            Error

        Returns
        -------

        """
        if isinstance(error, RuntimeError):
            await ctx.reply("No embed of yours was found in database.")
        elif isinstance(error, IndexError):
            await ctx.reply("The embed does not have such index")
        else:
            await ctx.reply(f"{type(error)}: {error}")


def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot

    Returns
    -------

    """
    bot.add_cog(EmbedBuilder(bot))
