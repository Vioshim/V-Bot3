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

from asyncio import TimeoutError, to_thread
from contextlib import suppress
from datetime import timedelta
from difflib import get_close_matches
from io import BytesIO
from pathlib import Path
from typing import Type, Union

from aiofiles import open as aiopen
from apscheduler.enums import ConflictPolicy
from apscheduler.triggers.date import DateTrigger
from discord import (
    AllowedMentions,
    CategoryChannel,
    DiscordException,
    Embed,
    File,
    Guild,
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
    WebhookMessage,
)
from discord.commands import (
    has_role,
    message_command,
    slash_command,
    user_command,
)
from discord.ext.commands import Cog
from discord.ui import Button, View
from discord.utils import utcnow
from docx import Document
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
from src.structures.character import (
    Character,
    doc_convert,
    fetch_all,
    oc_process,
)
from src.structures.mission import Mission
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.species import Fakemon, Fusion, Variant
from src.utils.doc_reader import docs_reader
from src.utils.etc import REGISTERED_IMG, RP_CATEGORIES, WHITE_BAR
from src.utils.matches import G_DOCUMENT, YAML_HANDLER
from src.views import (
    CharactersView,
    ImageView,
    MissionView,
    MoveView,
    RPView,
    StatsView,
    SubmissionView,
)


def oc_autocomplete(ctx: AutocompleteContext):
    member_id = int(ctx.options.get("member") or ctx.interaction.user.id)
    cog: Submission = ctx.bot.get_cog("Submission")
    text: str = ctx.value or ""
    ocs = cog.rpers.get(member_id, {}).values()
    values: set[tuple[str, str]] = set()

    if items := {oc.name: (oc.name, str(oc.id)) for oc in ocs}:
        values.update(
            items[item]
            for item in get_close_matches(
                word=text,
                possibilities=items,
                n=25,
            )
        )

    if len(values) <= 5:
        values.update(
            (oc.name, str(oc.id))
            for oc in ocs
            if oc.name.startswith(text.title())
        )

    return map(lambda x: OptionChoice(*x), values)


class Submission(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready: bool = False
        self.missions: set[Mission] = set()
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        self.ocs: dict[int, Character] = {}
        self.rpers: dict[int, dict[int, Character]] = {}
        self.oc_list: dict[int, int] = {}
        self.located: dict[int, set[Character]] = {}
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
                pass
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
            await ctx.send_followup(
                "The user only has one character",
                ephemeral=True,
                embed=ocs[0].embed,
            )
        elif ocs:
            ocs.sort(key=lambda x: x.name)
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
                pass
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
        if m := self.data_msg.pop(channel.id, None):
            with suppress(DiscordException):
                await m.delete()
        self.data_msg[channel.id] = await channel.send(
            "\n".join(
                [
                    "**。　　　　•　    　ﾟ　　。**",
                    "**　　.　　　.　　　.　　。　　   。　.**",
                    "** 　.　　      。             。　    .    •**",
                    "** •     RP claimable, feel free to use it.　 。　.**",
                    "**          Is assumed that everyone left**",
                    "**　 　　。　　　　ﾟ　　　.　　　　　.**",
                    "**,　　　　.　 .　　       .               。**",
                ]
            )
        )

    async def list_update(
        self,
        member: Member,
    ):
        """This function updates an user's character list message

        Parameters
        ----------
        member : Member
            User to update list
        """
        if not self.ready:
            return
        embed = Embed(
            title="Registered Characters",
            color=member.color,
        )
        guild = member.guild
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        embed.set_author(name=member.display_name)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=WHITE_BAR)
        webhook = await self.bot.fetch_webhook(919280056558317658)
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
        await thread.add_user(member)
        self.oc_list[member.id] = thread.id
        view = RPView(self.bot, member.id, self.oc_list)
        await message.edit(view=view)
        async with self.bot.database() as db:
            await db.execute(
                """--sql
                INSERT INTO THREAD_LIST(ID, AUTHOR, SERVER)
                VALUES ($1, $2, $3) ON CONFLICT(AUTHOR, SERVER)
                DO UPDATE SET ID = $1;
                """,
                thread.id,
                member.id,
                guild.id,
            )

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

        if isinstance(ctx, Message):

            user = ctx.author

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
                            name := str(x),
                            f"Adds the typing {name}",
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
                            name := "/".join(str(i) for i in x),
                            f"Adds the typing {name}",
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
                        parser=lambda x: (x.name, x.description),
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
            elif not oc.any_ability_at_first:
                if ability_errors := ", ".join(
                    ability.name
                    for ability in oc.abilities
                    if ability not in species.abilities
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

        else:
            user = ctx.user

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
        if member is None:
            member: Member = ctx.author
        await ctx.defer(ephemeral=True)
        if (character or "").isdigit() and (oc := self.ocs.get(int(character))):
            return await ctx.send_followup(embed=oc.embed)
        if ocs := self.rpers.get(member.id, {}).values():
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
                pass
        else:
            await ctx.send_followup(
                f"{member.mention} has no characters.", ephemeral=True
            )

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
            Member,
            description="Member, if not provided, it's current user.",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        if ctx.author == member or member is None:
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

    @Cog.listener()
    async def on_ready(self) -> None:
        """This method loads all the characters from the database."""

        if self.ready:
            return

        guild: Guild = self.bot.get_guild(719343092963999804)

        async with self.bot.database() as db:

            self.bot.logger.info("Loading all Characters.")

            for oc in await fetch_all(db):
                self.ocs[oc.id] = oc
                self.rpers.setdefault(oc.author, {})
                self.rpers[oc.author][oc.id] = oc
                if location := oc.location:
                    self.located.setdefault(location, set())
                    self.located[location].add(oc)

            self.bot.logger.info("Finished loading all characters")

            cog = self.bot.get_cog("Roles")

            await cog.load(rpers=self.rpers)

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
                    **loads(contents),
                )
                w = await self.bot.fetch_webhook(857435846454280244)
                await w.edit_message(903437849154711552, view=view)

            self.bot.logger.info("Finished loading Submission menu")

            self.bot.logger.info("Loading All Profiles")

            async for item in db.cursor(
                """--sql
                SELECT AUTHOR, ID
                FROM THREAD_LIST
                WHERE SERVER = $1;
                """,
                guild.id,
            ):
                author, thread_id = item
                self.oc_list[author] = thread_id
                if member := guild.get_member(author):
                    await self.list_update(member)
                elif view := RPView(
                    bot=self.bot,
                    member_id=author,
                    oc_list=self.oc_list,
                ):
                    self.bot.add_view(view=view, message_id=thread_id)

            self.bot.logger.info("Finished loading all Profiles.")

            self.ready = True

            self.bot.logger.info("Loading claimed missions")

            self.missions = await Mission.fetch_all(db)

            w = await self.bot.fetch_webhook(908549481807614022)

            for mission in self.missions:
                view = MissionView(bot=self.bot, mission=mission)
                if msg_id := mission.msg_id:
                    self.bot.add_view(view, message_id=msg_id)
                else:
                    msg = await w.send(
                        content=f"<@{mission.author}>",
                        embed=mission.embed,
                        view=view,
                        wait=True,
                        allowed_mentions=AllowedMentions(users=True),
                    )
                    mission.msg_id = msg.id
                    await mission.upsert(db)

        self.bot.logger.info("Loading claimed categories")

        for item in RP_CATEGORIES:

            if not (cat := self.bot.get_channel(item)):
                cat: CategoryChannel = await self.bot.fetch_channel(item)

            for ch in cat.channels:
                if ch.name.endswith("-ooc"):
                    continue

                async for m in ch.history(limit=1):
                    if m.author == self.bot.user:
                        if not m.webhook_id:
                            self.data_msg[ch.id] = m
                    elif (raw := utcnow() - m.created_at) > timedelta(days=3):
                        await self.unclaiming(ch)
                    elif date := utcnow() + (timedelta(days=3) - raw):

                        trigger = DateTrigger(date)
                        await self.bot.scheduler.add_schedule(
                            self.unclaiming,
                            trigger,
                            id=f"RP[{ch.id}]",
                            args=[ch.id],
                            conflict_policy=ConflictPolicy.replace,
                        )

        self.bot.logger.info("Finished loading claimed categories")

    @Cog.listener()
    async def on_member_update(
        self,
        past: Member,
        now: Member,
    ) -> None:
        try:
            if any(
                (
                    past.display_name != now.display_name,
                    past.display_avatar != now.display_avatar,
                    past.colour != now.colour,
                )
            ):
                if self.oc_list.get(now.id):
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
                await db.execute(
                    """--sql
                    DELETE FROM THREAD_LIST
                    WHERE ID = $1 AND SERVER = $2;
                    """,
                    payload.thread_id,
                    payload.guild_id,
                )

                for oc in self.rpers.pop(author_id, {}).values():
                    del self.ocs[oc.id]
                    if location := oc.location:
                        self.located.setdefault(location, set())
                        if oc in self.located[location]:
                            self.located[location].remove(oc)
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
            if location := oc.location:
                self.located.setdefault(location, set())
                if oc in self.located[location]:
                    self.located[location].remove(oc)
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
                    if location := oc.location:
                        self.located.setdefault(location, set())
                        if oc in self.located[location]:
                            self.located[location].remove(oc)
                    self.bot.logger.info(
                        "Character Removed as Thread was removed! > %s > %s",
                        str(type(oc)),
                        oc.url or "None",
                    )
                    await oc.delete(db)

    @Cog.listener()
    async def on_message(
        self,
        message: Message,
    ) -> None:
        """This method processes character submissions

        Attributes
        ----------
        message : Message
            Message to process
        """
        if not self.ready:
            return

        if not message.guild:
            return

        if message.mentions:
            return

        if message.channel.id == 852180971985043466:

            if message.author.id in self.ignore:
                return
            if message.author.bot:
                return

            text: str = codeblock_converter(message.content or "").content
            try:
                msg_data = None
                doc = None
                if doc_data := G_DOCUMENT.match(text):
                    doc = await to_thread(docs_reader, doc_data.group(1))
                    msg_data = doc_convert(doc, url=doc_data.group(1))
                elif text := YAML_HANDLER.sub(": ", text):
                    msg_data = safe_load(text)
                    if images := message.attachments:
                        msg_data["image"] = images[0].url
                elif attachments := message.attachments:
                    with suppress(Exception):
                        file = await attachments[0].to_file()
                        doc = await to_thread(Document, file.fp)
                        msg_data = doc_convert(doc)

                if doc:
                    with suppress(Exception):
                        data = list(doc.inline_shapes)
                        item = data[0]
                        blip = (
                            item._inline.graphic.graphicData.pic.blipFill.blip
                        )
                        rID = blip.embed
                        doc_part = doc.part
                        image_part = doc_part.related_parts[rID]
                        fp = BytesIO(image_part._blob)
                        msg_data["image"] = File(fp=fp, filename="image.png")

                channel: TextChannel = message.channel

                if isinstance(msg_data, dict):

                    author = self.supporting.get(message.author, message.author)

                    self.ignore.add(message.author.id)
                    if oc := oc_process(**msg_data):
                        oc.author = author.id
                        oc.server = message.guild.id
                        await self.registration(ctx=message, oc=oc)
                        await message.delete()
                    self.ignore.remove(message.author.id)
            except MarkedYAMLError:
                return
            except Exception as e:
                self.bot.logger.exception(
                    "Exception processing character", exc_info=e
                )
                await message.reply(f"Exception:\n\n{e}", delete_after=10)
                self.ignore.remove(message.author.id)
                return

        if tupper := message.guild.get_member(431544605209788416):
            if tupper.status != Status.online:
                return
        else:
            return

        if message.channel.category_id in RP_CATEGORIES:
            if message.webhook_id:
                return
            if message.channel.is_news():
                return

            context = await self.bot.get_context(message)

            if context.command:
                return

            def checker(value: Message) -> bool:
                if value.webhook_id:
                    if content := message.content:
                        return value.content in content
                    elif message.attachments:
                        return value.content is None and value.attachments
                return False

            try:
                msg: Message = await self.bot.wait_for(
                    "message", check=checker, timeout=3
                )
                self.bot.msg_cache_add(message)

                if isinstance(channel := message.channel, TextChannel):
                    time = utcnow() + timedelta(days=3)
                    if m := self.data_msg.get(channel.id):
                        with suppress(DiscordException):
                            await m.delete()
                    await self.bot.scheduler.add_schedule(
                        self.unclaiming,
                        DateTrigger(time),
                        id=f"RP[{channel.id}]",
                        args=[channel],
                        conflict_policy=ConflictPolicy.replace,
                    )
            except TimeoutError:
                if not self.rpers.get(message.author.id):
                    role = message.guild.get_role(719642423327719434)
                    await message.author.remove_roles(
                        role, reason="Without OCs, user isn't registered."
                    )
                    for cat_id in RP_CATEGORIES:
                        if ch := self.bot.get_channel(cat_id):
                            await ch.set_permissions(
                                message.author,
                                overwrite=None,
                            )
            else:
                for item in self.rpers.get(message.author.id, {}).values():
                    if any(
                        (
                            item.name.title() in msg.author.name.title(),
                            msg.author.name.title() in item.name.title(),
                        )
                    ):
                        if item.location != msg.channel.id:
                            former_channel = message.guild.get_channel(
                                item.location
                            )
                            previous = self.located.get(item.location, set())
                            current = self.located.get(msg.channel.id, set())
                            if item in previous:
                                previous.remove(item)
                            if item not in current:
                                current.add(item)

                            if len(previous) == 0:
                                with suppress(Exception):
                                    await self.unclaiming(former_channel)
                                    await self.bot.scheduler.remove_schedule(
                                        f"RP[{former_channel.id}]"
                                    )

                            async with self.bot.database() as db:
                                item.location = msg.channel.id
                                await self.oc_update(item)
                                await item.upsert(db)


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Submission(bot))
