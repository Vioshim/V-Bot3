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

from dataclasses import InitVar, dataclass, field
from datetime import datetime
from functools import reduce
from itertools import groupby
from operator import itemgetter
from re import DOTALL, IGNORECASE, MULTILINE, Pattern, compile, escape
from typing import Optional

from discord import Embed, Message
from discord.utils import snowflake_time
from frozendict import frozendict

CLYDE = compile(r"Clyde", IGNORECASE)
CLYDE.sub("Clxyde", "This is Clyde")
ID_DICEBEAR = compile(r"https://avatars\.dicebear\.com/api/identicon/(.+)\.png")


@dataclass(unsafe_hash=True, repr=False)
class TupperForm:
    id: int
    name: str
    image: str
    tupper_id: int
    description: Optional[str] = None
    username: Optional[str] = None

    @classmethod
    def from_message(cls, msg: Message):
        embed = msg.embeds[0]
        return TupperForm(
            id=msg.id,
            tupper_id=msg.channel.id,
            name=embed.title,
            description=embed.description or None,
            username=embed.footer.text or None,
            image=embed.image.url,
        )

    @property
    def created_at(self):
        return snowflake_time(self.id)

    @property
    def embed(self):
        embed = Embed(
            title=self.name,
            color=0xFFFFFE,
        )
        if self.description:
            embed.description = self.description
        embed.set_image(url=self.image)
        if self.username:
            embed.set_footer(text=self.username)
        return embed


@dataclass(unsafe_hash=True, repr=False)
class Tupper:
    name: str
    author: int
    regex_str: InitVar[str]
    form: str = "Default"
    id: Optional[int] = None
    value_regex: Optional[Pattern] = None
    display_prefix: Optional[str] = None
    character: Optional[int] = None
    birthday: Optional[datetime] = None
    forms: frozendict[str, TupperForm] = field(default_factory=frozendict)

    def __post_init__(self, regex_str: str):
        self.display_prefix = regex_str
        self.regex = regex_str

    def __call__(self, text: str):
        return self.value_regex.search(text)

    @property
    def safe_name(self):
        return CLYDE.sub("C\N{KHMER VOWEL INHERENT AA}lyde", self.name)

    @property
    def regex(self) -> str:
        return self.value_regex.pattern

    @regex.setter
    def regex(self, regex_str: str):
        data = escape(regex_str.strip()).replace("text", "(.*)")
        self.value_regex = compile(rf"^{data}$", DOTALL | MULTILINE)

    @classmethod
    def from_message(cls, msg: Message):
        embed = msg.embeds[0]
        fields = {x.name: x.value for x in embed.fields}
        if isinstance(character := fields.get("Character"), str):
            character = int(character)
        else:
            character = None

        return Tupper(
            id=msg.id,
            name=embed.author.name,
            author=int(ID_DICEBEAR.match(embed.author.icon_url).group(1)),
            regex_str=fields["Regex"],
            form=embed.footer.text,
            character=character,
            birthday=embed.timestamp or None,
        )

    def __repr__(self):
        return f"Proxy(name={self.name!r}, regex=`{escape(self.regex)}`)"

    @property
    def created_at(self):
        return snowflake_time(self.id)


def evaluate(message: Message, *proxies: Tupper) -> list[tuple[Tupper, str]]:
    current = None
    values: list[tuple[Tupper, str]] = []
    proxy_msgs: list[tuple[Tupper, str]] = []
    for paragraph in message.content.split("\n"):
        if findings := [
            (item, search.group(1).strip())
            for item in proxies
            if (search := item(paragraph))
        ]:
            values.append(findings[0])
            proxy, _ = findings[0]
            current = proxy
        elif current:
            item = current, paragraph
            values.append(item)
        else:
            break
    else:
        for key, paragraphs in groupby(
            values, itemgetter(0)
        ):  # type: Tupper, list[str]
            data = map(lambda z: z[1], paragraphs)
            entry = key, reduce(lambda x, y: f"{x}\n{y}", data)
            proxy_msgs.append(entry)
        if not proxy_msgs:
            if findings := [
                (item, search.group(1).strip())
                for item in proxies
                if (search := item(message.content))
            ]:
                proxy_msgs.append(findings[0])
        elif len(proxy_msgs) == 1:
            proxy, text = proxy_msgs[0]
            if proxy is None and (
                findings := [
                    (item, search.group(1).strip())
                    for item in proxies
                    if (search := item(text))
                ]
            ):
                return findings
    return proxy_msgs
