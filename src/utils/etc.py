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


from dataclasses import dataclass
from datetime import timedelta, timezone
from enum import Enum
from typing import NamedTuple

from discord import PartialEmoji

__all__ = (
    "WHITE_BAR",
    "DICE_NUMBERS",
    "MAP_ELEMENTS",
    "MAP_ELEMENTS2",
    "STICKER_EMOJI",
    "SETTING_EMOJI",
    "LOADING_EMOJI",
    "THUMBS_UP_EMOJI",
    "THUMBS_DOWN_EMOJI",
    "DEFAULT_TIMEZONE",
    "INVITE_EMOJI",
    "EMOTE_CREATE_EMOJI",
    "EMOTE_REMOVE_EMOJI",
    "EMOTE_UPDATE_EMOJI",
    "PING_EMOJI",
    "LIST_EMOJI",
    "KOFI_EMOJI",
    "RTFMPages",
)


class ArrowEmotes(NamedTuple):
    START = PartialEmoji(name="DoubleArrowLeft", id=1080654556272283739)
    BACK = PartialEmoji(name="ArrowLeft", id=1080654546461786122)
    CLOSE = PartialEmoji(name="Stop", id=1080654549062275142)
    FORWARD = PartialEmoji(name="ArrowRight", id=1080654553927663758)
    END = PartialEmoji(name="DoubleArrowRight", id=1080654551373324338)


REPLY_EMOJI = PartialEmoji(name="IconReply", id=816772114639487057)
EMOTE_CREATE_EMOJI = PartialEmoji(name="emotecreate", id=460538984263581696)
EMOTE_REMOVE_EMOJI = PartialEmoji(name="emoteremove", id=460538983965786123)
EMOTE_UPDATE_EMOJI = PartialEmoji(name="emoteupdate", id=460539246508507157)
PING_EMOJI = PartialEmoji(name="IconInsights", id=751160378800472186)
DEFAULT_TIMEZONE = timezone(name="GMT-5", offset=timedelta(hours=-5))
WHITE_BAR = "https://dummyimage.com/500x5/FFFFFF/000000&text=%20"
STICKER_EMOJI = PartialEmoji(name="MessageSticker", id=753338258963824801)
RICH_PRESENCE_EMOJI = PartialEmoji(name="StatusRichPresence", id=842328614883295232)
MOBILE_EMOJI = PartialEmoji(name="StatusMobileOld", id=716828817796104263)
SETTING_EMOJI = PartialEmoji(name="setting", id=962380600902320148, animated=True)
LOADING_EMOJI = PartialEmoji(name="loading", id=969722876003512320, animated=True)
LINK_EMOJI = PartialEmoji(name="MessageLink", id=778925231506587668)
THUMBS_UP_EMOJI = PartialEmoji(name="thumbs_up", id=995303508419026954)
THUMBS_DOWN_EMOJI = PartialEmoji(name="thumbs_down", id=995303546503311380)
INVITE_EMOJI = PartialEmoji(name="IconInvite", id=778931752835088426)
LIST_EMOJI = PartialEmoji(name="list", id=432986579007569922)
KOFI_EMOJI = PartialEmoji(name="kofi", id=952523061171716097)
CREATE_EMOJI = PartialEmoji(name="channelcreate", id=432986578781077514)
DELETE_EMOJI = PartialEmoji(name="channeldelete", id=432986579674333215)
PRESENCE_EMOJI = PartialEmoji(name="StatusRichPresence", id=842328614883295232)
DICE_NUMBERS = [
    PartialEmoji(name="one", id=952524707129868308),
    PartialEmoji(name="two", id=952524707176001546),
    PartialEmoji(name="three", id=952524707167612928),
    PartialEmoji(name="four", id=952524707129884782),
    PartialEmoji(name="five", id=952524707146637342),
    PartialEmoji(name="six", id=952524707159240754),
]


class RTFMPages(Enum):
    Discord = "https://discordpy.readthedocs.io/en/master/"
    Python = "https://docs.python.org/3"
    Apscheduler = "https://apscheduler.readthedocs.io/en/3.x/"
    BS4 = "https://www.crummy.com/software/BeautifulSoup/bs4/doc/"
    Dateparser = "https://dateparser.readthedocs.io/en/latest/"
    Black = "https://black.readthedocs.io/en/stable/"
    Uvloop = "https://uvloop.readthedocs.io/"
    D20 = "https://d20.readthedocs.io/en/latest/"
    Aiohttp = "https://docs.aiohttp.org/en/stable/"
    Python_Docx = "https://python-docx.readthedocs.io/en/latest/"


@dataclass(unsafe_hash=True)
class MapPair:
    name: str
    category: int
    emoji: str
    short_desc: str = ""
    desc: str = ""
    image: str = ""


MAP_ELEMENTS = [
    MapPair(
        name="Mysterious Island",
        category=1211907937442865232,
        emoji="🐲",
        desc="A mysterious island with a lot of secrets.",
    ),
    MapPair(
        name="Celesterra Kingdom",
        category=1196879061411176514,
        emoji="☀",
        desc="A steampunk kingdom with a lot of technology.",
    ),
    MapPair(
        name="Startrail Kingdom",
        category=1244398986853482607,
        emoji="\N{SHOOTING STAR}",
        desc="A star-themed kingdom with a lot of ice.",
    ),
    MapPair(
        name="Wilderness",
        category=1196879061872541823,
        emoji="\N{EVERGREEN TREE}",
        desc="A vast area of land with no civilization.",
    ),
]
MAP_ELEMENTS2 = {x.category: x for x in MAP_ELEMENTS}
