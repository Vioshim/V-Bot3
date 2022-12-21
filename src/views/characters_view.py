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
from typing import Optional

from discord import (
    AllowedMentions,
    ButtonStyle,
    Embed,
    File,
    Forbidden,
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
    WebhookMessage,
)
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import MISSING
from motor.motor_asyncio import AsyncIOMotorCollection

from src.pagination.complex import Complex
from src.structures.character import Character
from src.utils.etc import WHITE_BAR
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

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        origin = channel = interaction.channel
        user = interaction.user
        receiver = interaction.guild.get_member(self.oc.author)
        if isinstance(origin, Thread):
            origin = origin.parent
        await resp.defer(ephemeral=True, thinking=True)

        if self.thread_id:
            thread, channel_id = Object(id=self.thread_id), 958122815171756042
        else:
            thread, channel_id = MISSING, 740568087820238919

        channel: TextChannel = interaction.guild.get_channel(channel_id)
        embed = Embed(title=self.oc.name, description=self.message.value, color=user.color)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url, url=self.oc.jump_url)
        embed.set_footer(text=repr(self.oc))
        kit = ImageKit(base=self.oc.image_url, width=450, height=450, format="png")
        for index, item in enumerate(self.oc.types):
            kit.add_image(image=item.icon, width=200, height=44, x=250, y=44 * index)
        kit.add_text(
            text=self.oc.name,
            width=330,
            x=0,
            y=400,
            background=0xFFFFFF,
            background_transparency=90,
            font=Fonts.Whitney_Black,
            font_size=36,
        )
        if self.oc.pronoun.image:
            kit.add_image(image=self.oc.pronoun.image, height=120, width=120, x=330, y=330)
        file: File = await interaction.client.get_file(kit.url)
        embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.set_image(url=WHITE_BAR)
        webhook: Webhook = await interaction.client.webhook(channel)
        msg: WebhookMessage = await webhook.send(
            receiver.mention,
            file=file,
            allowed_mentions=AllowedMentions(users=True),
            embed=embed,
            username=user.display_name,
            avatar_url=user.display_avatar.url,
            thread=thread,
            wait=True,
        )
        if thread is MISSING:
            name = f"{user.display_name} -> {receiver.display_name}"
            thread = await msg.create_thread(name=name, reason=f"Ping: {name}")

        with suppress(Forbidden):
            if isinstance(thread, Thread):
                await thread.add_user(user)
                await thread.add_user(receiver)
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

    async def interaction_check(self, interaction: Interaction) -> bool:
        guild: Guild = interaction.guild
        resp: InteractionResponse = interaction.response
        registered = guild.get_role(719642423327719434)
        if registered not in interaction.user.roles:
            await resp.send_message("You don't have registered role", ephemeral=True)
            return False
        if not guild.get_member(self.oc.author):
            await resp.send_message("Owner of the OC is no longer in the Server", ephemeral=True)
            return False
        return True

    @button(label="Ping Character", style=ButtonStyle.blurple)
    async def ping(self, ctx: Interaction, btn: Button) -> None:
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
                options.append({"id": ctx.message.id})
                options.append({"message": ctx.message.id})
            if self.reference.message:
                options.append({"id": self.reference.message.id})
                options.append({"message": self.reference.message.id})

            if data := await db.find_one({"$and": [{"member": self.oc.author}, {"$or": options}]}):
                modal = PingModal(oc=self.oc, thread_id=data["id"])
            else:
                modal = PingModal(oc=self.oc)
        await resp.send_modal(modal)

    @button(
        label="Delete Character",
        style=ButtonStyle.red,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
    )
    async def delete(self, ctx: Interaction, btn: Button) -> None:
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
        target: Interaction | Webhook | TextChannel,
        ocs: set[Character],
        keep_working: bool = False,
        max_values: int = 1,
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
        )
        self.embed.title = "Select a character"


class CharactersView(BaseCharactersView):
    def __init__(
        self,
        member: Member,
        target: Interaction | Webhook | TextChannel,
        ocs: set[Character],
        keep_working: bool = False,
        msg_id: Optional[None] = None,
    ):
        super(CharactersView, self).__init__(
            member=member,
            target=target,
            ocs=ocs,
            keep_working=keep_working,
            max_values=1,
        )
        self.msg_id = int(msg_id) if msg_id else None

    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
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
            if isinstance(self.target, Interaction):
                target = self.target
            else:
                target = interaction
            view = PingView(oc=item, reference=target, msg_id=self.msg_id)
            await interaction.followup.send(content=item.id, embeds=embeds, view=view, ephemeral=True)
            await view.wait()
        await super(CharactersView, self).select_choice(interaction, sct)
