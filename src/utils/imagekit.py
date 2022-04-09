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

from abc import ABC, abstractproperty
from base64 import b64encode
from dataclasses import dataclass, field
from typing import Iterable, Optional

from src.utils.matches import (
    DISCORD_MATCH,
    GOOGLE_IMAGE,
    IMAGEKIT_API,
    IMAGEKIT_MATCH,
    POKEMON_IMAGE,
    SEREBII_IMAGE,
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

    for item in (
        DISCORD_MATCH,
        IMAGEKIT_MATCH,
        GOOGLE_IMAGE,
        POKEMON_IMAGE,
        SEREBII_IMAGE,
    ):
        if match := item.match(text):
            return match.group(1)
    return text


class ImageKitTransformation(ABC):
    @abstractproperty
    def tokenize(self) -> str:
        """Tokenize property

        Returns
        -------
        str
            tokenized data
        """


@dataclass(unsafe_hash=True)
class ImageTransformation(ImageKitTransformation):
    image: str
    height: Optional[int] = None
    weight: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None

    def __post_init__(self):
        self.image = image_formatter(self.image)

    @property
    def tokenize(self) -> str:
        items = [f"oi-{self.image}"]
        if self.height and isinstance(self.height, int):
            items.append(f"oh-{self.height}")
        if self.weight and isinstance(self.weight, int):
            items.append(f"ow-{self.height}")
        if isinstance(self.x, int):
            items.append(f"ox-N{abs(self.x)}" if self.x < 0 else f"ox-{self.x}")
        if isinstance(self.y, int):
            items.append(f"oy-N{abs(self.y)}" if self.y < 0 else f"oy-{self.y}")
        return ",".join(items)


@dataclass(unsafe_hash=True)
class TextTransformation(ImageKitTransformation):
    text: str
    font: Optional[str] = None
    font_size: Optional[int] = None
    color: Optional[int] = None
    transparency: Optional[int] = None
    radius: Optional[int] = None
    padding: Iterable[int] = field(default_factory=frozenset)
    alignment: Optional[str] = None
    background: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None

    @property
    def tokenize(self) -> str:
        encoded = b64encode(self.text.encode("utf-8"))
        decoded = encoded.decode("utf-8")

        raw = f"ote-{decoded}"
        if isinstance(self.font, str):
            raw = f"otf-{self.font},{raw}"
        extra = []

        if isinstance(self.radius, int):
            extra.append(f"or-{self.radius}")
        if isinstance(self.font_size, int):
            extra.append(f"ots-{self.font_size}")
        if isinstance(self.color, int):
            color_text = f"{self.color:#08x}"[2:].upper()
            extra.append(f"ofc-{color_text}")
        if isinstance(self.x, int):
            extra.append(f"ox-N{abs(self.x)}" if self.x < 0 else f"ox-{self.x}")
        if isinstance(self.y, int):
            extra.append(f"oy-N{abs(self.y)}" if self.y < 0 else f"oy-{self.y}")
        if isinstance(self.background, int):
            background_text = f"{self.color:#08x}"[2:].upper()
            extra.append(f"otbg-{background_text}")
        if isinstance(self.transparency, int):
            extra.append(f"oa-{self.transparency}")
        if isinstance(self.alignment, str):
            extra.append(f"otia-{self.alignment}")
        if padding_info := "_".join(map(str, self.padding)):
            extra.append(f"otp-{padding_info}")
        if content := ",".join(extra):
            return f"{raw},{content}"
        return raw


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
        self.height = height
        self.weight = weight
        self.elements: list[ImageKitTransformation] = []

    def __str__(self):
        return self.url

    def __repr__(self):
        return f"ImageKit(base={self._base!r}, extra={len(self.elements)})"

    @property
    def url(self) -> str:
        text = self.base_url
        if content := ":".join(x.tokenize for x in self.elements):
            if "?tr=" not in text:
                text += "?tr"
            return f"{text}:{content}"
        return text

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
        if weight := self.weight:
            extra.append(f"w-{weight}")
        if height := self.height:
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
        self.elements.append(
            ImageTransformation(
                image=image,
                height=height,
                weight=weight,
                x=x,
                y=y,
            )
        )

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
        self.elements.append(
            TextTransformation(
                text=text,
                font=font,
                font_size=font_size,
                color=color,
                transparency=transparency,
                radius=radius,
                padding=padding,
                alignment=alignment,
                background=background,
                x=x,
                y=y,
            )
        )
