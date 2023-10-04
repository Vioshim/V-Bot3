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


from typing import Iterable, Optional

from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    File,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Object,
    PartialEmoji,
    TextChannel,
    TextStyle,
    Thread,
    Webhook,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.structures.bot import CustomBot
from src.structures.character import Character
from src.utils.etc import WHITE_BAR
from src.utils.functions import safe_username
from src.utils.imagekit import Fonts, ImageKit

__all__ = ("BaseCharactersView", "CharactersView", "PingView")


class PingModal(Modal):
    def __init__(self, oc: Character, thread_id: Optional[int] = None) -> None:
        super(PingModal, self).__init__(title=f"Pinging {oc.name}"[:45], timeout=None)
        self.thread_id = thread_id
        self.message = TextInput(
            label="Message",
            style=TextStyle.paragraph,
            placeholder="Explain how you'd like to RP with the OC.",
            default=f"Hello\n\n I'm interested on RPing with your {oc.species.name}.",
            required=True,
        )
        self.add_item(self.message)
        self.oc = oc

    async def on_submit(self, interaction: Interaction[CustomBot]) -> None:
        resp: InteractionResponse = interaction.response
        origin = interaction.channel
        user = interaction.user
        receiver = interaction.guild.get_member(self.oc.author)
        if isinstance(origin, Thread):
            origin = origin.parent
        await resp.defer(ephemeral=True, thinking=True)

        if self.thread_id:
            thread, channel_id = Object(id=self.thread_id), 958122815171756042
        else:
            thread, channel_id = Object(id=1061008601335992422), 1061008601335992422

        channel: TextChannel = interaction.guild.get_channel(channel_id)
        embed = Embed(title=self.oc.name, description=self.message.value, color=user.color)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url, url=self.oc.jump_url)
        embed.set_footer(text=repr(self.oc))
        kit = ImageKit(base=self.oc.image_url, width=450, height=450, format="png")
        for index, item in enumerate(self.oc.types):
            kit.add_image(image=item.icon, width=200, height=44, x=250, y=44 * index)
        kit.add_text(
            text=self.oc.name,
            width=450,
            x=0,
            y=400,
            background=0xFFFFFF,
            background_transparency=90,
            font=Fonts.Whitney_Black,
            font_size=36,
            padding=15,
        )
        oc_file: File = await interaction.client.get_file(kit.url)
        embed.set_thumbnail(url=f"attachment://{oc_file.filename}")
        embed.set_image(url=WHITE_BAR)
        webhook: Webhook = await interaction.client.webhook(channel)
        view = View()
        view.add_item(Button(label=self.oc.name[:80], emoji=self.oc.emoji, url=self.oc.jump_url))
        msg = await webhook.send(
            receiver.mention,
            file=oc_file,
            allowed_mentions=AllowedMentions(users=True),
            embed=embed,
            username=safe_username(user.display_name),
            avatar_url=user.display_avatar.url,
            thread=thread,
            view=view,
            wait=True,
        )

        if isinstance(thread := msg.channel, Thread):
            await thread.add_user(user)

        await interaction.followup.send("Ping has been successful", ephemeral=True)
        self.stop()


class PingView(View):
    def __init__(
        self,
        oc: Character,
        reference: Interaction,
        msg_id: Optional[int] = None,
    ):
        super(PingView, self).__init__(timeout=None)
        self.oc = oc
        self.reference = reference
        self.msg_id = msg_id
        if reference.user.id != oc.author:
            self.remove_item(self.delete)

    async def interaction_check(self, interaction: Interaction[CustomBot]) -> bool:
        guild: Guild = interaction.guild
        resp = interaction.response
        registered = guild.get_role(719642423327719434)
        if registered not in interaction.user.roles:
            await resp.send_message("You don't have registered role", ephemeral=True)
            return False
        if not guild.get_member(self.oc.author):
            await resp.send_message("Owner of the OC is no longer in the Server", ephemeral=True)
            return False
        return True

    @button(emoji="\N{PRINTER}", style=ButtonStyle.blurple)
    async def printer(self, ctx: Interaction[CustomBot], _: Button):
        await ctx.response.defer(ephemeral=True, thinking=True)
        if await ctx.client.is_owner(ctx.user):
            oc_file = await self.oc.to_pdf(ctx.client)
        else:
            oc_file = await self.oc.to_docx(ctx.client)
        await ctx.followup.send(file=oc_file, ephemeral=True)
        ctx.client.logger.info("User %s printed %s", str(ctx.user), repr(self.oc))

    @button(label="Ping OC", style=ButtonStyle.blurple)
    async def ping(self, ctx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = ctx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)

        member: Member = ctx.guild.get_member(self.oc.author)
        resp: InteractionResponse = ctx.response
        db: AsyncIOMotorCollection = ctx.client.mongo_db("RP Search")
        if ctx.user == member:
            return await resp.send_message("You can't ping yourself.", ephemeral=True)

        if self.msg_id:
            modal = PingModal(oc=self.oc, thread_id=self.msg_id)
        else:
            options = [{"id": ctx.channel_id}]
            if ctx.message:
                options.extend(({"id": ctx.message.id}, {"message": ctx.message.id}))
            if self.reference.message:
                options.extend(({"id": self.reference.message.id}, {"message": self.reference.message.id}))
            if data := await db.find_one({"$and": [{"member": self.oc.author}, {"$or": options}]}):
                modal = PingModal(oc=self.oc, thread_id=data["id"])
            else:
                modal = PingModal(oc=self.oc)
        await resp.send_modal(modal)

    @button(
        label="Delete OC",
        style=ButtonStyle.red,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
    )
    async def delete(self, ctx: Interaction[CustomBot], btn: Button):
        resp: InteractionResponse = ctx.response
        if "Confirm" not in btn.label:
            btn.label = f"{btn.label} (Confirm)"
            return await resp.edit_message(view=self)

        member = ctx.guild.get_member(self.oc.author)
        if ctx.user != member:
            await resp.send_message("This is not yours", ephemeral=True)
            return

        await resp.send_message("Deleted character", ephemeral=True)
        channel = ctx.client.get_partial_messageable(
            id=self.oc.thread,
            guild_id=self.oc.server,
        )
        await channel.get_partial_message(self.oc.id).delete(delay=0)
        self.stop()


class BaseCharactersView(Complex[Character]):
    def __init__(
        self,
        member: Member,
        target: Interaction[CustomBot] | Webhook | TextChannel,
        ocs: Iterable[Character],
        keep_working: bool = False,
        max_values: int = 1,
        auto_conclude: bool = True,
    ):
        super(BaseCharactersView, self).__init__(
            member=member,
            target=target,
            values=ocs,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
            sort_key=lambda x: (x.name, repr(x)),
            max_values=max_values,
            silent_mode=True,
            auto_conclude=auto_conclude,
            auto_choice_info=True,
            auto_text_component=True,
        )
        self.embed.title = "Select a character"


class CharactersView(BaseCharactersView):
    def __init__(
        self,
        member: Member,
        target: Interaction[CustomBot] | Webhook | TextChannel,
        ocs: set[Character],
        keep_working: bool = False,
        msg_id: Optional[None] = None,
        auto_conclude: bool = True,
    ):
        super(CharactersView, self).__init__(
            member=member,
            target=target,
            ocs=ocs,
            keep_working=keep_working,
            max_values=1,
            auto_conclude=auto_conclude,
        )
        self.msg_id = int(msg_id) if msg_id else None

    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, interaction: Interaction[CustomBot], sct: Select):
        resp: InteractionResponse = interaction.response
        if item := self.current_choice:
            await resp.defer(ephemeral=True, thinking=True)
            embeds = item.embeds
            guild: Guild = self.member.guild
            if author := guild.get_member(item.author):
                embeds[0].set_author(
                    name=author.display_name,
                    url=item.jump_url,
                    icon_url=author.display_avatar.url,
                )
            target = self.target if isinstance(self.target, Interaction) else interaction
            view = PingView(oc=item, reference=target, msg_id=self.msg_id)
            await interaction.followup.send(content=item.id, embeds=embeds, view=view, ephemeral=True)
            await view.wait()
        await super(CharactersView, self).select_choice(interaction, sct)
