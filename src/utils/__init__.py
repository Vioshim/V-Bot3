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

from src.utils.doc_reader import docs_reader
from src.utils.etc import (
    DICE_NUMBERS,
    MAP_BUTTONS,
    NUMBERS,
    RAINBOW,
    RP_CATEGORIES,
    WHITE_BAR,
)
from src.utils.functions import (
    check_valid,
    common_get,
    common_pop_get,
    embed_handler,
    embed_modifier,
    fix,
    image_check,
    int_check,
    message_line,
    multiple_pop,
    stats_check,
    text_check,
)
from src.utils.imagekit import ImageKit, image_formatter
from src.utils.matches import (
    DATA_FINDER,
    DISCORD_MATCH,
    DISCORD_MSG_URL,
    EMOJI_REGEX,
    G_DOCUMENT,
    GOOGLE_IMAGE,
    IMAGEKIT_API,
    IMAGEKIT_MATCH,
    POKEMON_IMAGE,
    REGEX_URL,
)

__all__ = (
    "docs_reader",
    "DICE_NUMBERS",
    "MAP_BUTTONS",
    "NUMBERS",
    "RAINBOW",
    "RP_CATEGORIES",
    "WHITE_BAR",
    "fix",
    "common_get",
    "multiple_pop",
    "common_pop_get",
    "embed_modifier",
    "int_check",
    "stats_check",
    "check_valid",
    "text_check",
    "image_check",
    "message_line",
    "embed_handler",
    "ImageKit",
    "image_formatter",
    "IMAGEKIT_API",
    "DISCORD_MATCH",
    "IMAGEKIT_MATCH",
    "GOOGLE_IMAGE",
    "POKEMON_IMAGE",
    "G_DOCUMENT",
    "EMOJI_REGEX",
    "REGEX_URL",
    "DISCORD_MSG_URL",
    "DATA_FINDER"
)
