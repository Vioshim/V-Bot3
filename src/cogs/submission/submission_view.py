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
from logging import getLogger, setLoggerClass

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    TextStyle,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from jishaku.codeblocks import codeblock_converter
from yaml import safe_load

from src.cogs.submission.oc_modification import ModifyView
from src.pagination.complex import Complex
from src.structures.character import Character, doc_convert
from src.structures.logger import ColoredLogger
from src.utils.doc_reader import docs_reader
from src.utils.functions import yaml_handler
from src.utils.matches import G_DOCUMENT

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


class CharacterHandlerView(Complex[Character]):
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
        if oc := self.current_choice:
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
            try:
                await resp.edit_message(
                    embed=oc.embed,
                    view=None,
                )
            except DiscordException:
                pass


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
                msg_data["url"] = url
            else:
                text = yaml_handler(text)
                msg_data = safe_load(text)

            if isinstance(msg_data, dict):
                cog = interaction.client.get_cog("Submission")
                await cog.submission_handler(interaction, **msg_data)

        except Exception as e:
            if not resp.is_done():
                await resp.defer(ephemeral=True, thinking=True)
            await interaction.followup.send(str(e), ephemeral=True)

        if not resp.is_done():
            await resp.pong()
        self.stop()


class TemplateView(View):
    def __init__(self, message: Message):
        super().__init__(timeout=None)
        self.message = message
        self.info = message.embeds[0].description
        self.urls = {x.label: x.url for x in View.from_message(message).children if isinstance(x, Button)}

    @button(label="Form", row=0, style=ButtonStyle.blurple)
    async def mode1(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        modal = SubmissionModal(codeblock_converter(self.info).content)
        await resp.send_modal(modal)

    @button(label="Message", row=0, style=ButtonStyle.blurple)
    async def mode2(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        await resp.edit_message(content=self.info, embed=None, view=None)
        self.stop()

    @button(label="Google Document", row=0, style=ButtonStyle.blurple)
    async def mode3(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        content = (
            "**__Available Templates__**\n\n"
            "Make a copy of our templates, make sure it has reading permissions and then send the URL in this channel.\n"
        )

        for key, item in self.urls.items():
            content += f"\n• [{key}]({item})"

        await resp.edit_message(content=content, embed=None, view=None)
        self.stop()


class SubmissionView(View):
    def __init__(
        self,
        ocs: list[Character],
        supporting: dict[Member, Member],
    ):
        super(SubmissionView, self).__init__(timeout=None)
        self.ocs = ocs
        self.supporting = supporting
        self.templates = {}

    @select(placeholder="Click here to read our Templates", row=0, custom_id="read")
    async def show_template(self, ctx: Interaction, sct: Select) -> None:
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)

        try:
            msg = self.templates[sct.values[0]]
        except KeyError:
            if not (ch := ctx.guild.get_channel_or_thread(961345742222536744)):
                ch = await ctx.guild.fetch_channel(961345742222536744)
            msg = await ch.fetch_message(int(sct.values[0]))
            self.templates[str(msg.id)] = msg

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
            view=TemplateView(msg),
            ephemeral=True,
        )

    @button(label="Modify Character", emoji="\N{PENCIL}", row=1, custom_id="modify")
    async def oc_update(self, ctx: Interaction, _: Select):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        await resp.defer(ephemeral=True, thinking=True)
        member = self.supporting.get(member, member)
        values: list[Character] = [oc for oc in self.ocs.values() if member.id == oc.author]
        if not values:
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
            try:
                await resp.edit_message(embed=values[0].embed, view=None)
            except DiscordException:
                pass
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
