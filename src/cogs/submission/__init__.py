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
from textwrap import wrap
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
    TextChannel,
    Thread,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING, find, get
from rapidfuzz import fuzz, process

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
from src.utils.etc import (
    LINK_EMOJI,
    MAP_ELEMENTS2,
    REPLY_EMOJI,
    SETTING_EMOJI,
    WHITE_BAR,
)
from src.utils.functions import safe_username
from src.utils.matches import EMOJI_MATCHER, EMOJI_REGEX, TUPPER_REPLY_PATTERN
from src.views.characters_view import PingView
from src.views.move_view import MoveView

__all__ = ("Submission", "setup")


ENTRIES = set(MAP_ELEMENTS2) | {740552350703550545, 740567496721039401}


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

        e1 = Embed(title=aux1.title, description=aux1.description)
        e2 = Embed(title=aux2.title, description=aux2.description)
        e1.set_image(url=WHITE_BAR)
        e2.set_image(url=WHITE_BAR)

        img1 = before.image_url or before.image
        img2 = now.image_url or now.image

        if img1 != img2:
            if isinstance(img1, str):
                e1.set_image(url=img1)
            if isinstance(img2, str):
                e2.set_image(url=img2)

        if aux1.thumbnail != aux2.thumbnail:
            if aux1.thumbnail:
                e1.set_thumbnail(url=aux1.thumbnail.url)
            if aux2.thumbnail:
                e2.set_thumbnail(url=aux2.thumbnail.url)

        if aux1.footer != aux2.footer:
            e1.set_footer(text=aux1.footer.text, icon_url=aux1.footer.icon_url)
            e2.set_footer(text=aux2.footer.text, icon_url=aux2.footer.icon_url)

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

        if e1 != e2:
            if e1.title == e2.title:
                e2.title = None
            e1.color, e2.color = Color.red(), Color.brand_green()
            aux1_new.append(e1)
            aux2_new.append(e2)

    return aux1_new, aux2_new


class Submission(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        guild_ids = [719343092963999804]
        self.itx_menu1 = app_commands.ContextMenu(
            name="Moves & Abilities",
            callback=self.info_checker,
            guild_ids=guild_ids,
        )
        self.itx_menu2 = app_commands.ContextMenu(
            name="Check User's OCs",
            callback=self.check_ocs,
            guild_ids=guild_ids,
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
        ocs = [Character.from_mongo_dict(x) async for x in db.find({"author": member.id})]
        view = ModCharactersView(member=itx.user, ocs=ocs, target=itx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(itx.user), str(member))

    async def list_update(self, member: Object | User | Member, data: Optional[dict] = None):
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

        if not data:
            data = await db.find_one({"user": member.id, "server": channel.guild.id})

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
                    thread = await thread.edit(name=member.display_name, applied_tags=tags[:5], archived=False)
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

    async def register_oc(self, oc: Character, image_as_is: bool = False, logging: bool = True):
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
            view = View()
            if oc.location and oc.last_used:
                if not (ch := guild.get_channel_or_thread(oc.location)):
                    ch = await guild.fetch_channel(oc.location)
                msg = ch.get_partial_message(oc.last_used)
                try:
                    name = ch.name.replace("»", "")
                    emoji, name = name.split("〛")
                except ValueError:
                    emoji, name = SETTING_EMOJI, ch.name
                finally:
                    name = name.replace("-", " ")
                view.add_item(Button(label=name, emoji=emoji, url=msg.jump_url))
            kwargs["view"] = view

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

            await db.replace_one({"id": reference_id}, oc.to_mongo_dict(), upsert=True)

            if logging:
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
        thread = await self.list_update(oc.author)
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
        if msg_data:
            author = self.bot.supporting.get(refer_author, refer_author)
            if oc := Character.process(**msg_data):
                if isinstance(oc.image, File):
                    w = await self.bot.webhook(1020151767532580934)
                    msg = await w.send(
                        content=oc.document_url,
                        file=oc.image,
                        username=safe_username(author.display_name),
                        avatar_url=author.display_avatar.url,
                        thread=Object(id=1045687852069040148),
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

        try:
            name = message.channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, message.channel.name
        finally:
            name = name.replace("-", " ")

        view = View()
        view.add_item(Button(label=name[:80], url=message.jump_url, emoji=emoji))
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
                    self.bot.wait_for("message", check=checker),
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
                asyncio.create_task(
                    asyncio.sleep(2),
                    name="Timeout",
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
            if any(future.get_name() == "Timeout" for future in done):
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
                text = str(data.group("content")).strip()
            else:
                text = msg.content

            if not (
                fuzz.WRatio(text, message.content, score_cutoff=95)
                or (
                    attachments
                    and len(attachments) == len(msg.attachments)
                    and all(x.filename == y.filename for x, y in zip(attachments, msg.attachments))
                )
            ):
                continue

            await self.on_message_tupper(msg, message.author, kwargs)

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")
        view = SubmissionView(timeout=None)
        channel = self.bot.get_partial_messageable(id=852180971985043466, guild_id=719343092963999804)
        message = channel.get_partial_message(1005387453055639612)
        view.message = await message.edit(view=view)
        self.bot.logger.info("Finished loading Submission menu")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: Thread):
        if (
            not isinstance(parent := thread.parent, ForumChannel)
            or thread.category_id not in ENTRIES
            or self.bot.user == thread.owner
        ):
            return

        await asyncio.sleep(1)
        msg = await thread.get_partial_message(thread.id).fetch()

        if thread.parent_id != 1061008601335992422:
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
            return await thread.delete()

        db = self.bot.mongo_db("RP Search Banner")
        if item := await db.find_one({"author": thread.owner.id}):
            image = item["image"]
        else:
            image = "https://cdn.discordapp.com/attachments/748384705098940426/1096165342608380054/image.png"

        await msg.pin(reason=f"Thread created by {thread.owner}")
        embed = Embed(
            title="Reminder",
            description="> In order to see the User's OCs just hold their username for a while or press right click, you'll see what OCs they have available. </ocs:1017242400705490985> </find:1022520398488817686>",
        )
        embed.color, embed.timestamp = thread.owner.color, thread.created_at
        embed.set_image(url=image)
        embed.set_thumbnail(url=self.bot.user.display_avatar)
        embed.set_footer(text=thread.guild.name, icon_url=thread.guild.icon)
        await thread.send(embed=embed)
        w = await self.bot.webhook(thread)

        embed = Embed(
            title=thread.name,
            description=msg.content,
            color=thread.owner.color,
            timestamp=thread.created_at,
        )

        if images := [x for x in msg.attachments if str(x.content_type).startswith("image/")]:
            embed.set_thumbnail(url=images[0].url)

        embed.set_image(url=image)
        applied_tags = sorted(thread.applied_tags, key=lambda x: x.name)

        tags = ", ".join(x.name for x in applied_tags) or None
        embed.set_footer(text=f"Tags: {tags}")

        view = View()
        view.add_item(Button(label="Check Thread", url=msg.jump_url, emoji=LINK_EMOJI))

        await w.send(
            embed=embed,
            username=safe_username(thread.owner.display_name),
            avatar_url=thread.owner.display_avatar.url,
            thread=Object(id=1061010425136828628),
            view=view,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")

        thread = None
        if data := await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member, data)
            await thread.edit(
                name=member.display_name if thread.name != member.display_name else MISSING,
                reason=f"{thread.name} -> {member.display_name}",
                archived=False,
            )

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        db = self.bot.mongo_db("Roleplayers")
        if data := await db.find_one({"user": member.id, "server": member.guild.id}):
            thread = await self.list_update(member, data)
            await thread.edit(name=member.display_name, reason=f"Member left: {member.display_name}", archived=True)

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.display_name == now.display_name and past.display_avatar == now.display_avatar:
            return
        db = self.bot.mongo_db("Roleplayers")
        if data := await db.find_one({"user": now.id, "server": now.guild.id}):
            thread = await self.list_update(now, data)
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

        if message.channel.id == 852180971985043466:
            await self.on_message_submission(message)
        elif (
            (message.channel.category_id in MAP_ELEMENTS2 if hasattr(message.channel, "category_id") else True)
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
        if payload.parent_id != 919277769735680050:
            return

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

                role = get(guild.roles, name="Registered")
                member = get(guild.members, id=oc.author)

                if role and member and role in member.roles:
                    await member.remove_roles(role, reason="0 Characters")

        log_db = self.bot.mongo_db("RP Logs")
        proxy_db = self.bot.mongo_db("Tupper-logs")
        if item := await log_db.find_one_and_delete({"id": payload.message_id, "channel": payload.channel_id}):
            log_channel = self.bot.get_channel(item["log-channel"])
            w = await self.bot.webhook(log_channel)
            await proxy_db.delete_one({"channel": log_channel.id, "id": item["log"]})
            with suppress(DiscordException):
                await w.delete_message(item["log"])

    @commands.command()
    @commands.guild_only()
    async def oc_image(self, itx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with itx.typing():
            data = [x for x in itx.message.attachments if x.content_type.startswith("image/")]
            image = data[0].proxy_url if data else None
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.collage(ocs, background=image, font=font)
            if file := await self.bot.get_file(url):
                await itx.reply(file=file)
            else:
                await itx.reply(content=url)

    @commands.command()
    @commands.guild_only()
    async def oc_rack(self, itx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with itx.typing():
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.rack(ocs, font=font)
            view = View()
            for oc in ocs:
                view.add_item(Button(label=oc.name[:80], url=oc.jump_url, emoji=oc.emoji))
            if file := await self.bot.get_file(url):
                await itx.reply(file=file, view=view)
            else:
                await itx.reply(content=url, view=view)

    @commands.command()
    @commands.guild_only()
    async def oc_rack2(self, itx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with itx.typing():
            db = self.bot.mongo_db("Characters")
            ocs = [Character.from_mongo_dict(item) async for item in db.find({"id": {"$in": oc_ids}})]
            ocs.sort(key=lambda x: x.id)
            url = Character.rack2(ocs, font=font)
            view = View()
            for index, oc in enumerate(ocs):
                view.add_item(Button(label=oc.name[:80], url=oc.jump_url, row=index // 2, emoji=oc.emoji))
            if file := await self.bot.get_file(url):
                await itx.reply(file=file, view=view)
            else:
                await itx.reply(content=url, view=view)

    @app_commands.command(name="ocs")
    @app_commands.guilds(719343092963999804)
    async def get_ocs(
        self, itx: Interaction[CustomBot], member: Optional[Member | User], character: Optional[CharacterArg]
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
        ocs = [Character.from_mongo_dict(item) async for item in db.find({"author": member.id})]
        ocs.sort(key=lambda x: x.name)
        view = ModCharactersView(member=itx.user, ocs=ocs, target=itx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(itx.user), str(member))

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_role("Moderation")
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
