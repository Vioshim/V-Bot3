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


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from discord import Color, Embed, Interaction, Member, TextChannel, User
from discord.app_commands import Command as SlashCommand
from discord.app_commands import ContextMenu
from discord.app_commands import Group as SlashGroup
from discord.ext.commands import Cog, Command, Context, Group, HelpCommand
from discord.ui import Button, Select, button, select

from src.pagination.complex import Complex
from src.pagination.simple import SimplePaged
from src.pagination.view_base import BasicStop
from src.utils.etc import WHITE_BAR

__all__ = ("CustomHelp",)


@dataclass(unsafe_hash=True)
class Listener:
    name: str
    func: Callable[..., Any]

    @property
    def short_doc(self):
        if short_doc := self.__doc__:
            return short_doc.split("\n", 1)[0]
        return "Not Documented"


def parser(x: Listener | Command | Group | SlashCommand | ContextMenu | SlashGroup | Cog):
    if isinstance(x, Listener):
        return x.name, x.short_doc
    if isinstance(x, Cog):
        return x.qualified_name, x.description
    if isinstance(x, (Command, Group)):
        return x.name, x.short_doc
    if isinstance(x, (SlashCommand, SlashGroup)):
        return x.name, x.description
    if isinstance(x, ContextMenu):
        return x.name, x.callback.__doc__


def emoji_parser(x: Listener | Command | Group | SlashCommand | ContextMenu | SlashGroup | Cog):
    if isinstance(x, Listener):
        return "\N{NUT AND BOLT}"
    if isinstance(x, Cog):
        return "\N{GEAR}"
    if isinstance(x, (Group, SlashGroup)):
        return "\N{BLUE BOOK}"
    if isinstance(x, (Command, SlashCommand)):
        return "\N{PAGE FACING UP}"
    if isinstance(x, ContextMenu):
        return "\N{WRENCH}"


class HelpExploration(Complex[Cog | Command | Group | SlashCommand | SlashGroup | Listener]):
    def __init__(
        self,
        *,
        target: TextChannel,
        member: Member | User,
        value: Mapping[Cog, list[Command]] | Group | Cog,
    ):
        title, items, parent = self.flatten(value)
        super().__init__(
            target=target,
            member=member,
            timeout=None,
            values=items,
            parser=parser,
            emoji_parser=emoji_parser,
            keep_working=True,
        )
        self.parent = parent
        self.embed.title = title
        self.parent_button.disabled = parent is None

    @staticmethod
    def flatten(value: Mapping[Cog, list[Command]] | Group | Cog):
        if isinstance(value, Cog):
            items = [Listener(x, y) for x, y in value.get_listeners()]
            items.extend(value.get_app_commands())
            items.extend(value.get_commands())
            return f"Cog {value.qualified_name}", items, None

        if isinstance(value, Group):
            return f"Group {value.qualified_name}", [*value.commands], value.cog

        items = sorted(value.keys(), key=lambda x: x.qualified_name)
        return "All Cogs", items, None

    async def selection(
        self,
        interaction: Interaction,
        value: Listener | Command | Group | SlashCommand | ContextMenu | SlashGroup | Cog,
    ):
        self.embed.title, self.values, self.parent = self.flatten(value)
        if isinstance(value, Listener):
            self.embed.title = value.name
            self.embed.description = value.short_doc
        await self.edit(interaction=interaction, page=0)

    @select(row=1, placeholder="Select the elements", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        await self.selection(interaction, self.current_choice)

    @button(label="Parent", custom_id="parent", row=4)
    async def parent_button(self, interaction: Interaction, btn: Button):
        btn.disabled = True
        await self.selection(interaction, self.parent)


class CustomHelp(HelpCommand):
    async def send_bot_help(self, mapping: Mapping[Cog, list[Command]], /) -> None:
        """Bot Help (Cog Select)

        Parameters
        ----------
        mapping : Mapping[Cog, list[Command]]
            Mapping of all Cogs and commands
        """

        target = self.get_destination()

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
            cog_name = getattr(cog, "qualified_name", "No Category")
            commands = filter(lambda x: isinstance(x, Command), commands)
            commands = map(self.get_command_signature, commands)
            text_signatures = "\n".join(commands) or "No Commands"
            return cog_name, text_signatures

        view = SimplePaged(
            timeout=None,
            member=self.context.author,
            target=target,
            values=mapping.items(),
            entries_per_page=10,
            parser=mapping_parser,
        )
        await view.send(title="Help Command - Bot Options")

    async def send_command_help(self, cmd: Command, /) -> None:
        """Command Help

        Parameters
        ----------
        cmd : Command
            Command
        """
        target = self.get_destination()

        view = BasicStop(
            target=target,
            timeout=None,
            member=self.context.author,
        )
        embed = view.embed

        entries = {
            "Description": cmd.description,
            "Short document": cmd.short_doc,
            "Cog": cmd.cog_name,
            "Usage": cmd.usage,
            "Aliases": ", ".join(getattr(cmd, "aliases", [])),
        }

        if data := "\n".join(f"{k}: {v}" for k, v in entries.items() if v):
            embed.description = f"```yaml\n{data}\n```"

        for k, v in cmd.clean_params.items():
            embed.add_field(name=k.title(), value=str(v), inline=False)

        await view.send(
            title=f"Command {cmd.qualified_name!r}",
            desciption=cmd.description,
        )

    async def send_group_help(self, group: Group, /) -> None:
        """Group help

        Parameters
        ----------
        group: Group
            Group
        """

        entries = {
            "Description": group.description,
            "Short document": group.short_doc,
            "Cog": group.cog_name,
            "Usage": group.usage,
            "Aliases": ", ".join(getattr(group, "aliases", [])),
        }

        if description := "\n".join(f"{k}: {v}" for k, v in entries.items() if v):
            description = f"```yaml\n{description}\n```"

        view = Complex[Command](
            member=self.context.author,
            values=group.commands,
            target=self.get_destination(),
            timeout=None,
            parser=lambda x: (x.name, x.short_doc),
            emoji_parser=lambda x: "\N{BLACK SQUARE BUTTON}" if x.parent else "\N{BLACK LARGE SQUARE}",
            silent_mode=True,
            auto_text_component=True,
        )

        async with view.send(
            title=f"Group {group.qualified_name!r}",
            description=description,
            single=True,
        ) as cmd:
            if isinstance(cmd, Command):
                await self.send_command_help(cmd)

    async def send_cogs_help(self, cog: Cog, /) -> None:
        """Cog help

        Parameters
        ----------
        cog: Cog
            Cog
        """
        commands = sorted(f"> • {item.name}" for item in cog.get_commands())

        target = self.get_destination()

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

        view = SimplePaged(
            timeout=None,
            target=target,
            member=self.context.author,
            values=cog.get_listeners(),
            inline=False,
            entries_per_page=10,
            parser=cog_parser,
        )
        await view.send(
            title=f"Cog {cog.qualified_name} - Commands",
            description="\n".join(commands) or "> No Commands",
        )

    async def send_error_message(self, error: str, /):
        """Error sending function

        Parameters
        ----------
        error: str
            Error in the message
        """
        context = self.context
        embed = Embed(title="Help Error", description=error, color=Color.red())
        embed.set_image(url=WHITE_BAR)
        await context.reply(embed=embed)

    async def on_help_command_error(self, ctx: Context, error: Exception, /):
        """Error detection

        Parameters
        ----------
        ctx: Context
            Context
        error: Exception
            Exception that occurred
        """
        ctx.bot.logger.exception("Help Command > %s > %s", str(ctx.author), error, exc_info=error)
