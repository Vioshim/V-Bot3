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
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from typing import Any, Iterable, Optional

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


def item_parse(key: str, item: int | str | Enum):
    if isinstance(item, DefaultFonts):
        name = item.name.replace("_", "%20")
    elif isinstance(item, Enum):
        name = item.name if isinstance(item.value, int) else item.value
    else:
        name = item
    return f"{key}-{name}"


class ImageKitTransformation(ABC):
    @abstractproperty
    def tokenize(self) -> str:
        """Tokenize property

        Returns
        -------
        str
            tokenized data
        """

    def token_parse(self, elements: dict[str, Any]):
        return ",".join(
            item_parse(k, v)
            for k, v in elements.items()
            if isinstance(v, (int, str, Enum))
        )


class ImageMethod(ABC):
    @abstractproperty
    def tokenize(self) -> str:
        """Tokenize property

        Returns
        -------
        str
            tokenized data
        """

    def token_parse(self, elements: dict[str, Any]):

        return ",".join(
            item_parse(k, v)
            for k, v in elements.items()
            if isinstance(v, (int, str, Enum))
        )


class Focus(IntEnum):  # fo-foo
    left = auto()
    right = auto()
    top = auto()
    bottom = auto()
    top_left = auto()
    top_right = auto()
    bottom_left = auto()
    bottom_right = auto()
    auto_ = auto()
    face = auto()
    custom = auto()


class CropStrategy(IntEnum):  # cm-foo
    extract = auto()
    pad_resize = auto()


class DefaultFonts(IntEnum):  # otf-foo
    AbrilFatFace = auto()
    Amarnath = auto()
    Arvo = auto()
    Audiowide = auto()
    Chivo = auto()
    Crimson_Text = auto()
    exo = auto()
    Fredoka_One = auto()
    Gravitas_One = auto()
    Kanit = auto()
    Lato = auto()
    Lobster = auto()
    Lora = auto()
    Monoton = auto()
    Montserrat = auto()
    PT_Mono = auto()
    Open_Sans = auto()
    Roboto = auto()
    Old_Standard = auto()
    Ubuntu = auto()
    Vollkorn = auto()

    @property
    def supports_bold_or_italics(self):
        match self:
            case (
                self.AbrilFatFace
                | self.Audiowide
                | self.Fredoka_One
                | self.Gravitas_One
                | self.Lobster
                | self.Monoton
                | self.Montserrat
                | self.PT_Mono
            ):
                return False
            case _:
                return True


class Fonts(Enum):  # otf-foo
    TCM = "TCM______hBLPaUPE87t.TTF"
    unifont = "unifont_HcfNyZlJoK.otf"
    Arial = "ARIALN_b9DmSdG5S.TTF"
    Whitney_Black = "Whitney-BlackSC_HkjaO2ePAg.ttf"


class Typography(Enum):  # ott-foo
    bold = "b"
    italics = "i"


@dataclass(unsafe_hash=True)
class ImagePadResizeCropStrategy(ImageMethod):
    # w-{},h-{},cm-pad_resize,bg-{}
    height: Optional[int] = None
    weight: Optional[int] = None
    background: Optional[int] = None
    mode: Optional[Focus] = None

    @property
    def tokenize(self) -> str:
        elements = dict(
            h=self.height, w=self.weight, cm="pad_resize", mode=self.mode
        )
        if self.background:
            elements["bg"] = hex(self.background)[2:].upper()
        return self.token_parse(elements)


@dataclass(unsafe_hash=True)
class ImageTransformation(ImageKitTransformation):
    image: str
    height: Optional[int] = None
    weight: Optional[int] = None
    x: Optional[int] = None
    y: Optional[int] = None
    centered_x: Optional[int] = None
    centered_y: Optional[int] = None
    focus: Optional[Focus] = None
    strat: Optional[CropStrategy] = None
    trimming: bool = True

    def __post_init__(self):
        self.image = image_formatter(self.image)

    @property
    def tokenize(self) -> str:
        elements = dict(
            oi=self.image,
            oh=self.height,
            ow=self.weight,
            xc=self.centered_x,
            yc=self.centered_y,
            oifo=self.focus,
            cm=self.strat,
        )
        if isinstance(self.x, int):
            elements["ox"] = f"N{abs(self.x)}" if self.x < 0 else f"{self.x}"
        if isinstance(self.y, int):
            elements["oy"] = f"N{abs(self.y)}" if self.y < 0 else f"{self.y}"
        if not self.trimming:
            elements["oit"] = "false"
        return self.token_parse(elements)


@dataclass(unsafe_hash=True)
class TextTransformation(ImageKitTransformation):
    text: str
    width: Optional[int] = None
    font: Optional[DefaultFonts | Fonts | str] = None
    font_size: Optional[int] = None
    color: Optional[int] = None
    transparency: Optional[int] = None
    radius: Optional[int] = None
    padding: Optional[int | str] = None
    alignment: Optional[str] = None
    background: Optional[int] = None
    background_transparency: Optional[int] = None
    overlay: Optional[int] = None
    overlay_transparency: Optional[int] = None
    typography: Optional[Typography] = None
    x: Optional[int] = None
    y: Optional[int] = None

    @property
    def tokenize(self) -> str:
        encoded = b64encode(self.text.encode("utf-8"))
        decoded = encoded.decode("utf-8")
        elements = {
            "otf": self.font,
            "otw": self.width,
            "ote": decoded,
            "or": self.radius,
            "ots": self.font_size,
            "oa": self.transparency,
            "otia": self.alignment,
            "ott": self.typography,
            "otp": self.padding,
        }
        if isinstance(self.color, int):
            elements["otc"] = hex(self.color)[2:].upper()
        if isinstance(self.x, int):
            elements["ox"] = f"N{abs(self.x)}" if self.x < 0 else f"{self.x}"
        if isinstance(self.y, int):
            elements["oy"] = f"N{abs(self.y)}" if self.y < 0 else f"{self.y}"
        if isinstance(self.background, int):
            background = hex(self.background)[2:].upper()
            if isinstance(self.background_transparency, int):
                background += f"{self.background_transparency:02d}"
            elements["otbg"] = background
        if isinstance(self.overlay, int):
            overlay = hex(self.overlay)[2:].upper()
            if isinstance(self.overlay_transparency, int):
                overlay += f"{self.overlay_transparency:02d}"
            elements["otc"] = overlay

        return self.token_parse(elements)


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
        height: Optional[int] = None,
        weight: Optional[int] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        centered_x: Optional[int] = None,
        centered_y: Optional[int] = None,
        focus: Optional[Focus] = None,
        strat: Optional[CropStrategy] = None,
        trimming: bool = True,
    ):
        self.elements.append(
            ImageTransformation(
                image=image,
                height=height,
                weight=weight,
                x=x,
                y=y,
                centered_x=centered_x,
                centered_y=centered_y,
                focus=focus,
                strat=strat,
                trimming=trimming,
            )
        )

    def add_text(
        self,
        text: str,
        width: Optional[int] = None,
        font: Optional[DefaultFonts | str] = None,
        font_size: Optional[int] = None,
        color: Optional[int] = None,
        transparency: Optional[int] = None,
        radius: Optional[int] = None,
        padding: Iterable[int] = [],
        alignment: Optional[str] = None,
        background: Optional[int] = None,
        background_transparency: Optional[int] = None,
        overlay: Optional[int] = None,
        overlay_transparency: Optional[int] = None,
        typography: Optional[Typography] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ):
        self.elements.append(
            TextTransformation(
                text=text,
                width=width,
                font=font,
                font_size=font_size,
                color=color,
                transparency=transparency,
                radius=radius,
                padding=padding,
                alignment=alignment,
                background=background,
                background_transparency=background_transparency,
                overlay=overlay,
                overlay_transparency=overlay_transparency,
                typography=typography,
                x=x,
                y=y,
            )
        )
