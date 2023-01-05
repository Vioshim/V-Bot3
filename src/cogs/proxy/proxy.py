# Copyright 2023 Vioshim
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


from discord import Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.structures.proxy import Proxy, ProxyExtra


class ProxyVariantTransformer(Transformer):
    async def transform(self, _: Interaction, value: str, /):
        return value or ""

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Proxy")
        items: list[ProxyExtra] = []
        if item := db.find_one(
            {
                "id": int(oc) if (oc := ctx.namespace.oc) and str(oc).isdigit() else None,
                "server": ctx.guild_id,
            }
        ):
            items.extend(Proxy.from_mongo_dict(item).extras)

        if options := process.extract(
            value,
            choices=items,
            limit=25,
            processor=lambda x: getattr(x, "name", x),
            score_cutoff=60,
        ):
            options = [x[0] for x in options]
        elif not value:
            options = items[:25]
        return [Choice(name=x.name, value=x.name) for x in options]


ProxyVariantArg = Transform[str, ProxyVariantTransformer]
