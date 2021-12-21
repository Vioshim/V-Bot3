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

from typing import Callable, Optional, TypeVar, Union

from discord import Embed, Interaction, Member, Message, TextChannel, User
from discord.ext.commands import Context

_T = TypeVar("_T")


def fix(text: str) -> str:
    """This function removes special characters, and capitalizes an string

    Parameters
    ----------
    text : str
        string to be formatted

    Returns
    -------
    str
        formatted string
    """
    return "".join(e for e in str(text).upper().strip() if e.isalnum())


def common_get(item: dict[str, _T], *args: str) -> Optional[_T]:
    """Dict whose values to obtain from

    Attributes
    ----------
    item : dict[str, _T]
        Dict to obtain data from
    *args : str
        Parameters to possibly obtain data from

    Returns
    -------
    Optional[_T]
        The possibly removed data
    """
    for arg in args:
        if data := item.get(arg):
            return data


def multiple_pop(item: dict[str, _T], *args: str) -> dict[str, _T]:
    """Returns a dict removing all values

    Attributes
    ----------
    item : dict[str, _T]
        Dict to remove and obtain data from
    *args : str
        Parameters to possibly obtain data from

    Returns
    -------
    dict[str, _T]
        The possibly removed data
    """

    return {x: elem for x in args if (elem := item.pop(x, None))}


def common_pop_get(item: dict[str, _T], *args: str) -> Optional[_T]:
    """Dict whose values to remove from

    Attributes
    ----------
    item : dict[str, _T]
        Dict to remove and obtain data from
    *args : str
        Parameters to possibly obtain data from

    Returns
    -------
    Optional[_T]
        The possibly removed data
    """
    data: Optional[_T] = None
    for arg in args:
        item = item.pop(arg, None)
        data = data or item
    return data


def int_check(data: str, a: int, b: int) -> Optional[int]:
    """This is a method that checks the integer out of a string given a range

    Parameters
    ----------
    data : str
        string to scan
    a : int
        min range value (inclusive)
    b : int
        max range value (inclusive)

    Returns
    -------
    Optional[int]
        Determined value
    """
    if val := "".join(char for char in str(data) if char.isdigit()):
        if a <= (value := int(val)) <= b:
            return value


def stats_check(*args: str) -> int:
    """Stat checker function
    as replacement of
    sum(bool(i.strip()) for i in text[index + 1:][:5])

    Parameters
    ----------
    args : str
        Values for parsing

    Returns
    -------
    int
        The desired value
    """
    if data := int_check("".join(item for item in args), 1, 5):
        return data
    return sum([bool(item.strip()) for item in args])


def check_valid(ctx: Context) -> Callable[[Message], bool]:
    """Function for validation of the message to be awaited.

    Args:
        ctx (Union[SlashContext, commands.Context]): Current Context

    Returns:
        Callable[[Message], bool]: function to be used by the checker
    """

    def check(m: Message) -> bool:
        """Check wrapper

        Parameters
        ----------
        m : Message
            Message to be checked

        Returns
        -------
        bool
            Resulting boolean
        """
        return ctx.channel.id == m.channel.id and ctx.author.id == m.author.id

    return check


def text_check(ctx: Interaction):
    """Text checker

    Parameters
    ----------
    ctx: Interaction
        Current Slash Command context
    """

    def inner(message: Message) -> bool:
        """Wrapper method

        Parameters
        ----------
        message: Message
            Message to scan
        """
        if ctx.user == message.author and ctx.channel == message.channel:
            return bool(message.content)
        return False

    return inner


def image_check(ctx: Interaction):
    """Image checker

    Parameters
    ----------
    ctx: Interaction
        Current Slash Command context
    """

    def inner(message: Message) -> bool:
        """Wrapper method

        Parameters
        ----------
        message: Message
            Message to scan
        """
        if ctx.user == message.author and ctx.channel == message.channel:
            return bool(message.attachments or message.content)
        return False

    return inner


def image_check2(user: Union[Member, User], channel: TextChannel):
    """Image checker

    Parameters
    ----------
    user: Union[Member, User]
        User that interacts
    channel: TextChannel
        target channel
    """

    def inner(message: Message) -> bool:
        """Wrapper method

        Parameters
        ----------
        message: Message
            Message to scan
        """
        if user == message.author and channel == message.channel:
            return bool(message.attachments or message.content)
        return False

    return inner


def message_line(message: Message):
    """Message for formatting purposes

    Parameters
    ----------
    message: Message
        Current Message

    Returns
    -------
    dict[str, Any]
        Dict of string parsed properties out of a message
    """
    channel = message.channel
    user = message.author
    return dict(
        channel=f"{channel.name} - {channel.mention}",
        user=f"{user.display_name} - {user.mention}",
        created_at=message.created_at,
        files=[
            dict(
                url=item.url,
                proxy_url=item.proxy_url,
                filename=item.filename,
                type=item.content_type,
                spoiler=item.is_spoiler(),
            )
            for item in message.attachments
        ],
        embeds=[item.to_dict() for item in message.embeds],
        content=message.content,
    )


def embed_handler(message: Message, embed: Embed) -> Embed:
    for item in message.attachments:
        if image := embed.image:
            if item.url == image.url:
                embed.set_image(url=f"attachment://{item.filename}")
        if thumbnail := embed.thumbnail:
            if item.url == thumbnail.url:
                embed.set_thumbnail(url=f"attachment://{item.filename}")
        if author := embed.author:
            if item.url == author.icon_url:
                embed.set_author(
                    name=author.name,
                    icon_url=f"attachment://{item.filename}",
                    url=author.url,
                )
        if footer := embed.footer:
            if item.url == footer.icon_url:
                embed.set_footer(
                    text=footer.text,
                    icon_url=f"attachment://{item.filename}",
                )

    return embed
