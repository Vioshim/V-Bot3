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


import asyncio
from contextlib import suppress
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    File,
    ForumChannel,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    PartialEmoji,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    RawThreadDeleteEvent,
    RawThreadUpdateEvent,
    Role,
    Status,
    TextChannel,
    Thread,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, find, get
from rapidfuzz import process

from src.cogs.submission.oc_parsers import ParserMethods
from src.cogs.submission.oc_submission import (
    CreationOCView,
    ModCharactersView,
    SubmissionView,
)
from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.move import Move
from src.utils.etc import MAP_ELEMENTS2, SETTING_EMOJI, WHITE_BAR
from src.views.characters_view import PingView
from src.views.move_view import MoveView

__all__ = ("Submission", "setup")


def comparison_handler(before: Character, now: Character):
    aux1_new: list[Embed] = []
    aux2_new: list[Embed] = []

    before_embeds, now_embeds = before.embeds, now.embeds

    if len(before_embeds) != len(now_embeds):
        if len(before_embeds) == 1:
            before_embeds.append(Embed())
        if len(now_embeds) == 1:
            now_embeds.append(Embed())

    for aux1, aux2 in zip(before_embeds, now_embeds):
        elem1 = {field.name: (field.value, field.inline) for field in aux1.fields}
        elem2 = {field.name: (field.value, field.inline) for field in aux2.fields}

        e1 = Embed(title=aux1.title, description=aux1.description, color=Color.red())
        e2 = Embed(description=aux2.description, color=Color.brand_green())
        e1.set_image(url=WHITE_BAR)
        e2.set_image(url=WHITE_BAR)

        img1 = before.image_url or before.image
        img2 = now.image_url or now.image

        if img1 != img2:
            if isinstance(img1, str):
                e1.set_image(url=img1)
            if isinstance(img2, str):
                e2.set_image(url=img2)

        if before.pokeball != now.pokeball:
            if before.pokeball:
                e1.set_thumbnail(url=before.pokeball.url)
            if now.pokeball:
                e2.set_thumbnail(url=now.pokeball.url)

        if aux1.title != aux2.title:
            e2.title = aux2.title

        if aux1.footer.text != aux2.footer.text:
            e1.set_footer(text=aux1.footer.text)
            e2.set_footer(text=aux2.footer.text)

        if e1.description == e2.description:
            e1.description = e2.description = None

        for key in set(elem1) | set(elem2):
            if (v1 := elem1.get(key)) != (v2 := elem2.get(key)):
                if v1:
                    v1, i1 = v1
                    e1.add_field(name=key, value=v1, inline=i1)
                if v2:
                    v2, i2 = v2
                    e2.add_field(name=key, value=v2, inline=i2)

        conditions = (
            aux1.title == aux2.title,
            e1.description == e2.description,
            before.image == now.image,
            before.pokeball == now.pokeball,
            len(e1.fields) == len(e2.fields) == 0,
            e1.footer.text == e2.footer.text,
        )
        if not all(conditions):
            aux1_new.append(e1)
            aux2_new.append(e2)

    return aux1_new, aux2_new


class Submission(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        guild_ids = [719343092963999804]
        self.ctx_menu1 = app_commands.ContextMenu(
            name="Moves & Abilities",
            callback=self.info_checker,
            guild_ids=guild_ids,
        )
        self.ctx_menu2 = app_commands.ContextMenu(
            name="Check User's OCs",
            callback=self.check_ocs,
            guild_ids=guild_ids,
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.ctx_menu1)
        self.bot.tree.add_command(self.ctx_menu2)
        await self.load_submssions()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu1.name, type=self.ctx_menu1.type)
        self.bot.tree.remove_command(self.ctx_menu2.name, type=self.ctx_menu2.type)

    async def info_checker(self, ctx: Interaction, message: Message):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        moves: list[SpAbility | Ability | Move] = []
        db = self.bot.mongo_db("Characters")
        if data := await db.find_one({"id": message.id}):
            oc = Character.from_mongo_dict(data)
            moves = list(oc.moveset) + list(oc.abilities)
            if sp_ability := oc.sp_ability:
                moves.append(sp_ability)
        elif text := message.content:
            moves = [
                x[0]
                for x in process.extract(
                    text,
                    choices=Move.all() | Ability.all(),
                    score_cutoff=60,
                    processor=lambda x: getattr(x, "name", x),
                )
            ]

        moves.sort(key=lambda x: x.name)
        view = MoveView(member=ctx.user, moves=moves, target=ctx, keep_working=True)
        async with view.send(ephemeral=True):
            self.bot.logger.info(
                "User %s is reading the abilities/moves at %s",
                str(ctx.user),
                message.jump_url,
            )

    async def check_ocs(self, ctx: Interaction, member: Member):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        db = self.bot.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id})]
        view = ModCharactersView(member=ctx.user, ocs=ocs, target=ctx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(ctx.user), str(member))

    async def list_update(self, member: Object | User | Member):
        """This function updates an user's character list message

        Parameters
        ----------
        member : Object
            User to update list
        """
        if isinstance(member, int):
            member = Object(id=member)

        if not (channel := self.bot.get_channel(1019686568644059136)):
            channel: ForumChannel = await self.bot.fetch_channel(1019686568644059136)

        db = self.bot.mongo_db("Roleplayers")

        thread = None
        if item := await db.find_one({"user": member.id}):
            if not (thread := channel.guild.get_channel_or_thread(item["id"])):
                with suppress(DiscordException):
                    thread: Thread = await channel.guild.fetch_channel(item["id"])

        if thread:
            try:
                msg = thread.get_partial_message(thread.id)
                if isinstance(member, Object):
                    if aux := channel.guild.get_member(member.id):
                        member = aux
                    else:
                        with suppress(DiscordException):
                            member = await self.bot.fetch_user(member.id)

                if isinstance(member, (User, Member)):
                    roles: list[Role] = getattr(member, "roles", [])
                    tags = [
                        o
                        for x in map(
                            lambda x: x.name.removesuffix(" RP Search"),
                            filter(lambda x: " RP Search" in x.name, roles),
                        )
                        if (o := get(channel.available_tags, name=x))
                    ]
                    tags.sort(key=lambda x: x.name)
                    thread = await thread.edit(name=member.display_name, applied_tags=tags[:5])
                    msg = await msg.edit(content=f"{member.mention}\n{member.display_avatar.url}", attachments=[])
            except DiscordException:
                thread = None

        if thread is None:

            if isinstance(member, Object):
                if member_info := channel.guild.get_member(member.id) or self.bot.get_user(member.id):
                    member = member_info
                else:
                    member = await self.bot.fetch_user(member.id)

            if isinstance(member, (User, Member)):
                roles: list[Role] = getattr(member, "roles", [])
                tags = [
                    o
                    for x in map(
                        lambda x: x.name.removesuffix(" RP Search"),
                        filter(lambda x: " RP Search" in x.name, roles),
                    )
                    if (o := get(channel.available_tags, name=x))
                ]
                tags.sort(key=lambda x: x.name)
                x = await channel.create_thread(
                    name=member.display_name,
                    content=f"{member.mention}\n{member.display_avatar.url}",
                    applied_tags=tags[:5],
                    allowed_mentions=AllowedMentions(users=True),
                )
                thread = x.thread
                await db.replace_one(
                    {"user": member.id},
                    {
                        "id": thread.id,
                        "user": member.id,
                        "server": thread.guild.id,
                    },
                    upsert=True,
                )

        return thread

    async def register_oc(self, oc: Character, image_as_is: bool = False):
        try:
            member = Object(id=oc.author)
            thread = await self.list_update(member)
            oc.thread = thread.id
            guild: Guild = self.bot.get_guild(oc.server)

            user = guild.get_member(member.id) or member
            embeds = oc.embeds
            embeds[0].set_image(url="attachment://image.png")
            kwargs = dict(
                content=f"<@{user.id}>",
                embeds=embeds,
                allowed_mentions=AllowedMentions(users=True),
            )

            if not oc.image_url:
                if image_as_is:
                    image = oc.image
                elif img := await self.bot.mongo_db("OC Background").find_one({"author": oc.author}):
                    image = oc.generated_image(img["image"])
                else:
                    image = oc.generated_image()
                if file := await self.bot.get_file(url=image, filename="image"):
                    word = "attachments" if oc.id else "files"
                    kwargs[word] = [file]

            former: Optional[Character] = None

            if reference_id := oc.id:
                thread = await thread.edit(archived=False)
                try:
                    message = thread.get_partial_message(oc.id)
                    msg_oc = await message.edit(**kwargs)
                    word = "modified"
                except NotFound:
                    if attachments := kwargs.pop("attachments", []):
                        kwargs["files"] = attachments
                    elif isinstance(img := oc.image_url or oc.image, str) and (
                        file := await self.bot.get_file(img, filename="image")
                    ):
                        kwargs["file"] = file
                    msg_oc = await thread.send(**kwargs)
                    word = "registered"
                    former = oc
            elif msg_oc := await thread.send(**kwargs):
                reference_id = msg_oc.id
                word = "registered"
                former = oc

            oc.id = msg_oc.id
            oc.image_url = msg_oc.embeds[0].image.url

            db = self.bot.mongo_db("Characters")

            if former is None and (former := await db.find_one({"id": oc.id})):
                former = Character.from_mongo_dict(former)

            self.bot.logger.info(
                "Character has been %s! > %s > %s > %s",
                word,
                str(user),
                repr(oc),
                oc.document_url or "Manual",
            )

            await db.replace_one({"id": reference_id}, oc.to_mongo_dict(), upsert=True)

            try:
                if former:
                    pack_embeds: list[list[Embed]] = []
                    pack_files: list[list[File]] = []
                    log = await self.bot.webhook(1020151767532580934, reason="Logging")
                    if isinstance(user, (User, Member)):
                        username, avatar_url = user.display_name, user.display_avatar.url
                    else:
                        username, avatar_url = MISSING, MISSING

                    view = View()
                    if jump_url := former.jump_url:
                        view.add_item(
                            Button(
                                label=f"{word.title()} - Jump URL",
                                url=jump_url,
                                emoji=PartialEmoji(name="IconBuildoverride", id=815459629869826048),
                            )
                        )

                    if word == "modified":
                        for embed1, embed2 in zip(*comparison_handler(before=former, now=oc)):
                            embeds = [embed1, embed2]
                            files1, embed1 = await self.bot.embed_raw(embed1, "footer", "thumbnail")
                            files2, embed2 = await self.bot.embed_raw(embed2, "footer", "thumbnail")

                            files = files1 + files2
                            for index, (e, f) in enumerate(zip(embeds, files)):
                                f.filename = f"image{index}.png"
                                e.set_image(url=f"attachment://{f.filename}")

                            pack_embeds.append(embeds)
                            pack_files.append(files)
                    else:
                        embeds = oc.embeds
                        files, embeds[0] = await self.bot.embed_raw(embeds[0], "footer")
                        pack_embeds.append(embeds)
                        pack_files.append(files)

                    for embeds, files in zip(pack_embeds, pack_files):
                        await log.send(
                            embeds=embeds,
                            files=files,
                            thread=Object(id=1020153309425836122),
                            username=username,
                            avatar_url=avatar_url,
                            view=view,
                        )
            except Exception as e2:
                self.bot.logger.exception("Error when logging oc modification", exc_info=e2)
        except Exception as e1:
            self.bot.logger.exception("Error when logging oc modification main", exc_info=e1)

    async def oc_update(self, oc: Character):
        embeds = oc.embeds
        embeds[0].set_image(url="attachment://image.png")
        guild = self.bot.get_guild(oc.server)
        db = self.bot.mongo_db("Roleplayers")
        if (item := await db.find_one({"user": oc.author})) or oc.thread:
            item_id = item["id"] if item else oc.thread
            if not (thread := guild.get_channel_or_thread(item_id)):
                thread = await guild.fetch_channel(item_id)
        else:
            thread = await self.list_update(oc.author)

        msg = thread.get_partial_message(oc.id)
        try:
            if thread.archived:
                await thread.edit(archived=False)
            await msg.edit(embeds=embeds)
        except NotFound:
            await self.register_oc(oc)

    async def submission_handler(self, message: Interaction | Message, **msg_data):
        if isinstance(message, Interaction):
            refer_author = message.user
        else:
            refer_author = message.author
        if msg_data:
            author = self.bot.supporting.get(refer_author, refer_author)
            if oc := Character.process(**msg_data):
                view = CreationOCView(bot=self.bot, ctx=message, user=author, oc=oc)
                if isinstance(message, Message):
                    await message.delete(delay=0)
                await view.handler_send()
                await view.wait()

    async def on_message_submission(self, message: Message):
        """This method processes character submissions

        Attributes
        ----------
        message : Message
            Message to process
        """
        if (
            not message.guild
            or message.mentions
            or message.author.bot
            or message.author.id in self.ignore
            or message.stickers
        ):
            return
        self.ignore.add(message.author.id)
        try:
            async for item in ParserMethods.parse(text=message, bot=self.bot):
                return await self.submission_handler(message, **item)
        except Exception as e:
            self.bot.logger.exception("Exception processing character", exc_info=e)
            await message.reply(str(e), delete_after=15)
        finally:
            self.ignore -= {message.author.id}

    async def on_message_tupper(
        self,
        message: Message,
        kwargs: dict[str, Character],
    ):
        channel = message.channel
        author = message.author.name.title()

        if "Npc" in author or "Narrator" in author:
            return

        if item := process.extractOne(
            author,
            choices=kwargs.keys(),
            score_cutoff=85,
        ):
            key, oc = item[0], kwargs[item[0]]
        elif ocs := [(k, v) for k, v in kwargs.items() if k in author or author in k]:
            key, oc = ocs[0]
        else:
            return

        if info_channel := find(
            lambda x: isinstance(x, TextChannel) and x.name.endswith("-logs"),
            channel.category.channels,
        ):
            w = await self.bot.webhook(info_channel)

            try:
                name = message.channel.name.replace("»", "")
                emoji, name = name.split("〛")
            except ValueError:
                emoji, name = SETTING_EMOJI, message.channel.name
            finally:
                name = name.replace("-", " ")

            view = View()
            view.add_item(Button(label=name[:80], url=message.jump_url, emoji=emoji))
            view.add_item(Button(label=key[:80], url=oc.jump_url, emoji=oc.pronoun.emoji))

            msg = await w.send(
                content=message.content,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url,
                files=[await x.to_file() for x in message.attachments],
                allowed_mentions=AllowedMentions.none(),
                view=view,
                wait=True,
            )

            db = self.bot.mongo_db("RP Logs")
            await db.insert_one(
                {
                    "id": message.id,
                    "channel": message.channel.id,
                    "log": msg.id,
                    "log-channel": info_channel.id,
                }
            )
            db2 = self.bot.mongo_db("Tupper-logs")
            await db2.insert_one(
                {
                    "channel": info_channel.id,
                    "id": msg.id,
                    "author": oc.author,
                }
            )

        oc.last_used = message.id
        if oc.location != channel.id:
            oc.location = channel.id

        db = self.bot.mongo_db("Characters")
        await db.update_one(
            {"id": oc.id, "server": oc.server},
            {"$set": {"location": oc.location, "last_used": message.id}},
            upsert=False,
        )

    async def on_message_proxy(self, message: Message):
        """This method processes tupper messages

        Attributes
        ----------
        message : Message
            Message to process
        """
        context = await self.bot.get_context(message)

        if context.command and context.command.name not in ["npc", "pc"]:
            return

        messages: list[Message] = []

        def checker(m: Message):
            if not (m.webhook_id and message.channel == m.channel):
                return False

            attachments = message.attachments
            if (message.content and (m.content in message.content)) or (
                attachments and len(attachments) == len(m.attachments)
            ):
                messages.append(m)
            return False

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(
                    self.bot.wait_for("message", check=checker),
                    name="Message",
                ),
                task := asyncio.create_task(
                    self.bot.wait_for("message_edit", check=lambda x, _: x == message),
                    name="Edit",
                ),
                asyncio.create_task(
                    self.bot.wait_for("message_delete", check=lambda x: x == message, timeout=3),
                    name="Delete",
                ),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for future in pending:
            future.cancel()

        for future in done:
            future.exception()

        if any(task == future for future in done):
            return

        db = self.bot.mongo_db("Characters")
        kwargs = {}
        async for x in db.find({"author": message.author.id}):
            oc = Character.from_mongo_dict(x)
            for name in oc.name.split(","):
                if name := name.strip():
                    kwargs[name] = oc

        for msg in sorted(messages, key=lambda x: x.id):
            await self.on_message_tupper(msg, kwargs)

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")
        view = SubmissionView(timeout=None)
        channel = self.bot.get_partial_messageable(id=852180971985043466, guild_id=719343092963999804)
        message = channel.get_partial_message(1005387453055639612)
        await message.edit(view=view)
        self.bot.logger.info("Finished loading Submission menu")

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")

        thread = None
        if await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member)
            message = thread.get_partial_message(thread.id)
            await message.edit(content=f"{member.mention}\n{member.display_avatar.url}", attachments=[])
            await thread.edit(
                name=member.display_name if thread.name != member.display_name else MISSING,
                reason=f"{thread.name} -> {member.display_name}",
                archived=False,
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")
        if await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member)
            message = thread.get_partial_message(thread.id)
            await message.edit(content=f"{member.mention}\n{member.display_avatar.url}", attachments=[])
            if thread.name == member.display_name:
                await thread.edit(reason="Member left", archived=True)
            else:
                reason = f"Member left: {member.display_name}"
                await thread.edit(name=member.display_name, reason=reason, archived=True)

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.display_name == now.display_name and past.display_avatar == now.display_avatar:
            return
        db = self.bot.mongo_db("Roleplayers")
        if await db.find_one({"user": now.id, "server": now.guild.id}):
            thread = await self.list_update(now)
            if thread.name != now.display_name:
                reason = f"{thread.name} -> {now.display_name}."
                await thread.edit(name=now.display_name, reason=reason)

            message = thread.get_partial_message(thread.id)
            await message.edit(content=f"{now.mention}\n{now.display_avatar.url}", attachments=[])

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        """on_message handler

        Parameters
        ----------
        message : Message
            Message to process
        """
        if not message.guild:
            return

        if message.channel.id == 852180971985043466:
            await self.on_message_submission(message)
        elif (
            message.channel.category_id in MAP_ELEMENTS2
            and not message.channel.name.endswith("OOC")
            and not message.webhook_id
        ):
            if message.author.id == 431544605209788416:  # Tupper
                self.bot.msg_cache_add(message)
                await message.delete(delay=3)
            else:
                await self.on_message_proxy(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: RawMessageUpdateEvent):
        if payload.cached_message:
            return

        content: str = payload.data.get("content", "")
        db = self.bot.mongo_db("RP Logs")
        if item := await db.find_one({"id": payload.message_id, "channel": payload.channel_id}):
            w = await self.bot.webhook(item["log-channel"])
            await w.edit_message(item["log"], content=content)

    @commands.Cog.listener()
    async def on_message_edit(self, previous: Message, message: Message):
        """on_message_edit handler

        Parameters
        ----------
        previous : Message
            Previous message
        message : Message
            Message to process
        """
        if not message.guild or previous.content == message.content:
            return

        db = self.bot.mongo_db("RP Logs")
        if message.channel.id == 852180971985043466:
            await self.on_message_submission(message)
        elif (
            isinstance(message.channel, Thread)
            and message.channel.category_id in MAP_ELEMENTS2
            and not message.channel.name.endswith("OOC")
        ):
            if not message.webhook_id:
                await self.on_message_proxy(message)
            elif item := await db.find_one({"id": message.id, "channel": message.channel.id}):
                w = await self.bot.webhook(item["log-channel"])
                await w.edit_message(item["log"], content=message.content)

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: RawThreadUpdateEvent):
        """Detects if threads were archived

        Parameters
        ----------
        payload : RawThreadUpdateEvent
            Information
        """
        if not payload.data["thread_metadata"]["archived"]:
            return

        db = self.bot.mongo_db("Roleplayers")
        key = dict(server=payload.guild_id, id=payload.thread_id)
        if (
            (guild := self.bot.get_guild(payload.guild_id))
            and (data := await db.find_one(key))
            and guild.get_member(data["user"])
        ):
            try:
                if not (thread := payload.thread or guild.get_channel_or_thread(payload.thread_id)):
                    thread: Thread = await guild.fetch_channel(payload.thread_id)
                await thread.edit(archived=False)
            except NotFound:
                await db.delete_one(key)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: RawThreadDeleteEvent) -> None:
        """Detects if threads were removed

        Parameters
        ----------
        payload : RawThreadDeleteEvent
            Information
        """
        if payload.parent_id != 919277769735680050:
            return

        db = self.bot.mongo_db("Roleplayers")
        db2 = self.bot.mongo_db("Characters")
        key = {"server": payload.guild_id}
        await db.delete_one(key | {"id": payload.thread_id})
        await db2.delete_many(key | {"thread": payload.thread_id})

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Detects if ocs or lists were deleted

        Parameters
        ----------
        payload : RawMessageDeleteEvent
            Information
        """
        db = self.bot.mongo_db("Roleplayers")
        db2 = self.bot.mongo_db("Characters")
        key = {"id": payload.message_id}
        key2 = {"server": payload.guild_id}
        await db.delete_one(key | key2)
        await db2.delete_many(key2 | {"$or": [key, {"thread": payload.message_id}]})

        db = self.bot.mongo_db("RP Logs")
        db2 = self.bot.mongo_db("Tupper-logs")
        if item := await db.find_one_and_delete({"id": payload.message_id, "channel": payload.channel_id}):
            log_channel = self.bot.get_channel(item["log-channel"])
            w = await self.bot.webhook(log_channel)
            await db2.delete_one({"channel": log_channel.id, "id": item["log"]})
            await w.delete_message(item["log"])

    @commands.command()
    @commands.guild_only()
    async def oc_image(self, ctx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with ctx.typing():
            data = [x for x in ctx.message.attachments if x.content_type.startswith("image/")]
            image = data[0].proxy_url if data else None
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.collage(ocs, background=image, font=font)
            if file := await self.bot.get_file(url):
                await ctx.reply(file=file)
            else:
                await ctx.reply(content=url)

    @commands.command()
    @commands.guild_only()
    async def oc_rack(self, ctx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with ctx.typing():
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.rack(ocs, font=font)
            view = View()
            for oc in ocs:
                view.add_item(Button(label=oc.name, url=oc.jump_url, emoji=oc.pronoun.emoji))
            if file := await self.bot.get_file(url):
                await ctx.reply(file=file, view=view)
            else:
                await ctx.reply(content=url, view=view)

    @commands.command()
    @commands.guild_only()
    async def oc_rack2(self, ctx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with ctx.typing():
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.rack2(ocs, font=font)
            view = View()
            for index, oc in enumerate(ocs):
                view.add_item(Button(label=oc.name, url=oc.jump_url, row=index // 2, emoji=oc.pronoun.emoji))
            if file := await self.bot.get_file(url):
                await ctx.reply(file=file, view=view)
            else:
                await ctx.reply(content=url, view=view)

    @app_commands.command(name="ocs")
    @app_commands.guilds(719343092963999804)
    async def get_ocs(self, ctx: Interaction, member: Optional[Member | User], character: Optional[CharacterArg]):
        """Allows to show characters

        Parameters
        ----------
        ctx : Interaction
            Interaction
        member : Optional[Member | User]
            Member, if not provided it's current user.
        character : Optional[CharacterArg]
            Search by name, directly
        """
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        if member is None:
            member = ctx.user
        user = self.bot.supporting.get(ctx.user, ctx.user)

        if character:
            if character.author in [ctx.user.id, user.id]:
                view = CreationOCView(bot=self.bot, ctx=ctx, user=user, oc=character)
                await view.handler_send(ephemeral=True)
            else:
                view = PingView(oc=character, reference=ctx)
                await ctx.followup.send(content=character.id, embeds=character.embeds, view=view, ephemeral=True)
            return

        db = self.bot.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(item) async for item in db.find({"author": member.id})]
        ocs.sort(key=lambda x: x.name)
        view = ModCharactersView(member=ctx.user, ocs=ocs, target=ctx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(ephemeral=True):
            if member == ctx.user:
                self.bot.logger.info("User %s is reading their OCs", str(member))
            else:
                self.bot.logger.info("User %s is reading the OCs of %s", str(ctx.user), str(member))

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_role("Moderation")
    async def submit_as(self, ctx: Interaction, member: Optional[User]):
        """Allows to create OCs as an user

        Parameters
        ----------
        ctx : Interaction
            Interaction
        member : Optional[User]
            Member, if not provided, it's current user.
        """
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        if member is None or ctx.user == member:
            self.bot.supporting.pop(ctx.user, None)
            await ctx.followup.send(content="OCs registered now will be assigned to your account.!", ephemeral=True)
        else:
            self.bot.supporting[ctx.user] = member
            await ctx.followup.send(content=f"OCs registered now will be assigned to {member.mention}!", ephemeral=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Submission(bot))
