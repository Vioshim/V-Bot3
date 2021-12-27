from contextlib import suppress
from pathlib import Path
from typing import Optional

from aiofiles import open as aiopen
from apscheduler.triggers.cron import CronTrigger
from bs4 import BeautifulSoup
from discord import (
    AllowedMentions,
    CategoryChannel,
    Color,
    DiscordException,
    Embed,
    Guild,
    HTTPException,
    Member,
    Message,
    Option,
    TextChannel,
)
from discord.ext.commands import (
    CheckFailure,
    Cog,
    CommandError,
    CommandNotFound,
    CommandOnCooldown,
    DisabledCommand,
    MaxConcurrencyReached,
    UserInputError,
    slash_command,
)
from discord.ui import Button, View
from discord.utils import format_dt, utcnow
from orjson import loads
from yaml import dump

from src.cogs.information.area_selection import AreaSelection
from src.cogs.information.information_view import InformationView
from src.context import ApplicationContext, AutocompleteContext, Context
from src.structures.bot import CustomBot
from src.utils.etc import MAP_BUTTONS, WHITE_BAR
from src.utils.functions import message_line
from src.utils.imagekit import ImageKit

__all__ = ("Information", "setup")

URL = "https://www.conversationstarters.com/generator.php"


channels = {
    766018765690241034: "Question",
    918703451830100028: "Poll",
    728800301888307301: "Suggestion",
}


def map_find(ctx: AutocompleteContext):
    data: str = ctx.value or ""
    return [item for item in MAP_BUTTONS if item.name.startswith(data.title())]


class Information(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.join: dict[Member, Message] = {}
        self.view: Optional[InformationView] = None

    @Cog.listener()
    async def on_message(self, message: Message):

        if not message.content:
            return

        if message.channel.id not in channels:
            return

        if message.webhook_id:
            await message.delete()
            return

        if message.author.bot:
            return

        member: Member = message.author
        guild: Guild = member.guild
        self.bot.msg_cache_add(message)

        word = channels.get(message.channel.id, "Question")

        embed = Embed(
            title=word,
            description=message.content,
            timestamp=message.created_at,
            colour=message.author.colour,
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_author(name=f"{member}", icon_url=member.display_avatar.url)
        embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        msg = await message.channel.send(
            embed=embed,
            files=[await item.to_file() for item in message.attachments],
        )

        thread = await msg.create_thread(name=f"{word} {msg.id}")

        await thread.add_user(member)

        view = View()
        view.add_item(Button(label=f"Original {word}", url=msg.jump_url))
        msg2 = await thread.send(embed=embed, view=view)

        view = View()
        view.add_item(Button(label="Go to Thread", url=msg2.jump_url))
        await msg.edit(view=view)
        await message.delete()

    async def daily_question(self) -> None:
        """This function generates a daily question from a website, and sends it to all guilds
        as long as they have the feature enabled.
        """
        async with self.bot.session.get(url=URL) as r:
            content = await r.text()
            soup = BeautifulSoup(content, "html.parser")
            html = soup.find("div", attrs={"id": "random"})
            date = utcnow()
            embed = Embed(
                title="Daily Question",
                description=f"> {html.text}",
                color=Color.purple(),
                timestamp=date,
            )
            embed.set_image(url=WHITE_BAR)
            channel: TextChannel = self.bot.get_channel(860590339327918100)
            if guild := channel.guild:
                embed.set_footer(text=guild.name, icon_url=guild.icon.url)
            message = await channel.send(embed=embed, delete_after=3600 * 24)
            thread = await message.create_thread(name=date.strftime("%d-%m-%Y"))
            view = View()
            view.add_item(Button(label="Back to Information", url=message.jump_url))
            data = await thread.send(view=view, embed=embed)
            view = View()
            view.add_item(Button(label="Join the Discussion", url=data.jump_url))
            await message.edit(view=view)

    async def member_count(self):
        """Function which updates the member count and the Information's view"""
        webhook = await self.bot.fetch_webhook(860606374488047616)
        guild = webhook.guild
        members = len([m for m in guild.members if not m.bot])
        total = len(guild.members)
        message = await webhook.fetch_message(913555643699458088)
        embed = message.embeds[0]
        data = {
            "Members": members,
            "Bots   ": total - members,
            "Total  ": total,
        }
        text = ""
        for key, value in data.items():
            text += f"\n{key}: {value:03d}"
        embed.description = f"```yaml{text}\n```"
        source = Path("resources/faq.json")
        async with aiopen(source.resolve(), mode="r") as f:
            contents = await f.read()
            raw_data = loads(contents)
            self.view = InformationView(bot=self.bot, raw_data=raw_data)
            await message.edit(embed=embed, view=self.view)

    @slash_command(
        guild_ids=[719343092963999804],
        description="Map related information",
    )
    async def map(
        self,
        ctx: ApplicationContext,
        area: Option(
            str,
            description="Region to check about",
            required=False,
            autocomplete=map_find,
        ),
    ):
        await ctx.defer(ephemeral=True)

        if not area:
            await ctx.send_followup(
                "https://cdn.discordapp.com/attachments/823629617629495386/918221231210246184/5x4zl8.png",
                ephemeral=True,
            )
            return

        embed = self.view.embeds["Map Information"][area].copy()
        embed.colour = ctx.user.colour

        category: CategoryChannel = ctx.guild.get_channel(int(area))
        self.bot.logger.info("%s is reading /Map Information of %s", str(ctx.user), category.name)

        view = AreaSelection(bot=self.bot, cat=category, member=ctx.user)

        embed.set_footer(text=f"There's a total of {view.total:02d} OCs in this area.")

        for info_btn in self.view.buttons.get("Map Information", {}).get(area, []):
            view.add_item(info_btn)

        await ctx.send_followup(embed=embed, view=view, ephemeral=True)

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        await self.member_count()
        if msg := self.join.get(member):
            with suppress(DiscordException):
                await msg.delete()
        guild: Guild = member.guild
        channel: TextChannel = guild.get_channel(719663963297808436)
        roles = member.roles[1:]
        embed = Embed(
            title="Member Left - Roles",
            color=Color.red(),
            timestamp=utcnow(),
        )
        if text := "\n".join(f"> **•** {role.mention}" for role in roles[::-1]):
            embed.description = text
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_footer(text=f"ID: {member.id}", icon_url=guild.icon.url)
        embed.set_image(url=WHITE_BAR)
        if file := await self.bot.get_file(
            member.display_avatar.url,
            filename=str(member.id),
        ):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            await channel.send(file=file, embed=embed)

    @Cog.listener()
    async def on_member_join(self, member: Member):
        await self.member_count()
        guild: Guild = member.guild
        log: TextChannel = self.bot.get_channel(719663963297808436)
        welcome_channel: TextChannel = guild.get_channel(719343092963999807)
        if not welcome_channel:
            return
        embed = Embed(
            title="Member Joined",
            colour=Color.green(),
            description=f"{member.mention} - {member}",
            timestamp=utcnow(),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_footer(text=f"ID: {member.id}")
        asset = member.display_avatar.replace(format="png", size=512)
        if file := await self.bot.get_file(asset.url, filename="image"):
            embed.set_thumbnail(url=f"attachment://{file.filename}")
            embed.add_field(
                name="Account Age",
                value=format_dt(member.created_at, style="R"),
            )
            message = await log.send(embed=embed, file=file)
            image = ImageKit(base="welcome_TW8HUQOuU.png", weight=1920, height=1080)
            image.add_text(
                font="unifont_HcfNyZlJoK.otf",
                text=member.display_name,
                font_size=120,
                color=0xFFFFFF,
                x=180,
                y=480,
            )
            image.add_image(
                image=message.embeds[0].thumbnail.url,
                height=548,
                weight=548,
                x=1308,
                y=65,
            )
            if file := await self.bot.get_file(image.url, filename=str(member.id)):
                embed = Embed(
                    color=Color.blurple(),
                    title="__**`A new user has joined!`**__",
                    timestamp=utcnow(),
                )
                embed.set_footer(text=guild.name, icon_url=guild.icon.url)
                embed.set_image(url=f"attachment://{file.filename}")

                """
                view = View()
                view.add_item(
                    Button(
                        label="Information",
                        url="https://discord.com/channels/719343092963999804/860590339327918100/910274821613576312",
                    )
                )
                view.add_item(
                    Button(
                        label="Self Roles",
                        url="https://discord.com/channels/719343092963999804/719709333369258015/908814324196323381",
                    )
                )
                view.add_item(
                    Button(
                        label="Character Creation",
                        url="https://discord.com/channels/719343092963999804/852180971985043466/903437849154711552",
                    )
                )
                """

                # noinspection StrFormat
                self.join[member] = await welcome_channel.send(
                    content=member.mention,
                    embed=embed,
                    file=file,
                    view=self.view,
                    allowed_mentions=AllowedMentions(users=True),
                )

    @Cog.listener()
    async def on_member_update(self, past: Member, now: Member):
        if past.premium_since == now.premium_since:
            return
        log: TextChannel = self.bot.get_channel(719663963297808436)
        if past.premium_since and not now.premium_since:
            embed = Embed(
                title="Has un-boosted the Server!",
                colour=Color.red(),
                timestamp=utcnow(),
            )
        else:
            embed = Embed(
                title="Has boosted the Server!",
                colour=Color.brand_green(),
                timestamp=utcnow(),
            )
        embed.set_image(url=WHITE_BAR)
        embed.set_thumbnail(url=now.display_avatar.url)
        if guild := now.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)
        await log.send(content=now.mention, embed=embed)

    @Cog.listener()
    async def on_bulk_message_delete(self, messages: list[Message]) -> None:
        """This coroutine triggers upon bulk message deletions. YAML Format to Myst.bin

        Parameters
        ----------
        messages: list[Message]
            Messages that were deleted.
        """
        msg = messages[0]
        ch: TextChannel = msg.channel
        if not (guild := msg.guild):
            return
        if ids := set(item.id for item in messages) - self.bot.msg_cache:
            messages = [message for message in messages if message.id in ids]
            channel: TextChannel = self.bot.get_channel(719663963297808436)
            if post := await self.bot.m_bin.post(
                content=dump([message_line(item) for item in messages]),
                syntax="yaml",
            ):
                embed = Embed(
                    title="Bulk Message Delete",
                    url=post.url,
                    timestamp=utcnow(),
                )
                embed.set_image(url=WHITE_BAR)
                embed.add_field(name="Channel", value=ch.mention)
                embed.add_field(name="Amount", value=f"{len(messages)} messages")
                embed.set_author(name=guild.name, icon_url=guild.icon.url)
                await channel.send(embed=embed)
            self.bot.msg_cache -= ids

    @Cog.listener()
    async def on_message_delete(self, ctx: Message) -> None:
        """Message deleted detection

        Parameters
        ----------
        ctx: Message
            Deleted Message

        Returns
        -------

        """
        if not ctx.guild:
            return
        user: Member = ctx.author
        if self.bot.user.id == user.id:
            return
        if user.id == self.bot.owner_id or user.id in self.bot.owner_ids:
            return

        if ctx.id in self.bot.msg_cache:
            self.bot.msg_cache.remove(ctx.id)
        else:
            channel: TextChannel = self.bot.get_channel(719663963297808436)
            embed = Embed(
                title="Message Deleted",
                description=ctx.content,
                color=Color.blurple(),
                timestamp=utcnow(),
            )
            embeds: list[Embed] = ctx.embeds
            embed.set_image(url=WHITE_BAR)
            if avatar := user.avatar:
                embed.set_author(name=user.display_name, icon_url=avatar.url)
            else:
                embed.set_author(name=user.display_name)
            embed.add_field(name="Channel", value=ctx.channel.mention)
            embed.add_field(name="Embed", value=f"**{len(embeds)}**")
            embed.add_field(name="Attachments", value=f"**{len(ctx.attachments)}**")
            embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)
            files = []
            for item in ctx.attachments:
                with suppress(HTTPException):
                    file = await item.to_file(use_cached=True)
                    files.append(file)

            message = await channel.send(embed=embed, files=files)
            for item in embeds:
                if item.type != "gifv":
                    await message.reply(embed=item)
                else:
                    embed.set_image(url=item.url)
                    await message.reply(embed=embed)

    @Cog.listener()
    async def on_command(self, ctx: Context) -> None:
        """This allows me to check when commands are being used.

        Parameters
        ----------
        ctx: Context
            Context

        Returns
        -------

        """
        if guild := ctx.guild:
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

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError) -> None:
        """Command error handler

        Parameters
        ----------
        ctx: Context
            Context
        error: CommandError
            Error
        """
        error = getattr(error, "original", error)

        if isinstance(error, CommandNotFound):
            return

        if isinstance(
            error,
            (
                CheckFailure,
                UserInputError,
                CommandOnCooldown,
                MaxConcurrencyReached,
                DisabledCommand,
            ),
        ):
            await ctx.send(
                embed=Embed(
                    color=Color.red(),
                    title=f"Error - {ctx.command.qualified_name}",
                    description=str(error),
                )
            )
            return

        if hasattr(ctx.command, "on_error"):
            return

        if cog := ctx.cog:
            # noinspection PyProtectedMember
            if cog._get_overridden_method(cog.cog_command_error):
                return

        if error_cause := error.__cause__:
            await ctx.send(
                embed=Embed(
                    color=Color.red(),
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

    @Cog.listener()
    async def on_ready(self):
        """Loads the program in the scheduler"""
        await self.bot.scheduler.add_schedule(
            self.daily_question,
            trigger=CronTrigger(hour=13, minute=0, second=0),
            id="Daily Question",
        )
        await self.member_count()


def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot

    Returns
    -------

    """
    bot.add_cog(Information(bot))
