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


from asyncio import TimeoutError as AsyncTimeoutError
from contextlib import suppress
from typing import Optional

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    ForumChannel,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    PartialEmoji,
    PartialMessage,
    RawMessageDeleteEvent,
    RawThreadDeleteEvent,
    Status,
    Thread,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, View
from discord.utils import MISSING
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
from src.utils.etc import RP_CATEGORIES, WHITE_BAR
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
        self.ocs: dict[int, Character] = {}
        self.oc_list: dict[int, int] = {}
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
        await self.load_characters()
        await self.load_submssions()

    async def cog_unload(self) -> None:
        self.bot.tree.remove_command(self.ctx_menu1.name, type=self.ctx_menu1.type)
        self.bot.tree.remove_command(self.ctx_menu2.name, type=self.ctx_menu2.type)

    async def info_checker(self, ctx: Interaction, message: Message):
        resp: InteractionResponse = ctx.response
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        moves: list[SpAbility | Ability | Move] = []
        if oc := self.ocs.get(message.id):
            moves = list(oc.moveset) + list(oc.abilities)
            if sp_ability := oc.sp_ability:
                moves.append(sp_ability)
        elif text := message.content:
            items = Move.all() | Ability.all()
            moves = [
                x[0]
                for x in process.extract(
                    text.title(),
                    choices=items,
                    processor=lambda x: getattr(x, "name", x),
                    score_cutoff=60,
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
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        ocs = [oc for oc in self.ocs.values() if oc.author == member.id]
        view = ModCharactersView(member=ctx.user, ocs=ocs, target=ctx, keep_working=True)
        embed = view.embed
        embed.color = member.color
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(ephemeral=True):
            self.bot.logger.info("User %s is reading the OCs of %s", str(ctx.user), str(member))

    async def list_update(self, member: Object):
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
            try:
                thread: Thread = await channel.guild.fetch_channel(item["id"])
            except DiscordException:
                thread = None

        if not thread:
            if isinstance(member, User):
                file = await member.display_avatar.with_size(4096).to_file()
                x = await channel.create_thread(
                    name=member.display_name,
                    content=member.mention,
                    file=file,
                    allowed_mentions=AllowedMentions(users=True),
                )
            else:
                x = await channel.create_thread(
                    content=f"<@{member.id}>",
                    allowed_mentions=AllowedMentions(users=True),
                    name=f"{member.id}",
                )

            thread = x.thread

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

            if reference_id := oc.id:
                thread = await thread.edit(archived=False)
                try:
                    msg_oc = await PartialMessage(channel=thread, id=oc.id).edit(**kwargs)
                    word = "modified"
                except NotFound:
                    msg_oc = await thread.send(**kwargs)
                    word = "registered"
            elif msg_oc := await thread.send(**kwargs):
                reference_id = msg_oc.id
                word = "registered"

            oc.id = msg_oc.id
            oc.image_url = msg_oc.embeds[0].image.url

            former = self.ocs.pop(oc.id, None)
            self.ocs[oc.id] = oc
            self.bot.logger.info(
                "Character has been %s! > %s > %s > %s",
                word,
                str(user),
                repr(oc),
                oc.document_url or "Manual",
            )

            await self.bot.mongo_db("Characters").replace_one(
                {"id": reference_id},
                oc.to_mongo_dict(),
                upsert=True,
            )

            try:
                if former:
                    log = await self.bot.webhook(1001125143071965204, reason="Logging")
                    if isinstance(user, (User, Member)):
                        username, avatar_url = user.display_name, user.display_avatar.url
                    else:
                        username, avatar_url = MISSING, MISSING

                    for embed1, embed2 in zip(*comparison_handler(before=former, now=oc)):
                        embeds = [embed1, embed2]
                        files1, embed1 = await self.bot.embed_raw(embed1, "footer")
                        files2, embed2 = await self.bot.embed_raw(embed2, "footer")

                        files = files1 + files2
                        for index, (e, f) in enumerate(zip(embeds, files)):
                            f.filename = f"image{index}.png"
                            e.set_image(url=f"attachment://{f.filename}")

                        view = View()
                        view.add_item(
                            Button(
                                label="Jump URL",
                                url=former.jump_url,
                                emoji=PartialEmoji(name="IconBuildoverride", id=815459629869826048),
                            )
                        )

                        await log.send(
                            embeds=embeds,
                            files=files,
                            thread=Object(id=1001125684476915852),
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
        thread_id = self.oc_list.get(oc.author, oc.thread)
        channel = await guild.fetch_channel(thread_id)
        msg = PartialMessage(channel=channel, id=oc.id)
        try:
            if channel.archived:
                await channel.edit(archived=False)
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
                await view.send()
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

    async def on_message_tupper(self, message: Message, member_id: int):
        channel = message.channel
        author = message.author.name.title()

        if "Npc" in author or "Narrator" in author:
            return

        if ocs := [item for item in self.ocs.values() if item.author == member_id]:
            if item := process.extractOne(
                author,
                choices=ocs,
                score_cutoff=85,
                processor=lambda x: getattr(x, "name", x),
            ):
                oc = item[0]
            elif ocs := [oc for oc in ocs if oc.name in author or author in oc.name]:
                oc = ocs[0]
            else:
                return

            if isinstance(channel := message.channel, Thread):
                thread_id, channel_id = channel.id, channel.parent_id
            else:
                thread_id, channel_id = None, channel.id

            await self.bot.mongo_db("RP Samples").replace_one(
                {"id": message.id},
                {
                    "id": message.id,
                    "text": message.content,
                    "category": message.channel.category_id,
                    "thread": thread_id,
                    "channel": channel_id,
                    "server": message.guild.id,
                    "created_at": message.created_at,
                    "oc": oc.id,
                },
                upsert=True,
            )

            if oc.location != channel.id:
                oc.location = channel.id
                await self.bot.mongo_db("Characters").replace_one(
                    {"id": oc.id},
                    oc.to_mongo_dict(),
                    upsert=True,
                )

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

        def checker(m: Message):
            if m.webhook_id and message.channel == m.channel:
                if isinstance(content := message.content, str):
                    return m.content in content
                if attachments := message.attachments:
                    return len(attachments) == len(m.attachments)
            return False

        with suppress(AsyncTimeoutError):
            msg: Message = await self.bot.wait_for("message", check=checker, timeout=3)
            await self.on_message_tupper(msg, message.author.id)

    async def load_characters(self):
        self.bot.logger.info("Loading all Characters.")
        data: list[dict] = [x async for x in self.bot.mongo_db("Characters").find({})]
        self.ocs = {oc.id: oc for oc in map(Character.from_mongo_dict, data)}
        self.bot.logger.info("Finished loading all characters")

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")
        view = SubmissionView(timeout=None)
        if not (channel := self.bot.get_channel(852180971985043466)):
            channel = await self.bot.fetch_channel(852180971985043466)
        await PartialMessage(channel=channel, id=1005387453055639612).edit(view=view)
        self.bot.logger.info("Finished loading Submission menu")

    async def load_saved_submissions(self):
        self.bot.logger.info("Loading saved submission menu")
        db = self.bot.mongo_db("OC Creation")
        channel = self.bot.get_channel(852180971985043466)
        for data in await db.find({}).to_list(length=None):
            msg_id, template, author, character, progress = (
                data["id"],
                data["template"],
                data["author"],
                data["character"],
                data["progress"],
            )
            character = Character.from_mongo_dict(character)

            if not (member := channel.guild.get_member(author)):
                member = await self.bot.fetch_user(author)

            message = PartialMessage(channel=channel, id=msg_id)

            view = CreationOCView(
                bot=self.bot,
                ctx=message,
                user=member,
                oc=character,
                template=template,
                progress=progress,
            )

            try:
                message = await message.edit(view=view, embeds=view.embeds)
                view.message = message
                if not character.image_url and (image := message.embeds[0].image):
                    character.image_url = image.url
            except NotFound:
                view.message = message = await channel.send(
                    member.mention,
                    view=view,
                    embeds=view.embeds,
                    allowed_mentions=AllowedMentions(users=True),
                )
                await db.replace_one(data, data | {"id": message.id})

        self.bot.logger.info("Finished loading saved submission menu")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_saved_submissions()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if not (channel := self.bot.get_channel(1019686568644059136)):
            channel: ForumChannel = await self.bot.fetch_channel(1019686568644059136)

        db = self.bot.mongo_db("Roleplayers")

        thread = None
        if item := await db.find_one({"user": member.id}):
            try:
                msg = await PartialMessage(channel=channel, id=item["id"]).fetch()
            except DiscordException:
                await db.delete_one(item)
            else:
                file = await member.display_avatar.to_file()
                await msg.edit(attachments=[file])
                thread = await self.list_update(member)
                await thread.edit(
                    name=member.display_name,
                    reason=f"{thread.name} -> {member.display_name}",
                    archived=False,
                )

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.display_name == now.display_name and past.display_avatar == now.display_avatar:
            return

        if not (channel := self.bot.get_channel(1019686568644059136)):
            channel: ForumChannel = await self.bot.fetch_channel(1019686568644059136)

        db = self.bot.mongo_db("Roleplayers")
        thread = None
        if item := await db.find_one({"user": now.id}):
            try:
                msg = await PartialMessage(channel=channel, id=item["id"]).fetch()
            except DiscordException:
                await db.delete_one(item)
            else:
                if past.display_avatar != now.display_avatar:
                    file = await now.display_avatar.to_file()
                    await msg.edit(attachments=[file])

                if past.display_name != now.display_name:
                    thread = await self.list_update(now)
                    await thread.edit(
                        name=now.display_name,
                        reason=f"{past.name} -> {now.display_name}",
                    )

    @commands.Cog.listener()
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
            and "\N{RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK}" not in message.channel.name
        ):
            if tupper == message.author:
                self.bot.msg_cache_add(message)
                await message.delete(delay=3)
            else:
                await self.on_message_proxy(message)

    @commands.Cog.listener()
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
        ocs = [oc for oc in self.ocs.values() if oc.thread == payload.thread_id]

        if not ocs:
            return

        self.oc_list.pop(ocs[0].author, None)
        db = self.bot.mongo_db("Characters")
        for oc in ocs:
            self.ocs.pop(oc.id, None)
            self.bot.logger.info(
                "Character Removed as Thread was removed! > %s - %s > %s",
                oc.name,
                repr(oc),
                oc.document_url or "None",
            )
            await db.delete_one({"id": oc.id})

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Detects if ocs or lists were deleted

        Parameters
        ----------
        payload : RawMessageDeleteEvent
            Information
        """
        ocs = []
        message = "Character Removed as message was removed! > %s - %s > %s"
        if oc := self.ocs.get(payload.message_id):
            ocs.append(oc)
        elif payload.message_id in self.oc_list.values():
            author_id: int = [k for k, v in self.oc_list.items() if v == payload.message_id][0]
            del self.oc_list[author_id]
            ocs = [oc for oc in self.ocs.values() if oc.author == author_id]
            message = "Character Removed as Thread was removed! > %s - %s > %s"
        if not ocs:
            return
        db = self.bot.mongo_db("Characters")
        for oc in ocs:
            self.ocs.pop(oc.id, None)
            self.bot.logger.info(message, oc.name, repr(oc), oc.document_url or "None")
            await db.delete_one({"id": oc.id})

    @commands.command()
    @commands.guild_only()
    async def oc_image(self, ctx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with ctx.typing():
            data = [x for x in ctx.message.attachments if x.content_type.startswith("image/")]
            image = data[0].proxy_url if data else None
            ocs = [self.ocs[x] for x in oc_ids if x in self.ocs]
            url = Character.collage(ocs, background=image, font=font)
            if file := await self.bot.get_file(url):
                await ctx.reply(file=file)
            else:
                await ctx.reply(content=url)

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
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        if member is None:
            member = ctx.user
        user = self.bot.supporting.get(ctx.user, ctx.user)

        if character:
            if character.author in [ctx.user.id, user.id]:
                view = CreationOCView(bot=self.bot, ctx=ctx, user=user, oc=character)
                await view.send(ephemeral=True)
            else:
                view = PingView(oc=character, reference=ctx)
                await ctx.followup.send(embeds=character.embeds, view=view, ephemeral=True)
            return

        if ocs := [oc for oc in self.ocs.values() if oc.author == member.id]:
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
        else:
            await ctx.followup.send(f"{member.mention} has no characters.", ephemeral=True)

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
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
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
