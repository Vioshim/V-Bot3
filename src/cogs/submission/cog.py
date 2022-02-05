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

from asyncio import ALL_COMPLETED, TimeoutError, to_thread, wait
from contextlib import suppress
from datetime import datetime, timedelta
from difflib import get_close_matches
from itertools import chain
from pathlib import Path
from typing import Any, Optional, Type, Union

from aiofiles import open as aiopen
from apscheduler.enums import ConflictPolicy
from apscheduler.triggers.interval import IntervalTrigger
from asyncpg import Connection
from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    Guild,
    HTTPException,
    Interaction,
    Member,
    Message,
    Option,
    OptionChoice,
    RawMessageDeleteEvent,
    RawThreadDeleteEvent,
    Status,
    TextChannel,
    Thread,
    User,
    WebhookMessage,
)
from discord.commands import has_role, message_command, slash_command, user_command
from discord.ext.commands import Cog
from discord.ui import Button, View
from discord.utils import utcnow
from docx import Document
from docx.document import Document as DocumentType
from jishaku.codeblocks import codeblock_converter
from orjson import loads
from yaml import safe_load
from yaml.error import MarkedYAMLError

from src.context import ApplicationContext, AutocompleteContext
from src.pagination.boolean import BooleanView
from src.pagination.complex import ComplexInput
from src.pagination.text_input import TextInput
from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot
from src.structures.character import Character, doc_convert, fetch_all, oc_process
from src.structures.mission import Mission
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.species import Fakemon, Fusion, Variant
from src.utils.doc_reader import docs_reader
from src.utils.etc import REGISTERED_IMG, RP_CATEGORIES, WHITE_BAR
from src.utils.functions import yaml_handler
from src.utils.matches import G_DOCUMENT
from src.views import (
    CharactersView,
    ImageView,
    MissionView,
    MoveView,
    PingView,
    RPView,
    StatsView,
    SubmissionView,
)

CLAIM_MESSAGE = """
**。　　　　•　    　ﾟ　　。**
**　　.　　　.　　　.　　。　　   。　.**
** 　.　　      。             。　    .    •**
** •     RP claimable, feel free to use it.　 。　.**
**          Is assumed that everyone left**
**　 　　。　　　　ﾟ　　　.　　　　　.**
**,　　　　.　 .　　       .               。**
"""


def oc_autocomplete(ctx: AutocompleteContext) -> list[OptionChoice]:
    """Method to autocomplete the requested OCs

    Parameters
    ----------
    ctx : AutocompleteContext
        Context

    Returns
    -------
    list[OptionChoice]
        Values
    """
    member_id = int(ctx.options.get("member") or ctx.interaction.user.id)
    cog: Submission = ctx.bot.get_cog("Submission")
    text: str = str(ctx.value or "").title()
    ocs = cog.rpers.get(member_id, {}).values()
    items = {oc.name: str(oc.id) for oc in ocs}
    if data := get_close_matches(word=text, possibilities=items, n=25):
        values = [OptionChoice(item, items[item]) for item in data]
    else:
        values = [
            OptionChoice(oc.name, str(oc.id))
            for oc in ocs
            if oc.name.startswith(text)
        ]

    values.sort(key=lambda x: x.name)

    return values


def message_validator(message: Message):
    """Function used for checking compatiblity between messages

    Parameters
    ----------
    message : Message
        Message to check
    """

    def checker(value: Message) -> bool:
        if value.webhook_id and message.channel == value.channel:
            if message.content:
                return value.content in message.content
            if message.attachments and (
                len(message.attachments) == len(value.attachments)
            ):
                return value.content is None
        return False

    return checker


class Submission(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready: bool = False
        self.missions: set[Mission] = set()
        self.mission_claimers: dict[int, set[int]] = {}
        self.mission_cooldown: dict[int, datetime] = {}
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        self.ocs: dict[int, Character] = {}
        self.rpers: dict[int, dict[int, Character]] = {}
        self.oc_list: dict[int, int] = {}
        self.supporting: dict[Member, Member] = {}

    @message_command(
        guild_ids=[719343092963999804],
        name="Read Moves",
    )
    async def moves_checker(self, ctx: ApplicationContext, message: Message):
        await ctx.defer(ephemeral=True)
        moves = []
        if oc := self.ocs.get(message.id):
            moves = list(oc.moveset.copy())
        elif text := message.content:
            moves = [
                move
                for move in Move.all()
                if move.name in text.title() or move.id in text.upper()
            ]
        if len(moves) == 1:
            view = View()
            view.add_item(
                Button(
                    label="Click here to check more information at Bulbapedia.",
                    url=moves[0].url,
                )
            )
            await ctx.send_followup(
                embed=moves[0].embed,
                ephemeral=True,
                view=view,
            )
        elif moves:
            moves.sort(key=lambda x: x.name)
            view = MoveView(
                bot=self.bot,
                member=ctx.author,
                moves=moves,
                target=ctx.interaction,
                keep_working=True,
            )
            async with view.send(ephemeral=True):
                self.bot.logger.info(
                    "User %s is reading the moves at %s",
                    str(ctx.author),
                    message.jump_url,
                )
        else:
            await ctx.send_followup(
                "This message does not include moves.",
                ephemeral=True,
            )

    @user_command(
        name="Check User's OCs",
        guild_ids=[719343092963999804],
    )
    async def check_ocs(self, ctx: ApplicationContext, member: Member):
        if member is None:
            member: Member = ctx.author
        await ctx.defer(ephemeral=True)
        ocs: list[Character] = list(self.rpers.get(member.id, {}).values())
        if len(ocs) == 1:
            view = PingView(ocs[0], ctx.user.id == ocs[0].author)
            await ctx.send_followup(
                "The user only has one character",
                ephemeral=True,
                embed=ocs[0].embed,
                view=view,
            )
        elif ocs:
            view = CharactersView(
                bot=self.bot,
                member=ctx.author,
                ocs=ocs,
                target=ctx.interaction,
                keep_working=True,
            )
            embed = view.embed
            embed.color = member.color
            embed.set_author(name=member.display_name)
            embed.set_thumbnail(url=member.display_avatar.url)
            async with view.send(ephemeral=True):
                self.bot.logger.info(
                    "User %s is reading the OCs of %s",
                    str(ctx.author),
                    str(member),
                )
        else:
            await ctx.send_followup(
                f"{member.mention} has no characters.", ephemeral=True
            )

    @slash_command(
        guild_ids=[719343092963999804],
        description="Grants registered role to an user",
    )
    @has_role("Moderation")
    async def register(
        self,
        ctx: ApplicationContext,
        member: Option(
            Member,
            description="User to register",
        ),
    ) -> None:
        """Register Command

        Parameters
        ----------
        ctx : Context
            Context
        member : Member
            Member
        """
        guild: Guild = ctx.guild
        role = guild.get_role(719642423327719434)
        author: Member = ctx.author
        await ctx.defer(ephemeral=True)
        if role not in member.roles:
            await member.add_roles(role, reason=f"Registered by {author}")
            embed = Embed(
                description="You can try to use /ping `<role>` for finding a RP. "
                "(<#910914713234325504> also works)",
                colour=member.colour,
                timestamp=utcnow(),
            )
            embed.set_image(url=REGISTERED_IMG)
            embed.set_author(
                name=author.display_name, icon_url=author.avatar.url
            )
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
            files, embed = await self.bot.embed_raw(embed)

            view = View()
            view.add_item(
                Button(
                    label="Maps",
                    url="https://discord.com/channels/719343092963999804/812180282739392522/906430640898056222",
                )
            )
            view.add_item(
                Button(
                    label="Story-lines",
                    url="https://discord.com/channels/719343092963999804/903627523911458816/",
                )
            )

            view.add_item(
                Button(
                    label="RP Planning",
                    url="https://discord.com/channels/719343092963999804/722617383738540092/",
                )
            )

            with suppress(DiscordException):
                await member.send(embed=embed, files=files, view=view)
            await ctx.send_followup("User has been registered", ephemeral=True)
        else:
            await ctx.send_followup(
                "User is already registered", ephemeral=True
            )

    async def unclaiming(
        self,
        channel: Union[TextChannel, int],
    ):
        """This method is used when a channel has been inactivate for 3 days.

        Parameters
        ----------
        channel_id : int
            channel id to use
        """
        if isinstance(channel, int):
            channel: TextChannel = self.bot.get_channel(channel)
        if not self.data_msg.get(channel.id):
            if (msgs := await channel.history(limit=1).flatten()) and msgs[
                0
            ].content == CLAIM_MESSAGE:
                m = msgs[0]
            else:
                m = await channel.send(CLAIM_MESSAGE)
            self.data_msg[channel.id] = m

            async with self.bot.database() as conn:
                for oc in self.ocs.values():
                    if oc.location != channel.id:
                        continue
                    await conn.execute(
                        """--sql
                        UPDATE CHARACTER
                        SET LOCATION = NULL
                        WHERE ID = $1;
                        """,
                        oc.id,
                    )
                    oc.location = None
                    await self.oc_update(oc)

    async def list_update(
        self,
        member: Member | User,
    ):
        """This function updates an user's character list message

        Parameters
        ----------
        member : Member | User
            User to update list
        """
        if not self.ready:
            return
        embed = Embed(
            title="Registered Characters",
            color=member.color,
        )
        webhook = await self.bot.fetch_webhook(919280056558317658)
        if guild := webhook.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        embed.set_author(name=member.display_name)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=WHITE_BAR)
        if oc_list := self.oc_list.get(member.id, None):
            try:
                view = RPView(self.bot, member.id, self.oc_list)
                await webhook.edit_message(oc_list, embed=embed, view=view)
                return
            except DiscordException:
                with suppress(DiscordException):
                    thread = await self.bot.fetch_channel(oc_list)
                    await thread.delete(
                        reason="Former OC List Message was removed."
                    )
        message: WebhookMessage = await webhook.send(
            content=member.mention,
            wait=True,
            embed=embed,
            allowed_mentions=AllowedMentions(users=True),
        )
        thread = await message.create_thread(name=f"OCs⎱{member.id}")
        self.oc_list[member.id] = thread.id
        if isinstance(member, Member):
            await thread.add_user(member)
        view = RPView(self.bot, member.id, self.oc_list)
        await message.edit(view=view)

    async def registration(
        self,
        ctx: Union[Interaction, Message],
        oc: Type[Character],
    ):
        """This is the function which handles the registration process,
        it will try to autocomplete data it can deduce, or ask about what
        can not be deduced.

        Parameters
        ----------
        ctx : Union[Interaction, Message]
            Message that is being interacted with
        oc : Type[Character]
            Character
        """

        member: Member = ctx.guild.get_member(oc.author)

        if not self.ready:
            await ctx.reply(
                "Bot is restarting, please be patient",
                delete_after=5,
            )
            return

        user = ctx.author

        if isinstance(ctx, Message):

            await ctx.reply(
                "Starting submission process",
                delete_after=5,
            )

            if isinstance(species := oc.species, Fakemon):  # type: ignore
                if not oc.url:
                    stats_view = StatsView(
                        bot=self.bot,
                        member=user,
                        target=ctx,
                    )
                    async with stats_view:
                        if not (stats := stats_view.choice):
                            return
                        species.set_stats(*stats.value)
                if (
                    sum(species.stats) > 18
                    or min(species.stats) < 1
                    or max(species.stats) > 5
                ):
                    await ctx.reply(
                        "Max stats is 18. Min 1. Max 5", delete_after=5
                    )
                    return
                if not 1 <= len(species.types) <= 2:
                    view = ComplexInput(
                        bot=self.bot,
                        member=user,
                        target=ctx,
                        values=Typing.all(),
                        max_values=2,
                        timeout=None,
                        parser=lambda x: (
                            str(x),
                            f"Adds the typing {x}",
                        ),
                    )
                    async with view.send(
                        title="Select Typing",
                        description="Press the skip button in case you're going for single type.",
                    ) as types:
                        if not types:
                            return
                        species.types = frozenset(types)
            elif isinstance(species, Fusion):  # type: ignore
                values = species.possible_types
                if not species.types:
                    view = ComplexInput(
                        bot=self.bot,
                        member=user,
                        target=ctx,
                        values=values,
                        max_values=1,
                        timeout=None,
                        parser=lambda x: (
                            "/".join(str(i) for i in x),
                            f"Adds the typing {'/'.join(str(i) for i in x)}",
                        ),
                    )
                    async with view.send(
                        single=True,
                        title="Select Typing",
                    ) as types:
                        if not types:
                            return
                        species.types = frozenset(types)
                elif oc.types not in values:
                    items = ", ".join(
                        "/".join(i.name for i in item) for item in values
                    ).title()
                    await ctx.reply(
                        f"Invalid typing for the fusion, valid types are {items}",
                        delete_after=5,
                    )
                    return

            max_ab = oc.max_amount_abilities
            if not oc.abilities:
                if not isinstance(species, Fakemon) and max_ab == 1:
                    oc.abilities = species.abilities
                else:
                    ability_view = ComplexInput(
                        bot=self.bot,
                        member=user,
                        values=(
                            Ability.all()
                            if oc.any_ability_at_first
                            else oc.species.abilities
                        ),
                        target=ctx,
                        max_values=max_ab,
                    )

                    async with ability_view.send(
                        title=f"Select the Abilities (Max {max_ab})",
                        description="If you press the write button, you can add multiple by adding commas.",
                    ) as abilities:
                        if not abilities:
                            return
                        oc.abilities = frozenset(abilities)
            if len(oc.abilities) > max_ab:
                await ctx.reply(
                    f"Max Amount of Abilities for the current Species is {max_ab}"
                )
                return
            elif not oc.any_ability_at_first and (
                ability_errors := ", ".join(
                    ability.name
                    for ability in oc.abilities
                    if ability not in species.abilities
                )
            ):
                await ctx.reply(
                    f"the abilities [{ability_errors}] were not found in the species"
                )
                return

            text_view = TextInput(bot=self.bot, member=user, target=ctx)

            if not oc.moveset:
                if not (movepool := species.movepool):
                    movepool = Movepool(event=Move.all())

                moves_view = ComplexInput(
                    bot=self.bot,
                    member=user,
                    values=movepool(),
                    timeout=None,
                    target=ctx,
                    max_values=6,
                )

                async with moves_view.send(
                    title="Select the Moves",
                    description="If you press the write button, you can add multiple by adding commas.",
                ) as moves:
                    if not moves:
                        return
                    oc.moveset = frozenset(moves)

            if isinstance(species, (Variant, Fakemon)):
                species.movepool += Movepool(event=oc.moveset)

            if not oc.any_move_at_first:
                moves_movepool = species.movepool()
                if move_errors := ", ".join(
                    move.name
                    for move in oc.moveset
                    if move not in moves_movepool
                ):
                    await ctx.reply(
                        f"the moves [{move_errors}] were not found in the movepool"
                    )
                    return

            if (
                not oc.sp_ability
                and not oc.url
                and oc.can_have_special_abilities
                and len(oc.abilities) == 1
            ):
                bool_view = BooleanView(bot=self.bot, member=user, target=ctx)
                async with bool_view.handle(
                    title="Does the character have an Special Ability?",
                    description=(
                        "Special abilities are basically unique traits that their OC's kind usually can't do, "
                        "it's like being born with an unique power that could have been obtained by different "
                        "reasons, they are known for having pros and cons."
                    ),
                ) as answer:
                    if answer is None:
                        return
                    if answer:
                        data: dict[str, str] = {}
                        for item in SpAbility.__slots__:
                            async with text_view.handle(
                                title=f"Special Ability's {item.title()}",
                                description=(
                                    f"Here you'll define the Special Ability's {item.title()}, "
                                    "make sure it is actually understandable."
                                ),
                                required=True,
                            ) as answer:
                                if not answer:
                                    return
                                data[item] = answer
                        oc.sp_ability = SpAbility(**data)

            if not oc.backstory:
                async with text_view.handle(
                    title="Character's Backstory",
                    description=(
                        "Don't worry about having to write too much, this is just a summary of information "
                        "that people can keep in mind when interacting with your character. You can provide "
                        "information about how they are, information of their past, or anything you'd like to add."
                    ),
                    required=False,
                ) as text:
                    if text is None:
                        return
                    if text:
                        oc.backstory = text

            if not oc.extra:
                async with text_view.handle(
                    title="Character's extra information",
                    description=(
                        "In this area, you can write down information you want people to consider when they are rping with them, "
                        "the information can be from either the character's height, weight, if it uses clothes, if the character likes or dislikes "
                        "or simply just writing down that your character has a goal in specific."
                    ),
                    required=False,
                ) as text:
                    if text is None:
                        return
                    if text:
                        oc.extra = text

            image_view = ImageView(
                bot=self.bot,
                member=user,
                target=ctx,
                default_img=oc.image or oc.default_image,
            )
            async with image_view.send() as image:
                if image is None:
                    return
                oc.image = image
            if received := image_view.received:
                await received.delete(delay=10)

        await self.list_update(member)
        webhook = await self.bot.fetch_webhook(919280056558317658)
        thread_id = self.oc_list[member.id]
        oc.thread = thread_id
        thread: Thread = await self.bot.fetch_channel(thread_id)
        if file := await self.bot.get_file(
            url=oc.generated_image, filename="image"
        ):
            embed: Embed = oc.embed
            embed.set_image(url=f"attachment://{file.filename}")
            msg_oc = await webhook.send(
                content=member.mention,
                embed=embed,
                file=file,
                thread=thread,
                allowed_mentions=AllowedMentions(users=True),
                wait=True,
            )
            oc.id = msg_oc.id
            oc.image = msg_oc.embeds[0].image.url
            self.rpers.setdefault(member.id, {})
            self.rpers[member.id][oc.id] = oc
            self.ocs[oc.id] = oc
            self.bot.logger.info(
                "New character has been registered! > %s > %s > %s",
                str(member),
                repr(oc),
                oc.url or "Manual",
            )
            async with self.bot.database() as conn:
                await oc.update(connection=conn, idx=msg_oc.id)

    async def oc_update(self, oc: Type[Character]):
        webhook = await self.bot.fetch_webhook(919280056558317658)
        embed: Embed = oc.embed
        embed.set_image(url="attachment://image.png")
        thread: Thread = await self.bot.fetch_channel(oc.thread)
        if thread.archived:
            await thread.edit(archived=False)
        await webhook.edit_message(oc.id, embed=embed, thread=thread)

    @slash_command(
        name="ocs",
        guild_ids=[719343092963999804],
        description="Allows to show characters",
    )
    async def get_ocs(
        self,
        ctx: ApplicationContext,
        member: Option(
            Member,
            description="Member, if not provided, it's current user.",
            required=False,
        ),
        character: Option(
            str,
            description="Search by name, directly",
            autocomplete=oc_autocomplete,
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        if member is None:
            member: Member = ctx.author
        if isinstance(member, int):
            try:
                member = await self.bot.fetch_user(member)
            except DiscordException:
                return await ctx.send_followup("User no longer in Discord")
        if (character or "").isdigit() and (oc := self.ocs.get(int(character))):
            view = PingView(oc, ctx.user.id == oc.author)
            return await ctx.send_followup(embed=oc.embed, view=view)
        if ocs := list(self.rpers.get(member.id, {}).values()):
            ocs.sort(key=lambda x: x.name)
            if len(ocs) == 1:
                await ctx.send_followup(
                    f"{member.mention} has only one character.",
                    embed=ocs[0].embed,
                )
                return
            view = CharactersView(
                bot=self.bot,
                member=ctx.author,
                ocs=ocs,
                target=ctx.interaction,
                keep_working=True,
            )
            embed = view.embed
            embed.color = member.color
            embed.set_author(name=member.display_name)
            embed.set_thumbnail(url=member.display_avatar.url)
            async with view.send(ephemeral=True):
                if member == ctx.author:
                    self.bot.logger.info(
                        "User %s is reading their OCs", str(member)
                    )
                else:
                    self.bot.logger.info(
                        "User %s is reading the OCs of %s",
                        str(ctx.author),
                        str(member),
                    )
        else:
            await ctx.send_followup(f"{member.mention} has no characters.")

    @slash_command(
        name="submit_as",
        guild_ids=[719343092963999804],
        description="Allows to create OCs as an user",
    )
    @has_role("Moderation")
    async def submit_as(
        self,
        ctx: ApplicationContext,
        member: Option(
            User,
            description="Member, if not provided, it's current user.",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        if isinstance(member, int):
            try:
                member: User = await self.bot.fetch_user(member)
            except HTTPException:
                await ctx.send_followup(
                    content="User does not exist in discord.",
                    ephemeral=True,
                )
                return
        elif not member:
            member: Member = ctx.author
        if ctx.author == member:
            self.supporting.pop(ctx.author, None)
            await ctx.send_followup(
                content="OCs registered now will be assigned to your account.!",
                ephemeral=True,
            )
        else:
            self.supporting[ctx.author] = member
            await ctx.send_followup(
                content=f"OCs registered now will be assigned to {member.mention}!",
                ephemeral=True,
            )

        if self.oc_list.get(member.id):
            await self.list_update(member)

    async def load_characters(self, db: Connection):
        self.bot.logger.info("Loading all Characters.")
        for oc in await fetch_all(db):
            self.ocs[oc.id] = oc
            self.rpers.setdefault(oc.author, {})
            self.rpers[oc.author][oc.id] = oc

        cog = self.bot.get_cog("Roles")
        await cog.load(rpers=self.rpers)
        self.bot.logger.info("Finished loading all characters")

    async def load_profiles(self):
        self.bot.logger.info("Loading All Profiles")
        channel = await self.bot.fetch_channel(919277769735680050)
        async for m in channel.history(limit=None):
            if not (m.mentions and m.webhook_id):
                continue
            user = m.mentions[0]
            self.oc_list[user.id] = m.id
            view = RPView(self.bot, user.id, self.oc_list)
            self.bot.add_view(view=view, message_id=m.id)

        self.bot.logger.info("Finished loading all Profiles.")

    async def load_missions(self, db: Connection):
        self.bot.logger.info("Loading claimed missions")
        async for item in db.cursor(
            """--sql
            SELECT *
            FROM MISSIONS
            order by created_at;
            """
        ):
            mission = Mission(**dict(item))
            if mission.id:
                async for oc_item in db.cursor(
                    """--sql
                    SELECT character, assigned_at
                    FROM MISSION_ASSIGNMENT
                    where mission = $1;
                    """,
                    mission.id,
                ):
                    oc_id, assigned_at = (
                        oc_item["character"],
                        oc_item["assigned_at"],
                    )
                    if oc := self.ocs.get(oc_id):
                        self.mission_claimers.setdefault(mission.id, set())
                        self.mission_claimers[mission.id].add(oc.id)
                        date = self.mission_cooldown.get(oc.author, assigned_at)
                        if date <= assigned_at:
                            self.mission_cooldown[oc.author] = assigned_at

            self.missions.add(mission)
        self.bot.logger.info("Finished loading claimed missions")

    async def load_mission_views(self, db: Connection):
        self.bot.logger.info("Loading mission views")

        channel: TextChannel = await self.bot.fetch_channel(908498210211909642)

        for mission in self.missions:
            view = MissionView(
                bot=self.bot,
                mission=mission,
                mission_claimers=self.mission_claimers,
                mission_cooldown=self.mission_cooldown,
                supporting=self.supporting,
            )
            try:
                message = await channel.fetch_message(mission.msg_id)
                await message.edit(view=view)
            except DiscordException:
                if not (member := channel.guild.get_member(mission.author)):
                    await mission.remove(db)
                else:
                    msg = await channel.send(
                        content=member.mention,
                        embed=mission.embed,
                        view=view,
                        allowed_mentions=AllowedMentions(users=True),
                    )
                    mission.msg_id = msg.id
                    thread = await msg.create_thread(
                        name=f"Mission {mission.id:03d}"
                    )
                    await thread.add_user(member)
                    ocs = set(mission.ocs)
                    for oc_id in mission.ocs:
                        if oc := self.ocs.get(oc_id):
                            await thread.send(
                                f"{member} joined with {oc.name} `{oc!r}` as character for this mission.",
                                view=View(
                                    Button(label="Jump URL", url=oc.jump_url)
                                ),
                            )
                        else:
                            ocs.remove(oc_id)
                    mission.ocs = frozenset(ocs)

                    mission.msg_id = msg.id
                    await mission.upsert(db)

        self.bot.logger.info("Finished loading mission views")

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")
        source = Path("resources/templates.json")
        async with aiopen(source.resolve(), mode="r") as f:
            contents = await f.read()
            view = SubmissionView(
                bot=self.bot,
                ocs=self.ocs,
                rpers=self.rpers,
                oc_list=self.oc_list,
                supporting=self.supporting,
                missions=self.missions,
                mission_claimers=self.mission_claimers,
                mission_cooldown=self.mission_cooldown,
                **loads(contents),
            )
            w = await self.bot.fetch_webhook(857435846454280244)
            await w.edit_message(903437849154711552, view=view)
        self.bot.logger.info("Finished loading Submission menu")

    async def load_claimed_categories(self):
        items: list[list[TextChannel]] = [
            [
                x
                for x in self.bot.get_channel(ch).channels
                if not x.name.endswith("-ooc")
            ]
            for ch in RP_CATEGORIES
        ]
        for channel in chain(*items):
            async for m in channel.history(limit=1):

                date = m.created_at + timedelta(days=3)

                if m.author == self.bot.user and m.content == CLAIM_MESSAGE:
                    self.data_msg[channel.id] = m

                trigger = IntervalTrigger(days=3, start_time=date)

                await self.bot.scheduler.add_schedule(
                    self.unclaiming,
                    trigger=trigger,
                    id=f"RP[{channel.id}]",
                    args=[channel.id],
                    conflict_policy=ConflictPolicy.replace,
                )

    @Cog.listener()
    async def on_ready(self) -> None:
        """On ready, the parameters from Cog submisisons are loaded."""

        if self.ready:
            return

        async with self.bot.database() as db:
            await self.load_characters(db)
            await self.load_missions(db)
            await self.load_mission_views(db)

        await self.load_profiles()
        await self.load_submssions()
        await self.load_claimed_categories()
        self.ready = True

    @Cog.listener()
    async def on_member_update(
        self,
        past: Member,
        now: Member,
    ) -> None:
        try:
            if (
                past.display_name != now.display_name
                or past.display_avatar != now.display_avatar
                or past.colour != now.colour
            ) and self.oc_list.get(now.id):
                await self.list_update(now)
        except Exception as e:
            self.bot.logger.exception("Exception updating", exc_info=e)

    @Cog.listener()
    async def on_raw_thread_delete(
        self,
        payload: RawThreadDeleteEvent,
    ) -> None:
        """Detects if threads were removed

        Parameters
        ----------
        payload : RawThreadDeleteEvent
            Information
        """
        if payload.parent_id != 919277769735680050:
            return
        if payload.thread_id in self.oc_list.values():
            author_id: int = [
                k for k, v in self.oc_list.items() if v == payload.thread_id
            ][0]
            async with self.bot.database() as db:
                del self.oc_list[author_id]

                for oc in self.rpers.pop(author_id, {}).values():
                    del self.ocs[oc.id]
                    self.bot.logger.info(
                        "Character Removed as Thread was removed! > %s - %s > %s",
                        oc.name,
                        repr(oc),
                        oc.url or "None",
                    )
                    await oc.delete(db)

    @Cog.listener()
    async def on_raw_message_delete(
        self,
        payload: RawMessageDeleteEvent,
    ) -> None:
        """Detects if ocs or lists were deleted

        Parameters
        ----------
        payload : RawMessageDeleteEvent
            Information
        """
        if oc := self.ocs.get(payload.message_id):
            del self.ocs[oc.id]
            self.rpers.setdefault(oc.author, {})
            self.rpers[oc.author].pop(oc.id, None)
            async with self.bot.database() as db:
                self.bot.logger.info(
                    "Character Removed as message was removed! > %s - %s > %s",
                    oc.name,
                    repr(oc),
                    oc.url or "None",
                )
                await oc.delete(db)
        if payload.message_id in self.oc_list.values():
            author_id: int = [
                k for k, v in self.oc_list.items() if v == payload.message_id
            ][0]
            del self.oc_list[author_id]
            async with self.bot.database() as db:
                for oc in self.rpers.pop(author_id, {}).values():
                    del self.ocs[oc.id]
                    self.bot.logger.info(
                        "Character Removed as Thread was removed! > %s > %s",
                        str(type(oc)),
                        oc.url or "None",
                    )
                    await oc.delete(db)

    async def bio_google_doc_parser(
        self, message: Message
    ) -> Optional[tuple[DocumentType, str]]:
        text: str = codeblock_converter(message.content or "").content
        if doc_data := G_DOCUMENT.match(text):
            doc = await to_thread(docs_reader, url := doc_data.group(1))
            url = f"https://docs.google.com/document/d/{url}/edit?usp=sharing"
            return doc, url

    async def bio_word_doc_parser(
        self, message: Message
    ) -> Optional[DocumentType]:
        if attachments := message.attachments:
            with suppress(Exception):
                file = await attachments[0].to_file()
                return Document(file.fp)

    async def bio_discord_doc_parser(self, message: Message) -> Optional[dict]:
        text = codeblock_converter(message.content or "").content
        if G_DOCUMENT.match(text):
            return
        with suppress(MarkedYAMLError):
            text = yaml_handler(text)
            if isinstance(msg_data := safe_load(text), dict):
                if images := message.attachments:
                    msg_data["image"] = images[0].url
                return msg_data

    async def submission_handler(
        self,
        message: Message,
        **msg_data,
    ):
        if msg_data:
            author = self.supporting.get(message.author, message.author)
            self.ignore.add(message.author.id)
            if oc := oc_process(**msg_data):
                oc.author = author.id
                oc.server = message.guild.id
                await self.registration(ctx=message, oc=oc)
                await message.delete()
            self.ignore.remove(message.author.id)

    async def on_message_submission(self, message: Message):
        """This method processes character submissions

        Attributes
        ----------
        message : Message
            Message to process
        """
        if (
            not self.ready
            or not message.guild
            or message.mentions
            or message.author.bot
            or message.author.id in self.ignore
            or message.stickers
        ):
            return
        try:
            done, _ = await wait(
                [
                    self.bio_google_doc_parser(message),
                    self.bio_discord_doc_parser(message),
                    self.bio_word_doc_parser(message),
                ],
                return_when=ALL_COMPLETED,
            )

            for result in map(lambda x: x.result(), done):
                msg_data: Optional[dict[str, Any]] = result

                if isinstance(result, tuple):
                    result, url = result
                    msg_data = doc_convert(result)
                    msg_data["url"] = url
                elif isinstance(result, DocumentType):
                    if result.tables:
                        msg_data = doc_convert(result)
                    else:
                        with suppress(MarkedYAMLError):
                            msg_data = safe_load(
                                yaml_handler(
                                    "\n".join(
                                        element
                                        for p in result.paragraphs
                                        if (element := p.text.strip())
                                    )
                                )
                            )

                if isinstance(msg_data, dict):
                    await self.submission_handler(message, **msg_data)
                    return
        except Exception as e:
            self.bot.logger.exception(
                "Exception processing character", exc_info=e
            )
            await message.reply(str(e), delete_after=10)
            if message.author.id in self.ignore:
                self.ignore.remove(message.author.id)

    async def on_message_tupper(self, message: Message):
        channel = message.channel
        author = message.author.name.title()

        if "Npc" in author or "Narrator" in author:
            return

        ocs = {
            item.name: item
            for item in self.rpers.get(message.author.id, {}).values()
        }

        if items := get_close_matches(author, ocs, n=1, cutoff=0.85):
            oc = ocs[items[0]]
        elif not (
            oc := next(
                filter(
                    lambda x: x.name in author or author in x.name,
                    ocs.values(),
                ),
                None,
            )
        ):
            return

        trigger = IntervalTrigger(days=3)

        if oc.location != message.channel.id:

            former_channel: TextChannel = message.guild.get_channel(oc.location)

            if (
                former_channel
                and len(
                    [x for x in self.ocs.values() if x.location == oc.location]
                )
                == 0
            ):
                self.data_msg.pop(former_channel.id, None)
                scheduler = await self.bot.scheduler.get_schedule(
                    f"RP[{former_channel.id}]"
                )
                await self.unclaiming(former_channel)
                scheduler.trigger = trigger

        scheduler = await self.bot.scheduler.get_schedule(f"RP[{channel.id}]")
        scheduler.trigger = trigger

        async with self.bot.database() as db:
            oc.location = message.channel.id
            await self.oc_update(oc)
            await oc.upsert(db)

    async def on_message_proxy(self, message: Message):
        """This method processes tupper messages

        Attributes
        ----------
        message : Message
            Message to process
        """
        context = await self.bot.get_context(message)

        if context.command:
            return

        try:
            msg: Message = await self.bot.wait_for(
                event="message",
                check=message_validator(message),
                timeout=3,
            )
            self.bot.msg_cache_add(message)
            if isinstance(channel := message.channel, TextChannel):
                trigger = IntervalTrigger(days=3)
                await self.bot.scheduler.add_schedule(
                    self.unclaiming,
                    trigger,
                    id=f"RP[{channel.id}]",
                    args=[channel.id, False],
                    conflict_policy=ConflictPolicy.replace,
                )
            await self.on_message_tupper(msg)
        except TimeoutError:
            if not self.rpers.get(message.author.id):
                role = message.guild.get_role(719642423327719434)
                await message.author.remove_roles(
                    role, reason="Without OCs, user isn't registered."
                )
                for cat_id in RP_CATEGORIES:
                    if ch := self.bot.get_channel(cat_id):
                        await ch.set_permissions(message.author, overwrite=None)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """on_message handler

        Parameters
        ----------
        message : Message
            Message to process
        """
        if message.channel.id == 852180971985043466:
            await self.on_message_submission(message)
        elif (
            message.guild
            and (tupper := message.guild.get_member(431544605209788416))
            and tupper.status == Status.online
            and message.channel.category_id in RP_CATEGORIES
            and not message.webhook_id
            and not message.channel.name.endswith("-ooc")
        ):
            await self.on_message_proxy(message)

    @Cog.listener()
    async def on_message_edit(self, _: Message, message: Message):
        """on_message_edit handler

        Parameters
        ----------
        _ : Message
            Previous message
        message : Message
            Message to process
        """
        if message.channel.id == 852180971985043466:
            await self.on_message_submission(message)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Submission(bot))
