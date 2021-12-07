#  Copyright 2021 Vioshim
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


from asyncio import run
from functools import wraps
from os import getenv
from typing import Any, Callable, Coroutine

from aiohttp.client_exceptions import ClientConnectionError
from apscheduler.schedulers.async_ import AsyncScheduler
from asyncpg import Pool, create_pool
from discord import AllowedMentions, Intents, LoginFailure
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv

from src.structures.bot import CustomBot
from src.structures.help import CustomHelp

try:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from uvloop import install

    install()
except ModuleNotFoundError:
    print("Unable to use uvloop in Windows")
finally:
    load_dotenv()


def wrap_session(
        func: Callable[..., Coroutine[Any, Any, None]]
) -> Callable[[], Coroutine[Any, Any, None]]:
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


__all__ = (
    "COGS",
    "PREFIX",
)

PREFIX = "%"
INTENTS = Intents.all()
MENTIONS = AllowedMentions(
    users=False,
    roles=False,
    everyone=False,
    replied_user=True,
)

COGS = []


@wrap_session
async def main(
        pool: Pool, scheduler: AsyncScheduler
) -> None:  # , scheduler: AsyncScheduler) -> None:
    """Main Execution function

    Parameters
    ----------
    pool : Pool
        asyncpg's database pool
    scheduler : AsyncScheduler
        scheduler
    """
    bot = CustomBot(
        pool=pool,
        command_prefix=when_mentioned_or(PREFIX),
        scheduler=scheduler,
        description="This is Vioshim's bot",
        command_attrs=dict(hidden=True),
        case_insensitive=True,
        help_command=CustomHelp(),
        owner_ids={678374009045254198},
        allowed_mentions=MENTIONS,
        intents=INTENTS,
    )
    try:
        bot.load_extension("jishaku")
        for cog in COGS:
            bot.load_extension(f"cogs.{cog}")
            bot.logger.info("Successfully loaded %s", cog)
        await bot.start(getenv("DISCORD_TOKEN"))
    except LoginFailure as e:
        bot.logger.critical(msg="Login failed. The discord token is invalid.", exc_info=e)
    except SystemExit as e:
        bot.logger.critical(msg="Bot has been interrupted by system", exc_info=e)
    except KeyboardInterrupt as e:
        bot.logger.critical(msg="Bot has been interrupted by the user", exc_info=e)
    except ClientConnectionError as e:
        bot.logger.critical(msg="Unable to connect to discord.", exc_info=e)
    except AttributeError as e:
        bot.logger.critical(msg="Bot had issues when reading the cogs.", exc_info=e)
    except Exception as e:
        bot.logger.critical(msg="An exception occurred while trying to connect", exc_info=e)


if __name__ == "__main__":
    run(main())
