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

from io import StringIO
from os import getenv
from typing import Optional

from aiohttp import ClientResponseError
from colour import Color
from discord import (
    AllowedMentions,
    Attachment,
    ButtonStyle,
    ChannelType,
    Colour,
    DiscordException,
    Embed,
    File,
    Guild,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    Role,
    SelectOption,
    Thread,
    Webhook,
    WebhookMessage,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Modal, Select, TextInput, View, button, select
from discord.utils import find, format_dt, get, utcnow
from yaml import dump

from src.structures.bot import CustomBot
from src.utils.etc import DEFAULT_TIMEZONE, SETTING_EMOJI, WHITE_BAR
from src.utils.functions import embed_handler, message_line
from src.views.message_view import MessageView

__all__ = ("Information", "setup")


channels = {
    766018765690241034: "OC Question",
    918703451830100028: "Poll",
    728800301888307301: "Suggestion",
    769304918694690866: "Story",
    903627523911458816: "Storyline",
    957711698205216799: "RP",
    957726527666151505: "Game",
    839105256235335680: "Random Fact",
    723228500835958987: "Announcement",
    740606964727546026: "Question",
    908498210211909642: "Mission",
}

private = {
    860590339327918100: "Ticket",
}

LOGS = {
    719343092963999804: 719663963297808436,
    952517983786377287: 952588363263782962,
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


PING_ROLES = {
    "Announcements": 908809235012419595,
    "Everyone": 719343092963999804,
    "Radio": 805878418225889280,
    "Partners": 725582056620294204,
    "Moderation": 720296534742138880,
    "No": 0,
}


class AnnouncementModal(Modal):
    def __init__(self, *, word: str, name: str, **kwargs) -> None:
        super().__init__(title=word, timeout=None)
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

    async def on_submit(self, interaction: Interaction) -> None:
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=True)
        webhook: Webhook = await interaction.client.webhook(interaction.channel)
        if embeds := self.kwargs.get("embeds"):
            embeds[0].title = self.thread_name.value
        msg = await webhook.send(**self.kwargs, wait=True)
        thread = await msg.create_thread(name=self.thread_name.value)
        await thread.add_user(interaction.user)
        match self.word:
            case "Poll":
                await msg.add_reaction("\N{THUMBS UP SIGN}")
                await msg.add_reaction("\N{THUMBS DOWN SIGN}")
            case "RP" | "OC Question" | "Story" | "Storyline" | "Mission":
                if tupper := interaction.guild.get_member(431544605209788416):
                    await thread.add_user(tupper)
        await interaction.followup.send("Thread created successfully", ephemeral=True)
        self.stop()


class AnnouncementView(View):
    def __init__(self, *, member: Member, **kwargs):
        super(AnnouncementView, self).__init__()
        self.member = member
        self.kwargs = kwargs

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if interaction.user != self.member:
            await resp.send_message(f"Message requested by {self.member.mention}", ephemeral=True)
            return False
        return True

    @select(
        placeholder="Role to Ping",
        options=[
            SelectOption(
                label=f"{k} Role",
                value=f"{v}",
                description=f"Pings the {k} role" if v else "No pings",
                emoji="\N{CHEERING MEGAPHONE}",
                default=not v,
            )
            for k, v in PING_ROLES.items()
        ],
    )
    async def ping(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        if role := ctx.guild.get_role(int(sct.values[0])):
            if role.is_default():
                self.kwargs["content"] = "@everyone"
                mentions = AllowedMentions(everyone=True)
            else:
                self.kwargs["content"] = role.mention
                mentions = AllowedMentions(roles=True)
            self.kwargs["allowed_mentions"] = mentions
            info = f"Alright, will ping {role.mention}"
        else:
            self.kwargs["content"] = ""
            self.kwargs["allowed_mentions"] = AllowedMentions.none()
            info = "Alright, won't ping."
        await resp.send_message(info, ephemeral=True)

    @button(label="Proceed", style=ButtonStyle.blurple, emoji=SETTING_EMOJI)
    async def confirm(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        word = channels.get(ctx.channel_id)
        data = ctx.created_at.astimezone(tz=DEFAULT_TIMEZONE)
        name = f"{word} {ctx.user.display_name} {data.strftime('%B %d')}"
        modal = AnnouncementModal(word=word, name=name, **self.kwargs)
        await resp.send_modal(modal)
        await modal.wait()
        try:
            await ctx.message.delete()
        except DiscordException:
            pass
        self.stop()

    @button(label="Cancel", style=ButtonStyle.blurple, emoji=SETTING_EMOJI)
    async def cancel(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.pong()
        await ctx.message.delete()
        self.stop()


class Information(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.join: dict[Member, Message] = {}
        self.ready = False
        self.message: Optional[WebhookMessage] = None
        self.view: Optional[MessageView] = None
        self.bot.tree.on_error = self.on_error

    @app_commands.command()
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_role("Booster")
    async def custom_role(
        self,
        ctx: Interaction,
        name: Optional[str],
        color: Optional[str],
        icon: Optional[Attachment],
    ):
        """Create custom roles (no info deletes them)

        Parameters
        ----------
        ctx : Interaction
            Interaction
        name : Option, optional
            Role Name
        color : Option, optional
            Name or Hex color
        icon : Option, optional
            Valid Role Icon
        """
        resp: InteractionResponse = ctx.response
        guild: Guild = ctx.guild

        await resp.defer(ephemeral=True)

        AFK = get(guild.roles, name="AFK")
        BOOSTER = guild.premium_subscriber_role

        if not (AFK and BOOSTER):
            await ctx.followup.send("No function set here", ephemeral=True)
            return

        role = find(
            lambda x: BOOSTER < x < AFK and ctx.user in x.members,
            guild.roles,
        )

        if role or name:
            if not role:
                guild: Guild = ctx.guild
                try:
                    role: Role = await guild.create_role(name=name)
                    await role.edit(position=AFK.position - 1)
                    await ctx.user.add_roles(role)
                except DiscordException as e:
                    await ctx.followup.send(str(e), ephemeral=True)
                    return
            elif not (name or color or icon):
                try:
                    await role.delete()
                except DiscordException as e:
                    await ctx.followup.send(str(e), ephemeral=True)
                else:
                    await ctx.followup.send("Role deleted", ephemeral=True)
                return

            if isinstance(color, str):
                try:
                    data = Color(color)
                    await role.edit(colour=int(data.hex[1:], base=16))
                except ValueError:
                    await ctx.followup.send(
                        "Invalid color",
                        ephemeral=True,
                    )
                except DiscordException:
                    await ctx.followup.send(
                        "Invalid color for discord",
                        ephemeral=True,
                    )
            if isinstance(icon, Attachment):
                try:
                    data = await icon.read()
                    await role.edit(display_icon=data)
                except DiscordException:
                    await ctx.followup.send(
                        "Invalid icon for discord",
                        ephemeral=True,
                    )
            if not ctx.response.is_done():
                await ctx.followup.send("Role added/modified.", ephemeral=True)
        else:
            await ctx.followup.send(
                "You have to provide a name for the role",
                ephemeral=True,
            )

    @commands.Cog.listener()
    async def on_message(self, message: Message):

        if message.mention_everyone or message.role_mentions:
            return

        if not (word := (channels | private).get(message.channel.id)):
            return

        if message.author.bot:
            return

        webhook = await self.bot.webhook(message.channel)

        if message.webhook_id and webhook.id != message.webhook_id:
            await message.delete()
            return

        context = await self.bot.get_context(message)

        if context.command:
            return

        member: Member = message.author
        self.bot.msg_cache_add(message)
        kwargs = await self.embed_info(message)
        if embeds := kwargs.get("embeds", []):
            embeds[0].title = word
        files = kwargs.get("files", [])
        text = f"Embeds: {len(embeds)}, Attachments: {len(files)}"
        if message.channel.id in channels:
            del kwargs["view"]
            view = AnnouncementView(member=member, **kwargs)
            if word != "Announcement":
                view.remove_item(view.ping)
            conf_embed = Embed(title="Confirmation", color=0xFFFFFE, timestamp=utcnow())
            conf_embed.set_image(url=WHITE_BAR)
            conf_embed.set_footer(text=text)
            await message.reply(embed=conf_embed, view=view)
            await view.wait()
        elif message.channel.id in private:
            data = message.created_at.astimezone(tz=DEFAULT_TIMEZONE)
            name = f"{member.display_name} {data.strftime('%B %d, %Y')}"
            thread = await webhook.channel.create_thread(name=name, type=ChannelType.private_thread)
            msg = await webhook.send(thread=thread, wait=True, **kwargs)
            members = {member}
            members.update(message.mentions)
            for user in members:
                if isinstance(user, Member):
                    await thread.add_user(user)
            if word == "Ticket":
                mod_webhook = await self.bot.webhook(955477074016084050, reason=word)
                view = View()
                view.add_item(Button(label=f"See {word}", url=msg.jump_url, emoji=SETTING_EMOJI))
                embed = Embed(
                    title=f"New {word}",
                    description="\n".join(f"• {x.mention}" for x in members),
                    color=member.color,
                    timestamp=utcnow(),
                )
                embed.set_image(url=WHITE_BAR)
                embed.set_footer(text=text)
                await mod_webhook.send(
                    embed=embed,
                    view=view,
                    username=member.display_name,
                    avatar_url=member.display_avatar.url,
                )
        try:
            await message.delete()
        except DiscordException:
            pass

    async def member_count(self, guild: Guild):
        """Function which updates the member count and the Information's view"""
        channel = guild.rules_channel
        msg_id = MSG_INFO.get(guild.id)
        if not (channel and msg_id):
            return

        w = await self.bot.webhook(channel, reason="Member Count")
        msg = await w.fetch_message(msg_id)
        if not msg.embeds:
            return

        embed = embed_handler(msg, msg.embeds[0].copy())
        embed.clear_fields()
        members = len([m for m in guild.members if not m.bot])
        total = len(guild.members)
        embed.add_field(name="**__Members__**", value=f"`{members:04d}`")
        embed.add_field(name="**__Bots__**", value=f"`{total - members:02d}`")
        embed.add_field(name="**__Total__**", value=f"`{total:04d}`")
        if embed.fields != msg.embeds[0].fields:
            await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        await self.member_count(member.guild)
        if not (log_id := LOGS.get(member.guild.id)):
            return

        try:
            if msg := self.join.pop(member, None):
                await msg.delete()
        except DiscordException:
            pass
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

        cog = self.bot.get_cog("Submission")
        if value := cog.oc_list.get(member.id):
            view.add_item(
                Button(
                    label="Characters",
                    url=f"https://discord.com/channels/719343092963999804/919277769735680050/{value}",
                )
            )

        AFK = get(roles, name="AFK")
        BOOSTER = find(lambda x: x.is_premium_subscriber(), roles)

        if (AFK and BOOSTER) and (
            role := find(
                lambda x: BOOSTER < x < AFK and member in x.members,
                roles,
            )
        ):
            try:
                await role.delete(reason="User Left")
            except DiscordException:
                pass

        asset = member.display_avatar.replace(format="png", size=4096)
        if file := await self.bot.get_file(
            asset.url,
            filename=str(member.id),
        ):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            log = await self.bot.webhook(log_id, reason="Join Logging")
            await log.send(
                file=file,
                embed=embed,
                view=view,
                username=member.display_name,
                avatar_url=member.display_avatar.url,
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: Member):
        if not (log_id := LOGS.get(member.guild.id)):
            return

        await self.member_count(member.guild)

        embed = Embed(
            title="Member Joined",
            colour=Colour.green(),
            description=f"{member.mention} - {member}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {member.id}")
        asset = member.display_avatar.replace(format="png", size=512)
        log = await self.bot.webhook(log_id, reason="Join Logging")
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(
                name="Account Age",
                value=format_dt(member.created_at, style="R"),
            )
            view = View()
            cog = self.bot.get_cog("Submission")
            if value := cog.oc_list.get(member.id):
                view.add_item(
                    Button(
                        label="User Characters".center(80, "\u2008"),
                        url=f"https://discord.com/channels/719343092963999804/919277769735680050/{value}",
                    )
                )
            await log.send(embed=embed, file=file, view=view)

    @commands.Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.premium_since == now.premium_since:
            return
        if past.premium_since and not now.premium_since:
            embed = Embed(
                title="Has un-boosted the Server!",
                colour=Colour.red(),
                timestamp=utcnow(),
            )

            AFK = get(now.guild.roles, name="AFK")
            BOOSTER = find(lambda x: x.is_premium_subscriber(), now.guild.roles)

            if (AFK and BOOSTER) and (
                role := find(
                    lambda x: BOOSTER < x < AFK and now in x.members,
                    now.guild.roles,
                )
            ):
                try:
                    await role.delete(reason="User Left")
                except DiscordException:
                    pass
        else:
            embed = Embed(
                title="Has boosted the Server!",
                colour=Colour.brand_green(),
                timestamp=utcnow(),
            )
        embed.set_image(url=WHITE_BAR)
        asset = now.display_avatar.replace(format="png", size=4096)
        embed.set_thumbnail(url=asset.url)
        if icon := now.guild.icon:
            embed.set_footer(text=now.guild.name, icon_url=icon.url)
        else:
            embed.set_footer(text=now.guild.name)

        if log_id := LOGS.get(now.guild.id):
            log = await self.bot.webhook(log_id, reason="Logging")
            await log.send(content=now.mention, embed=embed)

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent) -> None:
        """This coroutine triggers upon raw bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        if payload.channel_id == 957604961330561065:
            messages = self.view.messages
            if any(x.id in payload.message_ids for x in messages):
                messages = [x for x in messages if x.id not in payload.message_ids]
                self.view.messages = messages
                await self.message.edit(view=self.view)

        if not (payload.guild_id and (log_id := LOGS.get(payload.guild_id))):
            return

        w = await self.bot.webhook(log_id, reason="Bulk delete logging")

        if messages := [
            message
            for message in payload.cached_messages
            if message.id not in self.bot.msg_cache and message.webhook_id != w.id
        ]:
            msg = messages[0]
            fp = StringIO()
            dump(list(map(message_line, messages)), stream=fp)
            fp.seek(0)
            file = File(fp=fp, filename="Bulk.yaml")
            embed = Embed(title="Bulk Message Delete", timestamp=utcnow())
            embed.set_footer(text=f"Deleted {len(messages)} messages")
            embed.set_image(url=WHITE_BAR)
            try:
                emoji, name = msg.channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = SETTING_EMOJI, msg.channel.name
            finally:
                name = name.replace("-", " ").title()

            view = View()
            view.add_item(Button(emoji=emoji, label=name, url=msg.jump_url))
            await w.send(embed=embed, file=file, view=view)

        self.bot.msg_cache -= payload.message_ids

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
        embed = Embed(
            title="Message",
            description=message.content,
            color=Colour.blurple(),
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        text = f"Embeds: {len(message.embeds)}, Attachments: {len(message.attachments)}"
        embed.set_footer(text=text, icon_url=message.guild.icon.url)
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

        for attachment in message.attachments:
            try:
                file = await attachment.to_file(use_cached=True)
            except HTTPException:
                continue
            else:
                if attachment.content_type.startswith("image/"):
                    if embed.image.url == WHITE_BAR:
                        aux = embed
                    else:
                        aux = Embed(color=Colour.blurple())
                        embeds.append(aux)
                    aux.set_image(url=f"attachment://{attachment.filename}")
                files.append(file)

        try:
            name = message.channel.name.replace("»", "")
            emoji, name = name.split("〛")
        except ValueError:
            emoji, name = SETTING_EMOJI, message.channel.name
        finally:
            name = name.replace("-", " ").title()

        view = View()
        view.add_item(
            Button(
                emoji=emoji,
                label=name,
                url=message.jump_url,
            )
        )

        username: str = message.author.display_name
        if message.author.bot and "〕" not in username:
            username = f"Bot〕{username}"

        return dict(
            embeds=embeds[:10],
            files=files,
            view=view,
            username=username,
            avatar_url=message.author.display_avatar.url,
        )

    @commands.Cog.listener()
    async def on_raw_message_delete(
        self,
        payload: RawMessageDeleteEvent,
    ) -> None:
        """Message deleted detection

        Parameters
        ----------
        payload: RawMessageDeleteEvent
            Deleted Message Event
        """
        if payload.channel_id == 957604961330561065:
            messages = self.view.messages
            if any(x.id == payload.message_id for x in messages):
                messages = [x for x in messages if x.id != payload.message_id]
                self.view.messages = messages
                await self.message.edit(view=self.view)

        if not (ctx := payload.cached_message):
            self.bot.msg_cache -= {payload.message_id}
            return

        if not (payload.guild_id and (log_id := LOGS.get(payload.guild_id))):
            return

        w = await self.bot.webhook(log_id, reason="Raw Message delete logging")

        user: Member = ctx.author

        if (
            not ctx.guild
            or ctx.webhook_id == w.id
            or self.bot.user == user
            or user.id == self.bot.owner_id
            or user.id in self.bot.owner_ids
        ):
            return

        if ctx.id in self.bot.msg_cache:
            self.bot.msg_cache.remove(ctx.id)
        elif kwargs := await self.embed_info(ctx):
            if not ctx.webhook_id:
                kwargs["content"] = ctx.author.mention
                kwargs["allowed_mentions"] = AllowedMentions.none()
            await w.send(**kwargs)

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context) -> None:
        """This allows me to check when commands are being used.

        Parameters
        ----------
        ctx: Context
            Context
        """
        guild: Optional[Guild] = ctx.guild
        if guild:
            self.bot.logger.info(
                "%s > %s > %s",
                guild.name,
                ctx.author,
                ctx.command.qualified_name,
            )
        else:
            self.bot.logger.info(
                "Private message > %s > %s",
                ctx.author,
                ctx.command.qualified_name,
            )

    async def on_error(
        self,
        interaction: Interaction,
        error: app_commands.AppCommandError,
    ):
        error: Exception | app_commands.AppCommandError = getattr(error, "original", error)
        command = interaction.command
        resp: InteractionResponse = interaction.response
        if command and command._has_any_error_handlers():
            return

        name = command.name if command else ""

        if not resp.is_done():
            await resp.defer(ephemeral=True)

        if isinstance(error, app_commands.AppCommandError):
            await interaction.followup.send(
                embed=Embed(
                    color=Colour.red(),
                    title=f"Error - {name}",
                    description=str(error),
                ),
                ephemeral=True,
            )
        elif error_cause := error.__cause__:
            await interaction.followup.send(
                embed=Embed(
                    color=Colour.red(),
                    title=f"Unexpected error - {name}",
                    description=f"```py\n{type(error_cause).__name__}: {error_cause}\n```",
                ),
                ephemeral=True,
            )

        self.bot.logger.error(
            "Interaction Error(%s, %s)",
            command,
            ", ".join(f"{k}={v!r}" for k, v in interaction.data.items()),
            exc_info=error,
        )

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError,
    ) -> None:
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

        if error_cause := error.__cause__:
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
        if not self.ready:
            for guild in self.bot.guilds:
                await self.member_count(guild)
            thread: Thread = await self.bot.fetch_channel(913555643699458088)
            if thread.archived:
                await thread.edit(archived=False)
            iterator = thread.history(limit=None, oldest_first=True)
            messages = [m async for m in iterator]
            w = await self.bot.webhook(thread)
            self.view = MessageView(messages)
            self.message = await w.edit_message(
                913555643699458088,
                view=self.view,
            )
            self.ready = True


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Information(bot))
