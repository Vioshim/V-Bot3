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
from __future__ import annotations

from typing import TYPE_CHECKING

from discord import ApplicationContext as ApplicationContextBase
from discord import AutocompleteContext as AutocompleteContextBase
from discord.ext.commands import Context as ContextBase

if TYPE_CHECKING:
    from src.structures.bot import CustomBot

__all__ = (
    "ApplicationContext",
    "AutocompleteContext",
    "Context",
)


class ApplicationContext(ApplicationContextBase):
    """Represents the context in which a slash command is being invoked under"""

    @property
    def bot(self) -> CustomBot:
        return super(ApplicationContext, self).bot


class AutocompleteContext(AutocompleteContextBase):
    """Represents the context in which autocomplete is being invoked under"""

    @property
    def bot(self) -> CustomBot:
        return super(AutocompleteContext, self).bot


class Context(ContextBase):
    """Represents the context in which a command is being invoked under"""

    @property
    def bot(self) -> CustomBot:
        return super(Context, self).bot
