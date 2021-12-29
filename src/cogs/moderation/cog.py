# Copyright 2021 Vioshim
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
from datetime import datetime, timedelta
from re import MULTILINE, compile
from typing import Optional, Union

from discord import (
    AllowedMentions,
    DiscordException,
    Embed,
    Guild,
    Interaction,
    InteractionResponse,
    Member,
    Message,
    Option,
    Role,
    TextChannel,
    User,
)
from discord.ext.commands import (
    Cog,
    bot_has_guild_permissions,
    command,
    group,
    has_guild_permissions,
    has_role,
    slash_command,
)
from discord.ui import Button, View, button
from discord.utils import get, utcnow, format_dt
from jishaku.codeblocks import Codeblock, codeblock_converter

from src.context import ApplicationContext, Context
from src.structures.bot import CustomBot
from src.utils.etc import WHITE_BAR


class Meeting(View):
    def __init__(
        self,
        reporter: Member,
        imposter: Member,
        reason: Optional[str] = None,
    ):
        super(Meeting, self).__init__(timeout=60)
        self.reporter = reporter
        self.imposter = imposter
        self.attack: set[Member] = set()
        self.defend: set[Member] = set()
        self.moderator: Optional[Member] = None
        self.guild = reporter.guild
        self.message: Optional[Message] = None
        embed = Embed(
            title=f"Meeting for {imposter} (Duration 60 segs)",
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
        embed.set_author(
            name=reporter.display_name, icon_url=reporter.display_avatar.url
        )
        embed.set_thumbnail(url=self.imposter.display_avatar.url)
        embed.set_footer(text="Agreed: 0 | Disagreed: 0")
        if reason:
            embed.add_field(name="Provided Reason", value=reason)
        self.embed = embed

    async def interaction_check(self, interaction: Interaction) -> bool:
        resp: InteractionResponse = interaction.response
        if interaction.user == self.reporter:
            await resp.send_message(
                "You are the one reporting.", ephemeral=True
            )
            return False
        elif interaction.user == self.imposter:
            await resp.send_message(
                "You are the one reporting.", ephemeral=True
            )
            return False
        elif interaction.user in self.attack | self.defense:
            await resp.send_message("You already voted.", ephemeral=True)
            return False
        return True

    @button(label="Agreed")
    async def agreement(self, _: Button, interaction: Interaction):
        resp: InteractionResponse = interaction.response
        user: Member = interaction.user
        if interaction.user.guild_permissions.manage_messages:
            self.moderator = interaction.user
            await resp.send_message(
                "Please congrat the users that did this.", ephemeral=True
            )
            await self.process(method=True)
            self.stop()
        else:
            self.attack.add(user)
            self.embed.set_footer(
                text=f"Agreed: {len(self.attack):02d} | Disagreed: {len(self.defend):02d}"
            )
            await interaction.edit_original_message(embed=self.embed)

    @button(label="Disagreed")
    async def disagreement(self, _: Button, interaction: Interaction):
        user: Member = interaction.user
        resp: InteractionResponse = interaction.response
        if interaction.user.guild_permissions.manage_messages:
            self.moderator = interaction.user
            await self.process(method=False)
            await resp.send_message(
                "Please warn the user that did this.", ephemeral=True
            )
            self.stop()
        else:
            self.defend.add(user)
            self.embed.set_footer(
                text=f"Agreed: {len(self.attack):02d} | Disagreed: {len(self.defend):02d}"
            )
            await interaction.edit_original_message(embed=self.embed)

    async def on_timeout(self):
        await self.process()

    async def process(self, method: Optional[bool] = None):
        sus: Member = self.imposter
        hero: Member = self.reporter
        channel = self.guild.get_channel(877376320093425685)
        embed = Embed(
            title=f"Users that Agreed with {sus}'s Votation",
            content="\n".join(i.mention for i in self.attack),
        )
        embed.set_author(
            name=hero.display_name,
            icon_url=hero.display_avatar.url,
        )
        embed.set_thumbnail(
            url=sus.display_avatar.url,
        )
        embed2 = embed.copy()
        embed2.title = f"Users that Disagreed with {sus}'s Votation"
        embed2.description = "\n".join(i.mention for i in self.defend)
        mode = "Moderation" if self.moderator else "Votation"

        if method is False or len(self.attack) < len(self.defend):
            self.embed.title = f"{sus} was not banned! ({mode})"
            if moderator := self.moderator:
                text = f"Ban Prevented. {moderator.mention} intervened"
            else:
                text = "Ban Prevented. No moderator intervened"

        elif method is True or len(self.attack) >= len(self.defend):
            self.embed.title = f"{sus} has been banned successfully! ({mode})"
            if moderator := self.moderator:
                text = f"Ban Done. {moderator.mention} intervened"
            else:
                text = "Ban Done. No moderator intervened"
            await sus.ban(
                reason=f"{sus} banned upon {mode}. Started by {hero}|{hero.id}.",
                delete_message_days=1,
            )

        view = View()
        view.add_item(Button(label="Jump URL", url=self.message.jump_url))
        await channel.send(content=text, embeds=[embed, embed2], view=view)
        self.message.edit(embed=self.embed, view=None)


class Moderation(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.loaded: bool = False

    @slash_command(
        guild_ids=[719343092963999804],
        description="Starts a meeting to report a raider",
    )
    @has_role("Registered")
    async def vote(
        self,
        ctx: ApplicationContext,
        member: Member,
        reason: str = None,
    ):
        interaction: Interaction = ctx.interaction
        resp: InteractionResponse = ctx.response
        moderation: Role = get(ctx.guild.roles, name="Moderation")
        view = Meeting(reporter=ctx.user, imposter=member, reason=reason)
        
        time = format_dt(utcnow() + timedelta(seconds=120), style="R")
        await resp.send_message(
            content=f"{moderation.mention}  -  {time}",
            embed=view.embed,
            allowed_mentions=AllowedMentions(roles=True),
        )
        msg = await interaction.original_message()
        thread = await msg.create_thread(name=f"Discuss {member.id}")
        await thread.add_user(ctx.user)
        view.message = msg
        await msg.edit(view=view)
        await view.wait()

    @slash_command(
        guild_ids=[719343092963999804],
        description="Reports a situation to staff.",
    )
    async def report(
        self,
        ctx: ApplicationContext,
        text: Option(
            str, description="Message to be sent to staff", required=True
        ),
        anonymous: Option(
            bool,
            description="If you want staff to know you reported it.",
            required=False,
        ),
    ):
        await ctx.defer(ephemeral=True)

        embed = Embed(title="New Report", description=text, timestamp=utcnow())

        embed.set_image(url=WHITE_BAR)

        if not anonymous:
            embed.set_author(
                name=ctx.user.display_name, icon_url=ctx.user.display_avatar.url
            )
        else:
            embed.set_author(name="Anonymous Source")

        channel = self.bot.get_channel(877376320093425685)
        if guild := channel.guild:
            embed.set_footer(text=guild.name, icon_url=guild.icon.url)

        await channel.send(embed=embed)

        await ctx.send_followup(
            "Report has been sent successfully!. This is how it looks.",
            embed=embed,
            ephemeral=True,
        )

    @command(name="cooldown", aliases=["sleep"])
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def cooldown(self, ctx: Context, time: int = 21600) -> None:
        """Makes the channel have cool down

        :param ctx: Context
        :param time: Time in seconds, defaults to 21600 seconds (12 hours)
        :return:
        """
        await ctx.channel.edit(slowmode_delay=time)
        await ctx.reply(content=f"Cool down set to {time} seconds")

    @group(name="clean", aliases=["purge"], invoke_without_command=True)
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clean(self, ctx: Context, amount: int = 5) -> None:
        """Cleans a channel's messages by a given amount, 5 as default

        :param ctx: Context
        :param amount: Amount of messages. Defaults to 5
        :return:
        """
        async with ctx.typing():
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=amount)
        await ctx.channel.send(
            f"Deleted {len(deleted)} message(s)", delete_after=3
        )

    @clean.command(name="bot")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clean_bot(self, ctx: Context, amount: int = 5):
        """Cleans a channel's bot messages by a given amount

        :param ctx: Context
        :param amount: Amount to clean. Default 5
        :return:
        """
        async with ctx.typing():
            await ctx.message.delete()
            deleted = await ctx.channel.purge(
                limit=amount, check=lambda m: m.author.bot
            )
        await ctx.channel.send(
            f"Deleted {len(deleted)} message(s)", delete_after=3
        )

    @clean.command(name="user")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clean_user(
        self, ctx: Context, user: Union[Member, User], amount: int = None
    ) -> None:
        """Cleans a channel's user messages by a given amount

        Parameters
        ----------
        ctx: Context
            Context
        user: Union[Member, User]
            Target User
        amount: int, optional
            Amount to clean. Defaults to None

        Returns
        -------

        """
        channel: TextChannel = ctx.channel
        async with ctx.typing():
            await ctx.message.delete()
            deleted = await channel.purge(
                limit=amount, check=lambda m: m.author.id == user.id
            )
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="regex")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clean_regex(
        self,
        ctx: Context,
        regex: codeblock_converter = Codeblock("re", ".*"),
        amount: int = None,
    ) -> None:
        """Cleans a channel's messages that match a regex by a given amount

        :param ctx: Context
        :param regex: Regex code block expression
        :param amount: Amount to delete. Defaults to None
        :return:
        """
        _, content = regex
        comparator = compile(content, MULTILINE)

        def check(message: Message):
            return bool(comparator.search(message.content))

        channel: TextChannel = ctx.channel

        async with ctx.typing():
            await ctx.message.delete()
            deleted = await channel.purge(limit=amount, check=check)
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @clean.command(name="after")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clean_after(
        self, ctx: Context, amount: int = None, *, message: Message = None
    ) -> None:
        """Cleans a channel's user messages after a message.

        :param ctx: Context
        :param amount: Amount. Defaults to 5
        :param message: Message. Defaults to None
        :return:
        """
        message = message or ctx.message
        channel: TextChannel = ctx.channel
        if ref := message.reference:
            if isinstance(ref.resolved, Message):
                message = ref.resolved
        async with ctx.typing():
            await ctx.message.delete()
            deleted = await channel.purge(limit=amount, after=message)
        await channel.send(f"Deleted {len(deleted)} message(s)", delete_after=3)

    @command(name="kick")
    @has_guild_permissions(kick_members=True)
    @bot_has_guild_permissions(kick_members=True)
    async def kick(
        self, ctx: Context, member: Member, *, reason: str = None
    ) -> None:
        """Kicks a member from the server.

        :param ctx: Context
        :param member: Member
        :param reason: Reason. Defaults to None
        :return:
        """
        if member.top_role >= ctx.author.top_role:
            await ctx.reply(
                "You can't kick someone with same or higher role than yours."
            )
            return
        with suppress(DiscordException):
            await member.send(
                f"Kicked from {ctx.guild} by the reason: {reason}"
            )
        await ctx.reply(f"Kicked from {ctx.guild} by the reason: {reason}")
        await member.kick(
            reason=f"Reason: {reason}| By {ctx.author.display_name}/{ctx.author.id}"
        )

    @command(name="ban")
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def ban(
        self, ctx: Context, user: Union[Member, User], *, reason: str = None
    ) -> None:
        """Bans an user from the guild

        :param ctx: Context
        :param user: User
        :param reason: Reason. Defaults to None
        :return:
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
                    await user.send(
                        content=f"You've been banned from {ctx.guild} by: {reason}"
                    )
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
        await ctx.message.delete()

    @command(name="massban")
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def mass_ban(
        self, ctx: Context, reason: str, *users: Union[User, Member]
    ) -> None:
        """Bans many users from the guild

        :param ctx: Context
        :param reason: Reason
        :param users: Members/Users
        :return:
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
                            await user.send(
                                content=f"You've been banned from {ctx.guild} by: {reason}"
                            )
                        # noinspection PyTypeChecker
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

        await ctx.message.delete()

    @command(name="unban")
    @bot_has_guild_permissions(ban_members=True)
    @has_guild_permissions(ban_members=True)
    async def unban(
        self, ctx: Context, user: User, *, reason: str = None
    ) -> None:
        """Removes a ban to an a user from the server.

        :param ctx: Context
        :param user: User
        :param reason: Reason
        :return:
        """
        if isinstance(user, User):
            await ctx.guild.unban(
                user=user,
                reason=f"{user.display_name} was unbanned by {ctx.author} ({ctx.author.id}). Reason: {reason}",
            )
            await ctx.send(
                f"Unbanned {user} for the reason: {reason}", delete_after=3
            )
        else:
            await ctx.reply("Unable to retrieve the user.")
        await ctx.message.delete()

    @command(name="warn")
    @bot_has_guild_permissions(manage_roles=True)
    @has_guild_permissions(manage_roles=True)
    async def warn(
        self, ctx: Context, user: Member, *, reason: str = None
    ) -> None:
        """Warn an user, providing warn roles

        :param ctx: Context
        :param user: User
        :param reason: Reason
        :return:
        """
        mod_channel: TextChannel = ctx.guild.get_channel(799091737875447808)
        guild: Guild = mod_channel.guild
        roles: list[Role] = [
            guild.get_role(732328576615055393),
            guild.get_role(732412511118164048),
            guild.get_role(732412547520659528),
        ]
        embed = Embed(
            title=f"Warned by {ctx.author.display_name}",
            description=reason or Embed.Empty,
            color=user.color,
            timestamp=datetime.utcnow(),
        )
        if roles[1] in user.roles:  # 2 -> 3
            embed.add_field(name="Note", value=roles[2].mention)
            await user.add_roles(roles[2], reason=reason)
        elif roles[0] in user.roles:  # 1 -> 2
            embed.add_field(name="Note", value=roles[1].mention)
            await user.add_roles(roles[1], reason=reason)
        elif roles[0] not in user.roles:  # 0 -> 1
            embed.add_field(name="Note", value=roles[0].mention)
            await user.add_roles(roles[0], reason=reason)
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url)
        if isinstance(mod_channel, TextChannel):
            files, embed = await self.bot.embed_raw(embed)
            await mod_channel.send(ctx.author.mention, files=files, embed=embed)

        await ctx.message.delete()


def setup(bot: CustomBot):
    """Default Cog Loader

    :param bot: Bot
    :return:
    """
    bot.add_cog(Moderation(bot))
