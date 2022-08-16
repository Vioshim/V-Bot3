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

from asyncio import run
from json import dumps
from logging import getLogger, setLoggerClass
from os import getenv

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
from apscheduler.schedulers.async_ import AsyncScheduler
from asyncpg import Connection, create_pool
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv
from orjson import loads

from src.structures.bot import CustomBot
from src.structures.help import CustomHelp
from src.structures.logger import ColoredLogger

# basicConfig(level=INFO)
setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

load_dotenv()

try:
    from uvloop import EventLoopPolicy  # type: ignore
except ModuleNotFoundError:
    logger.error("Not using uvloop")
else:
    from asyncio import set_event_loop_policy

    set_event_loop_policy(EventLoopPolicy())


async def init_connection(conn: Connection):
    await conn.set_type_codec("json", encoder=dumps, decoder=loads, schema="pg_catalog")
    await conn.set_type_codec("jsonb", encoder=dumps, decoder=loads, schema="pg_catalog")


async def main() -> None:
    """Main Execution function"""
    try:
        google_kwargs = loads(getenv("GOOGLE_API", "{}"))
        creds = ServiceAccountCreds(**google_kwargs)
        async with (
            Aiogoogle(service_account_creds=creds) as aiogoogle,
            AsyncScheduler() as scheduler,
            create_pool(getenv("POSTGRES_POOL_URI"), init=init_connection) as pool,
            CustomBot(
                scheduler=scheduler,
                pool=pool,
                logger=logger,
                owner_id=678374009045254198,
                command_prefix=when_mentioned_or("?"),
                description="This is Vioshim's bot",
                command_attrs=dict(hidden=True),
                case_insensitive=True,
                help_command=CustomHelp(),
                aiogoogle=aiogoogle,
            ) as bot,
        ):
            await bot.login(getenv("DISCORD_TOKEN"))
            await bot.connect(reconnect=True)
    except Exception as e:
        logger.critical("An exception occurred while trying to connect.", exc_info=e)


if __name__ == "__main__":
    run(main())
