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

from src.structures.character.character import Character
from src.structures.character.character_creation import kind_deduce
from src.structures.character.fakemon_character import FakemonCharacter
from src.structures.character.fusion_character import FusionCharacter
from src.structures.character.legendary_character import LegendaryCharacter
from src.structures.character.mega_character import MegaCharacter
from src.structures.character.mythical_character import MythicalCharacter
from src.structures.character.pokemon_character import PokemonCharacter
from src.structures.character.ultrabeast_character import UltraBeastCharacter

__all__ = (
    "Character",
    "FakemonCharacter",
    "FusionCharacter",
    "kind_deduce",
    "LegendaryCharacter",
    "MegaCharacter",
    "MythicalCharacter",
    "PokemonCharacter",
    "UltraBeastCharacter",
)
