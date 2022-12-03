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


class Pokeball(Enum):
    Poke_Ball = "9/93/Bag_Poké_Ball"
    Great_Ball = "c/ca/Bag_Great_Ball"
    Ultra_Ball = "0/03/Bag_Ultra_Ball"
    Master_Ball = "6/6d/Bag_Master_Ball"
    Safari_Ball = "e/eb/Bag_Safari_Ball"
    Fast_Ball = "7/70/Bag_Fast_Ball"
    Level_Ball = "d/df/Bag_Level_Ball"
    Lure_Ball = "2/25/Bag_Lure_Ball"
    Heavy_Ball = "7/74/Bag_Heavy_Ball"
    Love_Ball = "4/42/Bag_Love_Ball"
    Friend_Ball = "1/17/Bag_Friend_Ball"
    Moon_Ball = "f/f9/Bag_Moon_Ball"
    Sport_Ball = "3/3e/Bag_Sport_Ball"
    Net_Ball = "4/4b/Bag_Net_Ball"
    Dive_Ball = "f/f2/Bag_Dive_Ball"
    Nest_Ball = "4/42/Bag_Nest_Ball"
    Repeat_Ball = "8/89/Bag_Repeat_Ball"
    Timer_Ball = "3/3d/Bag_Timer_Ball"
    Luxury_Ball = "8/87/Bag_Luxury_Ball"
    Premier_Ball = "5/55/Bag_Premier_Ball"
    Dusk_Ball = "0/06/Bag_Dusk_Ball"
    Heal_Ball = "1/17/Bag_Heal_Ball"
    Quick_Ball = "4/41/Bag_Quick_Ball"
    Cherish_Ball = "f/ff/Bag_Cherish_Ball"
    Park_Ball = "b/b2/Bag_Park_Ball"
    Dream_Ball = "4/4a/Bag_Dream_Ball"
    Beast_Ball = "f/f2/Bag_Beast_Ball"
    Strange_Ball = "9/9c/Bag_Strange_Ball_HOME"
    Feather_Ball = "f/fe/Bag_Feather_Ball_HOME"
    Wing_Ball = "0/07/Bag_Wing_Ball_HOME"
    Jet_Ball = "d/d5/Bag_Jet_Ball_HOME"
    Leaden_Ball = "b/bc/Bag_Leaden_Ball_HOME"
    Gigaton_Ball = "1/15/Bag_Gigaton_Ball_HOME"
    Origin_Ball = "c/c7/Bag_Origin_Ball_HOME"
    Poke_Ball_HOME = "3/3d/Bag_Poké_Ball_HOME"
    Great_Ball_HOME = "b/bd/Bag_Great_Ball_HOME"
    Ultra_Ball_HOME = "b/b6/Bag_Ultra_Ball_HOME"
    Heavy_Ball_HOME = "e/eb/Bag_Heavy_Ball_HOME"

    @property
    def emoji(self):
        return PartialEmoji(name="pokeball", id=952522808435544074)

    @property
    def url(self):
        return f"https://archives.bulbagarden.net/media/upload/{self.value}_Sprite.png"

    @property
    def label(self):
        return self.name.replace("_", " ").replace("HOME", "Hisui")
