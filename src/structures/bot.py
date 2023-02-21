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


import sys
from contextlib import suppress
from io import BytesIO
from logging import Logger
from os import getenv
from pathlib import Path, PurePath
from typing import Literal, Optional

from aiogoogle import Aiogoogle
from aiohttp import ClientSession
from apscheduler.schedulers.async_ import AsyncScheduler
from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    File,
    ForumChannel,
    HTTPException,
    Intents,
    Member,
    Message,
    NotFound,
    PartialMessage,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
    Webhook,
)
from discord.abc import Messageable
from discord.ext.commands import Bot
from discord.utils import format_dt, utcnow
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from mystbin import Client as MystBinClient
from orjson import dumps

from src.utils.matches import REGEX_URL

__all__ = ("CustomBot",)


class CustomBot(Bot):
    """
    A Custom implementation of `commands.Bot`
    but based on specific bot needs.

    Attributes
    ----------
    logger: Logger
        logger instance
    scheduler : AsyncScheduler
        apscheduler's async instance
    session : ClientSession
        aiohttp's session
    m_bin : MystBinClient
        client for posting requests
    msg_cache : set[int]
        messages IDs to ignore
    dagpi : DagpiClient:
        Dagpi client
    """

    def __init__(
        self,
        scheduler: AsyncScheduler,
        logger: Logger,
        aiogoogle: Aiogoogle,
        **options,
    ):
        super(CustomBot, self).__init__(
            **options,
            intents=Intents.all(),
            allowed_mentions=AllowedMentions(
                users=False,
                roles=False,
                everyone=False,
                replied_user=True,
            ),
        )
        self.scheduler = scheduler
        self.logger = logger
        self.aiogoogle = aiogoogle
        self.session = ClientSession(json_serialize=dumps, raise_for_status=True)
        self.m_bin = MystBinClient(token=getenv("MYSTBIN_TOKEN"), session=self.session)
        self.mongodb = AsyncIOMotorClient(getenv("MONGO_URI"))
        self.start_time = utcnow()
        self.msg_cache: set[int] = set()
        self.scam_urls: set[str] = set()
        self.webhook_cache: dict[int, Webhook] = {}
        self.supporting: dict[Member, Member] = {}

    async def on_error(self, event_method: str, /, *args, **kwargs) -> None:
        self.logger.exception("Ignoring exception in %s", event_method, exc_info=sys.exc_info())

    def mongo_db(self, db: str) -> AsyncIOMotorCollection:
        return self.mongodb.discord[db]

    async def setup_hook(self) -> None:
        await self.load_extension("jishaku")
        path = Path("src/cogs")
        for cog in map(PurePath, path.glob("*/__init__.py")):
            route = ".".join(cog.parts[:-1])
            try:
                await self.load_extension(route)
            except Exception as e:
                self.logger.exception("Exception while loading %s", route, exc_info=e)
            else:
                self.logger.info("Successfully loaded %s", route)

    async def get_or_fetch_user(self, user_id: int, /) -> Optional[User]:
        if user := self.get_user(user_id):
            return user

        with suppress(DiscordException):
            return await self.fetch_user(user_id)

    async def fetch_webhook(self, webhook_id: int, /) -> Webhook:
        """|coro|

        Retrieves a :class:`.Webhook` with the specified ID.

        Raises
        --------
        :exc:`.HTTPException`
            Retrieving the webhook failed.
        :exc:`.NotFound`
            Invalid webhook ID.
        :exc:`.Forbidden`
            You do not have permission to fetch this webhook.

        Returns
        ---------
        :class:`.Webhook`
            The webhook you requested.
        """
        webhook: Webhook = await super(CustomBot, self).fetch_webhook(webhook_id)
        if webhook.user == self.user:
            self.webhook_cache[webhook.channel.id] = webhook
        return webhook

    async def on_webhooks_update(self, channel: TextChannel):
        """Bot's on_webhooks_update for caching

        Parameters
        ----------
        Channel : TextChannel
            Channel that got changes in its webhooks
        """
        try:
            if webhook := self.webhook_cache.get(channel.id):
                self.webhook_cache[channel.id] = await webhook.fetch()
        except (HTTPException, NotFound, ValueError):
            del self.webhook_cache[channel.id]

    async def on_message(self, message: Message) -> None:
        """Bot's on_message with nitro scam handler

        Parameters
        ----------
        message : Message
            message to process
        """
        if message.content and (not await self.is_owner(self.user)) and message.author != self.user:
            elements = REGEX_URL.findall(message.content)
            if self.scam_urls.intersection(elements):
                try:
                    if not message.guild:
                        await message.reply("That's a Nitro Scam")
                    else:
                        await message.delete()
                        await message.author.ban(delete_message_days=1, reason="Nitro Scam victim")
                    return
                except DiscordException:
                    return
        await self.process_commands(message)

    def msg_cache_add(self, message: Message | PartialMessage | int, /):
        """Method to add a message to the message cache

        Parameters
        ----------
        message : Message | PartialMessage | int
            Message to ignore in the logs
        """
        if isinstance(message, int):
            self.msg_cache.add(message)
        elif isinstance(message, (Message, PartialMessage)):
            self.msg_cache.add(message.id)

    async def embed_raw(
        self,
        embed: Embed,
        *exclude: Literal["thumbnail", "author", "footer", "image"],
    ) -> tuple[list[File], Embed]:
        """Asynchronous function for fetching files of an embed,
        and attached to itself

        Parameters
        ----------
        embed : Embed
            Embed for extraction purposes.
        exclude : str
            To not extract thumbnail | author | footer | image
        Returns
        -------
        tuple[list[File], Embed]
            A tuple that contains a list of files, and its produced embed.
        """
        files: list[File] = []
        properties: dict[str, str] = dict(
            image=embed.image.url,
            thumbnail=embed.thumbnail.url,
            author=embed.author.icon_url,
            footer=embed.footer.icon_url,
        )

        def wrapper(func, arg: str = "url", **kwargs2):
            """Wrapper Method

            Parameters
            ----------
            func : Callable[..., Embed]
                Function
            arg : str, optional
                Parameter, by default "url"
            """

            def inner(value: str) -> Embed:
                """Inner Wrapper

                Parameters
                ----------
                value : str
                    Value to be applies
                """
                kwargs2[arg] = value
                return func(**kwargs2)

            return inner

        methods = dict(
            image=wrapper(embed.set_image),
            thumbnail=wrapper(embed.set_thumbnail),
            author=wrapper(func=embed.set_author, arg="icon_url", name=embed.author.name, url=embed.author.url),
            footer=wrapper(func=embed.set_footer, arg="icon_url", text=embed.footer.text),
        )
        for item in set(properties) - set(exclude):
            if image := properties[item]:
                if image.startswith("attachment://"):
                    continue
                file = await self.get_file(image, filename=item)
                if isinstance(file, File):
                    files.append(file)
                    image = f"attachment://{file.filename}"
                method = methods[item]
                method(image)

        return files, embed

    async def get_file(self, url: str, filename: str = None, spoiler: bool = False) -> Optional[File]:
        """Early Implementation of an image downloader with size specified

        Parameters
        ----------
        url : str, optional
            URL, by default None
        filename : str, optional
            Filename without extension, by default None
        spoiler : bool, optional
            Enables Spoiler, by default False

        Returns
        -------
        Optional[File]
            File for discord usage
        """
        with suppress(Exception):
            async with self.session.get(str(url)) as resp:
                data = await resp.read()
                fp = BytesIO(data)
                text = resp.content_type.split("/")
                if filename and "." not in filename:
                    filename = f"{filename}.{text[-1]}"
                if not filename:
                    filename = ".".join(text)
                return File(fp=fp, filename=filename, spoiler=spoiler)

    def webhook_lazy(self, channel: Messageable | int) -> Optional[Webhook]:
        """Function which returns first webhook if cached

        Parameters
        ----------
        channel : Messageable | int
            Channel or its ID
        reason : str, optional
            Webhook creation reason, by default None

        Returns
        -------
        Optional[Webhook]
            Webhook if channel is valid.
        """
        if isinstance(channel, Thread):
            channel = channel.parent

        channel_id: int = getattr(channel, "id", channel)

        if webhook := self.webhook_cache.get(channel_id):
            return webhook

        if isinstance(channel, int):
            channel: TextChannel = self.get_channel(channel)
            if isinstance(channel, Thread):
                channel = channel.parent

        channel_id: int = getattr(channel, "id", channel)

        if webhook := self.webhook_cache.get(channel_id):
            return webhook

    async def webhook(self, channel: Messageable | int, *, reason: str = None) -> Webhook:
        """Function which returns first webhook of a
        channel creates one if there's no webhook

        Parameters
        ----------
        channel : Messageable | int
            Channel or its ID
        reason : str, optional
            Webhook creation reason, by default None

        Returns
        -------
        Webhook
            Webhook if channel is valid.
        """
        if webhook := self.webhook_lazy(channel):
            return webhook

        if isinstance(channel, int):
            aux = self.get_channel(channel)
            channel = await self.fetch_channel(channel) if aux is None else aux
        channel = getattr(channel, "parent", channel)

        if isinstance(channel, (TextChannel, ForumChannel, VoiceChannel)):
            for item in await channel.webhooks():
                if item.user == self.user:
                    self.webhook_cache[channel.id] = item
                    return item
            image = await self.user.display_avatar.read()
            item = await channel.create_webhook(
                name=self.user.display_name,
                avatar=image,
                reason=reason,
            )
            self.webhook_cache[channel.id] = item
            return item

    def __repr__(self) -> str:
        """Representation of V-Bot

        Returns
        -------
        str
            Message with Timestamp
        """
        time = format_dt(self.start_time, style="R")
        return f"V-Bot(Started={time})"
