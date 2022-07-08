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
from logging import getLogger, setLoggerClass
from typing import Optional, Union

from discord import (
    AllowedMentions,
    ButtonStyle,
    DiscordException,
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

from src.pagination.complex import Complex
from src.structures.character import Character
from src.structures.logger import ColoredLogger
from src.utils.etc import WHITE_BAR
from src.utils.imagekit import Fonts, ImageKit
from src.views.oc_modification import ModificationComplex

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

__all__ = ("CharactersView", "PingView")


class PingModal(Modal):
    message = TextInput(
        label="Message",
        style=TextStyle.paragraph,
        placeholder="Explain how you'd like to RP with the OC.",
        default="Hello\n\n I'm interested on RPing with your OC.",
        required=True,
    )

    def __init__(self, oc: Character, reference: Interaction, thread_id: Optional[int] = None) -> None:
        super(PingModal, self).__init__(title=f"Pinging {oc.name}", timeout=None)
        self.oc = oc
        self.reference = reference
        self.thread_id = thread_id

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        origin = channel = interaction.channel
        user = interaction.user
        receiver = interaction.guild.get_member(self.oc.author)
        if isinstance(origin, Thread):
            origin = origin.parent
        await resp.defer(ephemeral=True, thinking=True)
        if origin.id == 958122815171756042 and self.thread_id:
            thread = Object(id=self.thread_id)
        else:
            thread = MISSING
            channel: TextChannel = interaction.guild.get_channel(740568087820238919)
        embed = Embed(title=self.oc.name, description=self.message.value, color=user.color)
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.set_footer(text=repr(self.oc))
        kit = ImageKit(base=self.oc.image_url, width=450, height=450)
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
    def __init__(self, oc: Character, reference: Interaction):
        super(PingView, self).__init__(timeout=None)
        self.oc = oc
        self.reference = reference
        if isinstance(channel := reference.channel, Thread) and channel.parent.id == 958122815171756042:
            thread_id = channel.id
        else:
            thread_id = None
        self.thread_id = thread_id
        self.ping.label = f"Ping to RP with {oc.name}"
        if reference.user.id != oc.author:
            self.remove_item(self.delete)

    async def interaction_check(self, interaction: Interaction) -> bool:
        guild: Guild = interaction.guild
        resp: InteractionResponse = interaction.response
        registered = guild.get_role(719642423327719434)
        if registered not in interaction.user.roles:
            await resp.send_message("You don't have registered role", ephemeral=True)
            return False
        elif not guild.get_member(self.oc.author):
            await resp.send_message("Owner of the OC is no longer in the Server", ephemeral=True)
            return False
        return True

    @button(
        label="Ping to RP with the OC",
        style=ButtonStyle.blurple,
        emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
    )
    async def ping(self, ctx: Interaction, _: Button) -> None:
        member = ctx.guild.get_member(self.oc.author)
        resp: InteractionResponse = ctx.response
        if ctx.user != member:
            modal = PingModal(oc=self.oc, reference=self.reference, thread_id=self.thread_id)
            await resp.send_modal(modal)
        else:
            await resp.send_message("You can't ping yourself.", ephemeral=True)
        self.stop()

    @button(
        label="Delete Character",
        style=ButtonStyle.red,
        emoji=PartialEmoji(name="emoteremove", id=460538983965786123),
    )
    async def delete(self, ctx: Interaction, _: Button) -> None:
        resp: InteractionResponse = ctx.response
        member = ctx.guild.get_member(self.oc.author)
        if ctx.user != member:
            await resp.send_message("This is not yours", ephemeral=True)
            return
        try:
            await resp.send_message("Deleted character", ephemeral=True)
            thread = await ctx.guild.fetch_channel(self.oc.thread)
            message = await thread.fetch_message(self.oc.id)
            await message.delete()
        except DiscordException:
            pass
        finally:
            self.stop()


class CharactersView(Complex[Character]):
    def __init__(
        self,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        ocs: set[Character],
        keep_working: bool = False,
    ):
        super(CharactersView, self).__init__(
            member=member,
            target=target,
            values=ocs,
            timeout=None,
            parser=lambda x: (x.name, repr(x)),
            keep_working=keep_working,
        )
        self.embed.title = "Select a character"

    @select(row=1, placeholder="Select the Characters", custom_id="selector")
    async def select_choice(self, interaction: Interaction, sct: Select) -> None:
        response: InteractionResponse = interaction.response
        if item := self.current_choice:
            embed = item.embed
            guild: Guild = self.member.guild
            if author := guild.get_member(item.author):
                embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
            cog = interaction.client.get_cog("Submission")
            user: Member = cog.supporting.get(interaction.user, interaction.user)
            if item.author in [user.id, interaction.user.id]:
                view = ModificationComplex(oc=item, member=interaction.user, target=interaction)
            else:
                if isinstance(self.target, Interaction):
                    target = self.target
                else:
                    target = interaction
                view = PingView(oc=item, reference=target)
            await response.send_message(embed=embed, view=view, ephemeral=True)
            await view.wait()
        await super(CharactersView, self).select_choice(interaction, sct)
