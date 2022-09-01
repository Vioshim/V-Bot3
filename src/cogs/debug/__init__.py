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


from io import BytesIO
from typing import Optional

from discord import AllowedMentions, Embed, File, Message, Webhook
from discord.ext import commands
from discord.utils import (
    MISSING,
    as_chunks,
    escape_markdown,
    escape_mentions,
    find,
    format_dt,
    get,
    oauth_url,
    remove_markdown,
    sleep_until,
    snowflake_time,
    time_snowflake,
    utcnow,
)
from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReplResponseReactor
from jishaku.features.baseclass import Feature
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator, use_file_check
from jishaku.repl import AsyncCodeExecutor, Scope
from jishaku.repl.repl_builtins import (
    http_get_bytes,
    http_get_json,
    http_post_bytes,
    http_post_json,
)

from src.structures.bot import CustomBot

DEFAULT = {
    "oauth_url": oauth_url,
    "snowflake_time": snowflake_time,
    "time_snowflake": time_snowflake,
    "find": find,
    "get": get,
    "sleep_until": sleep_until,
    "utcnow": utcnow,
    "remove_markdown": remove_markdown,
    "escape_markdown": escape_markdown,
    "escape_mentions": escape_mentions,
    "as_chunks": as_chunks,
    "format_dt": format_dt,
    "MISSING": MISSING,
    "http_get_bytes": http_get_bytes,
    "http_get_json": http_get_json,
    "http_post_bytes": http_post_bytes,
    "http_post_json": http_post_json,
}


def generate_dict(ctx: commands.Context):
    webhook: Optional[Webhook] = ctx.bot.webhook_lazy(ctx.channel)
    return DEFAULT | {
        "message": ctx.message,
        "msg": ctx.message,
        "author": ctx.author,
        "bot": ctx.bot,
        "channel": ctx.channel,
        "ctx": ctx,
        "guild": ctx.guild,
        "me": ctx.me,
        "webhook": webhook,
    }


class Debug(Feature):
    def __init__(self, *args, **kwargs):
        super(Debug, self).__init__(*args, **kwargs)
        self._scope = Scope()
        self.retain = False
        self.last_result = None

    @property
    def scope(self):
        """
        Gets a scope for use in REPL.

        If retention is on, this is the internal stored scope,
        otherwise it is always a new Scope.
        """

        if self.retain:
            return self._scope
        return Scope()

    @Feature.Command(name="retain")
    async def retain(self, ctx: commands.Context, *, toggle: bool = None):
        """
        Turn variable retention for REPL on or off.

        Provide no argument for current status.
        """

        if toggle is None:
            if self.retain:
                return await ctx.send("Variable retention is set to ON.")

            return await ctx.send("Variable retention is set to OFF.")

        if toggle:
            if self.retain:
                return await ctx.send("Variable retention is already set to ON.")

            self.retain = True
            self._scope = Scope()
            return await ctx.send("Variable retention is ON. Future REPL sessions will retain their scope.")

        if not self.retain:
            return await ctx.send("Variable retention is already set to OFF.")

        self.retain = False
        return await ctx.send("Variable retention is OFF. Future REPL sessions will dispose their scope when done.")

    async def python_result_handling(self, ctx: commands.Context, result):
        """
        Determines what is done with a result when it comes out of jsk py.
        This allows you to override how this is done without having to rewrite the command itself.
        What you return is what gets stored in the temporary _ variable.
        """

        if isinstance(result, Message):
            return await ctx.send(f"<Message <{result.jump_url}>>")

        if isinstance(result, File):
            return await ctx.send(file=result)

        if isinstance(result, Embed):
            return await ctx.send(embed=result)

        if isinstance(result, PaginatorInterface):
            return await result.send_to(ctx)

        if not isinstance(result, str):
            # repr all non-strings
            result = repr(result)

        # Eventually the below handling should probably be put somewhere else
        if len(result) <= 2000:
            if result.strip() == "":
                result = "\u200b"

            return await ctx.send(
                result.replace(self.bot.http.token, "[token omitted]"),
                allowed_mentions=AllowedMentions.none(),
            )

        if use_file_check(ctx, len(result)):  # File "full content" preview limit
            # Discord's desktop and web client now supports an interactive file content
            #  display for files encoded in UTF-8.
            # Since this avoids escape issues and is more intuitive than pagination for
            #  long results, it will now be prioritized over PaginatorInterface if the
            #  resultant content is below the filesize threshold
            return await ctx.send(file=File(filename="output.py", fp=BytesIO(result.encode("utf-8"))))

        # inconsistency here, results get wrapped in codeblocks when they are too large
        #  but don't if they're not. probably not that bad, but noting for later review
        paginator = WrappedPaginator(prefix="```py", suffix="```", max_size=1980)
        paginator.add_line(result)
        interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
        return await interface.send_to(ctx)

    @Feature.listener()
    async def on_message(self, message: Message):
        if not await self.bot.is_owner(message.author):
            return
        if not message.content:
            return

        argument = codeblock_converter(message.content)
        if argument.language != "py":
            return

        ctx = await self.bot.get_context(message)

        arg_dict = generate_dict(ctx)
        arg_dict["_"] = self.last_result
        scope = self.scope

        try:
            async with ReplResponseReactor(ctx.message):
                with self.submit(ctx):
                    executor = AsyncCodeExecutor(argument.content, scope, arg_dict=arg_dict)
                    async for send, result in AsyncSender(executor):
                        if result is None:
                            continue

                        self.last_result = result

                        send(await self.python_result_handling(ctx, result))

        finally:
            scope.clear_intersection(arg_dict)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Debug(bot=bot))
