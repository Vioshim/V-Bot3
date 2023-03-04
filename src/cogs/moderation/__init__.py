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
from datetime import timedelta
from re import MULTILINE, compile
from typing import Optional

from aiohttp import ClientResponseError
from apscheduler.triggers.cron import CronTrigger
from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Role,
    TextChannel,
    User,
    app_commands,
)
from discord.ext import commands
from discord.ext.commands import Context
from discord.ui import Button, View, button
from discord.utils import format_dt, get, utcnow
from jishaku.codeblocks import Codeblock, codeblock_converter

from src.structures.bot import CustomBot
from src.structures.converters import AfterDateCall
from src.utils.etc import WHITE_BAR

__all__ = ("Moderation", "setup")


API = "https://phish.sinking.yachts/v2"
API_PARAM = {"X-Identity": "V-Bot"}


class Meeting(View):
    def __init__(self, reporter: Member, imposter: Member, reason: Optional[str] = None):
        super(Meeting, self).__init__(timeout=60)
        self.reporter = reporter
        self.imposter = imposter
        self.attack: set[Member] = set()
        self.defend: set[Member] = set()
        self.moderator: Optional[Member] = None
        self.guild = reporter.guild
        self.message: Optional[Message] = None
        embed = Embed(
            title=f"Meeting for {imposter}",
            description=(
                "This is a serious concern, if the user is "
                "raiding or similar proceed to vote, otherwise disagree. "
                "Fake reports will be punished with warning roles, "
                "keep this in mind when voting or doing this command.\n\n"
                "Moderators' votes will always be final, regardless of "
                "the current state of the votation, skipping it."
            ),
            colour=reporter.color,
            timestamp=utcnow(),
        )
        embed.set_author(name=reporter.display_name, icon_url=reporter.display_avatar.url)
        embed.set_thumbnail(url=self.imposter.display_avatar.url)
        embed.set_footer(text="Agreed: 0 | Disagreed: 0")
        if reason:
            embed.add_field(name="Provided Reason", value=reason)
        self.embed = embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        member: Member = interaction.user
        if member == self.reporter:
            await resp.send_message("You are the one reporting.", ephemeral=True)
            return False
        if member == self.imposter:
            await resp.send_message("You are the one reported.", ephemeral=True)
            return False
        if not get(member.roles, name="Registered"):
            await resp.send_message("Only registered members vote.", ephemeral=True)
            return False
        if member in self.attack:
            self.attack.remove(member)
        if interaction.user in self.defend:
            self.defend.remove(member)
        return True

    @button(label="Agreed")
    async def agreement(self, interaction: Interaction, _: Button):
        resp: InteractionResponse = interaction.response
        user: Member = interaction.user
        if interaction.user.guild_permissions.manage_messages:
            self.moderator = interaction.user
            await resp.send_message("Please congrat the users that did this.", ephemeral=True)
            await self.process(method=True)
            self.stop()
        else:
            self.attack.add(user)
            self.embed.set_footer(text=f"Agreed: {len(self.attack):02d} | Disagreed: {len(self.defend):02d}")
            await resp.edit_message(embed=self.embed)

    @button(label="Disagreed")
    async def disagreement(self, interaction: Interaction, _: Button):
        user: Member = interaction.user
        resp: InteractionResponse = interaction.response
        if interaction.user.guild_permissions.manage_messages:
            self.moderator = interaction.user
            await self.process(method=False)
            await resp.send_message("Please warn the user that did this.", ephemeral=True)
            self.stop()
        else:
            self.defend.add(user)
            self.embed.set_footer(text=f"Agreed: {len(self.attack):02d} | Disagreed: {len(self.defend):02d}")
            await resp.edit_message(embed=self.embed)

    async def on_timeout(self):
        await self.process()

    async def process(self, method: Optional[bool] = None):
        sus: Member = self.imposter
        hero: Member = self.reporter
        if not (channel := self.guild.get_channel_or_thread(1077697010490167308)):
            channel = await self.guild.fetch_channel(1077697010490167308)
        embed = Embed(
            title=f"Users that Agreed with {sus}'s Votation",
            description="\n".join(i.mention for i in self.attack),
        )
        embed.set_image(url=WHITE_BAR)
        embed.set_author(name=hero.display_name, icon_url=hero.display_avatar.url)
        embed.set_thumbnail(url=sus.display_avatar.url)
        embed2 = embed.copy()
        embed2.title = f"Users that Disagreed with {sus}'s Votation"
        embed2.description = "\n".join(i.mention for i in self.defend)
        mode = "Moderation" if self.moderator else "Votation"

        if method or len(self.attack) > len(self.defend):
            self.embed.title = f"{sus} has been banned successfully! ({mode})"
            if moderator := self.moderator:
                text = f"Ban Done. {moderator.mention} intervened"
            else:
                text = "Ban Done. No moderator intervened"
            await sus.ban(
                reason=f"{sus} banned upon {mode}. Started by {hero}|{hero.id}.",
                delete_message_days=1,
            )

        else:
            self.embed.title = f"{sus} was not banned! ({mode})"
            if moderator := self.moderator:
                text = f"Ban Prevented. {moderator.mention} intervened"
            else:
                text = "Ban Prevented. No moderator intervened"

        view = View()
        view.add_item(Button(label="Jump URL", url=self.message.jump_url))
        await channel.send(content=text, embeds=[embed, embed2], view=view)
        await self.message.edit(embed=self.embed, view=None)


class Moderation(commands.Cog):
    """This is a standard moderation Cog"""

    def __init__(self, bot: CustomBot):
        """Default init Method

        Parameters
        ----------
        bot : CustomBot
            Bot instance
        """
        self.bot = bot
        self.loaded: bool = False

    async def scam_all(self):
        """Function to load all API data"""
        try:
            async with self.bot.session.get(
                f"{API}/all",
                params=API_PARAM,
            ) as data:
                entries = await data.json()
                self.bot.scam_urls = set(entries)
        except ClientResponseError:
            self.bot.logger.error("Scam API is down.")

    async def scam_changes(self, seconds: str = 300):
        """Function to load API Changes

        Parameters
        ----------
        seconds : str, optional
            Seconds to retrieve, by default 300
        """
        try:
            async with self.bot.session.get(f"{API}/recent/{seconds}", params=API_PARAM) as data:
                items: list[dict[str, str]] = await data.json()
                for item in items:
                    handler = item.get("type")
                    domains: list[str] = set(item.get("domains", []))
                    if handler == "add":
                        self.bot.scam_urls |= domains
                    elif handler == "delete":
                        self.bot.scam_urls -= domains
        except ClientResponseError:
            self.bot.logger.error("Scam API is down.")

    async def scam_load(self):
        if not self.bot.scam_urls:
            await self.scam_all()
        else:
            await self.scam_changes()

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize the scam urls and schedule each 5 minutes"""
        await self.scam_all()
        await self.bot.scheduler.add_schedule(
            self.scam_load,
            id="Nitro Scam List",
            trigger=CronTrigger(minute="0,5,10,15,20,25,30,35,40,45,50,55", second=0),
        )

    @app_commands.command(description="Starts a meeting to report a raider")
    @app_commands.guilds(719343092963999804)
    @app_commands.checks.has_role("Registered")
    async def vote(self, interaction: Interaction, member: Member, reason: Optional[str] = None):
        """Starts a votation to report a member

        Parameters
        ----------
        interaction : Interaction
            Interaction
        member : Member
            Member to report
        reason : Optional[str], optional
            Reason for the votation, by default None
        """
        resp: InteractionResponse = interaction.response
        await resp.defer(ephemeral=False, thinking=True)

        if not isinstance(member, Member):
            member = interaction.guild.get_member(member)

        if not member:
            return await interaction.followup.send(content="Command failed as member was not found", ephemeral=True)
        if member == interaction.user:
            return await interaction.followup.send(
                content="You can't report yourself. Tool isn't a joke", ephemeral=True
            )
        if member.bot:
            return interaction.followup.send(content="That's a bot, if it's here was added by staff.", ephemeral=True)
        moderation: Role = get(interaction.guild.roles, name="Moderation")
        if member.top_role >= interaction.user.top_role:
            return await interaction.followup.send(
                content="Member has a higher or same role than yours.",
                ephemeral=True,
            )

        view = Meeting(reporter=interaction.user, imposter=member, reason=reason)
        time = format_dt(utcnow() + timedelta(seconds=60), style="R")
        msg = await interaction.followup.send(
            content=f"{moderation.mention}  -  {time}",
            embed=view.embed,
            allowed_mentions=AllowedMentions(roles=True),
            wait=True,
        )
        msg.guild = interaction.guild
        thread = await msg.create_thread(name=f"Discuss {member.id}")
        await thread.add_user(interaction.user)
        view.message = msg
        await msg.edit(view=view)
        await view.wait()

    @commands.command(name="cooldown", aliases=["sleep"])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def cooldown(self, ctx: Context, *, time: int = 21600):
        """Makes the channel have cool down

        Parameters
        ----------
        ctx : Context
            Context
        time : int, optional
            Time in seconds. Defaults to 21600 (6 hours)
        """
        await ctx.channel.edit(slowmode_delay=time)
        await ctx.reply(content=f"Cool down set to {time} seconds")

    @commands.group(name="clean", aliases=["purge"], invoke_without_command=True)
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def clean(self, ctx: Context, *, amount: int = 5):
        """Cleans a channel's messages by a given amount, 5 as default

        Parameters
        ----------
        ctx : Context
            Context
        amount : int, optional
            Amount to clean. Defaults to 5
        """
        async with ctx.typing():
            await ctx.message.delete(delay=0)
            deleted = await ctx.channel.purge(limit=amount)
        await ctx.channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="bot")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def clean_bot(self, ctx: Context, amount: int = 5):
        """Cleans a channel's bot messages by a given amount

        Parameters
        ----------
        ctx : Context
            Context
        amount : int, optional
            Amount to clean. Defaults to 5
        """
        async with ctx.typing():
            await ctx.message.delete(delay=0)
            deleted = await ctx.channel.purge(limit=amount, check=lambda m: m.author.bot)
        await ctx.channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="user")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def clean_user(self, ctx: Context, user: Member | User, amount: int = None):
        """Cleans a channel's user messages by a given amount

        Parameters
        ----------
        ctx: Context
            Context
        user: Member | User
            Target User
        amount: int, optional
            Amount to clean. Defaults to None
        """
        channel: TextChannel = ctx.channel
        async with ctx.typing():
            await ctx.message.delete(delay=0)
            deleted = await channel.purge(limit=amount, check=lambda m: m.author.id == user.id)
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="regex")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def clean_regex(
        self,
        ctx: Context,
        regex: codeblock_converter = Codeblock("re", ".*"),
        amount: int = None,
    ):
        """Cleans a channel's messages that match a regex by a given amount

        Parameters
        ----------
        ctx : Context
            Context
        regex : codeblock_converter, optional
            Regex to match, by default Codeblock("re", ".*")
        amount : int, optional
            Amount to clean, by default None
        """
        _, content = regex
        comparator = compile(content, MULTILINE)

        def check(message: Message):
            return bool(comparator.search(message.content))

        channel: TextChannel = ctx.channel

        async with ctx.typing():
            await ctx.message.delete(delay=0)
            deleted = await channel.purge(limit=amount, check=check)
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="after")
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_messages=True)
    async def clean_after(self, ctx: Context, amount: int = 5, *, message: Message = None):
        """Cleans a channel's user messages after a message.

        Parameters
        ----------
        ctx : Context
            Context
        amount : int, optional
            Amount to clean, by default 5
        message : Message, optional
            Message to clean after, by default None
        """
        message = message or ctx.message
        channel: TextChannel = ctx.channel
        if (ref := message.reference) and isinstance(ref.resolved, Message):
            message = ref.resolved
        async with ctx.typing():
            await ctx.message.delete(delay=0)
            deleted = await channel.purge(limit=amount, after=message)
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @commands.command(name="kick")
    @commands.has_guild_permissions(kick_members=True)
    @commands.bot_has_guild_permissions(kick_members=True)
    async def kick(self, ctx: Context, member: Member, *, reason: str = None):
        """Kicks a member from the server.

        Parameters
        ----------
        ctx : Context
            Context
        member : Member
            Member to kick
        reason : str, optional
            Reason, by default None
        """
        if member.top_role >= ctx.author.top_role:
            await ctx.reply("You can't kick someone with same or higher role than yours.")
            return
        with suppress(DiscordException):
            await member.send(f"Kicked from {ctx.guild} by the reason: {reason}")
        await ctx.reply(f"Kicked from {ctx.guild} by the reason: {reason}")
        await member.kick(reason=f"Reason: {reason}| By {ctx.author.display_name}/{ctx.author.id}")

    @commands.command(name="timeout", aliases=["mute"])
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def timeout(self, ctx: Context, user: Member, *, until: Optional[AfterDateCall] = None):
        """timeouts an user

        Parameters
        ----------
        ctx : Context
            Context
        user : Member
            User
        """
        await user.timeout(until)
        await ctx.message.delete(delay=0)

    @commands.command(name="ban")
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def ban(self, ctx: Context, user: Member | User, *, reason: str = None):
        """Bans an user from the guild

        Parameters
        ----------
        ctx : Context
            Context
        user : Member | User
            User to ban from the guild
        reason : str, optional
            Reason for the ban, by default None
        """
        if isinstance(user, Member):
            if user.top_role >= ctx.author.top_role:
                await ctx.reply(
                    f"{user.display_name} has a higher/same role than yours",
                    delete_after=3,
                )
            elif user.top_role >= ctx.me.top_role:
                await ctx.reply(
                    f"{user.display_name} has higher/same role than me",
                    delete_after=3,
                )
            else:
                with suppress(DiscordException):
                    await user.send(content=f"You've been banned from {ctx.guild} by: {reason}")
                await user.ban(
                    reason=f"{user.display_name} banned for: {reason}. By {ctx.author}|{ctx.author.id}.",
                    delete_message_days=0,
                )
        elif isinstance(user, User):
            await ctx.guild.ban(
                user,
                reason=f"{user.display_name} banned for: {reason}. By {ctx.author}|{ctx.author.id}.",
                delete_message_days=0,
            )
        await ctx.message.delete(delay=0)

    @commands.command(name="massban")
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def mass_ban(self, ctx: Context, reason: str, *users: User | Member):
        """Bans many users from the guild

        Parameters
        ----------
        ctx : Context
            Context
        reason : str
            Reason
        """
        async with ctx.typing():
            for user in users:
                if isinstance(user, Member):
                    if user.top_role >= ctx.author.top_role:
                        await ctx.send(
                            f"{user.display_name} has a higher/same role than yours",
                            delete_after=3,
                        )
                    elif user.top_role >= ctx.me.top_role:
                        await ctx.send(
                            f"{user.display_name} has higher/same role than me",
                            delete_after=3,
                        )
                    else:
                        with suppress(DiscordException):
                            await user.send(content=f"You've been banned from {ctx.guild} by: {reason}")
                        await user.ban(
                            reason=f"{user.display_name} banned for: {reason}. By {ctx.author}|{ctx.author.id}.",
                            delete_message_days=0,
                        )
                elif isinstance(user, User):
                    await ctx.guild.ban(
                        user,
                        reason=f"{user.display_name} banned for: {reason}. By {ctx.author}|{ctx.author.id}.",
                        delete_message_days=0,
                    )

        await ctx.message.delete(delay=0)

    @commands.command(name="unban")
    @commands.bot_has_guild_permissions(ban_members=True)
    @commands.has_guild_permissions(ban_members=True)
    async def unban(self, ctx: Context, user: User, *, reason: str = None):
        """Removes a ban to an a user from the server.

        Parameters
        ----------
        ctx : Context
            Context
        user : User
            User
        reason : str, optional
            Reason, by default None
        """
        if isinstance(user, User):
            await ctx.guild.unban(
                user=user,
                reason=f"{user.display_name} was unbanned by {ctx.author} ({ctx.author.id}). Reason: {reason}",
            )
            await ctx.send(f"Unbanned {user} for the reason: {reason}", delete_after=3)
        else:
            await ctx.reply("Unable to retrieve the user.")
        await ctx.message.delete(delay=0)


async def setup(bot: CustomBot):
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(Moderation(bot))
