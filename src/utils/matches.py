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
    r"^> (?P<response>.+)\n"
    r"@(?P<user>.*) \(<@!(?P<user_id>\d+)>\) - \[jump\]\(<https:\/\/discord\.com\/channels\/@me\/(?P<channel>\d+)\/(?P<message>\d+)>\)\n"
    r"(?P<content>.*)$",
    re.DOTALL,
)
BRACKETS_PARSER = re.compile(r"\{\{([^\{\}]+)\}\}")
ESCAPE_SEQ = re.compile(r"\\(.)")
CLYDE = re.compile(r"(c)(lyde)", re.IGNORECASE)
DISCORD = re.compile(r"(d)(iscord)", re.IGNORECASE)
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


EMOJI_REGEX = re.compile(r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>")
PARTIAL_EMOJI_REGEX = re.compile(r":(?P<name>[a-zA-Z0-9_]{2,32}):")
URL_DOMAIN_MATCH = re.compile(r"(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+")
REGEX_URL = re.compile(r"http[s]?://((?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+)")
DISCORD_MSG_URL = re.compile(
    r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/"
    r"(?:[0-9]{15,20}|@me)"
    r"/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?"
)
DISCORD_MSG_URL2 = re.compile(r"(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$")
INVITE = re.compile(r"(?:https?://)?discord(?:app)?\.(?:com/invite|gg)/([a-zA-Z0-9_\-]+)/?", re.IGNORECASE)
EMOJI_MATCHER = re.compile(
    r"^(\s*[^\s\u00A9\u00AE\u203C\u2049\u2122\u2139\u2194"
    r"-\u2199\u21A9-\u21AA\u231A-\u231B\u2328\u23CF\u23E9"
    r"-\u23F3\u23F8-\u23FA\u24C2\u25AA-\u25AB\u25B6\u25C0\u25FB"
    r"-\u25FE\u2600-\u2604\u260E\u2611\u2614-\u2615\u2618\u261D\u2620\u2622"
    r"-\u2623\u2626\u262A\u262E-\u262F\u2638-\u263A\u2648"
    r"-\u2653\u2660\u2663\u2665-\u2666\u2668\u267B\u267F\u2692"
    r"-\u2694\u2696-\u2697\u2699\u269B-\u269C\u26A0-\u26A1\u26AA"
    r"-\u26AB\u26B0-\u26B1\u26BD-\u26BE\u26C4-\u26C5\u26C8\u26CE"
    r"-\u26CF\u26D1\u26D3-\u26D4\u26E9-\u26EA\u26F0-\u26F5\u26F7"
    r"-\u26FA\u26FD\u2702\u2705\u2708"
    r"-\u270D\u270F\u2712\u2714\u2716\u271D\u2721\u2728\u2733"
    r"-\u2734\u2744\u2747\u274C\u274E\u2753-\u2755\u2757\u2763"
    r"-\u2764\u2795-\u2797\u27A1\u27B0\u27BF\u2934-\u2935\u2B05"
    r"-\u2B07\u2B1B-\u2B1C\u2B50\u2B55\u3030\u303D\u3297\u3299\u1F004\u1F0CF\u1F170"
    r"-\u1F171\u1F17E-\u1F17F\u1F18E\u1F191-\u1F19A\u1F201-\u1F202\u1F21A\u1F22F\u1F232"
    r"-\u1F23A\u1F250-\u1F251\u1F300-\u1F321\u1F324-\u1F393\u1F396-\u1F397\u1F399"
    r"-\u1F39B\u1F39E-\u1F3F0\u1F3F3-\u1F3F5\u1F3F7-\u1F4FD\u1F4FF-\u1F53D\u1F549"
    r"-\u1F54E\u1F550-\u1F567\u1F56F-\u1F570\u1F573-\u1F579\u1F587\u1F58A"
    r"-\u1F58D\u1F590\u1F595-\u1F596\u1F5A5\u1F5A8\u1F5B1-\u1F5B2\u1F5BC\u1F5C2"
    r"-\u1F5C4\u1F5D1-\u1F5D3\u1F5DC-\u1F5DE\u1F5E1\u1F5E3\u1F5EF\u1F5F3\u1F5FA"
    r"-\u1F64F\u1F680-\u1F6C5\u1F6CB-\u1F6D0\u1F6E0-\u1F6E5\u1F6E9\u1F6EB"
    r"-\u1F6EC\u1F6F0\u1F6F3\u1F910-\u1F918\u1F980-\u1F984\u1F9C0}]"
    r"|(\s*(:([a-zA-Z0-9_]{2,32}):)\s*)"
    r"|(\s*<(a?):([a-zA-Z0-9_]{2,32}):([0-9]{18,22})>)\s*)+$"
)
