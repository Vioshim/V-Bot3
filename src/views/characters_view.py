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
    Role,
    SelectOption,
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
from src.structures.logger import ColoredLogger
from src.utils.etc import WHITE_BAR
from src.utils.imagekit import Fonts, ImageKit

setLoggerClass(ColoredLogger)

logger = getLogger(__name__)

__all__ = ("CharactersView", "PingView")

PING_EMOJI = PartialEmoji(name="IconInsights", id=751160378800472186)


class PingModal(Modal):
    def __init__(self, oc: Character, reference: Interaction) -> None:
        super(PingModal, self).__init__(title=f"Pinging {oc.name}"[:45], timeout=None)
        self.message = TextInput(
            label="Message",
            style=TextStyle.paragraph,
            placeholder="Explain how you'd like to RP with the OC.",
            default=f"Hello\n\n I'm interested on RPing with your {oc.species.name}.",
            required=True,
        )
        self.add_item(self.message)
        self.ping_mode = Select(
            placeholder="Thread pinging?",
            options=[
                SelectOption(
                    label="Normal Ping",
                    value="0",
                    description="To ping at #rp-pings",
                    emoji=PING_EMOJI,
                    default=True,
                ),
            ],
        )
        self.add_item(self.ping_mode)
        self.oc = oc
        self.reference = reference

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        origin = channel = interaction.channel
        user = interaction.user
        receiver = interaction.guild.get_member(self.oc.author)
        if isinstance(origin, Thread):
            origin = origin.parent
        await resp.defer(ephemeral=True, thinking=True)

        if not self.ping_mode.values or "0" in self.ping_mode.values:
            thread = MISSING
            channel: TextChannel = interaction.guild.get_channel(740568087820238919)
        else:
            thread = Object(id=int(self.ping_mode.values[0]))
            channel: TextChannel = interaction.guild.get_channel(958122815171756042)

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
        self.ping2.label = f"Ping to RP with {oc.name}"
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

    async def ping_method(self, ctx: Interaction, mobile: bool = False):
        member = ctx.guild.get_member(self.oc.author)
        resp: InteractionResponse = ctx.response
        if ctx.user != member:
            modal = PingModal(oc=self.oc, reference=self.reference)
            if mobile:
                modal.remove_item(modal.ping_mode)
            db: AsyncIOMotorCollection = ctx.client.mongo_db("RP Search")
            items: dict[Role, str] = {
                role.name: str(item["id"])
                async for item in db.find({"member": self.oc.author})
                if (role := ctx.guild.get_role(item["role"]))
            }
            for k, v in items.items():
                modal.ping_mode.add_option(
                    label=k,
                    value=v,
                    description=f"Pinging in {k} thread"[:100],
                    emoji=PING_EMOJI,
                )
            await resp.send_modal(modal)
        else:
            await resp.send_message("You can't ping yourself.", ephemeral=True)

    @button(emoji=PartialEmoji(name="StatusMobileOld", id=716828817796104263))
    async def ping1(self, ctx: Interaction, _: Button) -> None:
        await self.ping_method(ctx, mobile=True)

    @button(
        label="Ping to RP with the OC",
        style=ButtonStyle.blurple,
        emoji=PartialEmoji(name="emotecreate", id=460538984263581696),
    )
    async def ping2(self, ctx: Interaction, _: Button) -> None:
        await self.ping_method(ctx)

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
        target: Interaction | Webhook | TextChannel,
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
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        if item := self.current_choice:
            embed = item.embed
            guild: Guild = self.member.guild
            if author := guild.get_member(item.author):
                embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
            if isinstance(self.target, Interaction):
                target = self.target
            else:
                target = interaction
            view = PingView(oc=item, reference=target)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            await view.wait()
        await super(CharactersView, self).select_choice(interaction, sct)
