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


from __future__ import annotations

import asyncio
from logging import getLogger, setLoggerClass
from os import getenv

from aiogoogle import Aiogoogle
from aiogoogle.auth.creds import ServiceAccountCreds
from apscheduler.schedulers.async_ import AsyncScheduler
from discord import Streaming
from discord.ext.commands import when_mentioned_or
from dotenv import load_dotenv
from orjson import loads

from src.structures.bot import CustomBot
from src.structures.logger import ColoredLogger

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

load_dotenv()


async def main() -> None:
    """Main Execution function"""
    try:
        google_kwargs = loads(open("service-account-key.json", "r").read())
        creds = ServiceAccountCreds(
            **google_kwargs,
            scopes=[
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/drive",
                "https://www.googleapis.com/auth/spreadsheets.readonly",
            ],
        )
        async with (
            Aiogoogle(service_account_creds=creds) as aiogoogle,
            AsyncScheduler() as scheduler,
            CustomBot(
                activity=Streaming(name="Support V-Bot!", url="https://ko-fi.com/Vioshim"),
                scheduler=scheduler,
                logger=logger,
                owner_id=678374009045254198,
                command_prefix=when_mentioned_or("?"),
                description="This is Vioshim's bot",
                command_attrs=dict(hidden=True),
                case_insensitive=True,
                help_command=None,
                aiogoogle=aiogoogle,
            ) as bot,
        ):
            await bot.login(getenv("DISCORD_TOKEN", ""))
            await bot.connect(reconnect=True)
    except Exception as e:
        logger.critical("An exception occurred while trying to connect.", exc_info=e)


if __name__ == "__main__":
    try:
        import uvloop  # type: ignore

        loop_factory = uvloop.new_event_loop
    except ModuleNotFoundError:
        loop_factory = None
        logger.error("Not using uvloop")

    with asyncio.Runner(loop_factory=loop_factory) as runner:
        runner.run(main())
