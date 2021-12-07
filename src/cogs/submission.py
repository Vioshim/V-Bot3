#  Copyright 2021 Vioshim
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from typing import Optional, Type

from discord import Message
from discord.ext.commands import Cog
from jishaku.codeblocks import codeblock_converter
from yaml import safe_load

from src.enums import Abilities, Moves, Species, Types
from src.structures.bot import CustomBot
from src.structures.character import Character, FakemonCharacter, kind_deduce
from src.structures.character.character_creation import doc_convert
from src.structures.movepool import Movepool
from src.structures.species import Fakemon
from src.utils.functions import common_pop_get
from src.utils.matches import G_DOCUMENT


class Submission(Cog):
    def __init__(self, bot: CustomBot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        """This method processes character submissions

        Attributes
        ----------
        message : Message
            Message to process
        """
        if message.channel.id != 852180971985043466:
            return
        if message.author.bot:
            return
        text: str = codeblock_converter(message.content or "").content
        character: Optional[Type[Character]] = None
        if doc_data := G_DOCUMENT.match(text):
            msg_data = await doc_convert(doc_data.group(1))
        elif not (msg_data := safe_load(text)):
            return

        if msg_data:
            data: dict[str, ...] = {k.lower(): v for k, v in msg_data.items()}
            fakemon_mode: bool = "fakemon" in data
            if species_name := common_pop_get(data, "fakemon", "species", "fusion"):
                if species := Species.deduce(species_name, fakemon_mode=fakemon_mode):
                    data["species"] = species

            """
            item = Complex(bot=self.bot, values=data, target=message.channel, member=message.author)
            async with item as db:
                db
            """

            if types := common_pop_get(data, "types", "type"):
                data["types"] = frozenset(Types.deduce(types))

            if abilities := common_pop_get(data, "abilities", "ability"):
                data["abilities"] = frozenset(Abilities.deduce(abilities))

            if moveset := common_pop_get(data, "moveset", "moves"):
                data["moveset"] = frozenset(Moves.deduce(moveset))

            if isinstance(species := data["species"], Fakemon):
                if not (stats := data.pop("stats", {})):
                    # TODO Request Stats to the User
                    pass
                species.set_stats(**stats)

                if movepool := data.pop("movepool", {}):
                    species.movepool.from_dict(**movepool)
                else:
                    species.movepool = Movepool(event=frozenset(moveset))

            if oc := kind_deduce(data.get("species"), **data):

                if isinstance(character, FakemonCharacter):
                    # Ask for stats
                    pass
                if character.can_have_special_abilities:
                    # Ask if desired
                    pass
