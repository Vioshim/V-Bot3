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

__all__ = ("RAINBOW", "WHITE_BAR", "NUMBERS", "DICE_NUMBERS")

from discord import PartialEmoji

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
