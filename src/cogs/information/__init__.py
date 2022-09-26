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
from os import getenv
from typing import Optional

from aiohttp import ClientResponseError
from discord import (
    AllowedMentions,
    Asset,
    Attachment,
    ButtonStyle,
    ChannelType,
    Colour,
    DiscordException,
    Embed,
    Emoji,
    Guild,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    Object,
    PartialEmoji,
    PartialMessage,
    PermissionOverwrite,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    RawReactionActionEvent,
    Role,
    TextChannel,
    TextStyle,
    User,
    Webhook,
    app_commands,
)
from discord.abc import GuildChannel
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import format_dt, get, utcnow
from motor.motor_asyncio import AsyncIOMotorCollection
from yaml import dump

from src.cogs.information.area_selection import RegionViewComplex
from src.cogs.information.perks import CustomPerks
from src.cogs.information.poll import PollView
from src.cogs.wiki.wiki import WikiEntry
from src.cogs.wiki.wiki_complex import WikiComplex
from src.structures.bot import CustomBot
from src.utils.etc import (
    DEFAULT_TIMEZONE,
    LINK_EMOJI,
    SETTING_EMOJI,
    STICKER_EMOJI,
    WHITE_BAR,
)
from src.utils.functions import message_line

__all__ = ("Information", "setup")


channels = {
    766018765690241034: "OC Question",
    918703451830100028: "Poll",
    728800301888307301: "Suggestion",
    769304918694690866: "Story",
    903627523911458816: "Storyline",
    839105256235335680: "Random Fact",
    723228500835958987: "Announcement",
    740606964727546026: "Question",
    908498210211909642: "Mission",
    836726822166593598: "To-Do",
}

roles = {
    "Storyline": 805878418225889280,
    "Mission": 805878418225889280,
    "Random Fact": 805878418225889280,
    "Poll": 967980442919784488,
    "Question": 967980442919784488,
    "Suggestion": 967980442919784488,
}

MSG_INFO = {
    719343092963999804: 913555643699458088,
    952517983786377287: 952617304095592478,
}

TENOR_URL = "https://g.tenor.com/v1/gifs"
GIPHY_URL = "https://api.giphy.com/v1/gifs"

TENOR_API = getenv("TENOR_API")
GIPHY_API = getenv("GIPHY_API")
WEATHER_API = getenv("WEATHER_API")
STARS_AMOUNT = 3

ICON_VALUES = {
    True: "\N{WHITE HEAVY CHECK MARK}",
    False: "\N{CROSS MARK}",
    None: "\N{BLACK SQUARE BUTTON}",
}


PING_ROLES = {
    "Announcements": 908809235012419595,
    "Everyone": 719343092963999804,
    "Radio": 805878418225889280,
    "Partners": 725582056620294204,
    "Moderation": 720296534742138880,
    "Registered": 719642423327719434,
    "Supporters": 967980442919784488,
}

DISABLED_CATEGORIES = [
    740550068922220625,  # Server & News
    740552350703550545,  # RP information
]


class AnnouncementModal(Modal):
    def __init__(self, *, word: str, name: str, **kwargs):
        super(AnnouncementModal, self).__init__(title=word, timeout=None)
        self.word = word

        self.kwargs = kwargs
        self.thread_name = TextInput(
            label="Title",
            placeholder=word,
            default=name,
            required=True,
            max_length=100,
        )
        self.add_item(self.thread_name)

        self.poll_data = TextInput(
            label="Poll Data",
            style=TextStyle.paragraph,
            placeholder="Value, Value, Value",
            required=True,
        )
        self.poll_range = TextInput(
            label="Poll min-max values (e.g. 1-2 or 4)",
            placeholder="1 - 25",
            default="1",
            required=True,
        )

        self.thread_mode = kwargs.pop("thread", False)
        self.poll_mode = kwargs.pop("poll", word == "Poll")

        if self.poll_mode:
            self.add_item(self.poll_data)
            self.add_item(self.poll_range)

    async def on_submit(self, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        webhook: Webhook = await interaction.client.webhook(interaction.channel)
        embeds: list[Embed] = self.kwargs.get("embeds")
        if embeds:
            embeds[0].title = self.thread_name.value

        msg = await webhook.send(**self.kwargs, allowed_mentions=AllowedMentions(everyone=True, roles=True), wait=True)

        if self.poll_mode:
            db: AsyncIOMotorCollection = interaction.client.mongo_db("Poll")
            if not (answers := [int(o) for x in self.poll_range.value.split("-") if (o := x.strip()) and o.isdigit()]):
                answers = [1]
            view = PollView.parse(text=self.poll_data.value, min_values=answers[0], max_values=answers[-1])
            await msg.edit(view=view)
            await db.insert_one({"id": msg.id} | view.data)

        if self.thread_mode:
            thread = await msg.create_thread(name=self.thread_name.value)
            await thread.add_user(interaction.user)
            match self.word:
                case "OC Question" | "Story" | "Storyline" | "Mission":
                    if tupper := interaction.guild.get_member(431544605209788416):
                        await thread.add_user(tupper)

        await interaction.followup.send("Thread created successfully", ephemeral=True)
        self.stop()


class AnnouncementView(View):
    def __init__(self, *, member: Member, **kwargs):
        super(AnnouncementView, self).__init__()
        self.member = member
        self.kwargs = kwargs
        self.format()

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if interaction.user != self.member:
            await resp.send_message(f"Message requested by {self.member.mention}", ephemeral=True)
            return False
        return True

    def format(self):
        self.features.options.clear()
        self.features.add_option(
            label="Pinging @supporters",
            value="supporters",
            emoji=PartialEmoji(name="memberjoin", id=432986578755911680),
        )
        self.features.add_option(
            label="Add a thread",
            value="thread",
            emoji=PartialEmoji(name="messageupdate", id=432986578927747073),
        )
        self.features.add_option(
            label="Add a poll",
            value="poll",
            emoji=PartialEmoji(name="channelcreate", id=432986578781077514),
        )
        self.features.add_option(
            label="Cancel Process",
            value="cancel",
            emoji="\N{CROSS MARK}",
        )
        if self.member.guild_permissions.administrator:
            for k, v in PING_ROLES.items():
                self.features.add_option(
                    label=f"{k} Role",
                    value=f"{v}",
                    description=f"Pings the {k} role",
                    emoji="\N{CHEERING MEGAPHONE}",
                )

    @select(placeholder="Select Features", max_values=3)
    async def features(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        if str(ctx.guild_id) in sct.values:
            self.kwargs["content"] = "@everyone"
        elif roles := " ".join(o.mention for x in sct.values if x.isdigit() and (o := ctx.guild.get_role(int(x)))):
            self.kwargs["content"] = roles
        elif "supporters" in sct.values:
            self.kwargs["content"] = "<@&967980442919784488>"
        else:
            self.kwargs["content"] = None

        self.kwargs["poll"] = "poll" in sct.values
        self.kwargs["thread"] = "thread" in sct.values

        if "cancel" in sct.values:
            await resp.pong()
        else:
            word = channels.get(ctx.channel_id)
            data = ctx.created_at.astimezone(tz=DEFAULT_TIMEZONE)
            name = f"{word} {ctx.user.display_name} {data.strftime('%B %d')}"
            modal = AnnouncementModal(word=word, name=name, **self.kwargs)
            await resp.send_modal(modal)
            await modal.wait()

        await ctx.message.delete(delay=0)
        self.stop()


class TicketModal(Modal, title="Ticket"):
    content = TextInput(
        label="Content",
        placeholder="What would you like to comment / report to Staff?",
        style=TextStyle.paragraph,
        required=True,
    )

    async def on_submit(self, interaction: Interaction):
        """This is a function that creates a thread whenever an user uses it

        Parameters
        ----------
        interaction : Interaction
            Interaction object
        """
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True, thinking=True)
        member: Member = interaction.user
        data = interaction.created_at.astimezone(tz=DEFAULT_TIMEZONE)
        name = data.strftime("%B %d, %Y")
        webhook: Webhook = await interaction.client.webhook(719343092963999807)
        thread = await webhook.channel.create_thread(name=name, type=ChannelType.private_thread, invitable=False)
        embed = Embed(title="Ticket", description=self.content.value, timestamp=data, color=member.color)
        msg = await webhook.send(thread=thread, wait=True, embed=embed)

        view = View()
        view.add_item(Button(label="Go to Message", url=msg.jump_url, emoji=STICKER_EMOJI))
        await interaction.followup.send("Ticket created successfully", ephemeral=True, view=view)
        await thread.add_user(member)

        if not (mod_channel := interaction.guild.get_channel_or_thread(1020157013126283284)):
            mod_channel = await interaction.guild.fetch_channel(1020157013126283284)

        embed = Embed(title=f"Ticket {name}"[:256], color=member.color, timestamp=utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_image(url=WHITE_BAR)
        await mod_channel.send(embed=embed, view=view)
        self.stop()


class InformationView(View):
    def __init__(self):
        super(InformationView, self).__init__(timeout=None)
        self.add_item(
            Button(
                label="Self Roles",
                emoji="\N{CHEERING MEGAPHONE}",
                url="https://canary.discord.com/channels/719343092963999804/719709333369258015/1023688500182261850",
                row=0,
            )
        )
        self.add_item(
            Button(
                label="Lore",
                emoji="\N{SCROLL}",
                url="https://canary.discord.com/channels/719343092963999804/1020286550753427478/1020286550753427478",
                row=0,
            )
        )
        self.add_item(
            Button(
                label="OC Submission",
                emoji="\N{OPEN BOOK}",
                url="https://canary.discord.com/channels/719343092963999804/852180971985043466/1005387453055639612",
                row=0,
            )
        )

    @button(label="See Map", emoji="\N{WORLD MAP}", row=1, style=ButtonStyle.blurple)
    async def see_map(self, ctx: Interaction, _: Button):
        view = RegionViewComplex(member=ctx.user, target=ctx)
        await view.simple_send(ephemeral=True)

    @button(label="Make a Ticket", emoji=STICKER_EMOJI, row=1, style=ButtonStyle.blurple)
    async def create_ticket(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_modal(TicketModal(timeout=None))

    @button(label="Read /Wiki", emoji=SETTING_EMOJI, row=1, style=ButtonStyle.blurple)
    async def read_wiki(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.defer(ephemeral=True, thinking=True)
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Wiki")
        entries = await db.find({}).to_list(length=None)
        tree = WikiEntry.from_list(entries)
        view = WikiComplex(tree=tree, target=ctx)
        content, embeds = tree.content, tree.embeds
        if not (content or embeds):
            embeds = [view.embed]
        view.message = await ctx.followup.send(
            ephemeral=True,
            content=content,
            embeds=embeds,
            view=view,
            wait=True,
        )


class Information(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.ready = False
        self.message: Optional[Message] = None
        self.bot.tree.on_error = self.on_error

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_role("Booster")
    async def perks(
        self,
        ctx: Interaction,
        perk: CustomPerks,
        icon: Optional[Attachment] = None,
    ):
        """Custom Functions for Supporters!

        Parameters
        ----------
        ctx : Interaction
            Interaction
        perk : Perks
            Perk to Use
        icon : Attachment
            Image File
        """
        resp: InteractionResponse = ctx.response
        if not icon or icon.content_type.startswith("image"):
            await perk.method(ctx, icon)
        else:
            await resp.send_message("Valid File Format: image/png", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.guild.id != 719343092963999804:
            return

        guild: Guild = member.guild
        embed = Embed(
            title="Member Left - Roles",
            description="The user did not have any roles.",
            color=Colour.red(),
            timestamp=utcnow(),
        )
        if roles := member.roles[:0:-1]:
            embed.description = "\n".join(f"> **•** {role.mention}" for role in roles)
        if icon := guild.icon:
            embed.set_footer(text=f"ID: {member.id}", icon_url=icon.url)
        else:
            embed.set_footer(text=f"ID: {member.id}")
        embed.set_image(url=WHITE_BAR)
        view = View()

        db1 = self.bot.mongo_db("Roleplayers")
        if item := await db1.find_one({"user": member.id}):
            url = f"https://discord.com/channels/{guild.id}/{item['id']}"
            view.add_item(Button(label="Characters", url=url))

        db = self.bot.mongo_db("Custom Role")
        if data := await db.find_one({"author": member.id}):
            if role := get(member.guild.roles, id=data["id"]):
                try:
                    await role.delete(reason="User left")
                except DiscordException:
                    pass

            await db.delete_one(data)

        asset = member.display_avatar.replace(format="png", size=4096)
        if file := await self.bot.get_file(asset.url, filename=str(member.id)):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
            await log.send(
                file=file,
                embed=embed,
                view=view,
                username=member.display_name,
                thread=Object(id=1020153313242665022),
                avatar_url=member.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if member.guild.id != 719343092963999804:
            return

        embed = Embed(
            title="Member Joined",
            colour=Colour.green(),
            description=f"{member.mention} - {member}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {member.id}")
        asset = member.display_avatar.replace(format="png", size=512)
        log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(name="Account Age", value=format_dt(member.created_at, style="R"))
            view = View()
            db1 = self.bot.mongo_db("Roleplayers")
            if item := await db1.find_one({"user": member.id}):
                url = f"https://discord.com/channels/{member.guild.id}/{item['id']}"
                view.add_item(Button(label="Characters", url=url))

            await log.send(
                embed=embed,
                file=file,
                view=view,
                thread=Object(id=1020153315255922738),
                username=member.display_name,
                avatar_url=member.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if now.guild.id != 719343092963999804 or past.premium_since == now.premium_since:
            return

        if past.premium_since and not now.premium_since:
            embed = Embed(
                title="Has un-boosted the Server!",
                colour=Colour.red(),
                timestamp=utcnow(),
            )

            db = self.bot.mongo_db("Custom Role")
            if data := await db.find_one({"author": now.id}):
                if role := get(now.guild.roles, id=data["id"]):
                    try:
                        await role.delete(reason="User unboosted")
                    except DiscordException:
                        pass

                await db.delete_one(data)
        else:
            embed = Embed(
                title="Has boosted the Server!",
                colour=Colour.brand_green(),
                timestamp=utcnow(),
            )

        embed.set_image(url=WHITE_BAR)
        asset = now.display_avatar.replace(format="png", size=4096)
        embed.set_thumbnail(url=asset.url)
        embed.set_footer(text=now.guild.name, icon_url=now.guild.icon)

        log = await self.bot.webhook(1020151767532580934, reason="Logging")
        await log.send(
            content=now.mention,
            embed=embed,
            thread=Object(id=1020153311200022528),
            username=now.display_name,
            avatar_url=now.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_member_ban(self, guild: Guild, user: Member | User):
        if guild.id != 719343092963999804:
            return

        embed = Embed(
            title="Member Banned",
            colour=Colour.red(),
            description=f"{user.mention} - {user}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {user.id}")
        asset = user.display_avatar.replace(format="png", size=512)
        log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(name="Account Age", value=format_dt(user.created_at, style="R"))
            view = View()
            db1 = self.bot.mongo_db("Roleplayers")
            if item := await db1.find_one({"user": user.id}):
                url = f"https://discord.com/channels/{guild.id}/{item['id']}"
                view.add_item(Button(label="Characters", url=url))

            await log.send(
                embed=embed,
                file=file,
                view=view,
                thread=Object(id=1020153286285865000),
                username=user.display_name,
                avatar_url=user.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_role_create(self, role: Role):
        """Role Create Event

        Parameters
        ----------
        role : Role
            Added role
        """
        embed = Embed(
            title="Role Created",
            description=role.name,
            color=role.color,
            timestamp=role.created_at,
        )
        if isinstance(icon := role.display_icon, Asset):
            embed.set_thumbnail(url=icon)
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=role.guild.name, icon_url=role.guild.icon)
        log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
        await log.send(embed=embed, thread=Object(id=1020153288617906256))

    @commands.Cog.listener()
    async def on_role_delete(self, role: Role):
        """Role Delete Event

        Parameters
        ----------
        role : Role
            Added role
        """
        embed = Embed(
            title="Role Deleted",
            description=role.name,
            color=role.color,
            timestamp=role.created_at,
        )
        files = []
        if isinstance(icon := role.display_icon, Asset):
            files.append(file := await icon.to_file())
            embed.set_thumbnail(url=f"attachment://{file.filename}")
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=role.guild.name, icon_url=role.guild.icon)
        log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
        await log.send(embed=embed, files=files, thread=Object(id=1020153288617906256))

    @commands.Cog.listener()
    async def on_role_update(self, before: Role, after: Role):
        """Role Update Event

        Parameters
        ----------
        before : Role
            Role before editing
        after : Role
            Role after editing
        """
        if not before.guild or before.guild.id != 719343092963999804:
            return

        embed1 = Embed(title=f"Role Update: {after.name}", colour=before.color, timestamp=before.created_at)
        embed1.set_image(url=WHITE_BAR)

        embed2 = Embed(colour=after.color, timestamp=utcnow())
        embed2.set_image(url=WHITE_BAR)

        embeds, files = [embed1, embed2], []

        if condition := before.name != after.name:
            embed1.title = f"Role Before: {before.name}"
            embed2.title = f"Role Afterwards: {after.name}"

        condition |= before.color != after.color

        if before.display_icon != after.display_icon:
            condition = True
            for aux1, aux2 in zip([embed1, embed2], [before.display_icon, after.display_icon]):
                if isinstance(aux2, Asset):
                    aux1.url = WHITE_BAR
                    files.append(file := await aux2.to_file())
                    aux1.set_image(url=f"attachment://{file.filename}")
                else:
                    aux1.description = f"Icon: {aux2}"

        if before.permissions != after.permissions:
            condition = True
            embeds.append(
                Embed(
                    title="Updated Permissions",
                    description="\n".join(
                        f"• {ICON_VALUES[v1]} -> {ICON_VALUES[v2]}: {k1.replace('_', ' ').title()}"
                        for ((k1, v1), (k2, v2)) in zip(before.permissions, after.permissions)
                        if k1 == k2 and v1 != v2
                    ),
                    color=Colour.blurple(),
                    timestamp=utcnow(),
                ).set_image(url=WHITE_BAR)
            )

        if not condition:
            return

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(
            embeds=embeds,
            files=files,
            thread=Object(id=1020153288617906256),
        )

    @commands.Cog.listener()
    async def on_guild_emojis_update(
        self,
        guild: Guild,
        before: list[Emoji],
        after: list[Emoji],
    ):
        """Guild Emoji Update

        Parameters
        ----------
        guild : Guild
            Guild
        before : list[Emoji]
            Cached Emojis
        after : list[Emoji]
            New Emojis
        """
        if guild.id != 719343092963999804:
            return

        aux_before, aux_after = set[Emoji](before), set[Emoji](after)
        description = "\n".join(f"+ {x} - {x!r}" for x in (aux_after - aux_before))
        embed = Embed(title="Emoji Changes", description=description, color=Colour.blurple(), timestamp=utcnow())
        embed.set_image(url=WHITE_BAR)

        embeds, files = [embed], []

        for item in aux_before - aux_after:
            files.append(file := await item.to_file())
            e = Embed(title=item.name)
            e.set_thumbnail(url=f"attachment://{file.filename}")
            e.set_image(url=WHITE_BAR)
            e.set_footer(text=f"ID: {item.id}")

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(embeds=embeds, thread=Object(id=1020153288617906256))

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        """Channel Create Event

        Parameters
        ----------
        channel : GuildChannel
            Channel Deleted
        after : GuildChannel
            Channel after editing
        """
        if not channel.guild or channel.guild.id != 719343092963999804:
            return

        if not isinstance(channel, TextChannel):
            return

        embed = Embed(
            title=f"Channel Create: {channel.name}",
            description=channel.topic,
            colour=Colour.green(),
            timestamp=channel.created_at,
        )

        for item, perms in channel.overwrites.items():

            if len(embed.fields) >= 25:
                break

            name = getattr(item, "name", str(item))

            text = "\n".join(
                f"{ICON_VALUES[value]}: {key.replace('_', ' ').title()}" for key, value in perms if value is not None
            )
            if text:
                embed.add_field(name=name, value=text[:1024])

        try:
            name = channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, channel.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        cat_name = getattr(channel.category, "name", "No Category")
        embed.set_footer(text=f"Category: {cat_name}")
        view.add_item(Button(emoji=emoji, label=name, url=channel.jump_url))

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(
            embed=embed,
            view=view,
            thread=Object(id=1020153288617906256),
        )

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        """Channel Update Event

        Parameters
        ----------
        channel : GuildChannel
            Channel Deleted
        after : GuildChannel
            Channel after editing
        """
        if not channel.guild or channel.guild.id != 719343092963999804:
            return

        embed = Embed(
            title=f"Channel Delete: {channel.name}",
            description=getattr(channel, "topic", None),
            colour=Colour.red(),
            timestamp=channel.created_at,
        )

        for item, perms in channel.overwrites.items():

            if len(embed.fields) >= 25:
                break

            name = getattr(item, "name", str(item))

            text = "\n".join(
                f"{ICON_VALUES[value]}: {key.replace('_', ' ').title()}" for key, value in perms if value is not None
            )
            if text:
                embed.add_field(name=name, value=text[:1024])

        if threads := "\n".join(f"• {x.name}" for x in getattr(channel, "threads", [])):
            embed.title = f"{embed.title} - Deleted Threads"
            embed.description = threads[:4096]

        try:
            name = channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, channel.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        if category := channel.category:
            embed.set_footer(text=f"Category: {category.name}")
            view.add_item(Button(emoji=emoji, label=name, url=category.jump_url))
        else:
            embed.set_footer(text="No Category")
            view.add_item(Button(emoji=emoji, label=name, url=channel.jump_url))

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(
            embed=embed,
            view=view,
            thread=Object(id=1020153288617906256),
        )

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self,
        before: GuildChannel,
        after: GuildChannel,
    ):
        """Channel Update Event

        Parameters
        ----------
        before : GuildChannel
            Channel before editing
        after : GuildChannel
            Channel after editing
        """
        if not before.guild or before.guild.id != 719343092963999804:
            return

        embed1 = Embed(title=f"Channel Update: {after.name}", colour=Colour.red(), timestamp=before.created_at)
        embed1.set_image(url=WHITE_BAR)
        embed2 = Embed(colour=Colour.green(), timestamp=utcnow())
        embed2.set_image(url=WHITE_BAR)

        embeds = [embed1]

        topic1 = getattr(before, "topic", None)
        topic2 = getattr(after, "topic", None)
        if condition := before.name != after.name or topic1 != topic2:
            embed1.title = f"Channel Before: {before.name}"
            embed2.title = f"Channel Afterwards: {after.name}"
            if topic1 != topic2:
                embed1.description, embed2.description = topic1, topic2

        if not any(
            (
                after.category and after.category.overwrites == after.overwrites,
                before.overwrites == after.overwrites,
            )
        ):
            condition = True

            differences = Embed(
                title="Permissions Overwritten",
                description="",
                colour=Colour.blurple(),
                timestamp=utcnow(),
            )
            items = []

            for item in before.overwrites | after.overwrites:

                if len(differences.fields) >= 25:
                    break

                if item not in before.overwrites:
                    items.append(f"+ {item}")
                elif item not in after.overwrites:
                    items.append(f"- {item}")
                elif not (item in before.overwrites and item in after.overwrites):
                    continue

                value1 = dict(before.overwrites.get(item, PermissionOverwrite()))
                value2 = dict(after.overwrites.get(item, PermissionOverwrite()))

                if text := "\n".join(
                    f"{icon1} -> {icon2}: {key.replace('_', ' ').title()}"
                    for key in value1.keys()
                    if value1[key] != value2[key]
                    and (icon1 := ICON_VALUES[value1[key]])
                    and (icon2 := ICON_VALUES[value2[key]])
                ):
                    differences.add_field(name=str(item), value=text[:1024])

            differences.description = "\n".join(items)

            embeds.append(differences)

        if not condition:
            return

        try:
            name = after.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, after.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        view.add_item(Button(emoji=emoji, label=name, url=after.jump_url))

        if embed2.title or embed2.description:
            embeds.append(embed2)

        if before.category != after.category:
            condition = True
            cat_name1 = getattr(before.category, "name", "No Category")
            cat_name2 = getattr(after.category, "name", "No Category")
            embeds[-1].set_footer(text=f"Category: {cat_name1} -> {cat_name2}")

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(
            embeds=embeds,
            view=view,
            thread=Object(id=1020153288617906256),
        )

    @commands.Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        if guild.id != 719343092963999804:
            return

        embed = Embed(
            title="Member Unbanned",
            colour=Colour.green(),
            description=f"{user.mention} - {user}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {user.id}")
        asset = user.display_avatar.replace(format="png", size=512)
        log = await self.bot.webhook(1020151767532580934, reason="Join Logging")
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(name="Account Age", value=format_dt(user.created_at, style="R"))
            db1 = self.bot.mongo_db("Roleplayers")
            view = View()
            if item := await db1.find_one({"user": user.id}):
                url = f"https://discord.com/channels/{guild.id}/{item['id']}"
                view.add_item(Button(label="Characters", url=url))
            await log.send(
                embed=embed,
                file=file,
                view=view,
                thread=Object(id=1020153286285865000),
                username=user.display_name,
                avatar_url=user.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_message(self, message: Message):

        if message.mention_everyone or message.role_mentions:
            return
        channel = message.channel

        if not (word := channels.get(channel.id)):
            return

        if message.author.bot:
            return

        webhook = await self.bot.webhook(channel)

        if message.webhook_id and webhook.id != message.webhook_id:
            await message.delete(delay=0)
            return

        context = await self.bot.get_context(message)

        if context.command:
            return

        member: Member = message.author
        self.bot.msg_cache_add(message)
        kwargs = await self.embed_info(message)
        if embeds := kwargs.get("embeds", []):
            embeds[0].title = word
        del kwargs["view"]
        view = AnnouncementView(member=member, **kwargs)
        conf_embed = Embed(title=word, color=Colour.blurple(), timestamp=utcnow())
        conf_embed.set_image(url=WHITE_BAR)
        conf_embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
        await message.reply(embed=conf_embed, view=view)
        await view.wait()
        await message.delete(delay=0)

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        """Bump handler for message editing bots

        Parameters
        ----------
        before : Message
            Message before editing
        after : Message
            Message after editing
        """
        if not isinstance(member := after.author, Member):
            return

        if member.guild.id != 719343092963999804:
            return

        if member.bot or await self.bot.is_owner(member):
            return

        embed1 = Embed(
            title="Previous Message",
            colour=Colour.red(),
            description="",
            timestamp=before.edited_at or before.created_at,
        )
        embed1.set_image(url=WHITE_BAR)
        embed2 = Embed(
            title="Message Afterwards",
            colour=Colour.green(),
            description="",
            timestamp=after.edited_at or utcnow(),
        )
        embed2.set_image(url=WHITE_BAR)

        embeds, files = [embed1, embed2], []

        if condition := before.content != after.content:
            embed1.description, embed2.description = before.content, after.content

        if before.attachments and not after.attachments:
            embed2.description += "Removed Attachments. "
            files = [await x.to_file(use_cached=True) for x in before.attachments]
            condition = True

        if before.pinned != after.pinned:
            condition = True
            if before.pinned:
                embed2.set_author(name="Unpinned Message")
            elif after.pinned:
                embed2.set_author(name="Pinned Message")

        if before.embeds and not after.embeds:
            condition = True
            embed2.description += "Removed Embeds. "
            embeds.extend(before.embeds)

        if not condition:
            return

        try:
            name = after.channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, after.channel.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        view.add_item(Button(emoji=emoji, label=name, url=after.jump_url))

        log = await self.bot.webhook(1020151767532580934, reason="Edit Logging")
        await log.send(
            username=member.display_name,
            avatar_url=member.display_avatar,
            files=files,
            embeds=embeds,
            view=view,
            thread=Object(id=1020153290471772200),
        )

    @commands.Cog.listener()
    async def on_message_delete(self, ctx: Message):
        """Cached Message deleted detection

        Parameters
        ----------
        message: Message
            Cached Message
        """
        if ctx.id in self.bot.msg_cache:
            return

        if not ctx.guild or ctx.guild.id != 719343092963999804:
            return

        user: Member = ctx.author
        w = await self.bot.webhook(1020151767532580934, reason="Raw Message delete logging")
        if (
            not ctx.guild
            or ctx.webhook_id == w.id
            or self.bot.user == user
            or user.id == self.bot.owner_id
            or user.id in self.bot.owner_ids
        ):
            return

        if kwargs := await self.embed_info(ctx):
            if not ctx.webhook_id:
                kwargs["content"] = ctx.author.mention
                kwargs["allowed_mentions"] = AllowedMentions.none()
            await w.send(**kwargs, thread=Object(id=1020153332481937518))

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        """Message deleted detection

        Parameters
        ----------
        payload: RawMessageDeleteEvent
            Deleted Message Event
        """
        with suppress(KeyError):
            self.bot.msg_cache.remove(payload.message_id)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages: list[Message]):
        """This coroutine triggers upon cached bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        if not messages:
            return

        msg = messages[0]

        if not msg.guild or msg.guild.id != 719343092963999804:
            return

        w = await self.bot.webhook(1020151767532580934, reason="Bulk delete logging")

        if (messages := [x for x in messages if x.id not in self.bot.msg_cache and x.webhook_id != w.id]) and (
            paste := await self.bot.m_bin.create_paste(
                filename=f"{utcnow().strftime('%x')} - {msg.channel}.yaml",
                content=dump(
                    data=[*map(message_line, messages)],
                    allow_unicode=True,
                    sort_keys=False,
                ),
                syntax="yaml",
            )
        ):
            embed = Embed(
                title="Bulk Message Delete",
                url=paste,
                description=f"Deleted {len(messages)} messages",
                timestamp=utcnow(),
            )
            embed.set_image(url=WHITE_BAR)
            embed.set_footer(text=msg.guild.name, icon_url=msg.guild.icon)

            emoji, name = SETTING_EMOJI, msg.channel.name
            try:
                name = msg.channel.name.replace("»", "")
                emoji, name = name.split("〛")
            except ValueError:
                emoji, name = SETTING_EMOJI, msg.channel.name
            finally:
                name = name.replace("-", " ").title()

            view = View()
            view.add_item(Button(emoji=emoji, label=name, url=msg.jump_url))
            view.add_item(Button(emoji=LINK_EMOJI, label="See Logs", url=str(paste)))
            await w.send(embed=embed, view=view, thread=Object(id=1020153317889953833))

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        """This coroutine triggers upon raw bulk message deletions.

        Parameters
        ----------
        payload: RawBulkMessageDeleteEvent
            Messages that were deleted.
        """
        self.bot.msg_cache -= payload.message_ids

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return

        try:
            guild: Guild = self.bot.get_guild(payload.guild_id)
            if not (channel := guild.get_channel_or_thread(payload.channel_id)):
                channel = await guild.fetch_channel(payload.channel_id)

            message = await channel.fetch_message(payload.message_id)
            everyone = guild.get_role(guild.id)

            reactions = [x for x in message.reactions if str(x.emoji) == str(payload.emoji)]
            reaction = reactions[0]

            if (
                not message.is_system()
                and channel.category_id is not None
                and message.author != self.bot.user
                and message.author != payload.member
                and bool(channel.permissions_for(everyone).add_reactions)
                and channel.category_id not in DISABLED_CATEGORIES
                and not any(x.type == "rich" for x in message.embeds)
                and (not message.author.bot or message.webhook_id)
            ):
                if reaction.count >= STARS_AMOUNT and not message.pinned:
                    await message.pin()
            else:
                await reaction.remove(payload.member)
        except DiscordException as e:
            self.bot.logger.exception("Error on Star System", exc_info=e)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        if str(payload.emoji) != "\N{WHITE MEDIUM STAR}":
            return

        try:
            guild: Guild = self.bot.get_guild(payload.guild_id)
            if not (channel := guild.get_channel_or_thread(payload.channel_id)):
                channel = await guild.fetch_channel(payload.channel_id)

            message = await channel.fetch_message(payload.message_id)
            everyone = guild.get_role(guild.id)

            reactions = [x for x in message.reactions if str(x.emoji) == str(payload.emoji)]
            reaction = reactions[0]

            if (
                not message.is_system()
                and channel.category_id is not None
                and message.author != self.bot.user
                and message.author != payload.member
                and bool(channel.permissions_for(everyone).add_reactions)
                and channel.category_id not in DISABLED_CATEGORIES
                and not any(x.type == "rich" for x in message.embeds)
                and (not message.author.bot or message.webhook_id)
                and reaction.count < STARS_AMOUNT
                and message.pinned
            ):
                await message.unpin()
        except DiscordException as e:
            self.bot.logger.exception("Error on Star System", exc_info=e)

    async def tenor_fetch(self, image_id: str):
        try:
            params = {"ids": image_id, "key": TENOR_API}
            async with self.bot.session.get(url=TENOR_URL, params=params) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["results"][0]
                    media = result["media"][0]
                    title: str = result["title"] or result["content_description"]
                    url: str = result["itemurl"]
                    image: str = media["gif"]["url"]
                    return title, url, image
        except (ClientResponseError, IndexError, KeyError):
            return None

    async def giphy_fetch(self, image_id: str):
        URL = f"{GIPHY_URL}/{image_id}"
        try:
            params = {"api_key": GIPHY_API}
            async with self.bot.session.get(url=URL, params=params) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["data"]
                    title: str = result["title"]
                    url: str = result["url"]
                    image: str = result["images"]["original"]["url"]
                    return title, url, image
        except (ClientResponseError, KeyError):
            return None

    async def gif_fetch(self, url: str):
        image_id = url.split("-")[-1]
        if url.startswith("https://tenor.com/"):
            return await self.tenor_fetch(image_id)
        if url.startswith("https://giphy.com/"):
            return await self.giphy_fetch(image_id)

    async def embed_info(self, message: Message):
        embed = Embed(title="Message", description=message.content, color=Colour.blurple())
        embed.set_image(url=WHITE_BAR)
        files = []
        embeds: list[Embed] = [embed]

        for sticker in message.stickers:
            if embed.title == "Sticker":
                aux = Embed(color=Colour.blurple())
                embeds.append(aux)
            else:
                aux = embed
                aux.description = None

            aux.title = "Sticker"
            aux.set_image(url=sticker.url)
            aux.add_field(name="Sticker Name", value=sticker.name)

        for e in message.embeds:
            match e.type:
                case "gifv":
                    if data := await self.gif_fetch(e.url):
                        gif_title, gif_url, gif_image = data
                        if embed.title == "GIF":
                            aux = Embed(color=Colour.blurple())
                            embeds.append(aux)
                        else:
                            aux = embed
                            aux.description = None

                        aux.title = "GIF"
                        aux.url = gif_url
                        aux.set_image(url=gif_image)
                        aux.add_field(name="GIF Title", value=gif_title)
                case "image":
                    if embed.description == e.url:
                        aux = embed
                    else:
                        aux = Embed(color=Colour.blurple())
                        embeds.append(aux)
                    aux.set_image(url=e.url)
                case "article" | "link":
                    if message.content == e.url:
                        aux = embed
                        aux.title = e.title
                        aux.description = e.description
                        aux.url = e.url
                    else:
                        aux = e
                    if provider := e.provider:
                        aux.set_author(name=provider.name, url=provider.url or e.url)
                    if thumbnail := e.thumbnail:
                        aux.set_image(url=thumbnail.url)
                        aux.set_thumbnail(url=None)
                    if aux != embed:
                        embeds.append(aux)
                case _:
                    embeds.append(e)

        for index, attachment in enumerate(message.attachments, start=1):
            try:
                extension = attachment.filename.split(".")[-1]
                if attachment.content_type.startswith("image/"):
                    file = await attachment.to_file(use_cached=True, filename=f"img{index}.{extension}")
                    if embed.image.url == WHITE_BAR:
                        aux = embed
                    else:
                        aux = Embed(color=Colour.blurple())
                        embeds.append(aux)
                    aux.set_image(url=f"attachment://{file.filename}")
                else:
                    file = await attachment.to_file(use_cached=True)
                files.append(file)
            except HTTPException:
                continue

        try:
            name = message.channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, message.channel.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        view.add_item(Button(emoji=emoji, label=name, url=message.jump_url))

        username: str = message.author.display_name
        if message.author.bot and "〕" not in username:
            username = f"Bot〕{username}"

        embeds = embeds[:10]
        last_embed = embeds[-1]
        last_embed.set_footer(text=message.guild.name, icon_url=message.guild.icon)
        last_embed.timestamp = utcnow()

        return dict(
            embeds=embeds,
            files=files,
            view=view,
            username=username,
            avatar_url=message.author.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        """This allows me to check when commands are being used.

        Parameters
        ----------
        ctx: Context
            Context
        """
        name: str = ctx.guild.name if ctx.guild else "Private Message"
        self.bot.logger.info("%s > %s > %s", name, ctx.author, ctx.command.qualified_name)

    async def on_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        error: Exception | app_commands.AppCommandError = getattr(error, "original", error)
        command = interaction.command
        resp: InteractionResponse = interaction.response
        if command and command._has_any_error_handlers():
            return

        self.bot.logger.error(
            "Interaction Error(%s, %s)",
            getattr(command, "name", "Unknown"),
            ", ".join(f"{k}={v}" for k, v in interaction.data.items()),
            exc_info=error,
        )

        with suppress(NotFound):
            if not resp.is_done():
                await resp.defer(thinking=True, ephemeral=True)

        embed = Embed(color=Colour.red(), timestamp=interaction.created_at)
        embed.set_image(url=WHITE_BAR)

        if not isinstance(error, app_commands.AppCommandError):
            embed.title = f"Error - {type(error := error.__cause__ or error).__name__}"
            embed.description = f"```py\n{error}\n```"
        else:
            embed.title = f"Error - {type(error).__name__}"
            embed.description = str(error)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """Command error handler

        Parameters
        ----------
        ctx: Context
            Context
        error: CommandError
            Error
        """
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(
            error,
            (
                commands.CheckFailure,
                commands.UserInputError,
                commands.CommandOnCooldown,
                commands.MaxConcurrencyReached,
                commands.DisabledCommand,
            ),
        ):
            await ctx.send(
                embed=Embed(
                    color=Colour.red(),
                    title=f"Error - {ctx.command.qualified_name}",
                    description=str(error),
                )
            )
            return

        if hasattr(ctx.command, "on_error"):
            return

        if (cog := ctx.cog) and cog._get_overridden_method(cog.cog_command_error):
            return

        error_cause = error.__cause__ or error
        await ctx.send(
            embed=Embed(
                color=Colour.red(),
                title=f"Unexpected error - {ctx.command.qualified_name}",
                description=f"```py\n{type(error_cause).__name__}: {error_cause}\n```",
            )
        )

        self.bot.logger.error(
            "Command Error(%s, %s)",
            ctx.command.qualified_name,
            ", ".join(f"{k}={v!r}" for k, v in ctx.kwargs.items()),
            exc_info=error,
        )

    @commands.Cog.listener()
    async def on_ready(self):
        """Loads the program in the scheduler"""
        if self.ready:
            return

        if not (channel := self.bot.get_channel(860590339327918100)):
            channel = await self.bot.fetch_channel(860590339327918100)

        db = self.bot.mongo_db("Poll")
        async for item in db.find({}):
            view = PollView.from_mongo(item)
            self.bot.add_view(view, message_id=item["id"])

        await PartialMessage(channel=channel, id=1023703599538257940).edit(view=InformationView())
        self.ready = True


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Information(bot))
