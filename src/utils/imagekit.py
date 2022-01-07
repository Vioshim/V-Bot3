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

from base64 import b64encode
from typing import Iterable

from src.utils.matches import (
    DISCORD_MATCH,
    GOOGLE_IMAGE,
    IMAGEKIT_API,
    IMAGEKIT_MATCH,
    POKEMON_IMAGE,
)

__all__ = ("ImageKit", "image_formatter")


def image_formatter(text: str) -> str:
    """Image formatter

    Parameters
    ----------
    text : str
        String to be checked

    Returns
    -------
    str:
        Shortcut or full URL
    """

    for item in (DISCORD_MATCH, IMAGEKIT_MATCH, GOOGLE_IMAGE, POKEMON_IMAGE):
        if match := item.match(text):
            return match.group(1)
    return text


class ImageKit:
    def __init__(self, base: str, height: int = None, weight: int = None):
        """Init Method

        Parameters
        ----------
        base : str
            Image Base url
        height : int, optional
            Height, by default None
        weight : int, optional
            Weight, by default None
        """
        self._base = image_formatter(base)
        self._height = height
        self._weight = weight
        self._media: list[str] = []

    def __str__(self):
        return self.url

    def __repr__(self):
        return f"ImageKit(base={self._base}, extra={len(self._media)})"

    @property
    def media(self):
        return self._media

    @media.setter
    def media(self, media: Iterable[str]):
        self._media = []
        for item in media:
            self.add_image(image=item)

    @property
    def url(self) -> str:
        if content := ":".join(self._media):
            if "?tr" in (text := self.base_url):
                return f"{text}:{content}"
            return f"{text}?tr:{content}"
        return self.base_url

    @property
    def base_url(self) -> str:
        """Base URL

        Returns
        -------
        str
            Base URL with height/weight
        """
        base = f"{IMAGEKIT_API}/{self._base}"
        extra: list[str] = []
        if self._weight or self._height:
            if weight := self._weight:
                extra.append(f"w-{weight}")
            if height := self._height:
                extra.append(f"h-{height}")
        if extra_text := ",".join(extra):
            return f"{base}?tr={extra_text}"
        return base

    def add_image(
        self,
        image: str,
        *,
        height: int = None,
        weight: int = None,
        x: int = None,
        y: int = None,
    ):
        entries = [f"oi-{image_formatter(image)}"]
        if isinstance(height, int) and height:
            entries.append(f"oh-{height}")
        if isinstance(weight, int) and weight:
            entries.append(f"ow-{weight}")
        if isinstance(x, int):
            entries.append(f"ox-N{abs(x)}" if x < 0 else f"ox-{x}")
        if isinstance(y, int):
            entries.append(f"oy-N{abs(y)}" if y < 0 else f"oy-{y}")
        self._media.append(",".join(entries))

    # noinspection DuplicatedCode
    def add_text(
        self,
        text: str,
        font: str = None,
        font_size: int = None,
        color: int = None,
        transparency: int = None,
        radius: int = None,
        padding: Iterable[int] = None,
        alignment: str = None,
        background: int = None,
        x: int = None,
        y: int = None,
    ):

        encoded = b64encode(text.encode("utf-8"))
        decoded = encoded.decode("utf-8")

        raw = f"ote-{decoded}"
        if isinstance(font, str):
            raw = f"otf-{font},{raw}"
        extra = []

        if isinstance(radius, int):
            extra.append(f"or-{radius}")
        if isinstance(font_size, int):
            extra.append(f"ots-{font_size}")
        if isinstance(color, int):
            color_text = f"{color:#08x}"[2:].upper()
            extra.append(f"ofc-{color_text}")
        if isinstance(x, int):
            extra.append(f"ox-N{abs(x)}" if x < 0 else f"ox-{x}")
        if isinstance(y, int):
            extra.append(f"oy-N{abs(y)}" if y < 0 else f"oy-{y}")
        if isinstance(background, int):
            background_text = f"{color:#08x}"[2:].upper()
            extra.append(f"otbg-{background_text}")
        if isinstance(transparency, int):
            extra.append(f"oa-{transparency}")
        if isinstance(alignment, str):
            extra.append(f"otia-{alignment}")
        if isinstance(padding, Iterable):
            if padding_info := "_".join(str(item) for item in padding):
                extra.append(f"otp-{padding_info}")
        if content := ",".join(extra):
            self._media.append(f"{raw},{content}")
        else:
            self._media.append(raw)
