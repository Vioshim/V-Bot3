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
from contextlib import suppress
from functools import wraps
from logging import getLogger, setLoggerClass
from os import getenv
from pathlib import Path

from apscheduler.schedulers.async_ import AsyncScheduler
from asyncpg import Pool, create_pool
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv

from src.structures.bot import CustomBot
from src.structures.help import CustomHelp
from src.structures.logger import ColoredLogger

with suppress(ModuleNotFoundError):
    from asyncio import set_event_loop_policy

    from uvloop import EventLoopPolicy  # type: ignore

    set_event_loop_policy(EventLoopPolicy())


setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

load_dotenv()


def wrap_session(func):
    """Bot wrapper, this allows the bot to start up
    its asynchronous methods

    Parameters
    ----------
    func : Callable[ [Pool, ClientSession, AsyncScheduler], Coroutine[Any, Any, None] ]
        Main function with the following parameters

    Returns
    -------
    Callable[[], Coroutine[Any, Any, None]]
        Bot instance caller
    """

    @wraps(func)
    async def wrapper() -> None:
        """Function Wrapper"""
        async with AsyncScheduler() as scheduler:
            async with create_pool(getenv("POSTGRES_POOL_URI")) as pool:
                await func(pool=pool, scheduler=scheduler)

    return wrapper


@wrap_session
async def main(pool: Pool, scheduler: AsyncScheduler) -> None:
    """Main Execution function

    Parameters
    ----------
    pool : Pool
        asyncpg's database pool
    scheduler : AsyncScheduler
        scheduler
    """
    try:
        bot = CustomBot(
            scheduler=scheduler,
            pool=pool,
            logger=logger,
            debug_guild=719343092963999804,
            owner_id=678374009045254198,
            command_prefix=when_mentioned_or("?"),
            description="This is Vioshim's bot",
            command_attrs=dict(hidden=True),
            case_insensitive=True,
            help_command=CustomHelp(),
        )
        bot.load_extension("jishaku")
        path = Path("src/cogs")
        path.resolve()
        for cog in path.glob("*/cog.py"):
            item = (
                str(cog)
                .removesuffix(".py")
                .replace("\\", ".")
                .replace("/", ".")
            )
            bot.load_extension(item)
            logger.info("Successfully loaded %s", item)
        await bot.login(getenv("DISCORD_TOKEN"))
        await bot.connect()
    except Exception as e:
        logger.critical(
            "An exception occurred while trying to connect", exc_info=e
        )


if __name__ == "__main__":
    run(main())
