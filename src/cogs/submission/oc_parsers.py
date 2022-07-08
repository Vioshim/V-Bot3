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

from abc import ABCMeta, abstractmethod
from asyncio import gather
from enum import Enum
from typing import Any, Optional

from discord import Message
from docx import Document
from docx.document import Document as DocumentType
from jishaku.codeblocks import codeblock_converter
from yaml import safe_load

from src.structures.bot import CustomBot
from src.structures.character import doc_convert
from src.utils.doc_reader import DOCX_FORMAT, docs_aioreader
from src.utils.functions import yaml_handler
from src.utils.matches import G_DOCUMENT, REGEX_URL

__all__ = ("OCParser", "ParserMethods")


class OCParser(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    async def parse(cls, text: str | Message, bot: Optional[CustomBot] = None) -> Optional[dict[str, Any]]:
        """Parser method if possible

        Parameters
        ----------
        text : str | Message
            str or Message with information
        bot : Optional[CustomBot]
            Client instance, defaults to None

        Returns
        -------
        Optional[dict[str, Any]]
            Character information
        """


class GoogleDocsOCParser(OCParser):
    @classmethod
    async def parse(cls, text: str | Message, bot: Optional[CustomBot] = None) -> Optional[dict[str, Any]]:
        if isinstance(text, Message):
            content = text.content
        else:
            content = text
        content: str = codeblock_converter(content or "").content
        if doc_data := G_DOCUMENT.match(content):
            doc = await docs_aioreader(url := doc_data.group(1), bot.aiogoogle)
            msg_data = doc_convert(doc)
            msg_data["url"] = url
            return msg_data


class WordOCParser(OCParser):
    @classmethod
    async def parse(cls, text: str | Message, bot: Optional[CustomBot] = None) -> Optional[dict[str, Any]]:
        if isinstance(text, Message) and (
            attachments := [x for x in text.attachments if x.content_type == DOCX_FORMAT]
        ):
            file = await attachments[0].to_file(use_cached=True)
            doc: DocumentType = Document(file.fp)
            if doc.tables:
                return doc_convert(doc)
            text = yaml_handler("\n".join(element for p in doc.paragraphs if (element := p.text.strip())))
            return safe_load(text)


class DiscordOCParser(OCParser):
    @classmethod
    async def parse(cls, text: str | Message, bot: Optional[CustomBot] = None) -> Optional[dict[str, Any]]:
        if isinstance(text, Message):
            content = text.content
        else:
            content = text
        content = codeblock_converter(content or "").content
        if REGEX_URL.match(content) or G_DOCUMENT.match(content):
            return
        content = yaml_handler(content)
        if isinstance(msg_data := safe_load(content), dict):
            if isinstance(text, Message) and (
                images := [x for x in text.attachments if x.content_type.startswith("image/")]
            ):
                msg_data["image"] = await images[0].to_file(use_cached=True)

            return msg_data


class ParserMethods(Enum):
    WORD = WordOCParser
    GOOGLEDOCS = GoogleDocsOCParser
    DISCORD = DiscordOCParser

    def __call__(self, text: str | Message, bot: Optional[CustomBot] = None):
        item: OCParser = self.value
        return item.parse(text=text, bot=bot)

    @classmethod
    async def parse(cls, text: str | Message, bot: Optional[CustomBot] = None):
        for x in await gather(*[item(text=text, bot=bot) for item in cls]):
            if x and isinstance(x, dict):
                yield x
