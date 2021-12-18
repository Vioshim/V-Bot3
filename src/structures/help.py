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

from typing import TYPE_CHECKING, Any, Callable, Mapping

from discord import SlashCommand

if TYPE_CHECKING:
    from discord.ext.commands import Command, Group, Cog, Context

from discord.ext.commands import HelpCommand

from src.pagination.simple import Simple


class CustomHelp(HelpCommand):
    async def send_bot_help(self, mapping: Mapping[Cog, list[Command]]) -> None:
        """Bot Help

        Parameters
        ----------
        mapping : Mapping[Cog, list[Command]]
            Mapping of all Cogs and commands
        """

        def mapping_parser(item: tuple[Cog, list[Command]]) -> tuple[str, str]:
            """Parsing Method

            Parameters
            ----------
            item : tuple[Cog, list[Command]]
                Parsing Values

            Returns
            -------
            tuple[str, str]
                title, description values
            """
            cog, commands = item
            cog_name = getattr(cog, "qualified_name", "No category")
            signatures = []
            for item in commands:
                if not isinstance(item, SlashCommand):
                    signatures.append(self.get_command_signature(item))
            text_signatures = "n".join(signatures) or "No Commands"
            return cog_name, text_signatures

        target = self.get_destination()

        view = Simple(
            bot=self.context.bot,
            timeout=None,
            member=self.context.author,
            target=target,
            values=mapping.items(),
            title="Help Command - Bot Options",
            parser=mapping_parser,
        )
        await view.send()

    async def send_command_help(self, cmd: Command) -> None:
        """Command Help

        Parameters
        ----------
        cmd : Command
            Command
        """

        values = {
            "Short document": cmd.short_doc or "None",
            "Aliases": "\n".join(f"> • {item}" for item in cmd.aliases) or "None",
            "Cog": getattr(cmd.cog, "qualified_name", None) or "None",
            "Usage": self.get_command_signature(cmd) or "None",
        }

        target = self.get_destination()

        view = Simple(
            bot=self.context.bot,
            timeout=None,
            target=target,
            title=f"Command {cmd.qualified_name!r}",
            member=self.context.author,
            description=cmd.description,
            values=values,
            inline=False,
        )

        await view.send()

    async def send_group_help(self, group: Group) -> None:
        """Group help

        Parameters
        ----------
        group: Group
            Group
        """
        aliases = "\n".join(f"> • {item}" for item in group.aliases) or "None"
        text = f"__**Short Document**__\n> {group.short_doc}\n\n" f"__**Aliases**__\n{aliases}"

        def group_parser(cmd: Command):
            return self.get_command_signature(cmd), f"\n> {cmd.short_doc}"

        target = self.get_destination()

        view = Simple(
            bot=self.context.bot,
            timeout=None,
            target=target,
            title=f"Group {group.qualified_name!r}",
            member=self.context.author,
            description=text,
            values=group.commands,
            parser=group_parser,
            inline=False,
        )

        await view.send()

    async def send_cog_help(self, cog: Cog) -> None:
        """Cog help

        Parameters
        ----------
        cog: Cog
            Cog
        """

        def cog_parser(item: tuple[str, Callable[[Any], Any]]) -> tuple[str, str]:
            """Parser for cogs

            Attributes
            ----------
            item:
                Element to check, which is a pair of name and callable listener

            Returns
            -------
            tuple[str, str]
                Value and short description
            """
            name, func = item
            if short_doc := func.__doc__:
                if len(split := short_doc.split("\n", 1)) == 2:
                    entry, _ = split
                    return name, f"> {entry}"
                return name, "\n".join(split)
            return name, "> Not Documented"

        # noinspection PyUnresolvedReferences
        commands = [f"> • {item.name}" for item in cog.get_commands()]

        commands.sort()

        description = "\n".join(commands) or "> No Commands"

        target = self.get_destination()

        view = Simple(
            bot=self.context.bot,
            timeout=None,
            target=target,
            title=f"Cog {cog.qualified_name} - Commands",
            description=description,
            member=self.context.author,
            values=cog.get_listeners(),
            parser=cog_parser,
            inline=False,
        )

        await view.send()

    async def send_error_message(self, error: str):
        """Error sending function

        Parameters
        ----------
        error: str
            Error in the message
        """
        context = self.context
        guild = context.bot.get_guild(719343092963999804)
        member = guild.get_member(context.author.id)
        target = self.get_destination()

        view = Simple(
            bot=self.context.bot,
            timeout=None,
            target=target,
            member=member,
            title="Help Error",
            description=f"> {error}",
        )
        await view.send()

    async def on_help_command_error(self, ctx: Context, error: Exception):
        """Error detection

        Parameters
        ----------
        ctx: Context
            Context
        error: Exception
            Exception that occurred
        """
        ctx.bot.logger.exception("Help Command > %s > %s", ctx.author, error, exc_info=error)
