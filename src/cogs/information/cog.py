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
from io import StringIO
from os import getenv
from typing import Optional

from colour import Color
from discord import (
    AllowedMentions,
    Attachment,
    Colour,
    DiscordException,
    Embed,
    File,
    Forbidden,
    Guild,
    HTTPException,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    NotFound,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    Role,
    SelectOption,
    Webhook,
    app_commands,
)
from discord.ext import commands
from discord.ui import Button, Select, View, button, select
from discord.utils import find, format_dt, get, utcnow
from yaml import dump

from src.structures.bot import CustomBot
from src.utils.etc import MAP_ELEMENTS, WHITE_BAR
from src.utils.functions import message_line

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
}

LOGS = {
    719343092963999804: 719663963297808436,
    952517983786377287: 952588363263782962,
}

MSG_INFO = {
    719343092963999804: 913555643699458088,
    952517983786377287: 952617304095592478,
}

TENOR_API = getenv("TENOR_API")
GIPHY_API = getenv("GIPHY_API")
WEATHER_API = getenv("WEATHER_API")


PING_ROLES = {
    "Announcements": 908809235012419595,
    "Radio": 805878418225889280,
    "Partners": 725582056620294204,
    "Moderation": 720296534742138880,
    "No": None,
}


class AnnouncementView(View):
    def __init__(self, *, member: Member, **kwargs):
        super().__init__()
        self.member = member
        self.kwargs = kwargs

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if interaction.user != self.member:
            await resp.send_message(
                f"Message requested by {self.member.mention}", ephemeral=True
            )
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
            )
            for k, v in PING_ROLES.items()
        ],
    )
    async def ping(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        await resp.pong()
        await ctx.message.delete()
        if role := ctx.guild.get_role(sct.values[0]):
            self.kwargs["content"] = role.mention
            self.kwargs["allowed_mentions"] = AllowedMentions(roles=True)
            info = f"Alright, will ping {role.mention}"
        else:
            self.kwargs["content"] = ""
            self.kwargs["allowed_mentions"] = AllowedMentions.none()
            info = "Alright, won't ping."
        await resp.send_message(info, ephemeral=True)
        self.stop()

    @button(label="Proceed")
    async def confirm(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.pong()
        await ctx.message.delete()
        webhook: Webhook = await ctx.client.webhook(ctx.channel)
        msg = await webhook.send(**self.kwargs, wait=True)
        word = channels.get(ctx.channel_id, "Question")
        thread = await msg.create_thread(name=f"{word} {msg.id}")
        await thread.add_user(ctx.user)
        match word:
            case "Poll":
                await msg.add_reaction("\N{THUMBS UP SIGN}")
                await msg.add_reaction("\N{THUMBS DOWN SIGN}")
            case "RP" | "OC Question" | "Story" | "Storyline":
                if tupper := ctx.guild.get_member(431544605209788416):
                    await thread.add_user(tupper)
        self.stop()

    @button(label="Cancel")
    async def cancel(self, ctx: Interaction, _: Button):
        await ctx.delete_original_message()
        self.stop()


class Information(commands.Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.join: dict[Member, Message] = {}
        self.bot.tree.on_error = self.on_error

    @app_commands.command(
        description="Weather information from the selected area."
    )
    @app_commands.guilds(719343092963999804)
    @app_commands.describe(area="Area to get weather info about.")
    @app_commands.choices(
        area=[
            app_commands.Choice(
                name=item.name,
                value=f"{item.lat}/{item.lon}",
            )
            for item in MAP_ELEMENTS
        ]
    )
    async def weather(
        self,
        ctx: Interaction,
        area: app_commands.Choice[str],
    ):
        """

        Parameters
        ----------
        ctx : ApplicationContext
            ctx
        area : str, optional
            area
        """
        resp: InteractionResponse = ctx.response
        if not isinstance(area, str):
            await resp.send_message("Wrong format", ephemeral=True)
        else:
            try:
                lat, lon = area.value.split("/")
                URL = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={WEATHER_API}"
                async with self.bot.session.get(URL) as f:
                    if f.status != 200:
                        await resp.send_message(
                            "Invalid response", ephemeral=True
                        )
                    data: dict = await f.json()
                    if weather := data.get("weather", []):
                        info: dict = weather[0]
                        main, desc, icon = (
                            info["main"],
                            info["description"],
                            info["icon"],
                        )
                        embed = Embed(
                            title=f"{main}: {desc}".title(),
                            color=ctx.user.color,
                            timestamp=utcnow(),
                        )
                        main_info = data["main"]

                        values = {
                            "Temp.": main_info["temp"],
                            "Temp. Min": main_info["temp_min"],
                            "Temp. Max": main_info["temp_max"],
                        }

                        for k, v in values.items():
                            embed.add_field(
                                name=k,
                                value=f"{v:.1f} ° C | {1.8 * v + 32:.1f} ° K",
                            )

                        embed.set_image(url=WHITE_BAR)
                        embed.set_thumbnail(
                            url=f"http://openweathermap.org/img/w/{icon}.png"
                        )
                        if wind := data.get("wind", {}):
                            deg, speed = wind["deg"], wind["speed"]
                            embed.set_footer(
                                text=f"Wind(Speed: {speed}, Degrees: {deg} °)"
                            )
                        await resp.send_message(embed=embed, ephemeral=True)
                        return
                await resp.send_message("Invalid value", ephemeral=True)
            except ValueError:
                await resp.send_message("Invalid value", ephemeral=True)

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

        if message.mention_everyone or not (
            message.content and message.channel.id in channels
        ):
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
        guild: Guild = member.guild
        word = channels.get(message.channel.id, "Question")

        self.bot.msg_cache_add(message)

        embed = Embed(
            title=word,
            description=message.content,
            timestamp=message.created_at,
            colour=message.author.colour,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        embeds = [embed]
        files = []
        for item in message.attachments:
            if len(embeds) < 10 and item.content_type.startswith("image/"):
                if embeds[0].image.url == WHITE_BAR:
                    aux = embed
                else:
                    aux = Embed(color=message.author.colour)
                    embeds.append(aux)
                aux.set_image(url=f"attachment://{item.filename}")
                file = await item.to_file()
                files.append(file)

        view = AnnouncementView(
            member=member,
            embeds=embeds,
            files=files,
            username=member.display_name,
            avatar_url=member.display_avatar.url,
        )
        if word != "Announcement":
            view.remove_item(view.ping)

        await message.reply("Confirmation", view=view)
        await view.wait()
        with suppress(NotFound, HTTPException, Forbidden):
            await message.delete()

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

        embed = msg.embeds[0]

        members = len([m for m in guild.members if not m.bot])
        total = len(guild.members)

        data: dict[str, int] = {}

        if cog := self.bot.get_cog("Submission"):
            ocs = [
                oc
                for oc in cog.ocs.values()
                if oc.server == guild.id and guild.get_member(oc.author)
            ]
            if total_ocs := len(ocs):
                data["Characters"] = total_ocs

        data["Members   "] = members
        data["Bots      "] = total - members
        data["Total     "] = total

        text = "\n".join(f"{key}: {value:03d}" for key, value in data.items())
        text = f"```yaml\n{text}\n```"

        if embed.description != text:
            embed.description = text
            await msg.edit(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: Member):
        await self.member_count(member.guild)
        if not (log_id := LOGS.get(member.guild.id)):
            return

        if msg := self.join.pop(member, None):
            with suppress(DiscordException):
                await msg.delete()
        guild: Guild = member.guild
        embed = Embed(
            title="Member Left - Roles",
            description="The user did not have any roles.",
            color=Colour.red(),
            timestamp=utcnow(),
        )
        if roles := member.roles[:0:-1]:
            embed.description = "\n".join(
                f"> **•** {role.mention}" for role in roles
            )
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
            with suppress(DiscordException):
                await role.delete(reason="User Left")

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
                with suppress(DiscordException):
                    await role.delete(reason="User Left")
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
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ) -> None:
        """This coroutine triggers upon raw bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        if not (payload.guild_id and (log_id := LOGS.get(payload.guild_id))):
            return

        w = await self.bot.webhook(log_id, reason="Bulk delete logging")

        if messages := [
            message
            for message in payload.cached_messages
            if message.id not in self.bot.msg_cache
            and message.webhook_id != w.id
        ]:
            msg = messages[0]
            fp = StringIO()
            fp.write(dump(list(map(message_line, messages))))
            fp.seek(0)
            file = File(fp=fp, filename="Bulk.yaml")
            embed = Embed(title="Bulk Message Delete", timestamp=utcnow())
            embed.set_footer(text=f"Deleted {len(messages)} messages")
            embed.set_image(url=WHITE_BAR)
            try:
                emoji, name = msg.channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = None, msg.channel.name
            finally:
                name = name.replace("-", " ").title().center(80, "\u2008")

            view = View()
            view.add_item(Button(emoji=emoji, label=name, url=msg.jump_url))
            await w.send(embed=embed, file=file, view=view)

        self.bot.msg_cache -= payload.message_ids

    async def tenor_fetch(self, image_id: str):
        URL = f"https://g.tenor.com/v1/gifs?ids={image_id}&key={TENOR_API}"
        with suppress(Exception):
            async with self.bot.session.get(url=URL) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["results"][0]
                    media = result["media"][0]
                    title: str = (
                        result["title"] or result["content_description"]
                    )
                    url: str = result["itemurl"]
                    image: str = media["gif"]["url"]
                    return title, url, image

    async def giphy_fetch(self, image_id: str):
        URL = f"https://api.giphy.com/v1/gifs/{image_id}?api_key={GIPHY_API}"
        with suppress(Exception):
            async with self.bot.session.get(url=URL) as data:
                if data.status == 200:
                    info = await data.json()
                    result = info["data"]
                    title: str = result["title"]
                    url: str = result["url"]
                    image: str = result["images"]["original"]["url"]
                    return title, url, image

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
            or self.bot.user.id == user.id
            or user.id == self.bot.owner_id
            or user.id in self.bot.owner_ids
        ):
            return

        if ctx.id in self.bot.msg_cache:
            self.bot.msg_cache.remove(ctx.id)
        else:
            embed = Embed(
                title="Message Deleted",
                description=ctx.content,
                color=Colour.blurple(),
                timestamp=utcnow(),
            )
            embed.set_image(url=WHITE_BAR)
            text = f"Embeds: {len(ctx.embeds)}, Attachments: {len(ctx.attachments)}"
            embed.set_footer(text=text, icon_url=ctx.guild.icon.url)
            files = []

            embeds: list[Embed] = [embed]

            for item in ctx.stickers:
                if embed.title == "Sticker Deleted":
                    aux = Embed(color=Colour.blurple())
                    embeds.append(aux)
                else:
                    aux = embed
                    aux.description = embed.Empty

                aux.title = "Sticker Deleted"
                aux.set_image(url=item.url)
                aux.add_field(name="Sticker Name", value=item.name)

            for item in ctx.embeds:
                if (
                    item.type == "gifv"
                    and isinstance(url := item.url, str)
                    and (items := url.split("-"))
                ):

                    image_id = items[-1]

                    if url.startswith("https://tenor.com/"):
                        method = self.tenor_fetch
                    elif url.startswith("https://giphy.com/"):
                        method = self.giphy_fetch
                    else:
                        method = None

                    if method and (data := await method(image_id)):
                        gif_title, gif_url, gif_image = data
                        if embed.title == "GIF Deleted":
                            aux = Embed(color=Colour.blurple())
                            embeds.append(aux)
                        else:
                            aux = embed.copy()
                            aux.description = embed.Empty

                        aux.title = "GIF Deleted"
                        aux.url = gif_url
                        aux.set_image(url=gif_image)
                        aux.add_field(name="GIF Title", value=gif_title)
                else:
                    embeds.append(item)

            for item in ctx.attachments:
                with suppress(HTTPException):
                    file = await item.to_file(use_cached=True)
                    if item.content_type.startswith("image/"):
                        if embed.image.url == WHITE_BAR:
                            aux = embed
                        else:
                            aux = Embed(color=Colour.blurple())
                            embeds.append(aux)
                        aux.set_image(url=f"attachment://{item.filename}")
                    files.append(file)

            try:
                emoji, name = ctx.channel.name.split("〛")
                emoji = emoji[0]
            except ValueError:
                emoji, name = None, ctx.channel.name
            finally:
                name = name.replace("-", " ").title().center(80, "\u2008")

            view = View()
            view.add_item(
                Button(
                    emoji=emoji,
                    label=name,
                    url=ctx.jump_url,
                )
            )

            username: str = user.display_name
            if user.bot and "〕" not in username:
                name = f"Bot〕{username}"
            elif not user.bot:
                embed.title = f"{embed.title} (User: {user.id})"

            await w.send(
                embeds=embeds[:10],
                files=files,
                view=view,
                username=username,
                avatar_url=user.display_avatar.url,
            )

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
        command: Optional[app_commands.Command | app_commands.ContextMenu],
        error: app_commands.AppCommandError,
    ):
        error: Exception | app_commands.AppCommandError = getattr(
            error, "original", error
        )
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

        if (cog := ctx.cog) and cog._get_overridden_method(
            cog.cog_command_error
        ):
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
        for guild in self.bot.guilds:
            await self.member_count(guild)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Information(bot))
