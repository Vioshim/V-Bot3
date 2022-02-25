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

from json import load

with open("resources\species.json", mode="r") as file1:
    data: list[dict] = load(fp=file1)

    data.append(
        dict(
            id="GROWLITHEHISUI",
            name="Hisuian Growlithe",
            shape="Quadruped",
            color="Red",
            base_image="https://www.serebii.net/swordshield/pokemon/058-h.png",
            base_image_shiny="https://www.serebii.net/Shiny/SWSH/058-h.png",
            female_image="https://www.serebii.net/swordshield/pokemon/058-h.png",
            female_image_shiny="https://www.serebii.net/Shiny/SWSH/058-h.png",
            types=["FIRE", "ROCK"],
            height=0.8,
            weight=22.7,
            HP=60,
            ATK=75,
            DEF=45,
            SPA=65,
            SPD=50,
            SPE=55,
            banned=False,
            evolves_from=None,
            evolves_to=["ARCANINEHISUI"],
            movepool=dict(
                level={
                    "1": ["TACKLE"],
                    "5": ["EMBER"],
                    "9": ["BITE"],
                    "15": ["FIREFANG"],
                    "21": ["ROCKSLIDE"],
                    "29": ["CRUNCH"],
                    "37": ["DOUBLEEDGE"],
                    "47": ["FLAREBLITZ"],
                },
                tutor=[
                    "FIREFANG",
                    "ROCKSMASH",
                    "AERIALACE",
                    "SWIFT",
                    "REST",
                    "ROCKSLIDE",
                    "IRONTAIL",
                    "SNARL",
                    "WILDCHARGE",
                    "OUTRAGE",
                    "PLAYROUGH",
                    "FLAMETHROWER",
                ],
            ),
            abilities=["INTIMIDATE", "FLASHFIRE", "JUSTIFIED"],
            kind="Pokemon",
        )
    )

    for mon in data:
        movepool: dict[str, list[str] | dict[str, list[str]]] = mon["movepool"]
        aux = movepool.copy()
        for key, value in aux.items():
            if isinstance(value, dict):
                movepool[key] = {
                    k: sorted(v)
                    for k, v in sorted(value.items(), key=lambda x: int(x[0]))
                }
            elif isinstance(value, list):
                movepool[key] = sorted(value)

print(data[-1])


#  from json import dump
#  with open("resources\species.json", mode="w") as file2:
#      dump(data, fp=file2, indent=4)
