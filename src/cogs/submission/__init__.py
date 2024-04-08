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
from itertools import zip_longest
from textwrap import wrap
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    File,
    Forbidden,
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
    TextChannel,
    Thread,
    User,
    app_commands,
)
from discord.app_commands import ContextMenu
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, find, get
from rapidfuzz import fuzz, process

from src.cogs.submission.oc_parsers import ParserMethods
from src.cogs.submission.oc_submission import (
    CreationOCView,
    ModCharactersView,
    SubmissionView,
    Template,
)
from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.move import Move
from src.utils.etc import REPLY_EMOJI, WHITE_BAR
from src.utils.functions import name_emoji_from_channel, safe_username
from src.utils.matches import EMOJI_MATCHER, EMOJI_REGEX, TUPPER_REPLY_PATTERN
from src.views.characters_view import PingView
from src.views.move_view import MoveView

__all__ = ("Submission", "setup")


DEFAULT_IMAGE = "https://cdn.discordapp.com/attachments/748384705098940426/1096165342608380054/image.png"


def comparison_handler(before: Character, now: Character):
    for aux1, aux2 in zip_longest(before.embeds, now.embeds, fillvalue=Embed()):
        elem1 = {field.name: (field.value, field.inline) for field in aux1.fields}
        elem2 = {field.name: (field.value, field.inline) for field in aux2.fields}

        e1 = Embed(title=aux1.title, description=aux1.description, color=Color.red())
        e2 = Embed(title=aux2.title, description=aux2.description, color=Color.brand_green())

        if e1.description == e2.description:
            e1.description = e2.description = None

        if before.image != now.image:
            e1.set_image(url=before.image)
            e2.set_image(url=now.image)
        else:
            e1.set_image(url=WHITE_BAR)
            e2.set_image(url=WHITE_BAR)

        if aux1.thumbnail != aux2.thumbnail:
            e1.set_thumbnail(url=aux1.thumbnail)
            e2.set_thumbnail(url=aux2.thumbnail)

        if aux1.footer != aux2.footer:
            e1.set_footer(text=aux1.footer.text, icon_url=aux1.footer.icon_url)
            e2.set_footer(text=aux2.footer.text, icon_url=aux2.footer.icon_url)

        for key in set(elem1) | set(elem2):
            value1, inline1 = elem1.get(key, (None, False))
            value2, inline2 = elem2.get(key, (None, False))
            if value1 != value2:
                if value1:
                    e1.add_field(name=key, value=value1, inline=inline1)
                if value2:
                    e2.add_field(name=key, value=value2, inline=inline2)

        key1 = e1.title, e1.description, e1.image, e1.thumbnail, e1.footer, e1.fields
        key2 = e2.title, e2.description, e2.image, e2.thumbnail, e2.footer, e2.fields

        if key1 != key2:
            if e1.title == e2.title:
                e2.title = None
            yield e1, e2


class Submission(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.data_db: dict[int, dict] = {}
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        self.itx_menu1 = ContextMenu(
            name="Moves & Abilities",
            callback=self.info_checker,
            guild_ids=[952518750748438549, 1196879060173852702],
        )
        self.itx_menu2 = ContextMenu(
            name="Check User's OCs",
            callback=self.check_ocs,
            guild_ids=[952518750748438549, 1196879060173852702],
        )

    async def cog_load(self) -> None:
        self.bot.tree.add_command(self.itx_menu1)
        self.bot.tree.add_command(self.itx_menu2)
        await self.load_submssions()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.itx_menu1.name, type=self.itx_menu1.type)
        self.bot.tree.remove_command(self.itx_menu2.name, type=self.itx_menu2.type)

    async def info_checker(self, itx: Interaction[CustomBot], message: Message):
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        moves: list[SpAbility | Ability | Move] = []
        db = self.bot.mongo_db("Characters")
        if data := await db.find_one({"id": message.id, "server": itx.guild_id}):
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
        view = MoveView(member=itx.user, moves=moves, target=itx, keep_working=True)
        async with view.send(ephemeral=True):
            self.bot.logger.info(
                "User %s is reading the abilities/moves at %s",
                str(itx.user),
                message.jump_url,
            )

    async def check_ocs(self, itx: Interaction[CustomBot], member: Member):
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        db = self.bot.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id, "server": itx.guild_id})]
        view = ModCharactersView(member=itx.user, ocs=ocs, target=itx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(itx.user), str(member))

    async def list_update(
        self,
        member: Object | User | Member,
        server_id: int,
        data: Optional[dict] = None,
    ):
        """This function updates an user's character list message

        Parameters
        ----------
        member : Object
            User to update list
        """
        if isinstance(member, int):
            member = Object(id=member)

        db = self.bot.mongo_db("Roleplayers")

        thread = None

        if not data:
            data = await db.find_one({"user": member.id, "server": server_id})

        data = data or {}

        if not (info := self.data_db.get(server_id)):
            db1 = self.bot.mongo_db("Server")
            info = await db1.find_one(
                {"id": server_id, "oc_list": {"$exists": True}},
                {"_id": 0, "oc_list": 1},
            )

        if not (channel := self.bot.get_channel(info["oc_list"])):
            channel: ForumChannel = await self.bot.fetch_channel(info["oc_list"])

        if data:
            if not (thread := channel.get_thread(data["id"])):
                with suppress(DiscordException):
                    thread: Thread = await channel.guild.fetch_channel(data["id"])

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
                    thread = await thread.edit(name=member.display_name, archived=False)
                    file = await member.display_avatar.with_size(4096).to_file()
                    msg = await msg.edit(content=member.mention, attachments=[file])
            except DiscordException:
                thread = None

        if thread is None:
            if isinstance(member, Object):
                if member_info := channel.guild.get_member(member.id) or self.bot.get_user(member.id):
                    member = member_info
                else:
                    member = await self.bot.fetch_user(member.id)

            if isinstance(member, (User, Member)):
                file = await member.display_avatar.with_size(4096).to_file()
                x = await channel.create_thread(
                    name=member.display_name,
                    content=member.mention,
                    file=file,
                    allowed_mentions=AllowedMentions(users=[member]),
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

    async def register_oc(self, oc: Character, logging: bool = True):
        try:
            member = Object(id=oc.author)
            thread = await self.list_update(member, oc.server)
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
            view = View()
            if oc.location and oc.last_used:
                if not (ch := guild.get_channel_or_thread(oc.location)):
                    ch = await guild.fetch_channel(oc.location)
                msg = ch.get_partial_message(oc.last_used)
                name, emoji = name_emoji_from_channel(ch)
                view.add_item(Button(label=name, emoji=emoji, url=msg.jump_url))
            kwargs["view"] = view

            if not oc.image_url:
                image = oc.image
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

            await db.replace_one(
                {
                    "id": reference_id,
                    "server": oc.server,
                },
                oc.to_mongo_dict(),
                upsert=True,
            )

            if not (info := self.data_db.get(thread.guild.id)):
                db1 = self.bot.mongo_db("Server")
                info = await db1.find_one(
                    {
                        "id": oc.server,
                        "oc_modifications": {"$exists": True},
                        "staff": {"$exists": True},
                    },
                    {"_id": 0, "oc_modifications": 1, "staff": 1},
                )

            if logging and info:
                self.bot.logger.info(
                    "Character has been %s! > %s > %s > %s",
                    word,
                    str(user),
                    repr(oc),
                    oc.document_url or "Manual",
                )

                try:
                    if former:
                        pack_embeds: list[list[Embed]] = []
                        pack_files: list[list[File]] = []
                        log = await self.bot.webhook(info["staff"], reason="Logging")
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
                            for embed1, embed2 in comparison_handler(before=former, now=oc):
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
                                thread=Object(id=info["oc_modifications"]),
                                username=safe_username(username),
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
        thread = await self.list_update(oc.author, oc.server)
        msg = thread.get_partial_message(oc.id)
        try:
            if thread.archived:
                await thread.edit(archived=False)
            await msg.edit(embeds=embeds)
        except NotFound:
            await self.register_oc(oc)

    async def submission_handler(self, message: Interaction[CustomBot] | Message, **msg_data):
        if isinstance(message, Interaction):
            refer_author = message.user
        else:
            refer_author = message.author

        if not (info := self.data_db.get(message.guild.id)):
            info = await self.bot.mongo_db("Server").find_one(
                {
                    "id": message.guild.id,
                    "oc_images": {"$exists": True},
                    "staff": {"$exists": True},
                },
                {"_id": 0, "oc_images": 1, "staff": 1},
            )

        if msg_data and info:
            author: Member = self.bot.supporting.get(refer_author, refer_author)
            if oc := Character.process(**msg_data):
                if isinstance(oc.image, File):
                    w = await self.bot.webhook(info["staff"])
                    msg = await w.send(
                        content=oc.document_url or "",
                        file=oc.image,
                        username=safe_username(author.display_name),
                        avatar_url=author.display_avatar.url,
                        thread=Object(id=info["oc_images"]),
                        wait=True,
                    )
                    if msg.attachments:
                        oc.image = msg.attachments[0].url
                view = CreationOCView(bot=self.bot, itx=message, user=author, oc=oc)
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
        user: Member,
        kwargs: Character | dict[str, Character] = None,
    ):
        channel = message.channel
        author = message.author.name.title()
        db = self.bot.mongo_db("RP Logs")
        db2 = self.bot.mongo_db("Tupper-logs")
        key, oc = message.author.name, Character(author=user.id, server=user.guild.id)
        if kwargs := kwargs or {}:
            if isinstance(kwargs, Character):
                key, oc = kwargs.name, kwargs
            elif item := process.extractOne(
                author,
                choices=kwargs.keys(),
                score_cutoff=85,
            ):
                key, oc = item[0], kwargs[item[0]]
            elif ocs := [(k, v) for k, v in kwargs.items() if k in author or author in k]:
                key, oc = ocs[0]

        if not (
            info_channel := find(
                lambda x: isinstance(x, TextChannel) and x.name.endswith("-logs"),
                channel.category.channels,
            )
        ):
            return

        log_w = await self.bot.webhook(info_channel)

        view = View()
        name, emoji = name_emoji_from_channel(message.channel)
        view.add_item(Button(label=name, url=message.jump_url, emoji=emoji))
        if oc_jump_url := oc.jump_url:
            view.add_item(Button(label=key[:80], url=oc_jump_url, emoji=oc.emoji))
        else:
            view.add_item(Button(label=key[:80], disabled=True))

        phrase = "Replying"
        channel_id, message_id = 0, 0

        if reference := message.reference:
            channel_id, message_id = reference.channel_id, reference.message_id
        elif data := TUPPER_REPLY_PATTERN.search(message.content):
            phrase = data.group("user").strip() or phrase
            content = data.group("content").strip()
            with suppress(ValueError):
                channel_id, message_id = int(data.group("channel")), int(data.group("message"))

        content = message.content
        if channel_id == message_id == 0:
            aux_view = View.from_message(message)
            if items := [
                x
                for x in aux_view.children
                if isinstance(x, Button) and x.url and x.url.startswith("https://discord.com/channels/")
            ]:
                with suppress(ValueError):
                    btn = items[0]
                    channel_id, message_id = map(int, btn.url.split("/")[-2:])
                    phrase = btn.label or phrase

        size = 60 if EMOJI_MATCHER.match(content) else 44
        for item in EMOJI_REGEX.finditer(content):
            match item.groupdict():
                case {"animated": "a", "name": name, "id": id}:
                    if id.isdigit() and not self.bot.get_emoji(int(id)):
                        url = f"[{name}](https://cdn.discordapp.com/emojis/{id}.gif?{size=})"
                        content = EMOJI_REGEX.sub(url, content)
                case {"name": name, "id": id}:
                    if id.isdigit() and not self.bot.get_emoji(int(id)):
                        url = f"[{name}](https://cdn.discordapp.com/emojis/{id}.webp?{size=})"
                        content = EMOJI_REGEX.sub(url, content)

        if channel_id and message_id:
            if item := await db.find_one({"id": message_id, "channel": channel_id}):
                aux = info_channel.get_partial_message(item["log"])
            else:
                ch = self.bot.get_partial_messageable(id=channel_id)
                aux = ch.get_partial_message(message_id)
            view.add_item(Button(label=phrase[:80], url=aux.jump_url, emoji=REPLY_EMOJI))

        for index, paragraph in enumerate(
            text := wrap(
                content or "\u200b",
                2000,
                replace_whitespace=False,
                placeholder="",
            )
        ):
            msg = await log_w.send(
                content=paragraph,
                username=safe_username(message.author.display_name),
                avatar_url=message.author.display_avatar.url,
                files=[await x.to_file() for x in message.attachments],
                allowed_mentions=AllowedMentions.none(),
                view=view if len(text) == index + 1 else MISSING,
                wait=True,
                silent=True,
            )

            await db.insert_one(
                {
                    "id": message.id,
                    "channel": message.channel.id,
                    "log": msg.id,
                    "log-channel": info_channel.id,
                }
            )
            await db2.insert_one(
                {
                    "channel": info_channel.id,
                    "id": msg.id,
                    "author": oc.author,
                }
            )
            if oc.id:
                oc.location, oc.last_used = message.channel.id, message.id
                await self.register_oc(oc, logging=False)

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

        messages: list[Message] = []

        def checker(m: Message):
            if m.webhook_id and message.channel == m.channel:
                messages.append(m)
            return False

        done, pending = await asyncio.wait(
            [
                asyncio.create_task(
                    self.bot.wait_for("message", check=checker, timeout=2),
                    name="Message",
                ),
                asyncio.create_task(
                    self.bot.wait_for("message_edit", check=lambda x, _: x == message),
                    name="Edit",
                ),
                asyncio.create_task(
                    self.bot.wait_for("message_delete", check=lambda x: x == message),
                    name="Delete",
                ),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for future in pending:
            future.cancel()

        for future in done:
            future.exception()

        if any(future.get_name() == "Edit" for future in done):
            return

        if not messages:
            if any(future.get_name() == "Message" for future in done):
                await self.on_message_tupper(message, message.author)
            return

        db = self.bot.mongo_db("Characters")
        kwargs: dict[str, Character] = {}
        async for x in db.find(
            {
                "author": message.author.id,
                "server": message.guild.id if message.guild else 0,
            }
        ):
            oc = Character.from_mongo_dict(x)
            for name in oc.name.split(","):
                if name := name.strip():
                    kwargs[name.split()[0]] = oc
                    kwargs[name] = oc

        attachments = message.attachments
        for msg in sorted(messages, key=lambda x: x.id):
            if data := TUPPER_REPLY_PATTERN.search(msg.content):
                text = str(data.group("content") or msg.content)
            else:
                text = msg.content

            if (
                fuzz.WRatio(text, message.content, score_cutoff=95)
                or text in message.content
                or (
                    attachments
                    and len(attachments) == len(msg.attachments)
                    and all(x.filename == y.filename for x, y in zip(attachments, msg.attachments))
                )
            ):
                await self.on_message_tupper(msg, message.author, kwargs)

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")

        db = self.bot.mongo_db("Server")
        async for item in db.find(
            {
                "oc_submission": {"$exists": True},
                "oc_submission_msg": {"$exists": True},
            },
        ):
            self.data_db[item["id"]] = item
            view = SubmissionView(timeout=None)
            channel = self.bot.get_partial_messageable(id=item["oc_submission"], guild_id=item["id"])
            message = channel.get_partial_message(item["oc_submission_msg"])
            try:
                view.message = await message.edit(view=view)
            except Forbidden:
                w = await self.bot.webhook(channel)
                await w.edit_message(message_id=message.id, view=view)

        self.bot.logger.info("Finished loading Submission menu")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: Thread):
        if not isinstance(parent := thread.parent, ForumChannel) or self.bot.user == thread.owner:
            return

        if not (item := self.data_db.get(thread.guild.id)):
            db = self.bot.mongo_db("Server")
            item = await db.find_one(
                {
                    "id": thread.guild.id,
                    "rp_planning": {"$exists": True},
                    "looking_for_rp": {"$exists": True},
                    "rp_session_log": {"$exists": True},
                },
                {
                    "_id": 0,
                    "no_thread_categories": 1,
                    "rp_planning": 1,
                    "looking_for_rp": 1,
                    "rp_session_log": 1,
                },
            )
            item = item or {}

        if thread.category_id in item.get("no_thread_categories", []):
            return

        await asyncio.sleep(1)
        msg = await thread.get_partial_message(thread.id).fetch()

        if thread.parent_id == item.get("rp_planning"):
            db = self.bot.mongo_db("RP Search Banner")
            if aux := await db.find_one({"author": thread.owner.id, "server": thread.guild.id}):
                image = aux["image"]
            else:
                image = DEFAULT_IMAGE

            ping_role = thread.guild.get_role(item["looking_for_rp"])
            await msg.pin(reason=f"Thread created by {thread.owner}")
            embed = Embed(
                title="Reminder",
                description="> In order to see the User's OCs just hold their username for a while or press right click, you'll see what OCs they have available.\n* </ocs:1197132689292152844>\n* </find:1186936002330243096>",
                color=thread.owner.color,
                timestamp=thread.created_at,
            )
            embed.set_image(url=image)
            embed.set_thumbnail(url=self.bot.user.display_avatar)
            embed.set_footer(text=thread.guild.name, icon_url=thread.guild.icon)
            await msg.reply(
                content=ping_role.mention,
                embed=embed,
                allowed_mentions=AllowedMentions(roles=[ping_role]),
                mention_author=True,
            )
        elif not item.get("no_threading"):
            data = await parent.create_thread(
                name=thread.name,
                content=msg.content[:2000],
                embeds=msg.embeds,
                files=[await x.to_file() for x in msg.attachments],
                applied_tags=thread.applied_tags,
                view=View.from_message(msg),
                reason=str(thread.owner),
                allowed_mentions=AllowedMentions.none(),
            )
            await data.message.pin()
            await data.thread.add_user(thread.owner)
            await thread.delete()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")

        thread = None
        if data := await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member, member.guild.id, data)
            await thread.edit(
                name=member.display_name if thread.name != member.display_name else MISSING,
                reason=f"{thread.name} -> {member.display_name}",
                archived=False,
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")
        if data := await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member, member.guild.id, data)
            await thread.edit(name=member.display_name, reason=f"Member left: {member.display_name}", archived=True)

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.display_name == now.display_name and past.display_avatar == now.display_avatar:
            return
        db = self.bot.mongo_db("Roleplayers")
        if data := await db.find_one({"user": now.id, "server": now.guild.id}):
            thread = await self.list_update(now, now.guild.id, data)
            if thread.name != now.display_name:
                reason = f"{thread.name} -> {now.display_name}."
                await thread.edit(name=now.display_name, reason=reason)

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

        if not (item := self.data_db.get(message.guild.id)):
            db = self.bot.mongo_db("Server")
            item = await db.find_one({"id": message.guild.id})
            item = item or {}

        if message.channel.id == item.get("oc_submission"):
            await self.on_message_submission(message)
        elif (
            (
                message.channel.category_id in item.get("no_thread_categories", [])
                if hasattr(message.channel, "category_id")
                else True
            )
            and not message.channel.name.endswith("OOC")
            and not message.webhook_id
        ):
            if message.application_id and message.application_id != self.bot.user.id:
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

        if not (info := self.data_db.get(message.guild.id)):
            db1 = self.bot.mongo_db("Server")
            info = await db1.find_one(
                {"id": message.guild.id, "oc_submission": {"$exists": True}},
                {"_id": 0, "oc_submission": 1},
            )
            info = info or {}

        if message.channel.id == info.get("oc_submission"):
            await self.on_message_submission(message)
        elif (
            isinstance(message.channel, Thread)
            and message.channel.category_id in info.get("no_thread_categories", [])
            and not message.channel.name.endswith("OOC")
        ):
            if item := await db.find_one({"id": message.id, "channel": message.channel.id}):
                w = await self.bot.webhook(item["log-channel"])
                await w.edit_message(item["log"], content=message.content)
            elif not message.webhook_id:
                await self.on_message_proxy(message)

    @commands.Cog.listener()
    async def on_raw_thread_update(self, payload: RawThreadUpdateEvent):
        """Detects if threads were archived

        Parameters
        ----------
        payload : RawThreadUpdateEvent
            Information
        """
        guild = self.bot.get_guild(payload.guild_id)
        if not (payload.data["thread_metadata"]["archived"] and guild):
            return

        db = self.bot.mongo_db("Roleplayers")

        data: Optional[dict[str, int]] = await db.find_one({"server": guild.id, "id": payload.thread_id})
        if not (data and guild.get_member(data["user"])):
            return

        try:
            if not (thread := payload.thread or guild.get_channel_or_thread(payload.thread_id)):
                thread: Thread = await guild.fetch_channel(payload.thread_id)
            await thread.edit(archived=False)
        except NotFound:
            await db.delete_one(data)

    @commands.Cog.listener()
    async def on_raw_thread_delete(self, payload: RawThreadDeleteEvent) -> None:
        """Detects if threads were removed

        Parameters
        ----------
        payload : RawThreadDeleteEvent
            Information
        """
        db = self.bot.mongo_db("Roleplayers")
        db2 = self.bot.mongo_db("Characters")
        await db.delete_one({"server": payload.guild_id, "id": payload.thread_id})
        await db2.delete_many({"server": payload.guild_id, "thread": payload.thread_id})

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Detects if ocs or lists were deleted

        Parameters
        ----------
        payload : RawMessageDeleteEvent
            Information
        """

        ocs_db = self.bot.mongo_db("Characters")
        if oc_data := await ocs_db.find_one_and_delete({"id": payload.message_id, "server": payload.guild_id}):
            oc = Character.from_mongo_dict(oc_data)
            if not await ocs_db.find_one({"author": oc.author, "server": payload.guild_id}):
                guild = self.bot.get_guild(payload.guild_id)
                if thread := get(guild.threads, id=oc.thread):
                    await thread.delete()

        log_db = self.bot.mongo_db("RP Logs")
        proxy_db = self.bot.mongo_db("Tupper-logs")
        if item := await log_db.find_one_and_delete({"id": payload.message_id, "channel": payload.channel_id}):
            log_channel = self.bot.get_channel(item["log-channel"])
            w = await self.bot.webhook(log_channel)
            await proxy_db.delete_one({"channel": log_channel.id, "id": item["log"]})
            with suppress(DiscordException):
                await w.delete_message(item["log"])

    @app_commands.command(name="ocs")
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def get_ocs(
        self,
        itx: Interaction[CustomBot],
        member: Optional[Member | User],
        character: Optional[CharacterArg],
    ):
        """Allows to show characters

        Parameters
        ----------
        itx : Interaction
            Interaction
        member : Optional[Member | User]
            Member, if not provided it's current user.
        character : Optional[CharacterArg]
            Search by name, directly
        """
        resp: InteractionResponse = itx.response
        await resp.defer(ephemeral=True, thinking=True)
        if member is None:
            member = itx.user
        user = self.bot.supporting.get(itx.user, itx.user)

        if character:
            if character.author in [itx.user.id, user.id]:
                view = CreationOCView(bot=self.bot, itx=itx, user=user, oc=character)
                await view.handler_send(ephemeral=True)
            else:
                view = PingView(oc=character, reference=itx)
                await itx.followup.send(content=character.id, embeds=character.embeds, view=view, ephemeral=True)
            return

        db = self.bot.mongo_db("Characters")
        ocs = [Character.from_mongo_dict(item) async for item in db.find({"author": member.id, "server": itx.guild_id})]
        ocs.sort(key=lambda x: x.name)
        view = ModCharactersView(member=itx.user, ocs=ocs, target=itx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(itx.user), str(member))

    @commands.hybrid_command(name="register", aliases=["create"])
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def register(
        self,
        ctx: commands.Context[CustomBot],
        template: Template = Template.Pokemon,
    ):
        """Allows to create OCs

        Parameters
        ----------
        ctx : commands.Context[CustomBot]
            Context
        template : Template, optional
            Template to use, by default Pokemon
        """
        user: Member = self.bot.supporting.get(ctx.author, ctx.author)
        await ctx.defer(ephemeral=True)
        users = {ctx.author.id, user.id}
        try:
            self.ignore |= users
            view = CreationOCView(bot=self.bot, itx=ctx, user=user, template=template)
            await view.handler_send(ephemeral=True)
            await view.wait()
        except Exception as e:
            await ctx.send(str(e), ephemeral=True)
            self.bot.logger.exception("Character Creation Exception", exc_info=e)
        finally:
            self.ignore -= users

    @commands.command()
    async def addchar(self, ctx: commands.Context[CustomBot], *, text: str = ""):
        """Allows to create OCs from text

        Parameters
        ----------
        ctx : commands.Context[CustomBot]
            Context
        text : str
            Text to parse
        """
        if (
            not ctx.guild
            or ctx.message.mentions
            or ctx.author.bot
            or ctx.author.id in self.ignore
            or ctx.message.stickers
        ):
            return await ctx.reply("Can't use this command with mentions, bots or stickers", delete_after=15)

        self.ignore.add(ctx.author.id)
        try:
            async for item in ParserMethods.parse(text=text, bot=self.bot):
                return await self.submission_handler(ctx, **item)
        except Exception as e:
            self.bot.logger.exception("Exception processing character", exc_info=e)
            await ctx.reply(str(e), delete_after=15)
        finally:
            self.ignore -= {ctx.author.id}

    @app_commands.command()
    @app_commands.checks.has_role("Moderation")
    @app_commands.guilds(952518750748438549, 1196879060173852702)
    async def submit_as(self, itx: Interaction[CustomBot], member: Optional[User]):
        """Allows to create OCs as an user

        Parameters
        ----------
        itx : Interaction
            Interaction
        member : Optional[User]
            Member, if not provided, it's current user.
        """
        resp: InteractionResponse = itx.response
        if member is None or itx.user == member:
            self.bot.supporting.pop(member := itx.user, None)
        else:
            self.bot.supporting[itx.user] = member
        await resp.send_message(
            content=f"OCs registered now will be assigned to {member.mention}!",
            ephemeral=True,
            delete_after=3,
        )


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Submission(bot))
