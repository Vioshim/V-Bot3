# Copyright 2021 Vioshim
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
from io import BytesIO
from logging import getLogger, setLoggerClass
from os import getenv
from typing import Literal, Optional, Union

from aiohttp import ClientSession
from apscheduler.schedulers.async_ import AsyncScheduler
from asyncdagpi import Client as DagpiClient
from asyncpg import Connection, Pool
from discord import Embed, File, Message, PartialMessage, TextChannel, Thread, Webhook
from discord.abc import Messageable
from discord.ext.commands import Bot
from discord.utils import format_dt, utcnow
from mystbin import Client as MystBinClient
from orjson import dumps

from src.structures.logger import ColoredLogger

__all__ = ("CustomBot",)

setLoggerClass(ColoredLogger)


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

    async def sync_commands(self) -> None:
        """
        Soon to be patched
        """

    def __init__(self, **options):
        super().__init__(**options)
        self.logger = getLogger(__name__)
        self.scheduler: AsyncScheduler = options.pop("scheduler")
        # noinspection PyTypeChecker
        self.session = ClientSession(json_serialize=dumps)
        self.m_bin = MystBinClient(session=self.session)
        self.start_time = utcnow()
        self.pool: Pool = options.pop("pool")
        self.msg_cache: set[int] = set()
        self.dagpi = DagpiClient(getenv("DAGPI_TOKEN"))

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
        self, embed: Embed, *exclude: Literal["thumbnail", "author", "footer", "image"]
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
            footer=wrapper(func=embed.set_footer, arg="icon_url", text=embed.footer.text),
        )
        for item in set(properties) - set(exclude):
            if image := properties[item]:
                file = await self.get_file(image, filename=item)
                if isinstance(file, File):
                    files.append(file)
                    image = f"attachment://{file.filename}"
                method = methods[item]
                method(image)

        return files, embed

    async def get_file(
        self, url: str, filename: str = None, spoiler: bool = False
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
        async with self.session.get(str(url)) as resp:
            if resp.status == 200:
                data = await resp.read()
                fp = BytesIO(data)
                text = resp.content_type.split("/")
                if filename:
                    return File(fp=fp, filename=f"{filename}.{text[-1]}", spoiler=spoiler)
                return File(fp=fp, filename=f"image.{text[-1]}", spoiler=spoiler)

    # noinspection PyBroadException
    @asynccontextmanager
    async def database(
        self,
        *,
        timeout: float = None,
        isolation: Literal["read_committed", "serializable", "repeatable_read"] = None,
        readonly: bool = False,
        deferrable: bool = False,
        raise_on_error: bool = False,
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
            self.logger.exception("An exception occurred in the transaction", exc_info=e)
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
    async def webhook(self, channel: Union[Messageable, int], *, reason: str = None) -> Webhook:
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
        if isinstance(channel, int):
            channel: TextChannel = self.get_channel(channel)
        if isinstance(channel, Thread):
            channel: TextChannel = channel.parent

        for item in await channel.webhooks():
            if item.user == self.user:
                return item
        image = await self.user.display_avatar.read()
        return await channel.create_webhook(
            name=self.user.display_name, avatar=image, reason=reason
        )

    def __repr__(self) -> str:
        """Representation of V-Bot

        Returns
        -------
        str
            Message with Timestamp
        """
        time = format_dt(self.start_time, style="R")
        return f"V-Bot(Started={time})"
