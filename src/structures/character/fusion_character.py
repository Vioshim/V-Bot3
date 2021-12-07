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
from random import choice

from asyncpg import Connection
from discord import Embed

from src.structures.character.character import Character
from src.structures.species import Fusion


@dataclass(unsafe_hash=True, slots=True)
class FusionCharacter(Character):
    def __post_init__(self):
        super(FusionCharacter, self).__post_init__()
        self.sp_ability = None
        if len(self.abilities) != 1:
            items = list(self.species.abilities)
            self.abilities = frozenset({choice(items)})

    @property
    def embed(self) -> Embed:
        c_embed = super(FusionCharacter, self).embed
        name1, name2 = self.species.name.split("/")
        c_embed.set_field_at(
            index=2, name="Fusion Species", value=f"> **•** {name1}\n> **•** {name2}".title()
        )
        return c_embed

    @property
    def species(self) -> Fusion:
        return self.species

    async def upsert(self, connection: Connection):
        """Upsert method for MegaCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await self.standard_upsert(connection, kind="FUSION")
        mon1, mon2 = self.species.id.split("_")  # type: str, str
        await connection.execute(
            "INSERT INTO FUSION_CHARACTER(ID, species1, species2) "
            "VALUES ($1, $2, $3) ON CONFLICT (ID) DO UPDATE SET "
            "SPECIES1 = $2, SPECIES2 = $3;",
            self.id,
            mon1,
            mon2,
        )
