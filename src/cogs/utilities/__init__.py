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


import os
import random
import re
from typing import Literal, Optional

import d20
from discord import (
    Attachment,
    Color,
    DiscordException,
    Embed,
    File,
    ForumChannel,
    HTTPException,
    Interaction,
    InteractionResponse,
    Message,
    Object,
    TextChannel,
    TextStyle,
    Thread,
    VoiceChannel,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View
from discord.utils import MISSING
from yarl import URL

from src.cogs.utilities.sphinx_reader import SphinxObjectFileReader, to_string
from src.structures.bot import CustomBot
from src.structures.move import Move
from src.utils.etc import WHITE_BAR, RTFMPages

LMGT_URL = URL("https://letmegooglethat.com/")


class ForumModal(Modal):
    def __init__(
        self,
        channel: ForumChannel | TextChannel | Message,
        file: Optional[File] = None,
    ) -> None:
        super(ForumModal, self).__init__(title="Forum management")
        self.name = TextInput(
            label="Name",
            max_length=100,
            default=channel.channel.name if isinstance(channel, Message) else getattr(channel, "name", None),
        )
        self.description = TextInput(
            label="Content",
            style=TextStyle.paragraph,
            max_length=2000,
            default=getattr(channel, "content", getattr(channel, "topic", None)),
            required=False,
        )
        self.add_item(self.name)
        self.add_item(self.description)

        self.channel = channel
        self.file = file

    async def on_error(self, interaction: Interaction[CustomBot], error: Exception, /) -> None:
        interaction.client.logger.error("Ignoring exception in modal %r:", self, exc_info=error)

    async def on_submit(self, itx: Interaction[CustomBot], /) -> None:
        view = View(timeout=None)
        if isinstance(msg := self.channel, Message):
            try:
                await msg.edit(
                    content=self.description.value,
                    attachments=[self.file] if self.file else MISSING,
                )
                if msg.channel.name != self.name.value:
                    await msg.channel.edit(name=self.name.value)
                view.add_item(Button(label="Jump URL", url=msg.jump_url))
            except DiscordException:
                await itx.response.send_message("Unable to modify it.", ephemeral=True)
            else:
                await itx.response.send_message("Modified Message", ephemeral=True, view=view)
        else:
            if isinstance(self.channel, TextChannel):
                data = await self.channel.create_thread(name=self.name.value)
                message = await data.send(content=self.description.value)
            else:
                data = await self.channel.create_thread(
                    name=self.name.value,
                    content=self.description.value,
                    file=self.file or MISSING,
                )
                message = data.message
            await message.pin()
            view.add_item(Button(label="Jump URL", url=message.jump_url))
            await itx.response.send_message("Added Forum thread", ephemeral=True, view=view)


class RollFlags(commands.FlagConverter, prefix="--", delimiter=" "):
    expression: str = commands.flag(default="d20", positional=True)
    ephemeral: bool = True


class Utilities(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self._rtfm_cache: dict[str, dict[str, str]] = {}

    @staticmethod
    def finder(text, collection, *, key=None, lazy=True):
        suggestions = []
        text = str(text)
        pat = ".*?".join(map(re.escape, text))
        regex = re.compile(pat, flags=re.IGNORECASE)

        for item in collection:
            to_search = key(item) if key else item
            if r := regex.search(to_search):
                suggestions.append((len(r.group()), r.start(), item))

        def sort_key(tup):
            return (tup[0], tup[1], key(tup[2])) if key else tup

        gen = (z for _, _, z in sorted(suggestions, key=sort_key))
        return gen if lazy else list(gen)

    @staticmethod
    def parse_object_inv(stream: SphinxObjectFileReader, url: str):
        result: dict[str, str] = {}

        inv_version = stream.readline().rstrip()

        if inv_version != "# Sphinx inventory version 2":
            raise RuntimeError("Invalid objects.inv file version.")

        stream.readline().rstrip()[11:]
        stream.readline().rstrip()[11:]

        line = stream.readline()
        if "zlib" not in line:
            raise RuntimeError("Invalid objects.inv file, not z-lib compatible.")

        entry_regex = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
        for line in stream.read_compressed_lines():
            match = entry_regex.match(line.rstrip())
            if not match:
                continue

            name, directive, _, location, dispname = match.groups()
            domain, _, subdirective = directive.partition(":")
            if directive == "py:module" and name in result:
                continue

            if directive == "std:doc":
                subdirective = "label"

            if location.endswith("$"):
                location = location[:-1] + name

            key = name if dispname == "-" else dispname
            prefix = f"{subdirective}:" if domain == "std" else ""

            result[f"{prefix}{key}"] = os.path.join(url, location)

        return result

    async def build_rtfm_lookup_table(self):
        cache = {}
        for item in RTFMPages:
            async with self.bot.session.get(f"{item.value}/objects.inv") as resp:
                if resp.status != 200:
                    raise RuntimeError("Cannot build rtfm lookup table, try again later.")

                stream = SphinxObjectFileReader(await resp.read())
                cache[item.name] = self.parse_object_inv(stream, item.value)

        self._rtfm_cache = cache

    async def do_rtfm(self, ctx: Interaction[CustomBot], key: RTFMPages, obj: Optional[str]):
        if obj is None:
            return await ctx.followup.send(key.value)

        if not self._rtfm_cache:
            await self.build_rtfm_lookup_table()

        cache = list(self._rtfm_cache[key].items())

        matches = self.finder(obj, cache, key=lambda t: t[0], lazy=False)
        if text := "\n".join(f"[`{key}`]({url})" for key, url in matches[:8]):
            await ctx.followup.send(text, ephemeral=True)
        else:
            await ctx.followup.send("Could not find anything. Sorry.", ephemeral=True)

    @commands.command()
    @commands.guild_only()
    async def sync(
        self,
        ctx: commands.Context,
        guilds: commands.Greedy[Object],
        spec: Optional[Literal["~", "*", "^"]] = None,
    ) -> None:
        if guilds:
            ret = 0
            for guild in guilds:
                try:
                    await self.bot.tree.sync(guild=guild)
                except HTTPException:
                    pass
                else:
                    ret += 1

            return await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

        match spec:
            case "~":
                synced = await self.bot.tree.sync(guild=ctx.guild)
            case "*":
                self.bot.tree.copy_global_to(guild=ctx.guild)
                synced = await self.bot.tree.sync(guild=ctx.guild)
            case "^":
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                synced = []
            case _:
                synced = await self.bot.tree.sync()

        word = "globally" if spec is None else "to the current guild."
        await ctx.send(f"Synced {len(synced)} commands {word}")

    @commands.command()
    async def charinfo(self, ctx: commands.Context, *, characters: str):
        """Shows you information about a number of characters.
        Only up to 25 characters at a time.
        """
        embed = Embed(
            title="Character Information",
            description="\n".join(map(to_string, characters)),
            color=Color.blurple(),
        )
        embed.set_image(url=WHITE_BAR)
        if len(embed.description) > 4096:
            embed.description = "Output too long to display."
            embed.color = Color.red()

        await ctx.send(embed=embed)

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def rtfm(self, ctx: Interaction[CustomBot], key: Optional[RTFMPages], query: Optional[str]):
        """Executes a manual query

        Parameters
        ----------
        ctx : Interaction
            Interaction
        key : Optional[RTFMPages]
            Website
        query : Optional[str]
            Query to look for
        """
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        await self.do_rtfm(ctx, key or RTFMPages.Discord, query)

    @app_commands.command()
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def forum(
        self,
        ctx: Interaction[CustomBot],
        forum: Optional[ForumChannel | Thread] = None,
        image: Optional[Attachment] = None,
    ):
        """Post Forums or Edit

        Parameters
        ----------
        ctx : Interaction
            Interaction
        forum : Optional[ForumChannel  |  Thread], optional
            Forum to manage, by default current
        image : Optional[Attachment], optional
            Image to attach, by default None
        """
        forum = forum or ctx.channel
        if isinstance(forum, VoiceChannel) or forum is None:
            name = forum.mention if forum else "Channel"
            await ctx.response.send_message(f"{name} can't forum", ephemeral=True)
        else:
            file = await image.to_file() if image else None
            if isinstance(forum, Thread):
                forum = await forum.get_partial_message(forum.id).fetch()
            modal = ForumModal(channel=forum, file=file)
            await ctx.response.send_modal(modal)

    @app_commands.command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def metronome(self, ctx: Interaction[CustomBot], valid: bool = True, hidden: bool = False):
        """Allows to use Metronome

        Parameters
        ----------
        ctx : Interaction
            Interaction
        valid : bool, optional
            Valid metronome, by default True
        hidden : bool, optional
            if hidden, by default False
        """
        resp: InteractionResponse = ctx.response
        item = random.choice([x for x in Move.all(banned=False, shadow=False) if not valid or x.metronome])
        await resp.send_message(content=f"Canon Metronome: {valid}", embed=item.embed, ephemeral=hidden)

    @commands.command()
    async def google(self, ctx: commands.Context, *, text: str):
        """Let me google that, as command

        Parameters
        ----------
        ctx : commands.Context
            Context
        text : str
            Query
        """
        url = LMGT_URL.with_query(q=text)
        if ctx.message.reference and isinstance(ctx.message.reference.resolved, Message):
            message = ctx.message.reference.resolved
        else:
            message = ctx.message
        await message.reply(content=str(url))

    @commands.hybrid_command()
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def roll(self, ctx: commands.Context[CustomBot], *, flags: RollFlags):
        """Allows to roll dice based on 20

        Parameters
        ----------
        ctx : Context
            Context
        expression : str
            Expression (Example: d20)
        ephemeral : bool
            Shows to only you, by default True
        """
        await ctx.defer(ephemeral=flags.ephemeral)

        embed = Embed(
            title=f"Rolling: {flags.expression}",
            color=Color.blurple(),
            timestamp=ctx.message.created_at,
        )

        if embed.title and len(embed.title) > 256:
            embed.title = "Rolling Expression"

        embed.set_image(url=WHITE_BAR)

        if guild := ctx.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon)

        try:
            value = d20.roll(expr=flags.expression, allow_comments=True)
            if len(value.result) > 4096:
                d20.utils.simplify_expr(value.expr)
            embed.description = value.result
            embed.set_thumbnail(url=f"https://dummyimage.com/512x512/FFFFFF/000000&text={value.total}")
        except Exception as e:
            embed.description = "Invalid expression."
            self.bot.logger.exception("Error while rolling dice.", exc_info=e)
        finally:
            await ctx.reply(embed=embed)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Utilities(bot))
