# Copyright 2021 Vioshim
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

from dataclasses import dataclass

from asyncpg import Connection
from discord import Embed

from src.structures.character.character import Character
from src.structures.species import Fakemon

__all__ = ("FakemonCharacter",)


@dataclass(unsafe_hash=True, slots=True)
class FakemonCharacter(Character):
    def __post_init__(self):
        super(FakemonCharacter, self).__post_init__()
        if not self.species.can_have_special_abilities:
            self.sp_ability = None

        self.abilities = self.species.abilities

    @property
    def species(self) -> Fakemon:
        return self.species

    @property
    def embed(self) -> Embed:
        c_embed = super(FakemonCharacter, self).embed
        c_embed.set_field_at(index=2, name="Fakemon Species", value=self.species.name)
        c_embed.insert_field_at(index=3, name="HP ", value=("🔳" * self.species.HP).ljust(5, "⬜"))
        c_embed.insert_field_at(index=4, name="ATK", value=("🔳" * self.species.ATK).ljust(5, "⬜"))
        c_embed.insert_field_at(index=5, name="DEF", value=("🔳" * self.species.DEF).ljust(5, "⬜"))
        c_embed.insert_field_at(index=6, name="SPA", value=("🔳" * self.species.SPA).ljust(5, "⬜"))
        c_embed.insert_field_at(index=7, name="SPD", value=("🔳" * self.species.SPD).ljust(5, "⬜"))
        c_embed.insert_field_at(index=8, name="SPE", value=("🔳" * self.species.SPE).ljust(5, "⬜"))
        return c_embed

    async def upsert(self, connection: Connection):
        """Upsert method for MegaCharacter

        Attributes
        ----------
        connection : Connection
            asyncpg connection
        """
        await self.standard_upsert(connection, kind="FAKEMON")
        await connection.execute(
            "INSERT INTO FAKEMON(ID, NAME, HP, ATK, DEF, SPA, SPD, SPE) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8) ON CONFLICT (ID) DO UPDATE SET "
            "NAME = $2, HP = $3, ATK = $4, DEF = $5, SPA = $6, SPD = $7, SPE = $8;",
            self.id,
            self.name,
            self.species.HP,
            self.species.ATK,
            self.species.DEF,
            self.species.SPA,
            self.species.SPD,
            self.species.SPE,
        )
        await self.movepool.upsert(connection, self.id)
