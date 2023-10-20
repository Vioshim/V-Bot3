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
from datetime import datetime
from re import compile
from typing import Optional

from discord import (
    AllowedMentions,
    Attachment,
    Color,
    DeletedReferencedMessage,
    DiscordException,
    Embed,
    Emoji,
    Guild,
    Member,
    Message,
    NotFound,
    PartialEmoji,
    RawMessageDeleteEvent,
    TextChannel,
    Thread,
    User,
    WebhookMessage,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, utcnow

from src.cogs.information import Information
from src.structures.bot import CustomBot
from src.structures.converters import AfterDateCall
from src.utils.etc import SETTING_EMOJI, WHITE_BAR
from src.utils.functions import discord_url_msg, embed_handler, safe_username

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
        self.db = self.bot.mongo_db("Embed Builder")
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
        await self.db.delete_one({"author": member.id, "server": member.guild.id})

    async def webhook_send(self, message: Message, **kwargs):
        webhook = await self.bot.webhook(message.channel)
        thread = message.channel if isinstance(message.channel, Thread) else MISSING

        await webhook.send(allowed_mentions=AllowedMentions.none(), thread=thread, **kwargs)
        await message.delete(delay=0)

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot or not message.content:
            return

        if data := discord_url_msg(message):
            with suppress(DiscordException):
                guild_id, message_id, channel_id = data
                if guild := self.bot.get_guild(guild_id):
                    if not (channel := guild.get_channel_or_thread(channel_id)):
                        channel = await guild.fetch_channel(channel_id)
                elif not (channel := self.bot.get_channel(channel_id)):
                    channel = await self.bot.fetch_channel(channel_id)

                reference = await channel.fetch_message(message_id)
                name = reference.author.display_name.removeprefix("URL〕")
                cog: Information = self.bot.get_cog("Information")
                kwargs = await cog.embed_info(reference)
                if embeds := kwargs.get("embeds", []):
                    embeds[-1].set_footer(
                        text=f"URL Requested by {message.author.display_name}",
                        icon_url=message.author.display_avatar,
                    )

                kwargs["username"] = f"URL〕{safe_username(name)}"
                await self.webhook_send(message, **kwargs)
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
                    view.add_item(Button(label="Watch Replay", url=content, emoji="\N{VIDEO CAMERA}"))

                    await self.webhook_send(
                        message,
                        embed=embed,
                        username=f"URL〕{safe_username(author.display_name)}",
                        avatar_url=author.display_avatar.url,
                        view=view,
                    )

    @commands.Cog.listener()
    async def on_raw_message_delete(self, ctx: RawMessageDeleteEvent):
        if ctx.guild_id:
            await self.db.delete_one(
                {
                    "id": ctx.message_id,
                    "channel": ctx.channel_id,
                    "server": ctx.guild_id,
                }
            )

    async def write(self, message: WebhookMessage | Message, author: Member):
        """A method for adding webhook messages to the database

        Parameters
        ----------
        message: Message
            Message to be uploaded
        author: Member
            Author who sent the message
        """
        await self.db.replace_one(
            {
                "server": message.guild.id,
                "author": author.id,
            },
            {
                "id": message.id,
                "channel": message.channel.id,
                "server": message.guild.id,
                "author": author.id,
            },
            upsert=True,
        )

    async def read(self, guild_id: int, author_id: int) -> Optional[WebhookMessage | Message]:
        with suppress(DiscordException):
            if data := await self.db.find_one({"server": guild_id, "author": author_id}):
                channel_id, guild_id, message_id = data["channel"], data["server"], data["id"]
                if guild := self.bot.get_guild(guild_id):
                    if not (channel := guild.get_channel_or_thread(channel_id)):
                        channel = await guild.fetch_channel(channel_id)
                    try:
                        w = await self.bot.webhook(channel, reason="Embed Builder")
                        thread = channel if isinstance(channel, Thread) else MISSING
                        return await w.fetch_message(message_id, thread=thread)
                    except NotFound:
                        return await channel.fetch_message(message_id)

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
        if ctx.message.interaction:
            if isinstance(ctx.channel, Thread) and ctx.channel.archived:
                await ctx.channel.edit(archived=False)
            await ctx.defer(ephemeral=True)

        message: Optional[Message] = None
        if (ref := ctx.message.reference) and isinstance(aux := ref.resolved, Message):
            if aux.author == self.bot.user:
                message = aux
            elif aux.webhook_id:
                w = await self.bot.webhook(ctx.channel)
                if w.id == aux.webhook_id:
                    message = aux

        if message:
            await self.write(message, ctx.author)
        else:
            message = await self.read(ctx.guild.id, ctx.author.id)

        try:
            embed = Embed()
            if message and message.embeds:
                embed = embed_handler(message, message.embeds[0])
            yield embed
        finally:
            if message:
                kwargs = dict(embed=embed)
                if editing_attachments:
                    kwargs["attachments"], kwargs["embed"] = await self.bot.embed_raw(embed)
                try:
                    if message.author == self.bot.user or isinstance(message, WebhookMessage):
                        await message.edit(**kwargs)
                    elif w := await self.bot.webhook(ctx.channel):
                        thread = ctx.channel if isinstance(ctx.channel, Thread) else MISSING
                        message = await w.edit_message(message.id, thread=thread, **kwargs)
                        await self.write(message, ctx.author)
                except DiscordException as e:
                    await self.db.delete_one({"server": ctx.guild.id, "author": ctx.author.id})
                    await ctx.reply(str(e), delete_after=3, ephemeral=True)
            self.bot.msg_cache_add(ctx.message)
            if inter := ctx.interaction:
                resp = inter.response
                if resp.is_done():
                    await resp.pong()
            else:
                await ctx.message.delete(delay=0)

    @commands.group(aliases=["e"], invoke_without_command=True)
    @commands.has_guild_permissions(manage_messages=True, send_messages=True, embed_links=True)
    async def embed(self, ctx: commands.Context):
        """Shows stored embed's location

        Parameters
        ----------
        ctx: commands.Context
            Message's commands.Context
        """
        embed = Embed(title="Embed Builder", color=ctx.author.color, timestamp=utcnow())
        embed.set_image(url=WHITE_BAR)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon)
        if data := await self.read(ctx.guild.id, ctx.author.id):
            try:
                emoji, name = data.channel.name.split("〛")
                emoji = emoji[0]
            except Exception:
                name = data.channel.name
                emoji = None

            view = View()
            view.add_item(Button(label=name, emoji=emoji, url=data.jump_url))
            await ctx.reply(embed=embed, view=view, ephemeral=True)
        else:
            await ctx.reply(embed=embed, ephemeral=True)

    @embed.command(name="new", aliases=["create"])
    async def embed_new(
        self,
        ctx: commands.Context,
        title: str = "",
        *,
        description: str = "",
        attachment: Optional[Attachment] = None,
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
        attachment: Optional[Attachment] = None
            Image to use in the embed.
        """
        embed = Embed(title=title, description=description)
        webhook = await self.bot.webhook(ctx.channel, reason="Created by Embed Builder")
        author: Member = ctx.author

        thread = ctx.channel if isinstance(ctx.channel, Thread) else MISSING
        attachments = [attachment] if attachment else ctx.message.attachments
        if len(images := [x for x in attachments if x.content_type.startswith("image/")]) == 1:
            embed.set_image(url=f"attachment://{images[0].filename}")

        message: WebhookMessage = await webhook.send(
            embed=embed,
            wait=True,
            username=safe_username(author.display_name),
            avatar_url=author.display_avatar.url,
            files=[await x.to_file() for x in attachments],
            thread=thread,
        )
        message.channel = ctx.channel
        await self.write(message, author)
        await ctx.message.delete(delay=0)

    @embed.command(name="set")
    async def embed_set(self, ctx: commands.Context, *, message: Optional[str] = None):
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
        elif message:
            message = await self.converter.convert(ctx, message)

        if isinstance(message, Message):
            if message.author == self.bot.user:
                await self.write(message, ctx.author)
                await ctx.reply(
                    "Message has been set",
                    delete_after=2,
                    ephemeral=True,
                )
            elif webhook_id := message.webhook_id:
                webhook = await self.bot.webhook(message.channel)
                if webhook_id != webhook.id:
                    await ctx.reply(
                        "Message can't be set",
                        delete_after=2,
                        ephemeral=True,
                    )
                else:
                    thread = message.channel if isinstance(message.channel, Thread) else MISSING
                    message: WebhookMessage = await webhook.fetch_message(message.id, thread=thread)
                    await self.write(message, ctx.author)
                    await ctx.reply(
                        "Message has been set",
                        delete_after=2,
                        ephemeral=True,
                    )
            else:
                await ctx.reply(
                    "I can't use that message for embedding purposes",
                    delete_after=2,
                    ephemeral=True,
                )
            await ctx.message.delete(delay=0)
        else:
            await ctx.reply(
                "No message was found.",
                delete_after=2,
                ephemeral=True,
            )

    @embed.group(name="post", fallback="copy", invoke_without_command=True)
    async def embed_post(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            webhook = await self.bot.webhook(ctx.channel)

            thread = ctx.channel if isinstance(ctx.channel, Thread) else MISSING
            message: Optional[WebhookMessage | Message] = None
            if reference := ctx.message.reference:
                if not isinstance(msg := reference.resolved, DeletedReferencedMessage):
                    try:
                        message = await webhook.edit_message(reference.message_id, thread=thread, embed=embed)
                    except DiscordException:
                        if not isinstance(msg, Message):
                            try:
                                msg = await ctx.channel.fetch_message(reference.message_id)
                            except DiscordException:
                                msg = None

                        if isinstance(msg, Message) and msg.author == self.bot.user:
                            try:
                                message = await msg.edit(embed=embed)
                            except DiscordException:
                                message = None

            if not message:
                message = await webhook.send(
                    embed=embed,
                    username=safe_username(ctx.author.display_name),
                    avatar_url=ctx.author.display_avatar.url,
                    thread=thread,
                    wait=True,
                )
            await self.write(message, ctx.author)

    @embed_post.command(name="raw")
    async def embed_post_raw(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            files, embed_aux = await self.bot.embed_raw(embed)
            webhook = await self.bot.webhook(ctx.channel)

            thread = ctx.channel if isinstance(ctx.channel, Thread) else MISSING
            message: Optional[WebhookMessage | Message] = None
            if reference := ctx.message.reference:
                if not isinstance(msg := reference.resolved, DeletedReferencedMessage):
                    try:
                        message = await webhook.edit_message(
                            reference.message_id,
                            thread=thread,
                            embed=embed,
                            files=files,
                        )
                    except DiscordException:
                        if not isinstance(msg, Message):
                            try:
                                msg = await ctx.channel.fetch_message(reference.message_id)
                            except DiscordException:
                                msg = None

                        if isinstance(msg, Message) and msg.author == self.bot.user:
                            try:
                                message = await msg.edit(embed=embed, files=files)
                            except DiscordException:
                                message = None

            if not message:
                message = await webhook.send(
                    files=files,
                    embed=embed_aux,
                    username=safe_username(ctx.author.display_name),
                    avatar_url=ctx.author.display_avatar.url,
                    thread=thread,
                    wait=True,
                )
            await self.write(message, ctx.author)

    @embed.group(aliases=["bot"], invoke_without_command=True)
    @commands.has_guild_permissions(manage_messages=True, send_messages=True, embed_links=True)
    async def embed_bot(self, ctx: commands.Context):
        await self.embed(ctx)

    @embed_bot.command(name="new", aliases=["create"])
    async def embed_bot_new(
        self,
        ctx: commands.Context,
        title: str = "",
        *,
        description: str = "",
        attachment: Optional[Attachment] = None,
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
        attachment: Optional[Attachment] = None
            Image to use in the embed.
        """
        embed = Embed(title=title, description=description)
        author: Member = ctx.author
        attachments = [attachment] if attachment else ctx.message.attachments
        if len(images := [x for x in attachments if x.content_type.startswith("image/")]) == 1:
            embed.set_image(url=f"attachment://{images[0].filename}")

        files = [await x.to_file() for x in attachments]
        message = await ctx.channel.send(embed=embed, files=files)
        await self.write(message, author)
        await ctx.message.delete(delay=0)

    @embed_bot.group(name="post", fallback="copy", invoke_without_command=True)
    async def embed_bot_post(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            message: Optional[Message] = None
            if reference := ctx.message.reference:
                if not isinstance(msg := reference.resolved, DeletedReferencedMessage):
                    try:
                        message = ctx.channel.get_partial_message(reference.message_id)
                        message = await message.edit(embed=embed)
                    except DiscordException:
                        if not isinstance(msg, Message):
                            try:
                                msg = await ctx.channel.fetch_message(reference.message_id)
                            except DiscordException:
                                msg = None

                        if isinstance(msg, Message) and msg.author == self.bot.user:
                            try:
                                message = await msg.edit(embed=embed)
                            except DiscordException:
                                message = None

            if not message:
                message = await ctx.channel.send(embed=embed)
            await self.write(message, ctx.author)

    @embed_bot_post.command(name="raw")
    async def embed_bot_post_raw(self, ctx: commands.Context):
        """Posts an embed in another channel

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            files, embed_aux = await self.bot.embed_raw(embed)
            message: Optional[Message] = None
            if reference := ctx.message.reference:
                if not isinstance(msg := reference.resolved, DeletedReferencedMessage):
                    try:
                        message = ctx.channel.get_partial_message(reference.message_id)
                        message = await message.edit(embed=embed, files=files)
                    except DiscordException:
                        if not isinstance(msg, Message):
                            try:
                                msg = await ctx.channel.fetch_message(reference.message_id)
                            except DiscordException:
                                msg = None

                        if isinstance(msg, Message) and msg.author == self.bot.user:
                            try:
                                message = await msg.edit(embed=embed, files=files)
                            except DiscordException:
                                message = None

            if not message:
                message = await ctx.channel.send(files=files, embed=embed_aux)
            await self.write(message, ctx.author)

    @embed_bot.command(name="unset")
    async def embed_unset(self, ctx: commands.Context):
        """Allows to remove the stored embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        if data := await self.db.find_one_and_delete({"server": ctx.guild.id, "author": ctx.author.id}):
            guild_id, channel_id, message_id = data["server"], data["channel"], data["id"]
            view = View()
            btn = Button(
                label="Jump URL",
                url=f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}",
            )
            view.add_item(btn)
            await ctx.reply("Removed stored embed.", view=view)
        else:
            await ctx.reply("No stored embed to remove.")

    @embed.command(name="title", aliases=["t"])
    async def embed_title(self, ctx: commands.Context, *, title: str = ""):
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

    @embed.command(name="description", aliases=["desc", "d", "text", "content"])
    async def embed_description(self, ctx: commands.Context, *, description: str = ""):
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

    @embed.command(name="color", aliases=["colour"], with_app_command=False)
    async def embed_color(self, ctx: commands.Context, *, color: Optional[Color] = None):
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

    @embed.group(name="timestamp", fallback="defined", aliases=["date", "time"], invoke_without_command=True)
    async def embed_timestamp(self, ctx: commands.Context, *, date: AfterDateCall = None):
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
    async def embed_timestamp_now(self, ctx: commands.Context):
        """Allows to edit the embed's timestamp

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.timestamp = utcnow()

    @embed.command(name="url", aliases=["link"])
    async def embed_url(self, ctx: commands.Context, *, url: str = ""):
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

    @embed.group(name="author", fallback="clear", invoke_without_command=True)
    async def embed_author(self, ctx: commands.Context, *, author: str = ""):
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
                embed.set_author(name=author, url=embed.author.url, icon_url=embed.author.icon_url)
            else:
                embed.remove_author()

    @embed_author.command(name="user")
    async def embed_author_user(self, ctx: commands.Context, *, author: Member | User = None):
        """Allows to set an user as author of an embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        author: User
            Discord User
        """
        async with self.edit(ctx) as embed:
            author = author or ctx.author
            embed.set_author(name=author.display_name, url=embed.author.url, icon_url=author.display_avatar.url)

    @embed_author.command(name="guild", aliases=["server"])
    async def embed_author_guild(self, ctx: commands.Context, *, guild: Optional[Guild] = None):
        """Allows to set the specified guild as Author of the embed

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild
            Guild. Defaults to Current
        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_author(name=guild.name, url=embed.author.url, icon_url=guild.icon)

    @embed_author.command(name="url", aliases=["link"])
    async def embed_author_url(self, ctx: commands.Context, *, url: str = ""):
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
                embed.set_author(name=author.name, url=url or author.url, icon_url=author.icon_url)

    @embed_author.command(name="icon")
    async def embed_author_icon(self, ctx: commands.Context, *, icon: Optional[Emoji | PartialEmoji | str] = None):
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
                    embed.set_author(name=author.name, url=author.url, icon_url=attachments[-1].proxy_url.split("?")[0])
                elif isinstance(icon, (Emoji, PartialEmoji)):
                    embed.set_author(name=author.name, url=author.url, icon_url=icon.url)
                elif icon:
                    embed.set_author(name=author.name, url=author.url, icon_url=icon)
                else:
                    embed.set_author(name=author.name, url=author.url)

    @embed.group(name="footer", fallback="clear", invoke_without_command=True)
    async def embed_footer(self, ctx: commands.Context, *, footer: str = ""):
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
    async def embed_footer_user(self, ctx: commands.Context, *, user: Optional[Member | User] = None):
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
            embed.set_footer(text=user.display_name, icon_url=user.display_avatar.url)

    @embed_footer.command(name="guild", aliases=["server"])
    async def embed_footer_guild(self, ctx: commands.Context, *, guild: Optional[Guild] = None):
        """Allows to edit an embed's author icon

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        guild: Guild
            Guild as Footer. Defaults to Self
        """
        async with self.edit(ctx) as embed:
            guild: Guild = guild or ctx.guild
            embed.set_footer(text=guild.name, icon_url=guild.icon)

    @embed_footer.command(name="icon")
    async def embed_footer_icon(self, ctx: commands.Context, *, icon: Optional[Emoji | PartialEmoji | str] = None):
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
                    embed.set_footer(text=footer.text, icon_url=attachments[-1].proxy_url.split("?")[0])
                elif isinstance(icon, (Emoji, PartialEmoji)):
                    embed.set_footer(text=footer.text, icon_url=icon.url)
                elif icon:
                    embed.set_footer(text=footer.text, icon_url=icon)
                else:
                    embed.set_footer(text=footer.text)

    @embed.group(name="thumbnail", fallback="clear", invoke_without_command=True)
    async def embed_thumbnail(self, ctx: commands.Context, *, thumbnail: Optional[Emoji | PartialEmoji | str] = None):
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
                embed.set_thumbnail(url=attachments[-1].proxy_url.split("?")[0])
            elif isinstance(thumbnail, (Emoji, PartialEmoji)):
                embed.set_thumbnail(url=thumbnail.url)
            elif thumbnail:
                embed.set_thumbnail(url=thumbnail)
            else:
                embed.set_thumbnail(url=None)

    @embed_thumbnail.command(name="user", invoke_without_command=True)
    async def embed_thumbnail_user(self, ctx: commands.Context, *, user: Optional[Member | User] = None):
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

    @embed_thumbnail.command(name="guild", aliases=["server"], invoke_without_command=True)
    async def embed_thumbnail_guild(self, ctx: commands.Context, *, guild: Optional[Guild] = None):
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

    @embed.group(name="image", fallback="clear", invoke_without_command=True)
    async def embed_image(self, ctx: commands.Context, *, image: Optional[Emoji | PartialEmoji | str] = None):
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
                embed.set_image(url=attachments[-1].proxy_url.split("?")[0])
            elif isinstance(image, (Emoji, PartialEmoji)):
                embed.set_image(url=image.url)
            elif image:
                embed.set_image(url=image)
            else:
                embed.set_image(url=None)

    @embed_image.command(name="user")
    async def embed_image_user(self, ctx: commands.Context, *, user: Optional[Member | User] = None):
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

    @embed_image.command(name="guild", aliases=["server"])
    async def embed_image_guild(self, ctx: commands.Context, *, guild: Optional[Guild] = None):
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
            embed.set_image(url=guild.icon)

    @embed_image.command(name="rainbow")
    async def embed_image_rainbow(self, ctx: commands.Context):
        """Allows to add a rainbow line as placeholder in embed images

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.set_image(url="https://hmp.me/dx4d")

    @embed_image.command(name="whitebar")
    async def embed_image_whitebar(self, ctx: commands.Context, x: int = 500, y: int = 5):
        """Allows to add a whitebar line as placeholder in embed images

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        url = f"https://dummyimage.com/{x}x{y}/FFFFFF/000000&text=%20"
        async with self.edit(ctx) as embed:
            embed.set_image(url=url)

    @commands.group(aliases=["field", "f"], invoke_without_command=True)
    @commands.has_guild_permissions(manage_messages=True, send_messages=True, embed_links=True)
    async def fields(self, ctx: commands.Context):
        """Outputs the fields that the current embed has

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            content = "\n".join(f"• {i}){f.name} > {f.value}" for i, f in enumerate(embed.fields))
            await ctx.send(f"```yaml\n{content}\n```")

    @fields.group(name="add", fallback="add", aliases=["a"], invoke_without_command=True)
    async def fields_add(self, ctx: commands.Context, name: str, *, value: str):
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

    @fields_add.command(name="key", aliases=["k"])
    async def fields_add_key(self, ctx: commands.Context, *, name: str):
        """Allows to add a field to an embed, given a key

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's name
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name=name, value="\u200b", inline=False)

    @fields_add.command(name="value", aliases=["v"])
    async def fields_add_value(self, ctx: commands.Context, *, value: str):
        """Allows to add a field to an embed, given a key

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        value: str
            Field's value
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name="\u200b", value=value, inline=False)

    @fields.group(name="inline_add", aliases=["iadd", "ia"], invoke_without_command=True)
    async def fields_inline_add(self, ctx: commands.Context, name: str, *, value: str):
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

    @fields_inline_add.command(name="key", aliases=["k"])
    async def fields_inline_add_key(self, ctx: commands.Context, *, name: str):
        """Allows to add a field to an embed, given a key

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        name: str
            Field's name
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name=name, value="\u200b", inline=True)

    @fields_inline_add.command(name="value", aliases=["v"])
    async def fields_inline_add_value(self, ctx: commands.Context, *, value: str):
        """Allows to add a field to an embed, given a key

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        value: str
            Field's value
        """
        async with self.edit(ctx) as embed:
            embed.add_field(name="\u200b", value=value, inline=True)

    @fields.command(name="name", aliases=["n"])
    async def fields_name(self, ctx: commands.Context, before: str, *, after: str):
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
                    embed.set_field_at(index, name=after, value=field.value, inline=field.inline)

    @fields.command(name="value")
    async def fields_value(self, ctx: commands.Context, name: str, *, value: str):
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
                    embed.set_field_at(index, name=field.name, value=value, inline=field.inline)

    @fields.command(name="inline")
    async def fields_inline(self, ctx: commands.Context, *, name: str):
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
                    embed.set_field_at(index, name=field.name, value=field.value, inline=not field.inline)

    @fields.group(name="delete", fallback="name", invoke_without_command=True, aliases=["d"])
    async def fields_delete(self, ctx: commands.Context, *, name: str):
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
    async def fields_delete_all(self, ctx: commands.Context):
        """Allows to enable/disable inline of fields with same name

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            embed.clear_fields()

    @fields.group(name="index", fallback="info", aliases=["i"], invoke_without_command=True)
    async def fields_index(self, ctx: commands.Context):
        """Outputs the amount of fields that the current embed has

        Parameters
        ----------
        ctx: commands.Context
            commands.Context
        """
        async with self.edit(ctx) as embed:
            await ctx.reply(f"There's {len(embed.fields):02d} fields in the embed.")

    @fields_index.group(name="add", aliases=["a"], invoke_without_command=True)
    async def fields_index_add(self, ctx: commands.Context, index: int, name: str, *, value: str):
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

    @fields_index_add.command(name="key", aliases=["k"])
    async def fields_index_add_key(self, ctx: commands.Context, index: int, *, name: str):
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
            embed.insert_field_at(index, name=name, value="\u200b", inline=False)

    @fields_index_add.command(name="value", aliases=["v"])
    async def fields_index_add_value(self, ctx: commands.Context, index: int, *, value: str):
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
            embed.insert_field_at(index, name="\u200b", value=value, inline=False)

    @fields_index.group(name="inline_add", aliases=["iadd", "ia"], invoke_without_command=True)
    async def fields_index_inline_add(self, ctx: commands.Context, index: int, name: str, *, value: str):
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

    @fields_index_inline_add.command(name="key", aliases=["k"])
    async def fields_index_inline_add_key(self, ctx: commands.Context, index: int, *, name: str):
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
            embed.insert_field_at(index, name=name, value="\u200b", inline=True)

    @fields_index_inline_add.command(name="value", aliases=["v"])
    async def fields_index_inline_add_value(self, ctx: commands.Context, index: int, *, value: str):
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
            embed.insert_field_at(index, name="\u200b", value=value, inline=True)

    @fields_index.command(name="name", aliases=["n"])
    async def fields_index_name(self, ctx: commands.Context, index: int, *, name: str):
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
            embed.set_field_at(index, name=name, value=field.value, inline=field.inline)

    @fields_index.command(name="value")
    async def fields_index_value(self, ctx: commands.Context, index: int, *, value: str):
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
    async def fields_index_inline(self, ctx: commands.Context, *, index: int):
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
            embed.set_field_at(index, name=field.name, value=field.value, inline=not field.inline)

    @fields_index.command(name="delete")
    async def fields_index_delete(self, ctx: commands.Context, *, index: int):
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
