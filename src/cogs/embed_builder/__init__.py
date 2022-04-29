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


from contextlib import asynccontextmanager
from datetime import datetime
from re import compile
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DeletedReferencedMessage,
    DiscordException,
    Embed,
    Emoji,
    Guild,
    Member,
    Message,
    PartialEmoji,
    TextChannel,
    Thread,
    User,
    Webhook,
    WebhookMessage,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, utcnow

from src.cogs.information import Information
from src.structures.bot import CustomBot
from src.structures.converters import AfterDateCall
from src.utils.etc import RAINBOW, SETTING_EMOJI, WHITE_BAR
from src.utils.functions import discord_url_msg, embed_handler

PLAYER_FINDER = compile(r"\|raw\|(.*)'s rating: \d+ &rarr; <strong>\d+</strong><br />\((.*)\)")
POKEMON_FINDER = compile(r"\|poke\|p(\d)\|(.*)\|")
RULE_FINDER = compile(r"\|rule\|(.*)")
GAMETYPE_FINDER = compile(r"\|gametype\|(.*)")
TIER_FINDER = compile(r"\|tier\|(.*)")


__all__ = ("EmbedBuilder", "setup")


class EmbedBuilder(commands.Cog):
    """Cog for embed building based on webhooks"""

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.cache: dict[tuple[int, int], WebhookMessage | Message] = {}
        self.blame: dict[WebhookMessage, tuple[int, int]] = {}
        self.loaded: bool = False
        self.converter = commands.MessageConverter()

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        """Removes messages from the user in the current guild

        Parameters
        ----------
        member: Member
            User who left
        """
        if data := self.cache.pop((member.id, member.guild.id), None):
            self.blame.pop(data, None)

    async def webhook_send(self, message: Message, **kwargs):
        webhook = await self.bot.webhook(message.channel)
        if not isinstance(thread := message.channel, Thread):
            thread = MISSING

        await webhook.send(
            allowed_mentions=AllowedMentions.none(),
            thread=thread,
            **kwargs,
        )
        await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message: Message):

        if not message.guild or message.author.bot or not message.content:
            return

        if data := discord_url_msg(message):
            try:
                guild_id, message_id, channel_id = data
                if guild := self.bot.get_guild(guild_id):
                    if not (channel := guild.get_channel_or_thread(channel_id)):
                        channel = await guild.fetch_channel(channel_id)
                elif not (channel := self.bot.get_channel(channel_id)):
                    channel = await self.bot.fetch_channel(channel_id)

                reference = await channel.fetch_message(message_id)

                author: User = reference.author
                name = author.display_name.removeprefix("URL〕")

                view = View()
                view.add_item(
                    Button(
                        label=f"URL Requested by {message.author.display_name}",
                        url=reference.jump_url,
                        emoji=SETTING_EMOJI,
                    )
                )

                cog: Information = self.bot.get_cog("Information")
                kwargs = await cog.embed_info(reference)
                kwargs["view"] = view
                kwargs["username"] = f"URL〕{name}"
                await self.webhook_send(message, **kwargs)
            except DiscordException:
                pass
        elif message.content.startswith("https://replay.pokemonshowdown.com/"):
            content = message.content.split(" ")[0]
            async with self.bot.session.get(url=f"{content}.json") as session:
                if session.status == 200:
                    item: dict[str, str] = await session.json()
                    log = item["log"]
                    (p1, score1), (p2, score2) = PLAYER_FINDER.findall(log)
                    p1 = f"{p1} ({score1})"
                    p2 = f"{p2} ({score2})"
                    items: dict[str, list[str]] = {}
                    for index, name in POKEMON_FINDER.findall(log):
                        name = f"• {name}"
                        if index == "1":
                            items.setdefault(p1, [])
                            items[p1].append(name)
                        else:
                            items.setdefault(p2, [])
                            items[p2].append(name)

                    gametype = GAMETYPE_FINDER.search(log).group(1).title()
                    tier = TIER_FINDER.search(log).group(1).title()

                    author = message.author

                    embed = Embed(
                        title=f"{tier} - {gametype}",
                        description="\n".join(f"• {i}" for i in RULE_FINDER.findall(log)),
                        color=author.color,
                        timestamp=datetime.fromtimestamp(item["uploadtime"]),
                    )

                    for key, value in items.items():
                        embed.add_field(name=key, value="\n".join(value))

                    author = message.author
                    view = View()
                    view.add_item(
                        Button(
                            label="Watch Replay",
                            url=content,
                            emoji="\N{VIDEO CAMERA}",
                        )
                    )

                    await self.webhook_send(
                        message,
                        embed=embed,
                        username=f"URL〕{author.display_name}",
                        avatar_url=author.display_avatar.url,
                        view=view,
                    )

    @commands.Cog.listener()
    async def on_message_delete(self, ctx: Message):
        """Checks if a message got deleted in order to remove it from DB

        Parameters
        ----------
        ctx: Message
            Message that got deleted
        """
        if (
            ctx.webhook_id
            and (items := [item for item in self.blame if not (ctx.channel == item.channel and ctx.id == item.id)])
            and (data := self.blame.pop(items[0], None))
        ):
            self.cache.pop(data, None)

    def write(self, message: WebhookMessage | Message, author: Member):
        """A method for adding webhook messages to the database

        Parameters
        ----------
        message: Message
            Message to be uploaded
        author: Member
            Author who sent the message
        """
        key = author.id, author.guild.id
        self.cache[key] = message
        self.blame[message] = key

    @asynccontextmanager
    async def edit(self, ctx: commands.Context, editing_attachments: bool = False):
        """Functions which edits and embed along its files

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        editing_attachments: bool
            if raw extracting
        """
        item_cache = (ctx.author.id, ctx.guild.id)
        message: Optional[Message | WebhookMessage] = None
        if (ref := ctx.message.reference) and isinstance(msg := ref.resolved, Message):
            if msg.author == self.bot.user:
                self.write(msg, ctx.author)
            elif msg.webhook_id:
                w = await self.bot.webhook(ctx.channel)
                if w.id == msg.webhook_id:
                    self.write(msg, ctx.author)

        message = self.cache.get(item_cache)
        try:
            embed = Embed()
            if message and (embeds := message.embeds):
                embed = embed_handler(message, embeds[0])
            yield embed
        finally:
            if message:
                kwargs = dict(embed=embed)
                if editing_attachments:
                    kwargs["files"], kwargs["embed"] = await self.bot.embed_raw(embed)
                try:
                    if message.author == self.bot.user or isinstance(message, WebhookMessage):
                        await message.edit(**kwargs)
                    elif w := await self.bot.webhook(ctx.channel):
                        if not isinstance(thread := ctx.channel, Thread):
                            thread = MISSING
                        message = await w.edit_message(message.id, thread=thread, **kwargs)
                        self.write(message, ctx.author)
                except DiscordException as e:
                    if item := self.cache.pop(item_cache, None):
                        del self.blame[item]
                    await ctx.reply(str(e), delete_after=3)
            self.bot.msg_cache_add(ctx.message)
            await ctx.message.delete(delay=0)

    @commands.group(
        name="embed",
        aliases=["e"],
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed(self, ctx: commands.Context):
        """Shows stored embed's location

        Parameters
        ----------
        ctx: commands.Context
            Message's commands.Context
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

            view = View()
            view.add_item(Button(label=name, emoji=emoji, url=data.jump_url))
            await ctx.reply(embed=embed, view=view)
        else:
            await ctx.reply(embed=embed)

    @embed.command(
        name="new",
        aliases=["create"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_new(
        self,
        ctx: commands.Context,
        title: str = "",
        *,
        description: str = "",
    ):
        """Allows to create discord embeds

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        title: str = ""
            Title of the embed. Defaults to None
        description: str = ""
            Description of the embed. Defaults to None
        """
        embed = Embed(title=title, description=description)
        webhook = await self.bot.webhook(ctx.channel, reason="Created by Embed Builder")
        author: Member = ctx.author

        if not isinstance(thread := ctx.channel, Thread):
            thread = MISSING

        attachments = ctx.message.attachments
        if len(images := [x for x in attachments if x.content_type.startswith("image/")]) == 1:
            embed.set_image(url=f"attachment://{images[0].filename}")

        message: WebhookMessage = await webhook.send(
            embed=embed,
            wait=True,
            username=author.display_name,
            avatar_url=author.display_avatar.url,
            files=[await x.to_file() for x in attachments],
            thread=thread,
        )
        message.channel = ctx.channel
        self.write(message, author)
        await ctx.message.delete()

    @embed.command(name="set")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_set(
        self,
        ctx: commands.Context,
        *,
        message: Message = None,
    ):
        """Allows to set a new editable Embed out of an existing message

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        message: Message
            Provided Message
        """
        guild: Guild = ctx.guild
        channel: TextChannel = ctx.channel
        if reference := ctx.message.reference:
            resolved = reference.resolved
            if isinstance(resolved, DeletedReferencedMessage):
                message = None
            elif isinstance(resolved, Message):
                message = resolved
            elif channel := guild.get_channel_or_thread(reference.channel_id):
                message = await channel.fetch_message(reference.message_id)
            else:
                message = None

        if isinstance(message, Message):
            if message.author == self.bot.user:
                self.write(message, ctx.author)
                await ctx.reply("Message has been set", delete_after=2)
            elif webhook_id := message.webhook_id:
                webhook = await self.bot.webhook(message.channel)
                if webhook_id != webhook.id:
                    await ctx.reply("Message can't be set", delete_after=2)
                else:
                    if not isinstance(thread := message.channel, Thread):
                        thread = MISSING
                    message: WebhookMessage = await webhook.fetch_message(message.id, thread=thread)
                    self.write(message, ctx.author)
                    await ctx.reply("Message has been set", delete_after=2)
            else:
                await ctx.reply(
                    "I can't use that message for embedding purposes",
                    delete_after=2,
                )
            await ctx.message.delete(delay=0)
        else:
            await ctx.reply("No message was found.", delete_after=2)

    @embed.group(
        name="post",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_post(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
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
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_post_raw(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
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

    @embed.command(name="unset")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_unset(self, ctx: commands.Context):
        """Allows to remove the stored embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        if message := self.cache.pop((ctx.author.id, ctx.guild.id), None):
            del self.blame[message]
            view = View()
            view.add_item(Button(label="Jump URL", url=message.jump_url))
            await ctx.reply("Removed stored embed.", view=view)
        else:
            await ctx.reply("No stored embed to remove.")

    @embed.command(
        name="title",
        aliases=["t"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_title(
        self,
        ctx: commands.Context,
        *,
        title: str = "",
    ):
        """Allows to edit the embed's title

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        title: str = ""
            Title of the embed. Defaults to None
        """
        async with self.edit(ctx) as embed:
            embed.title = title

    @embed.command(
        name="description",
        aliases=["desc", "d", "text", "content"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_description(
        self,
        ctx: commands.Context,
        *,
        description: str = "",
    ):
        """Allows to edit the embed's description

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        description: str = ""
            Description of the embed. Defaults to None
        """
        async with self.edit(ctx) as embed:
            embed.description = description

    @embed.command(
        name="color",
        aliases=["colour"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_color(
        self,
        ctx: commands.Context,
        *,
        color: Color = None,
    ):
        """Allows to edit the embed's color

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        color: Color = None
            Color of the embed. Defaults to None
        """
        async with self.edit(ctx) as embed:
            embed.colour = color or Color.default()

    @embed.group(
        name="timestamp",
        aliases=["date", "time"],
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_timestamp(
        self,
        ctx: commands.Context,
        *,
        date: AfterDateCall = None,
    ):
        """Allows to edit the embed's timestamp

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        date: datetime = None
            A specified Date. Defaults to None
        """
        async with self.edit(ctx) as embed:
            embed.timestamp = date

    @embed_timestamp.command(name="now")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_timestamp_now(self, ctx: commands.Context):
        """Allows to edit the embed's timestamp

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.timestamp = utcnow()

    @embed.command(
        name="url",
        aliases=["link"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_url(
        self,
        ctx: commands.Context,
        *,
        url: str = "",
    ):
        """Allows to edit the embed's url

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        url: str = ""
            Url of the embed. Defaults to None
        """
        async with self.edit(ctx) as embed:
            embed.url = url

    @embed.group(
        name="author",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_author(
        self,
        ctx: commands.Context,
        *,
        author: str = "",
    ):
        """Allows to add author to an embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        author: str = ""
            Embed's Author name. Defaults to None
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
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_author_user(
        self,
        ctx: commands.Context,
        *,
        author: Member | User = None,
    ):
        """Allows to set an user as author of an embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        author: User
            Discord User
        """
        async with self.edit(ctx) as embed:
            author = author or ctx.author  # type: Member | User
            embed.set_author(
                name=author.display_name,
                url=embed.author.url,
                icon_url=author.display_avatar.url,
            )

    @embed_author.command(
        name="guild",
        aliases=["server"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_author_guild(
        self,
        ctx: commands.Context,
        *,
        guild: Guild = None,
    ):
        """Allows to set the specified guild as Author of the embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild
            Guild. Defaults to Current
        """
        async with self.edit(ctx) as embed:
            guild = guild or ctx.guild
            embed.set_author(
                name=guild.name,
                url=embed.author.url,
                icon_url=guild.icon.url,
            )

    @embed_author.command(
        name="url",
        aliases=["link"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_author_url(
        self,
        ctx: commands.Context,
        *,
        url: str = "",
    ):
        """Allows to set URL to an embed's author

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        url: str = ""
            URL string
        """
        async with self.edit(ctx) as embed:
            if author := embed.author:
                embed.set_author(
                    name=author.name,
                    url=url or author.url,
                    icon_url=author.icon_url,
                )

    @embed_author.command(name="icon")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_author_icon(
        self,
        ctx: commands.Context,
        *,
        icon: Optional[Emoji | PartialEmoji | str] = None,
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context (Possible with Attachment or message reference with an Attachment)
        icon: Optional[Emoji | PartialEmoji | str] = None
            Emoji or URL. Defaults to None
        """
        attachments = ctx.message.attachments
        async with self.edit(ctx, editing_attachments=attachments) as embed:
            if author := embed.author:
                if attachments:
                    embed.set_author(
                        name=author.name,
                        url=author.url,
                        icon_url=attachments[-1].proxy_url,
                    )
                elif isinstance(icon, (Emoji, PartialEmoji)):
                    embed.set_author(
                        name=author.name,
                        url=author.url,
                        icon_url=icon.url,
                    )
                elif icon:
                    embed.set_author(
                        name=author.name,
                        url=author.url,
                        icon_url=icon,
                    )
                else:
                    embed.set_author(
                        name=author.name,
                        url=author.url,
                    )

    @embed.group(
        name="footer",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_footer(
        self,
        ctx: commands.Context,
        *,
        footer: str = "",
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        footer: str = ""
            Footer's text. Defaults to None
        """
        async with self.edit(ctx) as embed:
            if footer:
                embed.set_footer(text=footer, icon_url=embed.footer.icon_url)
            else:
                embed.remove_footer()

    @embed_footer.command(name="user")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_footer_user(
        self,
        ctx: commands.Context,
        *,
        user: Member | User = None,
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        user: User
            User as Footer. Defaults to Self
        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author
            embed.set_footer(
                text=user.display_name,
                icon_url=user.display_avatar.url,
            )

    @embed_footer.command(
        name="guild",
        aliases=["server"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_footer_guild(
        self,
        ctx: commands.Context,
        *,
        guild: Guild = None,
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild
            Guild as Footer. Defaults to Self
        """
        async with self.edit(ctx) as embed:
            guild = guild or ctx.guild
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)

    @embed_footer.command(name="icon")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_footer_icon(
        self,
        ctx: commands.Context,
        *,
        icon: Optional[Emoji | PartialEmoji | str] = None,
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        icon: Optional[Emoji | PartialEmoji | str] = None
            Footer Icon URL. Defaults to None
        """
        attachments = ctx.message.attachments
        async with self.edit(ctx, editing_attachments=attachments) as embed:
            if footer := embed.footer:
                if attachments:
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

    @embed.group(
        name="thumbnail",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_thumbnail(
        self,
        ctx: commands.Context,
        *,
        thumbnail: Optional[Emoji | PartialEmoji | str] = None,
    ):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        thumbnail: Optional[Emoji | PartialEmoji | str] = None
            Embed's thumbnail. Defaults to None
        """
        attachments = ctx.message.attachments
        async with self.edit(ctx, editing_attachments=attachments) as embed:
            if attachments:
                embed.set_thumbnail(url=attachments[-1].proxy_url)
            elif isinstance(thumbnail, (Emoji, PartialEmoji)):
                embed.set_thumbnail(url=thumbnail.url)
            elif thumbnail:
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.set_thumbnail(url=None)

    @embed_thumbnail.group(name="user", invoke_without_command=True)
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_thumbnail_user(
        self,
        ctx: commands.Context,
        *,
        user: Member | User = None,
    ):
        """Allows to edit an embed's thumbnail by an user

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        user: User
            User for embed. Defaults to self
        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author  # type: User
            embed.set_thumbnail(url=user.display_avatar.url)

    @embed_thumbnail.group(
        name="guild",
        aliases=["server"],
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_thumbnail_guild(
        self,
        ctx: commands.Context,
        *,
        guild: Guild = None,
    ):
        """Allows to edit an embed's thumbnail by an user

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild
            Guild for embed. Defaults to self
        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_thumbnail(url=guild.icon.url)

    @embed.group(name="image", invoke_without_command=True)
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_image(
        self,
        ctx: commands.Context,
        *,
        image: Optional[Emoji | PartialEmoji | str] = None,
    ):
        """Allows to edit an embed's image

        Parameters
        ----------
        ctx: commands.Context
            commands.Context (w/ attachment or reference to one)
        image: Optional[Emoji | PartialEmoji | str] = None
            URL. Defaults to None
        """
        attachments = ctx.message.attachments
        async with self.edit(ctx, editing_attachments=attachments) as embed:
            if attachments:
                embed.set_image(url=attachments[-1].proxy_url)
            elif isinstance(image, (Emoji, PartialEmoji)):
                embed.set_image(url=image.url)
            elif image:
                embed.set_image(url=image)
            else:
                embed.set_image(url=None)

    @embed_image.command(name="user")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_image_user(
        self,
        ctx: commands.Context,
        *,
        user: Member | User = None,
    ):
        """Allows to edit an embed's image based on an user

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        user: User
            User to take as reference. Defaults to self
        """
        async with self.edit(ctx) as embed:
            user = user or ctx.author  # type: User
            embed.set_image(url=user.display_avatar.url)

    @embed_image.command(
        name="guild",
        aliases=["server"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_image_guild(
        self,
        ctx: commands.Context,
        *,
        guild: Guild = None,
    ):
        """Allows to edit an embed's image based on an user

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild = None
            Guild to take as reference. Defaults to current
        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_image(url=guild.icon.url)

    @embed_image.command(name="rainbow")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_image_rainbow(self, ctx: commands.Context):
        """Allows to add a rainbow line as placeholder in embed images

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.set_image(url=RAINBOW)

    @embed_image.command(name="whitebar")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def embed_image_whitebar(self, ctx: commands.Context):
        """Allows to add a whitebar line as placeholder in embed images

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.set_image(url=WHITE_BAR)

    @commands.group(
        name="fields",
        aliases=["field", "f"],
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields(self, ctx: commands.Context):
        """Outputs the fields that the current embed has

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            if content := "\n".join(f"• {i}){f.name} > {f.value}" for i, f in enumerate(embed.fields)):
                await ctx.send(f"```yaml\n{content}\n```")

    @fields.command(
        name="add",
        aliases=["a"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_add(
        self,
        ctx: commands.Context,
        name: str,
        *,
        value: str,
    ):
        """Allows to add a field to an embed, given some parameters

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's name
        value: str
            Field's value
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name=name, value=value, inline=False)

    @fields.command(
        name="inline_add",
        aliases=["iadd", "ia"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_inline_add(
        self,
        ctx: commands.Context,
        name: str,
        *,
        value: str,
    ):
        """Allows to add a field to an embed, given some parameters

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's name
        value: str
            Field's value
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name=name, value=value, inline=True)

    @fields.command(
        name="name",
        aliases=["n"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_name(
        self,
        ctx: commands.Context,
        before: str,
        *,
        after: str,
    ):
        """Allows to rename fields with same names

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        before: str
            Current Name
        after: str
            Name to be changed as
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
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_value(
        self,
        ctx: commands.Context,
        name: str,
        *,
        value: str,
    ):
        """Allows to edit values of fields with same name

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's Name
        value: str
            Field's Value
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
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_inline(
        self,
        ctx: commands.Context,
        *,
        name: str,
    ):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's Name
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

    @fields.group(
        name="delete",
        invoke_without_command=True,
        aliases=["d"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_delete(
        self,
        ctx: commands.Context,
        *,
        name: str,
    ):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's name
        """
        async with self.edit(ctx) as embed:
            embed._fields = [
                dict(name=field.name, value=field.value, inline=field.inline)
                for field in embed.fields
                if field.name != name
            ]

    @fields_delete.command(name="all")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_delete_all(self, ctx: commands.Context):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.clear_fields()

    @fields.group(
        name="index",
        aliases=["i"],
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index(self, ctx: commands.Context):
        """Outputs the amount of fields that the current embed has

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            if fields := embed.fields:
                await ctx.reply(f"There's {len(fields)} fields in the embed")
            else:
                await ctx.reply("There's no fields in the embed")

    @fields_index.command(
        name="add",
        aliases=["a"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_add(
        self,
        ctx: commands.Context,
        index: int,
        name: str,
        *,
        value: str,
    ):
        """Allows to insert a field to an embed based on its index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
        name: str
            Field's Name
        value: str
            Field's Value
        """
        async with self.edit(ctx) as embed:
            embed.insert_field_at(index, name=name, value=value, inline=False)

    @fields_index.command(
        name="inline_add",
        aliases=["iadd", "ia"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_inline_add(
        self,
        ctx: commands.Context,
        index: int,
        name: str,
        *,
        value: str,
    ):
        """Allows to insert a field to an embed based on its index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
        name: str
            Field's Name
        value: str
            Field's Value
        """
        async with self.edit(ctx) as embed:
            embed.insert_field_at(index, name=name, value=value, inline=True)

    @fields_index.command(
        name="name",
        aliases=["n"],
    )
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_name(
        self,
        ctx: commands.Context,
        index: int,
        *,
        name: str,
    ):
        """Allows to rename a field in an embed based on its index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
        name: str
            Field's new name
        """
        async with self.edit(ctx) as embed:
            field = embed.fields[index]
            embed.set_field_at(
                index,
                name=name,
                value=field.value,
                inline=field.inline,
            )

    @fields_index.command(name="value")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_value(
        self,
        ctx: commands.Context,
        index: int,
        *,
        value: str,
    ):
        """Allows to edit a field's value in an embed based on its index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
        value: str
            Field's new value
        """
        async with self.edit(ctx) as embed:
            aux = embed.fields[index]
            embed.set_field_at(index, name=aux.name, value=value, inline=aux.inline)

    @fields_index.command(name="inline")
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_inline(
        self,
        ctx: commands.Context,
        *,
        index: int,
    ):
        """Allows to enable/disable inline of embed fields based on its index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
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
    @commands.has_guild_permissions(
        manage_messages=True,
        send_messages=True,
        embed_links=True,
    )
    async def fields_index_delete(
        self,
        ctx: commands.Context,
        *,
        index: int,
    ):
        """Allows to delete embed fields based on their index

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        index: int
            Integer Index
        """
        async with self.edit(ctx) as embed:
            embed.remove_field(index)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(EmbedBuilder(bot))
