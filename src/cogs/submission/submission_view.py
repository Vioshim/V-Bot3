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
from logging import getLogger, setLoggerClass
from typing import NamedTuple

from discord import (
    ButtonStyle,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    TextStyle,
    Thread,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from jishaku.codeblocks import codeblock_converter
from motor.motor_asyncio import AsyncIOMotorCollection

from src.cogs.submission.oc_parsers import ParserMethods
from src.cogs.submission.oc_submission import CreationOCView, ModCharactersView
from src.structures.character import Character
from src.structures.logger import ColoredLogger

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)


class NPC(NamedTuple):
    name: str = "Narrator"
    avatar: str = "https://cdn.discordapp.com/attachments/748384705098940426/986339510646370344/unknown.png"


class SubmissionModal(Modal):
    def __init__(self, text: str):
        super(SubmissionModal, self).__init__(title="Character Submission Template")
        self.text = TextInput(
            style=TextStyle.paragraph,
            label=self.title,
            placeholder="Template or Google Document goes here",
            default=text.strip(),
            required=True,
        )
        self.add_item(self.text)

    async def on_submit(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        try:
            cog = interaction.client.get_cog("Submission")
            async for item in ParserMethods.parse(text=self.text.value, bot=interaction.client):
                await cog.submission_handler(interaction, **item)
        except Exception as e:
            if not resp.is_done():
                if isinstance(interaction.channel, Thread) and interaction.channel.archived:
                    await interaction.channel.edit(archived=True)
                await resp.defer(ephemeral=True, thinking=True)
            await interaction.followup.send(str(e), ephemeral=True)
        else:
            if not resp.is_done():
                await resp.pong()
        finally:
            self.stop()


class NPCModal(Modal, title="NPC Modification - ?npc"):
    def __init__(self, npc: NPC):
        self.name = TextInput(label="Name", placeholder=npc.name, required=True)
        self.avatar = TextInput(label="Avatar URL", placeholder=npc.avatar, style=TextStyle.paragraph, required=True)
        self.add_item(self.name)
        self.add_item(self.avatar)

    async def on_submit(self, ctx: Interaction):
        db: AsyncIOMotorCollection = ctx.client.mongo_db("NPC")
        embed = Embed(title=self.name.value, description="It's ready to use with the ?npc command.")
        embed.set_image(url=self.avatar.value)
        try:
            await ctx.response.send_message(embed=embed, ephemeral=True)
        except DiscordException:
            await ctx.response.send_message("Invalid URL", ephemeral=True)
        else:
            await db.replace_one(
                {"author": ctx.user.id},
                {
                    "author": ctx.user.id,
                    "name": self.name.value,
                    "avatar": self.avatar.value,
                },
                upsert=True,
            )
        finally:
            self.stop()


class TemplateView(View):
    def __init__(self, message: Message):
        super(TemplateView, self).__init__(timeout=None)
        self.message = message
        embed = message.embeds[0]
        self.info = embed.description
        self.urls = {x.name: x.value[:-1].removeprefix("[Google Docs URL](") for x in embed.fields}

    @button(label="Form", row=0, style=ButtonStyle.blurple)
    async def mode1(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        modal = SubmissionModal(codeblock_converter(self.info).content.strip())
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
    def __init__(self, ocs: list[Character], supporting: dict[Member, Member]):
        super(SubmissionView, self).__init__(timeout=None)
        self.ocs = ocs
        self.supporting = supporting
        self.templates: dict[str, Message] = {}

    @select(placeholder="Click here to read our Templates", row=0, custom_id="read")
    async def show_template(self, ctx: Interaction, sct: Select) -> None:
        resp: InteractionResponse = ctx.response
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        try:
            msg = self.templates[sct.values[0]]
        except KeyError:
            if not (ch := ctx.guild.get_channel_or_thread(961345742222536744)):
                ch = await ctx.guild.fetch_channel(961345742222536744)
            msg = await ch.fetch_message(int(sct.values[0]))
            self.templates[str(msg.id)] = msg

        embed = Embed(title="How do you want to register your character?", color=0xFFFFFE)
        embed.set_image(url="https://cdn.discordapp.com/attachments/748384705098940426/957468209597018142/image.png")
        embed.set_footer(text="After sending, bot will ask for backstory, extra info and image.")
        await ctx.followup.send(embed=embed, view=TemplateView(msg), ephemeral=True)

    @button(label="Character Creation", emoji="\N{PENCIL}", row=1, custom_id="add-oc")
    async def oc_add(self, ctx: Interaction, _: Button):
        cog = ctx.client.get_cog("Submission")
        user = self.supporting.get(ctx.user, ctx.user)
        try:
            cog.ignore.add(ctx.user.id)
            cog.ignore.add(user.id)
            view = CreationOCView(ctx, user)
            await view.send()
            await view.wait()
            await view.delete()
        except Exception as e:
            await ctx.response.send_message(str(e), ephemeral=True)
        finally:
            cog.ignore -= {ctx.user.id, user.id}

    @button(label="Character Modification", emoji="\N{PENCIL}", row=1, custom_id="modify-oc")
    async def oc_update(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        member: Member = ctx.user
        if isinstance(ctx.channel, Thread) and ctx.channel.archived:
            await ctx.channel.edit(archived=True)
        await resp.defer(ephemeral=True, thinking=True)
        member = self.supporting.get(member, member)
        values: list[Character] = [oc for oc in self.ocs.values() if member.id == oc.author]
        if not values:
            return await ctx.followup.send("You don't have characters to modify", ephemeral=True)
        values.sort(key=lambda x: x.name)
        view = ModCharactersView(member=ctx.user, target=ctx, ocs=values)
        view.embed.title = "Select Character to modify"
        view.embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        async with view.send(single=True, ephemeral=True) as oc:
            if isinstance(oc, Character):
                logger.info("%s is modifying a Character(%s) aka %s", str(ctx.user), repr(oc), oc.name)
