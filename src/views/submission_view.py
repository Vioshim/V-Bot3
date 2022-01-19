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

from contextlib import suppress
from typing import Type, Union

from discord import (
    AllowedMentions,
    ButtonStyle,
    CategoryChannel,
    DiscordException,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    TextChannel,
)
from discord.ui import Button, Select, View, button, select
from yaml import dump

from src.cogs.submission.oc_modification import ModifyView
from src.pagination.complex import Complex, ComplexInput
from src.pagination.text_input import TextInput
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.structures.mission import Mission
from src.utils.etc import DICE_NUMBERS, RP_CATEGORIES
from src.views.mission_view import MissionView


class CharacterHandlerView(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: Interaction,
        values: set[Character],
    ):
        super(CharacterHandlerView, self).__init__(
            bot=bot,
            member=member,
            target=target,
            values=values,
            parser=lambda x: (x.name, repr(x)),
            timeout=None,
            sort_key=lambda x: x.name,
        )

    async def custom_choice(self, sct: Select, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        data: list[Type[Character]] = list(self.choices)
        view = ModifyView(
            bot=self.bot,
            member=interaction.user,
            oc=data[0],
            target=interaction,
        )
        await resp.send_message(
            embed=data[0].embed,
            view=view,
            ephemeral=True,
        )
        await view.wait()
        with suppress(DiscordException):
            await self.edit(page=None)
        with suppress(DiscordException):
            await interaction.edit_original_message(
                embed=data[0].embed,
                view=None,
            )


class TemplateView(View):
    def __init__(self, target: Interaction, template: dict):
        super().__init__(timeout=None)
        self.target = target
        self.template = template

    @button(label="Through Discord Message", row=0, style=ButtonStyle.blurple)
    async def mode1(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        info = self.template.get("Template", {})
        text = dump(info, sort_keys=False)
        await self.target.edit_original_message(
            content=f"```yaml\n{text}\n```",
            view=None,
        )
        await resp.pong()
        self.stop()

    @button(label="Through Google Documents", row=1, style=ButtonStyle.blurple)
    async def mode2(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response

        content = (
            "**__Available Templates__**\n\n"
            "Make a copy of our templates, make sure it has reading permissions and then send the URL in this channel.\n"
        )
        for item in self.template.get("Document", {}).values():
            content += (
                f"\nhttps://docs.google.com/document/d/{item}/edit?usp=sharing"
            )

        await self.target.edit_original_message(content=content, view=None)
        await resp.pong()
        self.stop()


class SubmissionView(View):
    def __init__(
        self,
        bot: CustomBot,
        ocs: dict[int, Character],
        rpers: dict[int, dict[int, Character]],
        oc_list: dict[int, int],
        supporting: dict[Member, Member],
        missions: set[Mission],
        **kwargs: Union[str, dict],
    ):
        super(SubmissionView, self).__init__(timeout=None)
        self.bot = bot
        self.kwargs = kwargs
        self.ocs = ocs
        self.rpers = rpers
        self.oc_list = oc_list
        self.missions = missions
        self.supporting = supporting
        self.show_template.options = [
            SelectOption(
                label=f"{key} Template",
                description=f"Press to get {key} Template.",
                value=key,
                emoji="\N{SPIRAL NOTE PAD}",
            )
            for key in kwargs
        ]

    @select(
        placeholder="Click here to read our templates",
        row=0,
        custom_id="a479517442c724c00cc2e15a4106d807",
    )
    async def show_template(self, _: Select, ctx: Interaction):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        if raw_data := ctx.data.get("values", []):
            template = self.kwargs.get(raw_data[0], {})
            view = TemplateView(target=ctx, template=template)
            await ctx.followup.send(
                "__How do you want to register your character?__",
                view=view,
                ephemeral=True,
            )

    @button(
        label="Modify Character",
        emoji="\N{PENCIL}",
        row=1,
        custom_id="a78a8dc33d0f303928209f6566187c3f",
    )
    async def oc_update(self, _: Button, ctx: Interaction):
        resp: InteractionResponse = ctx.response

        member: Member = ctx.user

        await resp.defer(ephemeral=True)

        member = self.supporting.get(member, member)

        if not (values := self.rpers.get(member.id, {}).values()):
            return await ctx.followup.send(
                "You don't have characters to modify", ephemeral=True
            )

        view = CharacterHandlerView(
            bot=self.bot,
            member=ctx.user,
            target=ctx,
            values=values,
        )

        oc: Type[Character]
        async with view.send(
            title="Select Character to modify", single=True
        ) as oc:
            if isinstance(oc, Character):
                self.bot.logger.info(
                    "%s is modifying a Character(%s) aka %s",
                    str(ctx.user),
                    repr(oc),
                    oc.name,
                )

    @button(
        label="Create Mission",
        emoji="✉",
        row=1,
        custom_id="3ec81ed922f2f2cde42a2fc3ed3392c4",
    )
    async def mission_create(self, _: Button, ctx: Interaction):
        guild: Guild = ctx.guild
        role = guild.get_role(719642423327719434)
        resp: InteractionResponse = ctx.response
        if role not in ctx.user.roles:
            await resp.send_message(
                "You don't have a character registered", ephemeral=True
            )
            return
        locations: list[CategoryChannel] = [
            guild.get_channel(item) for item in RP_CATEGORIES
        ]
        view = ComplexInput(
            bot=self.bot,
            member=ctx.user,
            target=ctx,
            values=locations,
            parser=lambda x: (
                name := x.name[2:].capitalize(),
                f"Sets it at {name}",
            ),
            emoji_parser=lambda x: x.name[0],
        )
        choice: CategoryChannel
        async with view.send(title="Select Region", single=True) as choice:
            if not choice:
                return
            view = ComplexInput(
                bot=self.bot,
                member=ctx.user,
                target=ctx.channel,
                values=[
                    item
                    for item in choice.channels
                    if (
                        "-ooc" not in item.name
                        and isinstance(item, TextChannel)
                    )
                ],
                parser=lambda x: (
                    x.name[2:].replace("-", " ").capitalize(),
                    desc[:50] if (desc := x.topic) else "No description.",
                ),
                emoji_parser=lambda x: x.name[0],
            )
            area: TextChannel
            async with view.send(title="Select Area", single=True) as area:
                if not area:
                    return
                mission = Mission(author=ctx.user.id, place=area.id)
                text_input = TextInput(
                    bot=self.bot,
                    member=ctx.user,
                    target=ctx.channel,
                    required=True,
                )

                async with text_input.send(
                    title="Mission's Title",
                    description="Small summary that will show in the top of the paper. (50 Characters)",
                ) as text:
                    if not text:
                        return
                    mission.title = text.capitalize()

                async with text_input.send(
                    title="Mission's Description",
                    description="In this area, specify what is the mission about, and describe whatever is needed.",
                ) as text:
                    if not text:
                        return
                    mission.description = text

                async with text_input.send(
                    title="Mission's Target",
                    description="Either be the one that you're looking for, or the item that is being searched.",
                ) as text:
                    if not text:
                        return
                    mission.target = text

                async with text_input.send(
                    title="Mission's Client",
                    description="The one that is making the mission and possibly reward if done.",
                ) as text:
                    if not text:
                        return
                    mission.client = text

                view = Complex(
                    bot=self.bot,
                    member=ctx.user,
                    target=ctx.channel,
                    values=range(1, 7),
                    emoji_parser=lambda x: DICE_NUMBERS[x - 1],
                    parser=lambda x: (item := f"{x} / 6", f"Sets to {item}"),
                    title="Mission's Difficulty",
                )
                async with view.send(
                    title="Mission's difficulty", single=True
                ) as item:
                    if not item:
                        return
                    mission.difficulty = item
                    w = await self.bot.webhook(908498210211909642)
                    view = MissionView(bot=self.bot, mission=mission)
                    msg = await w.send(
                        content=ctx.user.mention,
                        embed=mission.embed,
                        view=view,
                        wait=True,
                        allowed_mentions=AllowedMentions(users=True),
                    )
                    mission.msg_id = msg.id
                    self.missions.add(mission)
                    async with self.bot.database() as session:
                        await mission.upsert(session)
                        self.bot.logger.info("Mission added: %s", repr(mission))
