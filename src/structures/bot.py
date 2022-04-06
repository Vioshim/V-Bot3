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
from io import BytesIO
from logging import Logger
from os import getenv
from pathlib import Path
from typing import Literal, Optional, Union

from aiohttp import ClientSession
from apscheduler.schedulers.async_ import AsyncScheduler
from asyncdagpi import Client as DagpiClient
from asyncpg import Connection, Pool
from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    File,
    Intents,
    Message,
    PartialMessage,
    TextChannel,
    Thread,
    Webhook,
)
from discord.abc import Messageable
from discord.ext.commands import Bot
from discord.utils import format_dt, utcnow
from mystbin import Client as MystBinClient
from orjson import dumps

from src.utils.matches import URL_DOMAIN_MATCH

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
    pool : Pool
        asyncpg's Pool instance
    msg_cache : set[int]
        messages IDs to ignore
    dagpi : DagpiClient:
        Dagpi client
    """

    def __init__(
        self,
        scheduler: AsyncScheduler,
        pool: Pool,
        logger: Logger,
        **options,
    ):
        super().__init__(
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
        self.pool = pool
        self.logger = logger
        self.session = ClientSession(
            json_serialize=dumps,
            raise_for_status=True,
        )
        self.m_bin = MystBinClient(session=self.session)
        self.start_time = utcnow()
        self.msg_cache: set[int] = set()
        self.dagpi = DagpiClient(getenv("DAGPI_TOKEN"))
        self.scam_urls: set[str] = set()
        self.webhook_cache: dict[int, Webhook] = {}

    async def setup_hook(self) -> None:
        await self.load_extension("jishaku")
        path = Path("src/cogs")
        path.resolve()
        for cog in path.glob("*/cog.py"):
            item = str(cog).removesuffix(".py").replace("\\", ".").replace("/", ".")
            await self.load_extension(item)
            self.logger.info("Successfully loaded %s", item)

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

    async def on_message(self, message: Message) -> None:
        """Bot's on_message with nitro scam handler

        Parameters
        ----------
        message : Message
            message to process
        """
        if message.content:
            elements = URL_DOMAIN_MATCH.findall(message.content)
            if self.scam_urls.intersection(elements):
                with suppress(DiscordException):
                    if not message.guild:
                        await message.reply("That's a Nitro Scam")
                    else:
                        await message.delete()
                        await message.author.ban(
                            delete_message_days=1,
                            reason="Nitro Scam victim",
                        )
                return
        await self.process_commands(message)

    def msg_cache_add(self, message: Union[Message, PartialMessage, int], /):
        """Method to add a message to the message cache

        Parameters
        ----------
        message : Union[Message, PartialMessage, int]
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
            author=wrapper(
                func=embed.set_author,
                arg="icon_url",
                name=embed.author.name,
                url=embed.author.url,
            ),
            footer=wrapper(
                func=embed.set_footer,
                arg="icon_url",
                text=embed.footer.text,
            ),
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

    async def get_file(
        self,
        url: str,
        filename: str = None,
        spoiler: bool = False,
    ) -> Optional[File]:
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
                if resp.status == 200:
                    data = await resp.read()
                    fp = BytesIO(data)
                    text = resp.content_type.split("/")
                    if not filename:
                        filename = ".".join(text)
                    else:
                        filename = f"{filename}.{text[-1]}"
                    return File(
                        fp=fp,
                        filename=filename,
                        spoiler=spoiler,
                    )

    @asynccontextmanager
    async def database(
        self,
        *,
        timeout: float = None,
        isolation: Literal[
            "read_committed",
            "serializable",
            "repeatable_read",
        ] = None,
        readonly: bool = False,
        deferrable: bool = False,
        raise_on_error: bool = True,
    ):
        """Database connection function

        Parameters
        ----------
        timeout : float, optional
            Timeout, by default None
        isolation : str, optional
            Isolation mode, by default None
        readonly : bool, optional
            If it restricts modification, by default False
        deferrable : bool, optional
            if it can be deferred, by default False
        raise_on_error: bool, optional
            If it will raise exceptions, by default False

        Yields
        ------
        Connection
            Connection
        """
        connection: Connection = await self.pool.acquire(timeout=timeout)
        transaction = connection.transaction(
            isolation=isolation, readonly=readonly, deferrable=deferrable
        )
        await transaction.start()
        try:
            yield connection
        except Exception as e:
            self.logger.exception(
                "An exception occurred in the transaction", exc_info=e
            )
            if not connection.is_closed():
                await transaction.rollback()
            if raise_on_error:
                raise e
        else:
            if not connection.is_closed():
                await transaction.commit()
        finally:
            await self.pool.release(connection)

    # noinspection PyTypeChecker
    async def webhook(
        self,
        channel: Union[Messageable, int],
        *,
        reason: str = None,
    ) -> Webhook:
        """Function which returns first webhook of a
        channel creates one if there's no webhook

        Parameters
        ----------
        channel : Union[Thread, TextChannel, int]
            Channel or its ID
        reason : str, optional
            Webhook creation reason, by default None

        Returns
        -------
        Webhook
            Webhook if channel is valid.
        """
        if isinstance(channel, Thread):
            channel = channel.guild.get_channel(channel.parent_id)

        channel_id: int = getattr(channel, "id", channel)

        if webhook := self.webhook_cache.get(channel_id):
            return webhook

        if isinstance(channel, int):
            channel: TextChannel = self.get_channel(channel)
            if isinstance(channel, Thread):
                channel = channel.guild.get_channel(channel.parent_id)

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
