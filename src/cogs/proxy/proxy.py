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

from typing import Optional

from aiohttp import ClientSession
from discord import Interaction
from discord.app_commands import Choice, Transformer
from discord.app_commands.transformers import Transform
from yarl import URL

API = URL.build(scheme="https", host="randomuser.me", path="/api")


class Proxy(Transformer):
    @classmethod
    async def transform(cls, _: Interaction, value: Optional[str]):
        """If a name is found, this function titlecases it and returns it.

        Parameters
        ----------
        _ : Interaction
            Interaction
        value : Optional[str]
            The name to be titlecased.

        Returns
        -------
        str
            The titlecased name.
        """
        if value:
            return value.title()

    @classmethod
    async def autocomplete(cls, ctx: Interaction, _: str) -> list[Choice[str]]:
        """This function returns a list of choices for the autocomplete.

        Parameters
        ----------
        ctx : Interaction
            Interaction
        value : str
            The name to be titlecased.

        Returns
        -------
        list[Choice[str]]
            The list of choices.
        """
        session: ClientSession = ctx.client.session
        async with session.get(
            API.with_query(
                gender=str(ctx.namespace.gender).lower(),
                results="25",
                inc="name",
                noinfo="True",
            )
        ) as data:
            info = await data.json()
            return [
                Choice(name=name, value=name)
                for x in map(lambda x: x["name"], info["results"])
                if (name := f"{x['first']} {x['last']}")
            ]


NameGenerator = Transform[str, Proxy]
