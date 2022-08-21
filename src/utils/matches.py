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

from re import IGNORECASE, MULTILINE
from re import compile as re_compile

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
)
ESCAPE_SEQ = re_compile(r"\\(.)")
CLYDE = re_compile(r"C(.)lyde", IGNORECASE)
ID_DICEBEAR = re_compile(r"https://avatars\.dicebear\.com/api/identicon/(.+)\.png")
SCAM_FINDER = re_compile(r"hb\.bizmrg\.com", IGNORECASE)
DATA_FINDER = re_compile(r"(Move|Level|Egg|TM|Tutor|Event|Species|Ability|Type) (\d+)", MULTILINE)
YAML_HANDLER1 = re_compile(r":\s*")
YAML_HANDLER2 = re_compile(r"\n\s+")
IMAGEKIT_API = "https://ik.imagekit.io/vioshim"
DISCORD_MATCH = re_compile(r"https://\w+\.discordapp\.\w+/(.*)", IGNORECASE)
IMAGEKIT_MATCH = re_compile(f"{IMAGEKIT_API}/(.*)", IGNORECASE)
GOOGLE_IMAGE = re_compile(r"https://lh\d\.googleusercontent\.com/(.+)", IGNORECASE)
POKEMON_IMAGE = re_compile(
    r"https://projectpokemon\.org/images/sprites-models/homeimg/"
    r"(poke_capture_\d{4}_\d{3}_\w{2}_n_00000000_f_[n|r]\.png)",
    IGNORECASE,
)
SEREBII_IMAGE = re_compile(r"https://www\.serebii\.net/(.+)", IGNORECASE)
VISPRONET_IMAGE = re_compile(r"https://images\.vispronet\.com/(.+)", IGNORECASE)
G_DOCUMENT = re_compile(r"https://docs\.google\.com/document/d/(.+)/", IGNORECASE)


EMOJI_REGEX = re_compile(r"(<a?:\s?[\w~]{2,32}:\s?\d{17,19}>|:[\w]{2,32}:)")
URL_DOMAIN_MATCH = re_compile(r"(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+")
REGEX_URL = re_compile(r"http[s]?://((?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+)")
DISCORD_MSG_URL = re_compile(
    r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/"
    r"(?:[0-9]{15,20}|@me)"
    r"/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?"
)
DISCORD_MSG_URL2 = re_compile(r"(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$")
INVITE = re_compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/([a-zA-Z0-9_\-]+)/?", IGNORECASE)
