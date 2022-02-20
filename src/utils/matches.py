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

from re import IGNORECASE, MULTILINE, compile

__all__ = (
    "IMAGEKIT_API",
    "DISCORD_MATCH",
    "IMAGEKIT_MATCH",
    "GOOGLE_IMAGE",
    "POKEMON_IMAGE",
    "G_DOCUMENT",
    "EMOJI_REGEX",
    "REGEX_URL",
    "DISCORD_MSG_URL",
    "DISCORD_MSG_URL2",
    "DATA_FINDER",
    "INVITE",
    "YAML_HANDLER1",
    "YAML_HANDLER2",
    "SCAM_FINDER",
    "URL_DOMAIN_MATCH",
)
SCAM_FINDER = compile(r"hb\.bizmrg\.com", IGNORECASE)
DATA_FINDER = compile(
    r"(Move|Level|Egg|TM|Tutor|Event|Species|Ability|Type) (\d+)", MULTILINE
)
YAML_HANDLER1 = compile(r":\s*")
YAML_HANDLER2 = compile(r"\n\s+")
IMAGEKIT_API = "https://ik.imagekit.io/vioshim"
DISCORD_MATCH = compile(r"https://\w+\.discordapp\.\w+/(.*)", IGNORECASE)
IMAGEKIT_MATCH = compile(f"{IMAGEKIT_API}/(.*)", IGNORECASE)
GOOGLE_IMAGE = compile(r"https://lh\d\.googleusercontent\.com/(.+)", IGNORECASE)
POKEMON_IMAGE = compile(
    r"https://projectpokemon\.org/images/sprites-models/homeimg/"
    r"(poke_capture_\d{4}_\d{3}_\w{2}_n_00000000_f_[n|r]\.png)",
    IGNORECASE,
)
G_DOCUMENT = compile(r"https://docs\.google\.com/document/d/(.+)/", IGNORECASE)

EMOJI_REGEX = compile(r"(<a?:\s?[\w~]{2,32}:\s?\d{17,19}>|:[\w]{2,32}:)")
URL_DOMAIN_MATCH = compile(
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]"
)
REGEX_URL = compile(
    r"http[s]?://"
    r"(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]| %[0-9a-fA-F][0-9a-fA-F])+"
)
DISCORD_MSG_URL = compile(
    r"https?://(?:(ptb|canary|www)\.)?discord(?:app)?\.com/channels/"
    r"(?:[0-9]{15,20}|@me)"
    r"/(?P<channel_id>[0-9]{15,20})/(?P<message_id>[0-9]{15,20})/?"
)
DISCORD_MSG_URL2 = compile(
    r"(?:(?P<channel_id>[0-9]{15,20})-)?(?P<message_id>[0-9]{15,20})$"
)
INVITE = compile(
    r"(https?://)?(www\.)?(discord\.(gg|io|me|li)|discordapp\.com/invite)/([^\s/]+?(?=\b))",
    IGNORECASE,
)
