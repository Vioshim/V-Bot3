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

from typing import Any, Optional, Type, Union

from discord import (
    AllowedMentions,
    Embed,
    Member,
    Message,
    Option,
    OptionChoice,
    Thread,
    WebhookMessage,
)
from discord.commands import Permission, SlashCommandGroup
from discord.ext.commands import Cog
from jishaku.codeblocks import codeblock_converter
from yaml import safe_load
from yaml.parser import ParserError

from src.enums import Abilities, Moves, Pronoun, Species, Types
from src.pagination.boolean import BooleeanView
from src.pagination.complex import ComplexInput
from src.pagination.text_input import TextInput
from src.structures.ability import SpAbility
from src.structures.bot import CustomBot
from src.structures.character import (
    Character,
    FakemonCharacter,
    FusionCharacter,
    LegendaryCharacter,
    MegaCharacter,
    MythicalCharacter,
    PokemonCharacter,
    UltraBeastCharacter,
    doc_convert,
    fetch_all,
    kind_deduce,
)
from src.structures.movepool import Movepool
from src.structures.species import (
    Fakemon,
    Fusion,
    Legendary,
    Mega,
    Mythical,
    Pokemon,
)
from src.structures.species import Species as SpeciesBase
from src.structures.species import UltraBeast
from src.type_hinting.context import ApplicationContext, AutocompleteContext
from src.utils.etc import WHITE_BAR
from src.utils.functions import common_pop_get
from src.utils.matches import G_DOCUMENT
from src.views.image_view import ImageView
from src.views.stats_view import StatsView


def detection(kind: Type[SpeciesBase]):
    """This method is used to provide an autocomplete
    depending on the desired kind

    Parameters
    ----------
    kind : Type[SpeciesBase]
        Species to search
    """

    def inner(ctx: AutocompleteContext) -> list[OptionChoice]:
        """Inner method for searching

        Parameters
        ----------
        ctx : AutocompleteContext
            Context

        Returns
        -------
        list[OptionChoice]
            Options that matches the criteria
        """
        data = ctx.value or ""
        elements = []
        for item in Species:
            if not item.banned and item.name.startswith(data.title()):
                if isinstance(item.value, kind):
                    elements.append(OptionChoice(item.name, item.id))

        return elements

    return inner


class Submission(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready: bool = False
        self.check_oc: Optional[Character] = None

        # Msg ID - Character
        self.ocs: dict[int, Character] = {}
        # User ID - set[Character]
        self.rpers: dict[int, set[Character]] = {}
        # User ID - Thread ID / List Message ID
        self.oc_list: dict[int, int] = {}

    @Cog.listener()
    async def on_ready(self):
        """This method loads all the characters from the database."""
        async with self.bot.database() as db:
            self.oc_list = dict(
                await db.fetch(
                    """--sql
                    SELECT AUTHOR, ID
                    FROM THREAD_LIST
                    WHERE SERVER = $1;
                    """,
                    719343092963999804,
                )
            )
            for oc in await fetch_all(db):
                self.ocs[oc.id] = oc
                self.rpers.setdefault(oc.author, set())
                self.rpers[oc.author].add(oc)
            self.bot.logger.info("All ocs were loaded")
            self.ready = True

    register = SlashCommandGroup(
        "register",
        "Command used for registering characters",
        [719343092963999804],
        permissions=[Permission("owner", 2, True)],
    )

    async def list_update(self, member: Member):
        embed = Embed(
            title="Registered Characters",
            color=member.color,
        )
        guild = member.guild
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        embed.set_author(name=member.display_name)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=WHITE_BAR)
        # view = RPView(self.bot, author, self.oc_list)
        webhook = await self.bot.fetch_webhook(919280056558317658)
        if not (oc_list := self.oc_list.get(member.id, None)):
            async with self.bot.database() as db:
                message: WebhookMessage = await webhook.send(
                    content=member.mention,
                    wait=True,
                    embed=embed,
                    allowed_mentions=AllowedMentions(users=True),
                    view=None,
                )
                thread = await message.create_thread(name=f"OCs⎱{member.id}")
                self.oc_list[member.id] = thread.id
                # await message.edit(view=view)
                await db.execute(
                    """--sql
                    INSERT INTO THREAD_LIST(ID, AUTHOR, SERVER)
                    VALUES ($1, $2, $3);
                    """,
                    thread.id,
                    member.id,
                    guild.id,
                )
        else:
            await webhook.edit_message(oc_list, embed=embed, view=None)

    async def registration(
        self,
        ctx: Union[ApplicationContext, Message],
        oc: Type[Character],
        sp_ability: bool = True,
        moveset: bool = True,
    ):
        async def ctx_send(
            msg: str, delete_after: int = None
        ) -> Optional[Message]:
            """This is a handler for sending messages depending on the context

            Parameters
            ----------
            msg : str
                message to send
            delete_after : int, optional
                If it will be deleted after some time, by default None

            Returns
            -------
            Optional[Message]
                If non interaction, returns the message
            """
            if isinstance(ctx, ApplicationContext):
                await ctx.respond(msg, ephemeral=True)
                return
            return await ctx.channel.send(msg, delete_after=delete_after)

        if not self.ready:
            await ctx_send(
                "Bot is restarting, please be patient", delete_after=5
            )
            return

        if oc.url:
            await ctx_send(
                "Character has been loaded successfully", delete_after=5
            )
        else:
            text_view = TextInput(
                bot=self.bot,
                member=ctx.author,
                target=ctx,
                required=True,
            )
            await ctx_send("Starting submission process", delete_after=5)

            if isinstance(oc, FakemonCharacter):
                stats_view = StatsView(
                    bot=self.bot,
                    member=ctx.author,
                    target=ctx,
                )
                async with stats_view:
                    if not (stats := stats_view.choice):
                        return
                    oc.species.set_stats(*stats.value)

                types = None
                while types is None:
                    text_view.embed.title = (
                        "Write the character's types (Min 1, Max 2)"
                    )
                    text_view.embed.description = "For example: Fire, Psychic"
                    async with text_view.send(required=True) as answer:
                        if not answer:
                            return
                        types = Types.deduce(answer)
                        if 1 <= len(types) <= 2:
                            oc.types = types
                        else:
                            types = None

            if isinstance(oc, FusionCharacter):
                pass  # Ask for the typing

            if not oc.abilities:
                max_ab = oc.species.abilities
                ability_view = ComplexInput(
                    bot=self.bot,
                    member=ctx.author,
                    values=oc.species.abilities,
                    target=ctx,
                    max_values=max_ab,
                )
                ability_view.embed.title = (
                    f"Select the Abilities (Max {max_ab})"
                )
                if max_ab == 2:
                    ability_view.embed.description = "If you press the write button, you can add multiple by adding commas."

                async with ability_view as abilities:
                    if not abilities:
                        return
                    oc.abilities = frozenset(abilities)

            if sp_ability and oc.can_have_special_abilities:
                bool_view = BooleeanView(
                    bot=self.bot, member=ctx.author, target=ctx
                )
                bool_view.embed.title = (
                    "Does the character have an Special Ability?'"
                )
                bool_view.embed.description = (
                    "Special abilities are basically unique traits that their OC's kind usually can't do,"
                    " it's like being born with an unique power that could have been obtained by different"
                    " reasons, they are known for having pros and cons."
                )
                async with bool_view.send() as answer:
                    if answer is None:
                        return
                    if answer:
                        data: dict[str, str] = {}
                        for item in [
                            "name",
                            "description",
                            "method",
                            "pros",
                            "cons",
                        ]:
                            if item == "method":
                                word = "origin"
                            text_view.embed.title = (
                                f"Special Ability's {word.title()}"
                            )
                            text_view.embed.description = f"Here you'll define the Special Ability's {word.title()}, make sure it is actually understandable."
                            async with text_view.send(required=True) as answer:
                                if not answer:
                                    return
                                data[item] = answer
                        oc.sp_ability = SpAbility(**data)

            if moveset and not oc.moveset:
                if not (movepool := oc.movepool):
                    movepool = Movepool(event=frozenset(Moves))

                moves_view = ComplexInput(
                    bot=self.bot,
                    member=ctx.author,
                    values=movepool(),
                    timeout=None,
                    target=ctx,
                    max_values=6,
                )
                moves_view.embed.title = "Select the Moves (Max 6)"
                moves_view.embed.description = "If you press the write button, you can add multiple by adding commas."

                async with moves_view as moves:
                    if not moves:
                        return
                    oc.moveset = frozenset(moves)

                if isinstance(oc, FakemonCharacter):
                    oc.species.movepool = Movepool(event=oc.moveset)

            move_errors: set[Moves] = set()
            for item in oc.moveset:
                if item not in oc.movepool:
                    move_errors.add(item)

            if text := ", ".join(i.value.name for i in move_errors):
                await ctx_send(
                    f"the moves [{text}] were not found in the movepool"
                )
                return

            # Ask for backstory
            text_view.embed.title = "Character's backstory"
            text_view.embed.description = (
                "Don't worry about having to write too much, this is just a summary of information "
                "that people can keep in mind when interacting with your character. You can provide "
                "information about how they are, information of their past, or anything you'd like to add."
            )
            async with text_view.send() as text:
                if text is None:
                    return
                oc.backstory = text

            text_view.embed.title = "Character's extra information"
            text_view.embed.description = (
                "In this area, you can write down information you want people to consider when they are rping with them, "
                "the information can be from either the character's height, weight, if it uses clothes, if the character likes or dislikes "
                "or simply just writing down that your character has a goal in specific."
            )
            async with text_view.send() as text:
                if text is None:
                    return
                oc.extra = text

            if not oc.image:
                image_view = ImageView(
                    bot=self.bot,
                    member=ctx.author,
                    target=ctx,
                    default_img=oc.default_image,
                )
                async with image_view.send() as image:
                    if image is None:
                        return
                    oc.image = image
                if received := image_view.received:
                    await received.delete(delay=10)

        await self.list_update(ctx.author)
        webhook = await self.bot.fetch_webhook(919280056558317658)
        thread_id = self.oc_list[ctx.author.id]
        thread: Thread = await self.bot.fetch_channel(thread_id)
        oc.thread = thread.id
        if file := await self.bot.get_file(
            url=oc.generated_image, filename="image"
        ):
            embed: Embed = oc.embed
            embed.set_image(url=f"attachment://{file.filename}")
            msg_oc = await webhook.send(
                content=ctx.author.mention,
                embed=embed,
                file=file,
                thread=thread,
                allowed_mentions=AllowedMentions(users=True),
                wait=True,
            )
            oc.image = msg_oc.embeds[0].image.url
            self.check_oc = oc
            self.rpers.setdefault(ctx.author.id, frozenset())
            self.rpers[ctx.author.id].add(oc)
            self.ocs[oc.id] = oc
            self.bot.logger.info(
                "New character registered! > %s > %s > %s",
                str(ctx.author),
                str(type(oc)),
                oc.url or "Manual",
            )
            async with self.bot.database() as conn:
                await oc.update(connection=conn, idx=msg_oc.id)

    @register.command()
    async def document(self, ctx: ApplicationContext, url: str):
        if not (doc_data := G_DOCUMENT.match(url)):
            return await ctx.respond(
                "That's not a google document", ephemeral=True
            )
        msg_data = await doc_convert(doc_data.group(1))
        if oc := await self.process(**msg_data):
            oc.author = ctx.author.id
            await self.registration(ctx=ctx, oc=oc)

    @register.command()
    async def pokemon(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Select the species.",
            autocomplete=detection(Pokemon),
        ),
        age: Option(
            int,
            description="Age. Use 0 if unknown",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[species]
        oc = PokemonCharacter(
            name=name.title(),
            author=ctx.author.id,
            species=mon,
            thread=self.oc_list.get(ctx.author.id),
            server=ctx.guild_id,
            age=age,
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @register.command()
    async def legendary(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Select the species.",
            autocomplete=detection(Legendary),
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[species]
        oc = LegendaryCharacter(
            name=name.title(),
            species=mon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @register.command()
    async def mythical(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Select the species.",
            autocomplete=detection(Mythical),
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[species]
        oc = MythicalCharacter(
            name=name.title(),
            species=mon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @register.command()
    async def ultra_beast(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Select the species.",
            autocomplete=detection(UltraBeast),
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[species]
        oc = UltraBeastCharacter(
            name=name.title(),
            species=mon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @register.command()
    async def mega(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Select the species.",
            autocomplete=detection(Mega),
        ),
        age: Option(
            int,
            description="Character's age",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[species]
        oc = MegaCharacter(
            name=name.title(),
            species=mon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @register.command()
    async def fusion(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species1: Option(
            str,
            description="Select the species 1.",
            autocomplete=detection(SpeciesBase),
        ),
        species2: Option(
            str,
            description="Select the species 2.",
            autocomplete=detection(SpeciesBase),
        ),
        age: Option(
            int,
            description="Character's age",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)

        mon1, mon2 = Species[species1], Species[species2]
        if mon1 == mon2:
            return await ctx.respond(
                "Both species are the same", ephemeral=True
            )
        oc = FusionCharacter(
            name=name.title(),
            species=Fusion(mon1, mon2),
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            age=age,
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    fakemon = register.create_subgroup(
        description="This is for creating a fakemon."
    )

    @fakemon.command(name="Common")
    async def fakemon_common(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Name of the Species",
        ),
        age: Option(
            int,
            description="Character's age",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        fakemon = Fakemon(name=species.title())
        oc = FakemonCharacter(
            name=name.title(),
            species=fakemon,
            author=ctx.author.id,
            thread=self.oc_list.get(ctx.author.id),
            server=ctx.guild_id,
            age=age,
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc)

    @fakemon.command(name="Legendary")
    async def fakemon_legendary(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Species' name.",
        ),
    ):
        await ctx.defer(ephemeral=True)
        fakemon = Fakemon(name=species.title())
        oc = FakemonCharacter(
            name=name.title(),
            species=fakemon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc, sp_ability=False)

    @register.command(name="Mythical")
    async def fakemon_mythical(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Species' name.",
        ),
    ):
        await ctx.defer(ephemeral=True)
        fakemon = Fakemon(name=species.title())
        oc = FakemonCharacter(
            name=name.title(),
            species=fakemon,
            author=ctx.author.id,
            server=ctx.guild_id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc, sp_ability=False)

    @register.command(name="Ultra Beast")
    async def fakemon_ultra_beast(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        species: Option(
            str,
            description="Species' name.",
        ),
    ):
        await ctx.defer(ephemeral=True)
        fakemon = Fakemon(
            name=species.title(),
            abilities=frozenset(
                {Abilities.BEASTBOOST},
            ),
        )
        oc = FakemonCharacter(
            name=name.title(),
            species=fakemon,
            server=ctx.guild_id,
            author=ctx.author.id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
        )
        await self.registration(ctx, oc, sp_ability=False)

    @register.command(name="Mega")
    async def fakemon_mega(
        self,
        ctx: ApplicationContext,
        name: str,
        pronoun: Option(
            str,
            description="Preferred pronoun",
            choices=[item.name for item in Pronoun],
        ),
        mega: Option(
            str,
            description="Select the species.",
            autocomplete=detection(Pokemon),
        ),
        age: Option(
            int,
            description="Character's age",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)
        mon = Species[mega]
        fakemon = Fakemon(
            name=f"Mega {mon.value.name}",
            movepool=mon.movepool,
        )
        oc = FakemonCharacter(
            name=name.title(),
            species=fakemon,
            server=ctx.guild_id,
            author=ctx.author.id,
            thread=self.oc_list.get(ctx.author.id),
            pronoun=Pronoun[pronoun],
            age=age,
        )
        await self.registration(ctx, oc, sp_ability=False)

    async def process(self, **kwargs):
        data: dict[str, Any] = {k.lower(): v for k, v in kwargs.items()}
        fakemon_mode: bool = "fakemon" in data
        if species_name := common_pop_get(
            data,
            "fakemon",
            "species",
            "fusion",
        ):
            if species := Species.deduce(
                species_name,
                fakemon_mode=fakemon_mode,
            ):
                data["species"] = species

        if types := common_pop_get(data, "types", "type"):
            data["types"] = frozenset(Types.deduce(types))

        if abilities := common_pop_get(data, "abilities", "ability"):
            data["abilities"] = frozenset(Abilities.deduce(abilities))

        if moveset := common_pop_get(data, "moveset", "moves"):
            data["moveset"] = frozenset(Moves.deduce(moveset))

        data["pronoun"] = Pronoun.deduce(data.get("pronoun", "Them"))
        if isinstance(age := data.get("age"), str):
            data["age"] = int(age)

        if isinstance(species := data["species"], Fakemon):
            if stats := data.pop("stats", {}):
                species.set_stats(**stats)

            if movepool := data.pop("movepool", {}):
                species.movepool.from_dict(**movepool)
            else:
                species.movepool = Movepool(event=frozenset(moveset))

        data = {k: v for k, v in data.items() if v}

        return kind_deduce(data.get("species"), **data)

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """This method processes character submissions

        Attributes
        ----------
        message : Message
            Message to process
        """
        if message.channel.id != 852180971985043466:
            return
        if message.author.bot:
            return
        text: str = codeblock_converter(message.content or "").content
        if doc_data := G_DOCUMENT.match(text):
            msg_data = await doc_convert(doc_data.group(1))
        else:
            try:
                msg_data = safe_load(text)
            except ParserError:
                return
        if images := message.attachments:
            msg_data["image"] = images[0].url

        if msg_data:
            if oc := await self.process(**msg_data):
                oc.author = message.author.id
                await self.registration(ctx=message, oc=oc)
                await message.delete()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    bot.add_cog(Submission(bot))
