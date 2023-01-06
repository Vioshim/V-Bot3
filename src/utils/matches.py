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

import re

__all__ = (
    "ESCAPE_SEQ",
    "CLYDE",
    "IMAGEKIT_API",
    "ID_DICEBEAR",
    "DISCORD_MATCH",
    "IMAGEKIT_MATCH",
    "GOOGLE_IMAGE",
    "POKEMON_IMAGE",
    "SEREBII_IMAGE",
    "G_DOCUMENT",
    "EMOJI_REGEX",
    "REGEX_URL",
    "DISCORD_MSG_URL",
    "DISCORD_MSG_URL2",
    "DATA_FINDER",
    "INVITE",
    "VISPRONET_IMAGE",
    "YAML_HANDLER1",
    "YAML_HANDLER2",
    "SCAM_FINDER",
    "URL_DOMAIN_MATCH",
    "TUPPER_REPLY_PATTERN",
    "BRACKETS_PARSER",
)
TUPPER_REPLY_PATTERN = re.compile(
    r"> (.+)\n@.+ \(<@!\d+>\) - \[jump\]\(<https:\/\/discord\.com\/channels\/@me\/(\d+)\/(\d+)>\)\n(.*)",
    re.DOTALL,
)
BRACKETS_PARSER = re.compile(r"\{\{([^\{\}]+)\}\}")
ESCAPE_SEQ = re.compile(r"\\(.)")
CLYDE = re.compile(r"(c)(lyde)", re.IGNORECASE)
ID_DICEBEAR = re.compile(r"https://avatars\.dicebear\.com/api/identicon/(.+)\.png")
SCAM_FINDER = re.compile(r"hb\.bizmrg\.com", re.IGNORECASE)
DATA_FINDER = re.compile(r"(Move|Level|Egg|TM|Tutor|Event|Species|Ability|Type) (\d+)", re.MULTILINE)
YAML_HANDLER1 = re.compile(r":\s*")
YAML_HANDLER2 = re.compile(r"\n\s+")
IMAGEKIT_API = "https://ik.imagekit.io/vioshim"
DISCORD_MATCH = re.compile(r"https://\w+\.discordapp\.\w+/(.*)", re.IGNORECASE)
IMAGEKIT_MATCH = re.compile(f"{IMAGEKIT_API}/(.*)", re.IGNORECASE)
GOOGLE_IMAGE = re.compile(r"https://lh\d\.googleusercontent\.com/(.+)", re.IGNORECASE)
POKEMON_IMAGE = re.compile(
    r"https://projectpokemon\.org/images/sprites-models/homeimg/"
    r"(poke_capture_\d{4}_\d{3}_\w{2}_n_00000000_f_[n|r]\.png)",
    re.IGNORECASE,
)
SEREBII_IMAGE = re.compile(r"https://www\.serebii\.net/(.+)", re.IGNORECASE)
VISPRONET_IMAGE = re.compile(r"https://images\.vispronet\.com/(.+)", re.IGNORECASE)
G_DOCUMENT = re.compile(r"https://docs\.google\.com/document/d/(.+)/", re.IGNORECASE)


EMOJI_REGEX = re.compile(r"(<a?:\s?[\w~]{2,32}:\s?\d{17,19}>|:[\w]{2,32}:)")
URL_DOMAIN_MATCH = re.compile(r"(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+")
REGEX_URL = re.compile(r"http[s]?://((?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+)")
DISCORD_MSG_URL = re.compile(
    r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/"
    r"(?:[0-9]{15,20}|@me)"
    r"/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?"
)
DISCORD_MSG_URL2 = re.compile(r"(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$")
INVITE = re.compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/([a-zA-Z0-9_\-]+)/?", re.IGNORECASE)
