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
from collections import namedtuple
from datetime import timedelta, timezone
from enum import Enum

from discord import PartialEmoji

__all__ = (
    "RAINBOW",
    "WHITE_BAR",
    "MAP_URL",
    "DICE_NUMBERS",
    "RP_CATEGORIES",
    "MAP_ELEMENTS",
    "MAP_ELEMENTS2",
    "STICKER_EMOJI",
    "SETTING_EMOJI",
    "LOADING_EMOJI",
    "REGISTERED_IMG",
    "THUMBS_UP_EMOJI",
    "THUMBS_DOWN_EMOJI",
    "DEFAULT_TIMEZONE",
    "INVITE_EMOJI",
    "LIST_EMOJI",
    "RTFMPages",
)
DEFAULT_TIMEZONE = timezone(name="GMT-5", offset=timedelta(hours=-5))
REGISTERED_IMG = "https://cdn.discordapp.com/attachments/797618220382027839/867427444579106856/registered_1.png"
RAINBOW = "https://cdn.discordapp.com/attachments/748384705098940426/863415224626184192/image.gif"
WHITE_BAR = "https://cdn.discordapp.com/attachments/748384705098940426/1001229327188365423/line.png"
MAP_URL = "https://cdn.discordapp.com/attachments/748384705098940426/980675600664653844/unknown.png"
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
DICE_NUMBERS = [
    PartialEmoji(name="one", id=952524707129868308),
    PartialEmoji(name="two", id=952524707176001546),
    PartialEmoji(name="three", id=952524707167612928),
    PartialEmoji(name="four", id=952524707129884782),
    PartialEmoji(name="five", id=952524707146637342),
    PartialEmoji(name="six", id=952524707159240754),
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


class RTFMPages(Enum):
    Discord = "https://discordpy.readthedocs.io/en/master/"
    Python = "https://docs.python.org/3"
    Apscheduler = "https://apscheduler.readthedocs.io/en/3.x/"
    BS4 = "https://www.crummy.com/software/BeautifulSoup/bs4/doc/"
    Dateparser = "https://dateparser.readthedocs.io/en/latest/"
    Asyncpg = "https://magicstack.github.io/asyncpg/current/"
    Black = "https://black.readthedocs.io/en/stable/"
    Uvloop = "https://uvloop.readthedocs.io/"
    D20 = "https://d20.readthedocs.io/en/latest/"
    Aiohttp = "https://docs.aiohttp.org/en/stable/"
    Python_Docx = "https://python-docx.readthedocs.io/en/latest/"


MapPair = namedtuple(
    "MapPair",
    [
        "name",
        "category",
        "message",
        "role",
        "lat",
        "lon",
        "emoji",
        "short_desc",
        "desc",
        "image",
    ],
)


MAP_ELEMENTS = [
    MapPair(
        name="Ashouria",
        category=909239415287738418,
        message=937180387099152404,
        role=956973695883165776,
        lat=30,
        lon=31,
        emoji="\N{FIRE}",
        short_desc="",
        desc="Ashouria is a wealthy country with a main vacation spot, which is a large city which holds a lot of things to do, it has a Battle Arena as well. It is usually very hot there, luckily it was built near the beach, so feel free to take a swim from time to time! If you guess that the mayor of this city is a fire type, you are right!",
        image="",
    ),
    MapPair(
        name="Athar",
        category=909243882133389342,
        message=937180388013535252,
        role=956973697493790821,
        lat=27,
        lon=153,
        emoji="\N{FIREWORK SPARKLER}",
        short_desc="",
        desc="Welcome to Athar and the city of Bienri where Fairy and Psychic live together. For a long time, Fairies have claimed this large country, that is until a few years later, the Psychic types came and settled in. At first, the fairies were a bit standoffish, until they finally bonded with each other. Come to the present day and they lived in harmony, there's even a large guild called the Faery Guild to fend off attackers. Now, the Fairy Type Battle Arena was made, this arena was made to test if fairy dust isn't the only thing you can resist.",
        image="",
    ),
    MapPair(
        name="Brevania",
        category=909249684621647942,
        message=937180388764315698,
        role=956973699548999740,
        lat=10,
        lon=67,
        emoji="\N{GHOST}",
        short_desc="",
        desc="If you like to visit abandoned places for some spooks? Well, you've come to the right place, Welcome to Pandus, a small city that has abandoned structures dotted around, quite a lot of 'mons still live here. Some of the buildings have a lot of history tied behind it. If you want to learn more about these buildings, you'll have to meet the leader of this city. The Battle arena is actually one of the actual abandoned.",
        image="",
    ),
    MapPair(
        name="Broxburn",
        category=874015245251797012,
        message=937180388911120435,
        role=956973701281243166,
        lat=41,
        lon=2,
        emoji="\N{CAMPING}",
        short_desc="",
        desc="It's pretty much a forest town, there's some citizens here and even some outlaws, but you'll most likely love this place if you want to chill and hang out with people. It's common to see kids play in the grass, despite the great amount of trees which can easily hinder visibility to police officers.",
        image="",
    ),
    MapPair(
        name="Chandra Nur",
        category=909250294506983505,
        message=937180389817069608,
        role=956973702950584401,
        lat=34,
        lon=135,
        emoji="\N{BOXING GLOVE}",
        short_desc="",
        desc="Welcome to Chandra Nur and the city of Axrid, the home ground for fighting types. The weather here is pretty calm, mostly cloudy half the time, and the temperature here is at a stable 60 degrees. Just like Ashouria, Chandra Nur welcomes a lot of outsiders and pokemon from overseas. The fighting types that live here are generally nice since the battle arena was built here, making those who came to spectate or participate in the tournament feel quite at home.",
        image="",
    ),
    MapPair(
        name="Estelia",
        category=909250668672466974,
        message=937180396079177728,
        role=956973705228091402,
        lat=48,
        lon=11,
        emoji="\N{MOVIE CAMERA}",
        short_desc="",
        desc="Welcome to Estelia and the city of Rici! If you are currently coming in from a different region to this place, it'll look like a normal city, but what you don't know is that this place is at least 2 years ahead in technology! This is also the home to quite a lot of steel and electric types. No, there are no flying cars here… at least, not yet of course.",
        image="",
    ),
    MapPair(
        name="Lougy",
        category=909264695414910996,
        message=937180396611838032,
        role=956973707073585172,
        lat=14,
        lon=120,
        emoji="\N{CROSSED FLAGS}",
        short_desc="",
        desc='A very peculiar hospital, which has been designed to deal with all the problems that one could deem "otherworldly", it has all the kind of medics that you may expect from a hospital but also has experts in the different disciplines such as magic, therapies, special abilities and all that.',
        image="",
    ),
    MapPair(
        name="Muzatoorah",
        category=874017660470431784,
        message=937180397064818768,
        role=956973708822577192,
        lat=21,
        lon=39,
        emoji="\N{CACTUS}",
        short_desc="",
        desc="Muzatoorah is your generic desert town, which despite its limitations it's quite great in the commerce aspect, its citizens tend to be very smart and always ready to start business, however they also tend to have distrust on foreigners due to historical reasons. This kingdom has a royal family which keeps making decisions for the benefit of it while also trying to keep in good terms with the rest of the regions.",
        image="",
    ),
    MapPair(
        name="Norwich",
        category=874017703411720212,
        message=937180397484273674,
        role=956973710919757915,
        lat=55,
        lon=4,
        emoji="\N{HOUSE WITH GARDEN}",
        short_desc="",
        desc="Currently one of the most stable places in the whole region, this place is widely known by its rice production, and the fact that most of the citizens tend to be very friendly, which makes it an easy place for travellers to start their journey. It has a very noticeable english design and it also contains one of the main guilds which despite not having a specific name, it's very known by its efforts with monster hunting.",
        image="",
    ),
    MapPair(
        name="Parvi",
        category=909264770018988072,
        message=937180405298249728,
        role=956973715239882802,
        lat=43,
        lon=5,
        emoji="\N{CRYSTAL BALL}",
        short_desc="",
        desc="Welcome to Parvi and the city of Belle where most of the over-seas trading happens and where merchants come to sell their items. This city is popular for trading because of its unique resources and culture. However, not only is it that this city is near water, the Battle Arena is in the water! Hope you've taken some swimming lessons.",
        image="",
    ),
    MapPair(
        name="Pixy Foundation",
        category=909266661515870258,
        message=937180405713477642,
        role=956973718012317707,
        lat=45,
        lon=9,
        emoji="\N{LAB COAT}",
        short_desc="",
        desc="This is the Pixy Foundation, here is where most of their research is conducted. Today, they're letting people take a tour around, but of course, they have their restricted areas, so there's really not a lot to see other than prototype machines and weapons, which are more likely to be recycled.",
        image="",
    ),
    MapPair(
        name="Richmod",
        category=909279217995370536,
        message=937180406380392508,
        role=956973720075915294,
        lat=33,
        lon=70,
        emoji="\N{ANT}",
        short_desc="",
        desc="Richmod holds yet another large port city, always open for overseas trading and merchants piling up all over the city. Recently, the city was struck by a tsunami, luckily everyone was safe, but the markets weren't. Though everything was quickly repaired and now everything is back to normal, since there is a risk for another tsunami, there was a wall that was built, it was big enough to have cargo ships come in without getting damaged when they're docking.",
        image="",
    ),
    MapPair(
        name="Sashi",
        category=909279584732721184,
        message=937180406476832780,
        role=956973722013687808,
        lat=35,
        lon=41,
        emoji="\N{TROPICAL DRINK}",
        short_desc="",
        desc="Say hello to Sashi! This country isn't as hot as Ashouria, but it has its days. Lougy is a medium-sized city that is surrounded by trees but also holds a Battle Arena as well. Though it is on the other side of the river, luckily there's a bridge that leads to the arena.",
        image="",
    ),
    MapPair(
        name="Schalzburg",
        category=874017935369310218,
        message=937180407550607441,
        role=956973725805318215,
        lat=52,
        lon=21,
        emoji="\N{SNOWFLAKE}",
        short_desc="",
        desc="Schalzburg, one of the most reserved areas in the whole continent, It is quite known due to its weather always being snow, which makes it a place quite common for ice types. This area tends to be very independent of the other regions, however recently they have opened their gates as a way to keep their community living, due to it being in a slow decay as time happened.",
        image="",
    ),
    MapPair(
        name="Shiey Shea",
        category=909280179006877706,
        message=937180414034997289,
        role=956973728363864074,
        lat=48,
        lon=11,
        emoji="\N{CLASSICAL BUILDING}",
        short_desc="",
        desc="If you know a thing or two about Astronomy, it would be very useful because Shiey Shea has a large Rainforest along the border. Further past the forest, you'll see the city of Giram. Giram is similar to Lougy, but a bit small. Back then, this city was known for its many battles over history, some of which were civil conflicts. Giram is also quite a hotspot for a lot of thunderstorms, but thankfully they aren't too severe. The Battle Arena was built a few miles south from the city, so it'll take a hefty walk up there.",
        image="",
    ),
    MapPair(
        name="Shouhead Peaks",
        category=909294313303846932,
        message=937180414378917939,
        role=956973730519715911,
        lat=53,
        lon=3,
        emoji="\N{CURLING STONE}",
        short_desc="",
        desc="This is a town that is widely known by its heavy focus on rocks, there's many reasons to visit this place such as its museum, the crystal lake and its mystical forest. As you explore the land, you can get to discover that the guild here stopped operating as they have finally reached a relative state of peace in their territory, this is quite a great town if you want to have a slice of life kind of story without much involvement in the main events.",
        image="",
    ),
    MapPair(
        name="Tomalia",
        category=909294458204487690,
        message=937180414940946522,
        role=956973734009405490,
        lat=23,
        lon=82,
        emoji="\N{DRAGON FACE}",
        short_desc="",
        desc="If you've passed the Fire type battle arena, this is where your resistance to excessive heat comes in handy, there is nothing but desert that stretches for miles. However, there is a city (about the size of present day dubai) that is near the coast. Make it there safely and you'll be given lots of water and somewhere to cool down. Priland is a city where Dragon, Ground, and Fire types live among each other in peace. The Battle Arena is located in the middle of this extremely large city. The city holds a lot of cultural value to the 'mons here though, So there are some very old structures around. The whole town heavily relies on something they consider as Magic.",
        image="",
    ),
    MapPair(
        name="Upria",
        category=909302744676986890,
        message=937180415268122656,
        role=956973735909425222,
        lat=55,
        lon=37,
        emoji="\N{ICE CUBE}",
        short_desc="",
        desc="This is the Kingdom of Upria and the city of Ponta, a large and seemingly medieval like city. However, this country is mainly cold, and if you guessed it, ice types make a living here. Back in the day, the Kingdom of Upria raged war against Ashouria. Though, it quickly came to an end due to Ashouria having the Advantage over Ice. Stories say that Upria had tried to battle Ashouria many times, but ended up failing multiple times. Upria is known for its hardened battle skills and because since it's very cold in Ponta, Battling in the battle arena will be difficult. Moreso, Upria is known for their hate against Ashouria and refuse to be allies with them, so any Ashourian that enters Upria will most likely be robbed or attacked viciously.",
        image="",
    ),
    MapPair(
        name="Wilderness",
        category=874018024649265172,
        message=937180415582679111,
        role=956973738073669632,
        lat=34,
        lon=56,
        emoji="\N{EVERGREEN TREE}",
        short_desc="",
        desc="All the towns are connected by wilderness, curiously Despa is mostly wilderness despite the big cities that have settled here. Dungeons are bound to be more common in this area, and as expected, wild pokemon and outlaws tend to be more frequent in this area.",
        image="",
    ),
]

MAP_ELEMENTS2 = {x.category: x for x in MAP_ELEMENTS}
