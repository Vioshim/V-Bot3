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


from enum import Enum

from discord import PartialEmoji

"https://archives.bulbagarden.net/media/upload/_Sprite.png"


class Pokeball(Enum):
    Poke_Ball = "7/79/Dream_Pok%C3%A9_Ball"
    Great_Ball = "b/bf/Dream_Great_Ball"
    Ultra_Ball = "a/a8/Dream_Ultra_Ball"
    Master_Ball = "9/95/Dream_Master_Ball"
    Safari_Ball = "1/15/Dream_Safari_Ball"
    Fast_Ball = "4/44/Dream_Fast_Ball"
    Level_Ball = "1/19/Dream_Level_Ball"
    Lure_Ball = "4/4e/Bag_Lure_Ball_IV"
    Heavy_Ball = "b/bb/Dream_Heavy_Ball"
    Love_Ball = "9/94/Dream_Love_Ball"
    Friend_Ball = "7/7a/Dream_Friend_Ball"
    Moon_Ball = "2/22/Dream_Moon_Ball"
    Sport_Ball = "d/df/Dream_Sport_Ball"
    Net_Ball = "a/a0/Dream_Net_Ball"
    Nest_Ball = "8/8c/Dream_Nest_Ball"
    Repeat_Ball = "d/df/Dream_Repeat_Ball"
    Timer_Ball = "f/f0/Dream_Timer_Ball"
    Luxury_Ball = "7/7e/Dream_Luxury_Ball"
    Premier_Ball = "6/64/Dream_Premier_Ball"
    Dive_Ball = "9/9a/Dream_Dive_Ball"
    Dusk_Ball = "5/59/Dream_Dusk_Ball"
    Heal_Ball = "0/0e/Dream_Heal_Ball"
    Quick_Ball = "9/90/Dream_Quick_Ball"
    Cherish_Ball = "f/f6/Dream_Cherish_Ball"
    Park_Ball = "b/b2/Bag_Park_Ball"
    Dream_Ball = "2/27/Dream_Dream_Ball"
    Beast_Ball = "6/65/Dream_Beast_Ball"
    Strange_Ball = "1/19/Bag_Strange_Ball_LA"
    Poke_Ball_HOME = "3/3d/Bag_Pok%C3%A9_Ball_HOME"
    Great_Ball_HOME = "b/bd/Bag_Great_Ball_HOME"
    Ultra_Ball_HOME = "b/b6/Bag_Ultra_Ball_HOME"
    Heavy_Ball_HOME = "e/eb/Bag_Heavy_Ball_HOME"
    Leaden_Ball_HOME = "b/bc/Bag_Leaden_Ball_HOME"
    Gigaton_Ball_HOME = "1/15/Bag_Gigaton_Ball_HOME"
    Feather_Ball_HOME = "f/fe/Bag_Feather_Ball_HOME"
    Wing_Ball_HOME = "0/07/Bag_Wing_Ball_HOME"
    Jet_Ball_HOME = "d/d5/Bag_Jet_Ball_HOME"
    Origin_Ball_HOME = "c/c7/Bag_Origin_Ball_HOME"

    @property
    def emoji(self):
        return PartialEmoji(name="pokeball", id=952522808435544074)

    @property
    def url(self):
        return f"https://archives.bulbagarden.net/media/upload/{self.value}_Sprite.png"

    @property
    def label(self):
        return self.name.replace("_", " ").replace("HOME", "Hisui")
