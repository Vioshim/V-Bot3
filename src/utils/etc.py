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

__all__ = (
    "RAINBOW",
    "WHITE_BAR",
    "MAP_URL",
    "NUMBERS",
    "DICE_NUMBERS",
    "RP_CATEGORIES",
    "MAP_ELEMENTS",
    "REGISTERED_IMG",
    "RTFM_PAGES",
)
from collections import namedtuple

from discord import PartialEmoji

REGISTERED_IMG = "https://cdn.discordapp.com/attachments/797618220382027839/867427444579106856/registered_1.png"
RAINBOW = "https://cdn.discordapp.com/attachments/748384705098940426/863415224626184192/image.gif"
WHITE_BAR = "https://cdn.discordapp.com/attachments/748384705098940426/880837466007949362/image.gif"
MAP_URL = "https://cdn.discordapp.com/attachments/801227409881694218/935642408434159668/Untitled147_20220125150721.png"

NUMBERS = [
    PartialEmoji(name="one", id=861932320373866497),
    PartialEmoji(name="two", id=861932320420266015),
    PartialEmoji(name="three", id=861932320076464139),
    PartialEmoji(name="four", id=861932320214089728),
    PartialEmoji(name="five", id=861932320055230464),
    PartialEmoji(name="six", id=861932319875137536),
]

DICE_NUMBERS = [
    PartialEmoji(name="one", id=869558773067427870),
    PartialEmoji(name="two", id=869558772761235466),
    PartialEmoji(name="three", id=869558772551544834),
    PartialEmoji(name="four", id=869558773147119646),
    PartialEmoji(name="five", id=869558773205856336),
    PartialEmoji(name="six", id=869558772631228457),
]

RP_CATEGORIES = [
    909239415287738418,
    909243882133389342,
    909249684621647942,
    874015245251797012,
    909250294506983505,
    909250668672466974,
    909264695414910996,
    874017660470431784,
    874017703411720212,
    909264739488649246,
    909264770018988072,
    909266661515870258,
    909279217995370536,
    909279584732721184,
    874017935369310218,
    909280179006877706,
    909294313303846932,
    909294458204487690,
    909302744676986890,
    874018024649265172,
]

RTFM_PAGES: dict[str, str] = {
    "discord": "https://pycord.readthedocs.io/en/master/",
    "python": "https://docs.python.org/3",
    "apscheduler": "https://apscheduler.readthedocs.io/en/3.x/",
    "bs4": "https://www.crummy.com/software/BeautifulSoup/bs4/doc/",
    "dateparser": "https://dateparser.readthedocs.io/en/latest/",
    "asyncpg": "https://magicstack.github.io/asyncpg/current/",
    "black": "https://black.readthedocs.io/en/stable/",
    "uvloop": "https://uvloop.readthedocs.io/",
    "d20": "https://d20.readthedocs.io/en/latest/",
    "aiohttp": "https://docs.aiohttp.org/en/stable/",
}


MapPair = namedtuple("MapPair", "name category message")


MAP_ELEMENTS = [
    MapPair(
        name="Ashouria",
        category=909239415287738418,
        message=937180387099152404,
    ),
    MapPair(
        name="Athar",
        category=909243882133389342,
        message=937180388013535252,
    ),
    MapPair(
        name="Brevania",
        category=909249684621647942,
        message=937180388764315698,
    ),
    MapPair(
        name="Broxburn",
        category=874015245251797012,
        message=937180388911120435,
    ),
    MapPair(
        name="Chandra Nur",
        category=909250294506983505,
        message=937180389817069608,
    ),
    MapPair(
        name="Estelia",
        category=909250668672466974,
        message=937180396079177728,
    ),
    MapPair(
        name="Lougy",
        category=909264695414910996,
        message=937180396611838032,
    ),
    MapPair(
        name="Muzatoorah",
        category=874017660470431784,
        message=937180397064818768,
    ),
    MapPair(
        name="Norwich",
        category=874017703411720212,
        message=937180397484273674,
    ),
    MapPair(
        name="Osfield",
        category=909264739488649246,
        message=937180398016946177,
    ),
    MapPair(
        name="Parvi",
        category=909264770018988072,
        message=937180405298249728,
    ),
    MapPair(
        name="Pixy Foundation",
        category=909266661515870258,
        message=937180405713477642,
    ),
    MapPair(
        name="Richmod",
        category=909279217995370536,
        message=937180406380392508,
    ),
    MapPair(
        name="Sashi",
        category=909279584732721184,
        message=937180406476832780,
    ),
    MapPair(
        name="Schalzburg",
        category=874017935369310218,
        message=937180407550607441,
    ),
    MapPair(
        name="Shiey Shea",
        category=909280179006877706,
        message=937180414034997289,
    ),
    MapPair(
        name="Shouhead Peaks",
        category=909294313303846932,
        message=937180414378917939,
    ),
    MapPair(
        name="Tomalia",
        category=909294458204487690,
        message=937180414940946522,
    ),
    MapPair(
        name="Upria",
        category=909302744676986890,
        message=937180415268122656,
    ),
    MapPair(
        name="Wilderness",
        category=874018024649265172,
        message=937180415582679111,
    ),
]
