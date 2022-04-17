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

from asyncio import to_thread
from contextlib import suppress
from logging import getLogger, setLoggerClass
from typing import Union

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    SelectOption,
    TextStyle,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from jishaku.codeblocks import codeblock_converter
from yaml import dump, safe_load

from src.cogs.submission.oc_modification import ModifyView
from src.pagination.complex import Complex
from src.structures.character import Character, doc_convert
from src.structures.logger import ColoredLogger
from src.utils.doc_reader import docs_reader
from src.utils.functions import yaml_handler
from src.utils.matches import G_DOCUMENT

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


class CharacterHandlerView(Complex):
    def __init__(
        self,
        member: Member,
        target: Interaction,
        values: set[Character],
    ):
        super(CharacterHandlerView, self).__init__(
            member=member,
            target=target,
            values=values,
            parser=lambda x: (x.name, repr(x)),
            timeout=None,
            sort_key=lambda x: x.name,
        )

    @select(
        row=1,
        placeholder="Select the elements",
        custom_id="selector",
    )
    async def select_choice(
        self,
        interaction: Interaction,
        _: Select,
    ) -> None:
        resp: InteractionResponse = interaction.response
        oc: Character = self.current_choice
        view = ModifyView(
            member=interaction.user,
            oc=self.current_choice,
            target=interaction,
        )
        await resp.edit_message(
            embed=oc.embed,
            view=view,
        )
        await view.wait()
        with suppress(DiscordException):
            await resp.edit_message(
                embed=oc.embed,
                view=None,
            )


class SubmissionModal(Modal):
    def __init__(self, text: str):
        super().__init__(title="Character Submission Template")
        self.text = TextInput(
            style=TextStyle.paragraph,
            label=self.title,
            placeholder="Template or Google Document goes here",
            default=text.strip(),
            required=True,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: Interaction):
        text: str = codeblock_converter(self.text.value or "").content
        resp: InteractionResponse = interaction.response
        try:
            if doc_data := G_DOCUMENT.match(text):
                doc = await to_thread(docs_reader, url := doc_data.group(1))
                msg_data = doc_convert(doc)
                url = f"https://docs.google.com/document/d/{url}/edit?usp=sharing"
                msg_data["url"] = url
            else:
                text = yaml_handler(text)
                msg_data = safe_load(text)

            if isinstance(msg_data, dict):
                cog = interaction.client.get_cog("Submission")
                await cog.submission_handler(interaction, **msg_data)

        except Exception as e:
            if not resp.is_done():
                await resp.defer(ephemeral=True)
            await interaction.followup.send(str(e), ephemeral=True)

        if not resp.is_done():
            await resp.pong()
        self.stop()


class TemplateView(View):
    def __init__(
        self,
        template: dict,
        title: str,
    ):
        super().__init__(timeout=None)
        self.template = template
        self.title = title

    @button(label="Form", row=0, style=ButtonStyle.blurple)
    async def mode1(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        info = self.template.get("Template", {})
        text: str = dump(info, sort_keys=False)
        modal = SubmissionModal(text)
        await resp.send_modal(modal)

    @button(label="Message", row=0, style=ButtonStyle.blurple)
    async def mode2(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        info = self.template.get("Template", {})
        text = dump(info, sort_keys=False)
        await resp.edit_message(
            content=f"```yaml\n{text}\n```",
            embed=None,
            view=None,
        )
        self.stop()

    @button(label="Google Document", row=0, style=ButtonStyle.blurple)
    async def mode3(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        content = (
            "**__Available Templates__**\n\n"
            "Make a copy of our templates, make sure it has reading permissions and then send the URL in this channel.\n"
        )

        for key, item in self.template.get("Document", {}).items():
            content += f"\n• [{key}](https://docs.google.com/document/d/{item}/edit?usp=sharing)"

        await resp.edit_message(content=content, embed=None, view=None)
        self.stop()


class SubmissionView(View):
    def __init__(
        self,
        ocs: dict[int, Character],
        rpers: dict[int, dict[int, Character]],
        oc_list: dict[int, int],
        supporting: dict[Member, Member],
        **kwargs: Union[str, dict],
    ):
        """Init method

        Parameters
        ----------
        bot : CustomBot
            Bot instance
        ocs : dict[int, Character]
            OCs
        rpers : dict[int, dict[int, Character]]
            OCs per rper
        oc_list : dict[int, int]
            OC list
        supporting : dict[Member, Member]
            Mods assisting to
        """
        super(SubmissionView, self).__init__(timeout=None)
        self.kwargs = kwargs
        self.ocs = ocs
        self.rpers = rpers
        self.oc_list = oc_list
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
    async def show_template(self, ctx: Interaction, sct: Select) -> None:
        """Shows the provided Templates

        Parameters
        ----------
        _ : Select
            Select
        ctx : Interaction
            Interaction
        """
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True)
        template = self.kwargs.get(title := sct.values[0], {})
        view = TemplateView(
            template=template,
            title=title,
        )
        embed = Embed(
            title="How do you want to register your character?",
            color=0xFFFFFE,
        )
        embed.set_image(
            url="https://cdn.discordapp.com/attachments/748384705098940426/957468209597018142/image.png",
        )
        embed.set_footer(text="After sending, bot will ask for backstory, extra info and image.")
        await ctx.followup.send(
            embed=embed,
            view=view,
            ephemeral=True,
        )

    @button(
        label="Modify Character",
        emoji="\N{PENCIL}",
        row=1,
        custom_id="a78a8dc33d0f303928209f6566187c3f",
    )
    async def oc_update(self, ctx: Interaction, _: Select):
        resp: InteractionResponse = ctx.response

        member: Member = ctx.user

        await resp.defer(ephemeral=True)

        member = self.supporting.get(member, member)

        if not (values := list(self.rpers.get(member.id, {}).values())):
            return await ctx.followup.send("You don't have characters to modify", ephemeral=True)

        values.sort(key=lambda x: x.name)

        if len(values) == 1:
            view = ModifyView(
                member=ctx.user,
                oc=values[0],
                target=ctx,
            )
            await ctx.followup.send(
                content="User only has one character",
                embed=values[0].embed,
                view=view,
                ephemeral=True,
            )
            await view.wait()
            with suppress(DiscordException):
                await resp.edit_message(
                    embed=values[0].embed,
                    view=None,
                )
        else:
            view = CharacterHandlerView(
                member=ctx.user,
                target=ctx,
                values=values,
            )

            view.embed.title = "Select Character to modify"
            view.embed.set_author(
                name=member.display_name,
                icon_url=member.display_avatar.url,
            )

            async with view.send(single=True, ephemeral=True) as oc:
                if isinstance(oc, Character):
                    logger.info(
                        "%s is modifying a Character(%s) aka %s",
                        str(ctx.user),
                        repr(oc),
                        oc.name,
                    )
