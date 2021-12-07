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

from dataclasses import dataclass

from asyncpg import Connection

from src.structures.character.character import Character
from src.structures.species import Legendary

__all__ = ("LegendaryCharacter",)


@dataclass(unsafe_hash=True, slots=True)
class LegendaryCharacter(Character):
    def __post_init__(self):
        super(LegendaryCharacter, self).__post_init__()
        self.sp_ability = None
        self.abilities = self.species.abilities

    @property
    def species(self) -> Legendary:
        return self.species

    async def upsert(self, connection: Connection):
        """Upsert method for LegendaryCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await self.standard_upsert(connection, kind="LEGENDARY")
        await connection.execute(
            "INSERT INTO POKEMON_CHARACTER(ID, SPECIES) "
            "VALUES ($1, $2) ON CONFLICT (ID) DO UPDATE SET SPECIES = $2;",
            self.id,
            self.species.id,
        )
