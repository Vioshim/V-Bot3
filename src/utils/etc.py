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


from dataclasses import dataclass, field
from datetime import timedelta, timezone
from enum import Enum, IntEnum, StrEnum
from typing import NamedTuple

from discord import PartialEmoji
from discord.ext import commands

from src.structures.weather import Weather

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


REPLY_EMOJI = PartialEmoji(name="IconReply", id=1080654543672594432)
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


class Month(IntEnum):
    January = 1
    February = 2
    March = 3
    April = 4
    May = 5
    June = 6
    July = 7
    August = 8
    September = 9
    October = 10
    November = 11
    December = 12

    @classmethod
    async def convert(cls, ctx: commands.Context, value: str):
        try:
            return cls(int(value)) if value.isdigit() else cls[value.casefold()]
        except (KeyError, ValueError):
            raise commands.BadArgument(f"Invalid month {value!r}.") from None


class RTFMPages(StrEnum):
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


@dataclass(unsafe_hash=True, slots=True)
class MapPair:
    name: str
    category: int
    emoji: str
    short_desc: str = ""
    desc: str = ""
    image: str = ""
    weather: dict[Month, dict[Weather, int]] = field(default_factory=dict, hash=False)


class MapElements(Enum):
    Mysterious_Island = MapPair(
        name="Mysterious Island",
        category=1211907937442865232,
        emoji="\N{DRAGON FACE}",
        desc="A mysterious island with a lot of secrets.",
        weather={
            Month.January: {
                Weather.Clear: 50,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 5,
                Weather.Snow: 30,
                Weather.Blizzard: 10,
                Weather.Diamond_Dust: 40,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 2,
            },
            Month.February: {
                Weather.Clear: 60,
                Weather.Cloudy: 45,
                Weather.Rain: 25,
                Weather.Thunderstorm: 10,
                Weather.Snow: 10,
                Weather.Blizzard: 5,
                Weather.Diamond_Dust: 10,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 5,
            },
            Month.March: {
                Weather.Clear: 20,
                Weather.Cloudy: 30,
                Weather.Rain: 30,
                Weather.Thunderstorm: 5,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 2,
            },
            Month.April: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 60,
                Weather.Thunderstorm: 40,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 2,
            },
            Month.May: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 30,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 5,
            },
            Month.June: {
                Weather.Clear: 50,
                Weather.Cloudy: 10,
                Weather.Rain: 10,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 0,
                Weather.Harsh_Sunlight: 7,
            },
            Month.July: {
                Weather.Clear: 50,
                Weather.Cloudy: 5,
                Weather.Rain: 25,
                Weather.Thunderstorm: 15,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 0,
                Weather.Harsh_Sunlight: 7,
            },
            Month.August: {
                Weather.Clear: 60,
                Weather.Cloudy: 10,
                Weather.Rain: 30,
                Weather.Thunderstorm: 10,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 6,
            },
            Month.September: {
                Weather.Clear: 40,
                Weather.Cloudy: 50,
                Weather.Rain: 20,
                Weather.Thunderstorm: 15,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 3,
            },
            Month.October: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 30,
                Weather.Thunderstorm: 30,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 1,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 1,
            },
            Month.November: {
                Weather.Clear: 40,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 10,
                Weather.Snow: 5,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 5,
            },
            Month.December: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 10,
                Weather.Thunderstorm: 3,
                Weather.Snow: 50,
                Weather.Blizzard: 30,
                Weather.Diamond_Dust: 20,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 0,
            },
        },
    )
    Celesterra_Kingdom = MapPair(
        name="Celesterra Kingdom",
        category=1196879061411176514,
        emoji="\N{GEAR}",
        desc="A steampunk kingdom with a lot of technology.",
        weather={
            Month.January: {
                Weather.Clear: 20,
                Weather.Cloudy: 40,
                Weather.Rain: 10,
                Weather.Thunderstorm: 1,
                Weather.Snow: 20,
                Weather.Blizzard: 10,
                Weather.Diamond_Dust: 60,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 0,
            },
            Month.February: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 20,
                Weather.Thunderstorm: 3,
                Weather.Snow: 5,
                Weather.Blizzard: 3,
                Weather.Diamond_Dust: 20,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 2,
            },
            Month.March: {
                Weather.Clear: 40,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 5,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 10,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 3,
            },
            Month.April: {
                Weather.Clear: 20,
                Weather.Cloudy: 40,
                Weather.Rain: 40,
                Weather.Thunderstorm: 30,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 1,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 2,
            },
            Month.May: {
                Weather.Clear: 50,
                Weather.Cloudy: 10,
                Weather.Rain: 20,
                Weather.Thunderstorm: 40,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 3,
            },
            Month.June: {
                Weather.Clear: 60,
                Weather.Cloudy: 5,
                Weather.Rain: 5,
                Weather.Thunderstorm: 10,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 8,
            },
            Month.July: {
                Weather.Clear: 64,
                Weather.Cloudy: 20,
                Weather.Rain: 10,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 9,
            },
            Month.August: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 10,
                Weather.Thunderstorm: 15,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 5,
                Weather.Harsh_Sunlight: 7,
            },
            Month.September: {
                Weather.Clear: 50,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 10,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 6,
                Weather.Harsh_Sunlight: 5,
            },
            Month.October: {
                Weather.Clear: 20,
                Weather.Cloudy: 40,
                Weather.Rain: 20,
                Weather.Thunderstorm: 5,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 3,
            },
            Month.November: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 20,
                Weather.Thunderstorm: 5,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 2,
            },
            Month.December: {
                Weather.Clear: 30,
                Weather.Cloudy: 40,
                Weather.Rain: 5,
                Weather.Thunderstorm: 1,
                Weather.Snow: 70,
                Weather.Blizzard: 30,
                Weather.Diamond_Dust: 50,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 5,
            },
        },
    )
    Startrail_Kingdom = MapPair(
        name="Startrail Kingdom",
        category=1244398986853482607,
        emoji="\N{SHOOTING STAR}",
        desc="A star-themed kingdom with a lot of ice.",
        weather={
            Month.January: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 1,
                Weather.Thunderstorm: 10,
                Weather.Snow: 50,
                Weather.Blizzard: 30,
                Weather.Diamond_Dust: 50,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 0,
            },
            Month.February: {
                Weather.Clear: 10,
                Weather.Cloudy: 60,
                Weather.Rain: 5,
                Weather.Thunderstorm: 5,
                Weather.Snow: 40,
                Weather.Blizzard: 20,
                Weather.Diamond_Dust: 45,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 0,
            },
            Month.March: {
                Weather.Clear: 10,
                Weather.Cloudy: 40,
                Weather.Rain: 5,
                Weather.Thunderstorm: 1,
                Weather.Snow: 20,
                Weather.Blizzard: 10,
                Weather.Diamond_Dust: 30,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 0,
            },
            Month.April: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 40,
                Weather.Thunderstorm: 45,
                Weather.Snow: 10,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 15,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 1,
            },
            Month.May: {
                Weather.Clear: 30,
                Weather.Cloudy: 10,
                Weather.Rain: 40,
                Weather.Thunderstorm: 20,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 50,
                Weather.Harsh_Sunlight: 5,
            },
            Month.June: {
                Weather.Clear: 70,
                Weather.Cloudy: 15,
                Weather.Rain: 50,
                Weather.Thunderstorm: 30,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 3,
            },
            Month.July: {
                Weather.Clear: 80,
                Weather.Cloudy: 10,
                Weather.Rain: 60,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 4,
            },
            Month.August: {
                Weather.Clear: 50,
                Weather.Cloudy: 10,
                Weather.Rain: 30,
                Weather.Thunderstorm: 14,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 1,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 2,
            },
            Month.September: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 20,
                Weather.Thunderstorm: 15,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 1,
            },
            Month.October: {
                Weather.Clear: 69,
                Weather.Cloudy: 40,
                Weather.Rain: 10,
                Weather.Thunderstorm: 20,
                Weather.Snow: 5,
                Weather.Blizzard: 1,
                Weather.Diamond_Dust: 10,
                Weather.Sandstorm: 0,
                Weather.Fog: 50,
                Weather.Harsh_Sunlight: 5,
            },
            Month.November: {
                Weather.Clear: 20,
                Weather.Cloudy: 60,
                Weather.Rain: 5,
                Weather.Thunderstorm: 20,
                Weather.Snow: 40,
                Weather.Blizzard: 20,
                Weather.Diamond_Dust: 40,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 1,
            },
            Month.December: {
                Weather.Clear: 20,
                Weather.Cloudy: 80,
                Weather.Rain: 5,
                Weather.Thunderstorm: 10,
                Weather.Snow: 80,
                Weather.Blizzard: 40,
                Weather.Diamond_Dust: 60,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 1,
            },
        },
    )
    Wilderness = MapPair(
        name="Wilderness",
        category=1196879061872541823,
        emoji="\N{EVERGREEN TREE}",
        desc="A vast area of land with no civilization.",
        weather={
            Month.January: {
                Weather.Clear: 50,
                Weather.Cloudy: 50,
                Weather.Rain: 10,
                Weather.Thunderstorm: 0,
                Weather.Snow: 40,
                Weather.Blizzard: 20,
                Weather.Diamond_Dust: 60,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 5,
            },
            Month.February: {
                Weather.Clear: 30,
                Weather.Cloudy: 30,
                Weather.Rain: 30,
                Weather.Thunderstorm: 5,
                Weather.Snow: 20,
                Weather.Blizzard: 5,
                Weather.Diamond_Dust: 40,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 1,
            },
            Month.March: {
                Weather.Clear: 50,
                Weather.Cloudy: 40,
                Weather.Rain: 20,
                Weather.Thunderstorm: 30,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 20,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 6,
            },
            Month.April: {
                Weather.Clear: 60,
                Weather.Cloudy: 80,
                Weather.Rain: 30,
                Weather.Thunderstorm: 50,
                Weather.Snow: 0,
                Weather.Blizzard: 1,
                Weather.Diamond_Dust: 10,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 4,
            },
            Month.May: {
                Weather.Clear: 70,
                Weather.Cloudy: 30,
                Weather.Rain: 10,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 2,
            },
            Month.June: {
                Weather.Clear: 50,
                Weather.Cloudy: 20,
                Weather.Rain: 40,
                Weather.Thunderstorm: 5,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 5,
            },
            Month.July: {
                Weather.Clear: 70,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 5,
                Weather.Harsh_Sunlight: 4,
            },
            Month.August: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 10,
                Weather.Thunderstorm: 5,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 1,
                Weather.Harsh_Sunlight: 5,
            },
            Month.September: {
                Weather.Clear: 30,
                Weather.Cloudy: 50,
                Weather.Rain: 25,
                Weather.Thunderstorm: 40,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 4,
            },
            Month.October: {
                Weather.Clear: 30,
                Weather.Cloudy: 70,
                Weather.Rain: 30,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 1,
                Weather.Sandstorm: 0,
                Weather.Fog: 50,
                Weather.Harsh_Sunlight: 2,
            },
            Month.November: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 20,
                Weather.Thunderstorm: 30,
                Weather.Snow: 1,
                Weather.Blizzard: 1,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 1,
            },
            Month.December: {
                Weather.Clear: 10,
                Weather.Cloudy: 30,
                Weather.Rain: 15,
                Weather.Thunderstorm: 10,
                Weather.Snow: 69,
                Weather.Blizzard: 40,
                Weather.Diamond_Dust: 80,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 0,
            },
        },
    )
    Wilderness_2 = MapPair(
        name="Wilderness",
        category=1263893136623796314,
        emoji="\N{EVERGREEN TREE}",
        desc="A vast area of land with no civilization.",
        weather={
            Month.January: {
                Weather.Clear: 50,
                Weather.Cloudy: 50,
                Weather.Rain: 10,
                Weather.Thunderstorm: 0,
                Weather.Snow: 40,
                Weather.Blizzard: 20,
                Weather.Diamond_Dust: 60,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 5,
            },
            Month.February: {
                Weather.Clear: 30,
                Weather.Cloudy: 30,
                Weather.Rain: 30,
                Weather.Thunderstorm: 5,
                Weather.Snow: 20,
                Weather.Blizzard: 5,
                Weather.Diamond_Dust: 40,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 1,
            },
            Month.March: {
                Weather.Clear: 50,
                Weather.Cloudy: 40,
                Weather.Rain: 20,
                Weather.Thunderstorm: 30,
                Weather.Snow: 1,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 20,
                Weather.Sandstorm: 0,
                Weather.Fog: 30,
                Weather.Harsh_Sunlight: 6,
            },
            Month.April: {
                Weather.Clear: 60,
                Weather.Cloudy: 80,
                Weather.Rain: 30,
                Weather.Thunderstorm: 50,
                Weather.Snow: 0,
                Weather.Blizzard: 1,
                Weather.Diamond_Dust: 10,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 4,
            },
            Month.May: {
                Weather.Clear: 70,
                Weather.Cloudy: 30,
                Weather.Rain: 10,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 2,
            },
            Month.June: {
                Weather.Clear: 50,
                Weather.Cloudy: 20,
                Weather.Rain: 40,
                Weather.Thunderstorm: 5,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 5,
            },
            Month.July: {
                Weather.Clear: 70,
                Weather.Cloudy: 30,
                Weather.Rain: 20,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 5,
                Weather.Harsh_Sunlight: 4,
            },
            Month.August: {
                Weather.Clear: 40,
                Weather.Cloudy: 20,
                Weather.Rain: 10,
                Weather.Thunderstorm: 5,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 1,
                Weather.Harsh_Sunlight: 5,
            },
            Month.September: {
                Weather.Clear: 30,
                Weather.Cloudy: 50,
                Weather.Rain: 25,
                Weather.Thunderstorm: 40,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 0,
                Weather.Sandstorm: 0,
                Weather.Fog: 10,
                Weather.Harsh_Sunlight: 4,
            },
            Month.October: {
                Weather.Clear: 30,
                Weather.Cloudy: 70,
                Weather.Rain: 30,
                Weather.Thunderstorm: 20,
                Weather.Snow: 0,
                Weather.Blizzard: 0,
                Weather.Diamond_Dust: 1,
                Weather.Sandstorm: 0,
                Weather.Fog: 50,
                Weather.Harsh_Sunlight: 2,
            },
            Month.November: {
                Weather.Clear: 20,
                Weather.Cloudy: 50,
                Weather.Rain: 20,
                Weather.Thunderstorm: 30,
                Weather.Snow: 1,
                Weather.Blizzard: 1,
                Weather.Diamond_Dust: 5,
                Weather.Sandstorm: 0,
                Weather.Fog: 40,
                Weather.Harsh_Sunlight: 1,
            },
            Month.December: {
                Weather.Clear: 10,
                Weather.Cloudy: 30,
                Weather.Rain: 15,
                Weather.Thunderstorm: 10,
                Weather.Snow: 69,
                Weather.Blizzard: 40,
                Weather.Diamond_Dust: 80,
                Weather.Sandstorm: 0,
                Weather.Fog: 20,
                Weather.Harsh_Sunlight: 0,
            },
        },
    )


MAP_ELEMENTS = [x.value for x in MapElements]
MAP_ELEMENTS2 = {x.category: x for x in MAP_ELEMENTS}
