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

__all__ = (
    "RAINBOW",
    "WHITE_BAR",
    "NUMBERS",
    "DICE_NUMBERS",
    "RP_CATEGORIES",
    "MAP_BUTTONS",
)

from discord import OptionChoice, PartialEmoji

RAINBOW = "https://cdn.discordapp.com/attachments/748384705098940426/863415224626184192/image.gif"
WHITE_BAR = (
    "https://cdn.discordapp.com/attachments/748384705098940426/880837466007949362/image.gif"
)
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

MAP_BUTTONS = [
    OptionChoice(
        name="Ashouria",
        value="909239415287738418",
    ),
    OptionChoice(
        name="Athar",
        value="909243882133389342",
    ),
    OptionChoice(
        name="Brevania",
        value="909249684621647942",
    ),
    OptionChoice(
        name="Broxburn",
        value="874015245251797012",
    ),
    OptionChoice(
        name="Chandra Nur",
        value="909250294506983505",
    ),
    OptionChoice(
        name="Estelia",
        value="909250668672466974",
    ),
    OptionChoice(
        name="Lougy",
        value="909264695414910996",
    ),
    OptionChoice(
        name="Muzatoorah",
        value="874017660470431784",
    ),
    OptionChoice(
        name="Norwich",
        value="874017703411720212",
    ),
    OptionChoice(
        name="Osfield",
        value="909264739488649246",
    ),
    OptionChoice(
        name="Parvi",
        value="909264770018988072",
    ),
    OptionChoice(
        name="Pixy Foundation",
        value="909266661515870258",
    ),
    OptionChoice(
        name="Richmod",
        value="909279217995370536",
    ),
    OptionChoice(
        name="Sashi",
        value="909279584732721184",
    ),
    OptionChoice(
        name="Schalzburg",
        value="874017935369310218",
    ),
    OptionChoice(
        name="Shiey Shea",
        value="909280179006877706",
    ),
    OptionChoice(
        name="Shouhead Peaks",
        value="909294313303846932",
    ),
    OptionChoice(
        name="Tomalia",
        value="909294458204487690",
    ),
    OptionChoice(
        name="Upria",
        value="909302744676986890",
    ),
    OptionChoice(
        name="Wilderness",
        value="874018024649265172",
    ),
]
