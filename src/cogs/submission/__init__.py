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

from asyncio import TimeoutError
from contextlib import suppress
from random import choice as random_choice
from typing import Optional, Type

from discord import (
    AllowedMentions,
    Color,
    DiscordException,
    Embed,
    Guild,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    PartialEmoji,
    RawMessageDeleteEvent,
    RawThreadDeleteEvent,
    Status,
    TextStyle,
    Thread,
    User,
    WebhookMessage,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, TextInput, View
from discord.utils import MISSING, utcnow
from rapidfuzz import process

from src.cogs.submission.oc_parsers import ParserMethods
from src.cogs.submission.oc_submission import CreationOCView, ModCharactersView
from src.cogs.submission.submission_view import SubmissionView
from src.pagination.complex import Complex
from src.pagination.text_input import ModernInput
from src.structures.ability import Ability, SpAbility
from src.structures.bot import CustomBot
from src.structures.character import Character, CharacterArg
from src.structures.mon_typing import Typing
from src.structures.move import Move
from src.structures.movepool import Movepool
from src.structures.species import Fakemon, Fusion, Variant
from src.utils.etc import RP_CATEGORIES, WHITE_BAR
from src.utils.imagekit import Fonts, ImageKit
from src.views.ability_view import SPAbilityView
from src.views.characters_view import PingView
from src.views.image_view import ImageView
from src.views.move_view import MoveView
from src.views.movepool_view import MovepoolView
from src.views.rp_view import RPView

__all__ = ("Submission", "setup")


def comparison_handler(before: Character, now: Character):
    aux1, aux2 = before.embed, now.embed

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
        return e1, e2


class Submission(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ignore: set[int] = set()
        self.data_msg: dict[int, Message] = {}
        self.ocs: dict[int, Character] = {}
        self.oc_list: dict[int, int] = {}
        self.supporting: dict[Member, Member] = {}
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
            moves = list(oc.moveset.copy()) + list(oc.abilities.copy())
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
        if len(moves) == 1:
            view = View()
            if url := getattr(moves[0], "url", None):
                view.add_item(Button(label="Click here to check more information at Bulbapedia.", url=url))
            await ctx.followup.send(embed=moves[0].embed, ephemeral=True, view=view)
        elif moves:
            moves.sort(key=lambda x: x.name)
            view = MoveView(member=ctx.user, moves=moves, target=ctx, keep_working=True)
            async with view.send(ephemeral=True):
                self.bot.logger.info("User %s is reading the abilities/moves at %s", str(ctx.user), message.jump_url)
        else:
            await ctx.followup.send("This message does not include abilities or moves.", ephemeral=True)

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
        webhook = await self.bot.webhook(919277769735680050)
        if oc_list := self.oc_list.get(member.id):
            try:
                await webhook.edit_message(oc_list, embed=None)
            except NotFound:
                oc_list = None

        if not oc_list:
            message: WebhookMessage = await webhook.send(
                content=f"<@{member.id}>",
                wait=True,
                allowed_mentions=AllowedMentions(users=True),
            )
            if user := webhook.guild.get_member(member.id):
                thread = await message.create_thread(name=user.display_name)
                await thread.add_user(user)
            else:
                thread = await message.create_thread(name=f"OCs⎱{member.id}")

            self.oc_list[member.id] = oc_list = thread.id
            await message.edit(view=RPView(member.id, self.oc_list))
        return oc_list

    async def register_oc(self, oc: Type[Character], image_as_is: bool = False):
        member = Object(id=oc.author)
        webhook = await self.bot.webhook(919277769735680050)
        try:
            thread_id = self.oc_list[member.id]
        except KeyError:
            thread_id = await self.list_update(member)
        oc.thread = thread_id
        guild: Guild = self.bot.get_guild(oc.server)
        user = guild.get_member(member.id) or member
        embed: Embed = oc.embed
        embed.set_image(url="attachment://image.png")
        kwargs = dict(
            content=f"<@{user.id}>",
            embed=embed,
            thread=Object(id=oc.thread),
            allowed_mentions=AllowedMentions(users=True),
        )

        if not oc.image_url:
            if not image_as_is:
                image = oc.generated_image
            else:
                image = oc.image
            if file := await self.bot.get_file(url=image, filename="image"):
                word = "attachments" if oc.id else "files"
                kwargs[word] = [file]

        if oc.id:
            msg_oc = await webhook.edit_message(oc.id, **kwargs)
            word = "modified"
        else:
            msg_oc = await webhook.send(**kwargs, wait=True)
            word = "registered"

        oc.id = msg_oc.id
        oc.image_url = msg_oc.embeds[0].image.url
        former = self.ocs.pop(oc.id, None)
        self.ocs[oc.id] = oc
        self.bot.logger.info(
            "New character has been %s! > %s > %s > %s",
            word,
            str(user),
            repr(oc),
            oc.document_url or "Manual",
        )
        async with self.bot.database() as conn:
            await oc.update(connection=conn, idx=msg_oc.id)

        try:
            if former and (embeds := comparison_handler(before=former, now=oc)):
                embed1, embed2 = embeds
                files1, embed1 = await self.bot.embed_raw(embed1)
                files2, embed2 = await self.bot.embed_raw(embed2)

                files = files1 + files2
                for index, (e, f) in enumerate(zip(embeds, files)):
                    f.filename = f"image{index}.png"
                    e.set_image(url=f"attachment://{f.filename}")

                log = await self.bot.webhook(1001125143071965204, reason="Logging")
                if isinstance(user, (User, Member)):
                    username, avatar_url = user.display_name, user.display_avatar.url
                else:
                    username, avatar_url = MISSING, MISSING

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

        except Exception as e:
            self.bot.logger.exception("Error when logging oc modification", exc_info=e)

    async def registration(self, ctx: Interaction | Message, oc: Type[Character], worker: Member):
        """This is the function which handles the registration process,
        it will try to autocomplete data it can deduce, or ask about what
        can not be deduced.

        Parameters
        ----------
        ctx : Interaction | Message
            Message that is being interacted with
        oc : Type[Character]
            Character
        worker : Member
            User that interacts
        """

        async def send(text: Optional[str] = None, view: Optional[View] = MISSING, error: bool = False):
            if error:
                embed = Embed(title="Error", description=text, timestamp=utcnow(), color=Color.red())
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/498095663729344514.webp")
            else:
                embed = Embed(title=text, timestamp=utcnow(), color=Color.blurple())
            embed.set_image(url=WHITE_BAR)
            kwargs = dict(view=view, embed=embed)
            if isinstance(ctx, Interaction):
                resp: InteractionResponse = ctx.response
                if not resp.is_done():
                    if isinstance(ctx.channel, Thread) and ctx.channel.archived:
                        await ctx.channel.edit(archived=True)
                    await resp.defer(ephemeral=True, thinking=True)
                return await ctx.followup.send(**kwargs, wait=True, ephemeral=True)

            if not view:
                kwargs["delete_after"] = 5

            try:
                return await ctx.reply(**kwargs)
            except DiscordException:
                return await ctx.channel.send(**kwargs)

        if isinstance(species := oc.species, Fakemon):  # type: ignore
            if not 1 <= len(species.types) <= 2:
                view = Complex(
                    member=worker,
                    target=ctx,
                    values=Typing.all(),
                    max_values=2,
                    timeout=None,
                    parser=lambda x: (str(x), f"Adds the typing {x}"),
                    text_component=TextInput(label="Character's Types", placeholder="Type, Type", required=True),
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
                view = Complex(
                    member=worker,
                    target=ctx,
                    values=values,
                    max_values=1,
                    timeout=None,
                    parser=lambda x: (y := "/".join(i.name for i in x), f"Adds the typing {y}"),
                    text_component=TextInput(
                        label="Fusion Typing",
                        placeholder=" | ".join("/".join(i.name for i in x).title() for x in values),
                        default="/".join(i.name for i in random_choice(values)).title(),
                    ),
                )
                async with view.send(single=True, title="Select Typing") as types:
                    if not types:
                        return
                    species.types = frozenset(types)
            elif oc.types not in values:
                items = ", ".join("/".join(i.name for i in item) for item in values).title()
                await send(f"Invalid typing for the fusion, valid types are {items}", error=True)
                return

        max_ab: int = oc.max_amount_abilities
        oc.abilities = species.abilities
        if not oc.abilities or len(oc.abilities) > max_ab:
            placeholder = ("Ability, " * max_ab).removesuffix(", ")
            default = ", ".join(x.name for x in oc.randomize_abilities)
            ability_view = Complex(
                member=worker,
                values=oc.usable_abilities,
                parser=lambda x: (x.name, x.description),
                target=ctx,
                max_values=max_ab,
                text_component=TextInput(
                    label="Ability",
                    style=TextStyle.paragraph,
                    placeholder=placeholder,
                    default=default,
                ),
            )

            async with ability_view.send(
                title=f"Select the Abilities (Max {max_ab})",
                description="If you press the write button, you can add multiple by adding commas.",
            ) as abilities:
                if not abilities:
                    return
                oc.abilities = frozenset(abilities)
        if len(oc.abilities) > max_ab:
            await send(f"Max Amount of Abilities for the current Species is {max_ab}", error=True)
            return
        if not oc.any_ability_at_first and (
            ability_errors := ", ".join(ability.name for ability in oc.abilities if ability not in species.abilities)
        ):
            await send(f"the abilities [{ability_errors}] were not found in the species", error=True)
            return

        text_view = ModernInput(member=worker, target=ctx)

        if isinstance(species := oc.species, (Variant, Fakemon)):
            view = MovepoolView(target=ctx, member=worker, oc=oc)
            await view.send()
            await view.wait()

        if not oc.moveset or len(oc.moveset) > 6:
            if movepool := species.total_movepool:
                movepool = movepool()
            else:
                movepool = Move.all()

            moves_view = Complex(
                member=worker,
                values=movepool,
                timeout=None,
                target=ctx,
                max_values=6,
                text_component=TextInput(
                    label="Moveset",
                    placeholder="Move, Move, Move, Move, Move, Move",
                    default=", ".join(x.name for x in oc.randomize_moveset),
                ),
            )

            async with moves_view.send(
                title="Select the Moves",
                description="If you press the write button, you can add multiple by adding commas.",
            ) as moves:
                if not moves:
                    return
                oc.moveset = frozenset(moves)

        if oc.url and isinstance(species, (Variant, Fakemon)):
            species.movepool += Movepool(event=oc.moveset)

        if not oc.any_move_at_first:
            moves_movepool = species.total_movepool()
            if move_errors := ", ".join(move.name for move in oc.moveset if move not in moves_movepool):
                await send(f"the moves [{move_errors}] were not found in the movepool", error=True)
                return
        elif len(oc.moveset) > 6:
            await send("Max amount of moves in a pokemon is 6.", error=True)
            return

        if isinstance(oc.sp_ability, SpAbility) and not oc.sp_ability.valid:
            sp_view = SPAbilityView(worker, oc)
            message = await send("Continue with Submission", view=sp_view)
            await sp_view.wait()
            await message.delete(delay=0)
            if sp_view.sp_ability and not sp_view.sp_ability.valid:
                return

            oc.sp_ability = sp_view.sp_ability

        if not (oc.url or oc.backstory):
            async with text_view.handle(
                label="Character's Backstory",
                style=TextStyle.paragraph,
                placeholder=(
                    "Don't worry about having to write too much, this is just a summary of information "
                    "that people can keep in mind when interacting with your character. You can provide "
                    "information about how they are, information of their past, or anything you'd like to add."
                ),
                required=False,
            ) as text:
                if text is None:
                    return
                oc.backstory = text or None

        if not (oc.url or oc.extra):
            async with text_view.handle(
                label="Character's Extra information",
                style=TextStyle.paragraph,
                placeholder=(
                    "In this area, you can write down information you want people to consider when they are rping with them, "
                    "the information can be from either the character's height, weight, if it uses clothes, if the character likes or dislikes "
                    "or simply just writing down that your character has a goal in specific."
                ),
                required=False,
            ) as text:
                if text is None:
                    return
                oc.extra = text or None

        image_view = ImageView(
            member=worker,
            target=ctx,
            default_img=oc.image or oc.default_image,
        )
        async with image_view.send() as image:
            if image is None:
                return
            oc.image = image

        await self.register_oc(oc)

    async def oc_update(self, oc: Type[Character]):
        embed: Embed = oc.embed
        embed.set_image(url="attachment://image.png")
        webhook = await self.bot.webhook(919277769735680050)
        try:
            try:
                await webhook.edit_message(oc.id, embed=embed, thread=Object(id=oc.thread))
            except HTTPException:
                guild = self.bot.get_guild(oc.server)
                if not (thread := guild.get_thread(oc.thread)):
                    thread: Thread = await self.bot.fetch_channel(oc.thread)
                await thread.edit(archived=False)
                await webhook.edit_message(oc.id, embed=embed, thread=thread)
        except NotFound:
            await self.register_oc(oc)

    async def submission_handler(self, message: Interaction | Message, **msg_data):
        if isinstance(message, Interaction):
            refer_author = message.user
        else:
            refer_author = message.author
        if msg_data:
            author = self.supporting.get(refer_author, refer_author)
            if oc := Character.process(**msg_data):
                oc.author = author.id
                oc.server = message.guild.id
                await self.registration(ctx=message, oc=oc, worker=refer_author)
                role = message.guild.get_role(719642423327719434)
                if role and role not in author.roles:
                    await author.add_roles(role, reason=f"Registered by {refer_author}")
                    embed = Embed(
                        title="How to get access to the RP?",
                        description="In order to have access, go to the Maps section and click on the roles.",
                        colour=author.colour,
                        timestamp=utcnow(),
                    )
                    embed.add_field(
                        name="Note",
                        value="You can try to use /ping `<role>` for finding a RP. "
                        "(<#958122815171756042> also works)",
                    )
                    embed.set_image(url=WHITE_BAR)
                    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
                    embed.set_footer(text=message.guild.name, icon_url=message.guild.icon.url)
                    view = View()
                    view.add_item(
                        Button(
                            label="Maps & Roles",
                            url="https://discord.com/channels/719343092963999804/719709333369258015/962830944576864356",
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
                            url="https://discord.com/channels/719343092963999804/958122815171756042/",
                        )
                    )

                    try:
                        await author.send(embed=embed, view=view)
                    except DiscordException:
                        pass

                if isinstance(message, Message):
                    await message.delete(delay=0)

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

        ocs = [item for item in self.ocs.values() if item.author == member_id]

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

        if oc.location != channel.id:
            async with self.bot.database() as db:
                oc.location = channel.id
                await db.execute("UPDATE CHARACTER SET LOCATION = $1 WHERE ID = $2", channel.id, oc.id)
                await self.oc_update(oc)

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

        with suppress(TimeoutError):
            msg: Message = await self.bot.wait_for("message", check=checker, timeout=3)
            await self.on_message_tupper(msg, message.author.id)

    async def load_characters(self):
        async with self.bot.database() as db:
            self.bot.logger.info("Loading all Characters.")
            self.ocs = {oc.id: oc async for oc in Character.fetch_all(db)}
            self.bot.logger.info("Finished loading all characters")

    async def load_profiles(self):
        self.bot.logger.info("Loading All Profiles")
        ch = self.bot.get_channel(919277769735680050)
        async for message in ch.history(limit=None, oldest_first=True):
            if message.webhook_id and message.mentions:
                user = message.mentions[0]
                self.oc_list[user.id] = message.id
                view = RPView(user.id, self.oc_list)
                self.bot.add_view(view=view, message_id=message.id)
        self.bot.logger.info("Finished loading all Profiles.")

    async def load_submssions(self):
        self.bot.logger.info("Loading Submission menu")
        thread: Thread = await self.bot.fetch_channel(961345742222536744)
        webhook = await self.bot.webhook(852180971985043466)
        view = SubmissionView(ocs=self.ocs, supporting=self.supporting)
        async for msg in thread.history(limit=None, oldest_first=True):
            if (embeds := msg.embeds) and msg.webhook_id:
                view.show_template.add_option(
                    label=embeds[0].title,
                    value=str(msg.id),
                    description=embeds[0].footer.text[:100],
                    emoji=PartialEmoji(name="StatusRichPresence", id=842328614883295232),
                )
                msg = await webhook.edit_message(msg.id, thread=thread, view=None)
                view.templates[str(msg.id)] = msg

        await webhook.edit_message(961345742222536744, view=view)
        self.bot.logger.info("Finished loading Submission menu")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_profiles()

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if not (entry := self.oc_list.get(member.id)):
            return
        if not (thread := member.guild.get_thread(entry)):
            thread = await self.bot.fetch_channel(entry)
        if thread.archived:
            await thread.edit(archived=False)
        await thread.edit(name=member.display_name, reason=f"Unknown -> {member.display_name}")

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if not (entry := self.oc_list.get(now.id)) or past.display_name == now.display_name:
            return
        if not (thread := now.guild.get_thread(entry)):
            thread = await self.bot.fetch_channel(entry)
        if thread.archived:
            await thread.edit(archived=False)
        await thread.edit(name=now.display_name, reason=f"{past.display_name} -> {now.display_name}")

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
        async with self.bot.database() as db:
            for oc in ocs:
                self.ocs.pop(oc.id, None)
                self.bot.logger.info(
                    "Character Removed as Thread was removed! > %s - %s > %s",
                    oc.name,
                    repr(oc),
                    oc.document_url or "None",
                )
                await oc.delete(db)

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
        async with self.bot.database() as db:
            for oc in ocs:
                self.ocs.pop(oc.id, None)
                self.bot.logger.info(message, oc.name, repr(oc), oc.document_url or "None")
                await oc.delete(db)

    @commands.command()
    @commands.guild_only()
    async def oc_image(self, ctx: commands.Context, oc_ids: commands.Greedy[int], font: bool = True):
        async with ctx.typing():
            ocs = [self.ocs[x] for x in oc_ids if x in self.ocs]
            kit = ImageKit(base="OC_list_9a1DZPDet.png", width=1500, height=1000)
            for index, oc in enumerate(ocs[:6]):
                x = 500 * (index % 3) + 25
                y = 500 * (index // 3) + 25
                kit.add_image(image=oc.image_url, height=450, width=450, x=x, y=y)
                for index, item in enumerate(oc.types):
                    kit.add_image(image=item.icon, width=200, height=44, x=250 + x, y=y + 44 * index)
                if font:
                    kit.add_text(
                        text=oc.name,
                        width=330,
                        x=x,
                        y=y + 400,
                        background=0xFFFFFF,
                        background_transparency=70,
                        font=Fonts.Whitney_Black,
                        font_size=36,
                    )
                if oc.pronoun.image:
                    kit.add_image(image=oc.pronoun.image, height=120, width=120, x=x + 325, y=y + 325)
            file = await self.bot.get_file(kit.url)
            await ctx.reply(file=file)

    @app_commands.command(name="ocs")
    @app_commands.guilds(719343092963999804)
    async def get_ocs(self, ctx: Interaction, member: Optional[User], character: Optional[CharacterArg]):
        """Allows to show characters

        Parameters
        ----------
        ctx : Interaction
            Interaction
        member : Optional[User]
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
        user = self.supporting.get(ctx.user, ctx.user)

        if character:
            if character.author in [ctx.user.id, user.id]:
                view = CreationOCView(ctx=ctx, user=user, oc=character)
                view.message = await ctx.followup.send(embed=character.embed, view=view, ephemeral=True, wait=True)
            else:
                view = PingView(oc=character, reference=ctx)
                await ctx.followup.send(embed=character.embed, view=view, ephemeral=True)
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
        if not member:
            member = ctx.user
        if ctx.user == member:
            self.supporting.pop(ctx.user, None)
            await ctx.followup.send(content="OCs registered now will be assigned to your account.!", ephemeral=True)
        else:
            self.supporting[ctx.user] = member
            await ctx.followup.send(content=f"OCs registered now will be assigned to {member.mention}!", ephemeral=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Submission(bot))
