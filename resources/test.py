# Load species.json

import json

import requests

with open("resources/species.json") as f:
    species: list[dict] = json.load(f)

URL = "https://pokeapi.co/api/v2"

species2 = list(filter(lambda x: not x.get("egg_groups"), species))
print(", ".join(item["name"] for item in species2))

"""
for item in species2:
    name: str = item["name"].split(" ")[0]
    name = (
        name
        .lower()
        .replace("r.", "r")
        .replace("é", "e")
        .replace("'", "")
        .replace(' ', '-')
        .removeprefix("primal-")
        .removeprefix("mega-")
        .removeprefix("black-")
        .removeprefix("white-")
        .removeprefix("shadow-")
        .removeprefix("ultra-")
        .removesuffix("-galar")
        .removesuffix("-alola")
        .removesuffix("-hisui")
        .removesuffix("-paldea")
        .removesuffix("-x")
        .removesuffix("-y")
    )
    r = requests.get(f"{URL}/pokemon-species/{name}")
    if r.status_code == 200:
        data: dict[str, list[dict[str, str]]] = r.json()
        if egg_groups := data.get("egg_groups", []):
            item["egg_groups"] = [group["name"] for group in egg_groups]

# Save species.json
with open("resources/species.json", "w") as f:
    json.dump(species, f, indent=4, sort_keys=False, ensure_ascii=False)
"""
