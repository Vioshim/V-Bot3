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


class Pokeball(Enum):
    Poké_Ball = "9/93"
    Great_Ball = "c/ca"
    Ultra_Ball = "0/03"
    Master_Ball = "6/6d"
    Safari_Ball = "e/eb"
    Fast_Ball = "7/70"
    Level_Ball = "d/df"
    Lure_Ball = "2/25"
    Heavy_Ball = "7/74"
    Love_Ball = "4/42"
    Friend_Ball = "1/17"
    Moon_Ball = "f/f9"
    Sport_Ball = "3/3e"
    Net_Ball = "4/4b"
    Dive_Ball = "f/f2"
    Nest_Ball = "4/42"
    Repeat_Ball = "8/89"
    Timer_Ball = "3/3d"
    Luxury_Ball = "8/87"
    Premier_Ball = "5/55"
    Dusk_Ball = "0/06"
    Heal_Ball = "1/17"
    Quick_Ball = "4/41"
    Cherish_Ball = "f/ff"
    Park_Ball = "b/b2"
    Dream_Ball = "4/4a"
    Beast_Ball = "f/f2"
    Strange_Ball = "9/9c"
    Feather_Ball = "f/fe"
    Wing_Ball = "0/07"
    Jet_Ball = "d/d5"
    Leaden_Ball = "b/bc"
    Gigaton_Ball = "1/15"
    Origin_Ball = "c/c7"
    Poké_Ball_HOME = "3/3d"
    Great_Ball_HOME = "b/bd"
    Ultra_Ball_HOME = "b/b6"
    Heavy_Ball_HOME = "e/eb"
    Leaden_Ball_HOME = "b/bc"
    Gigaton_Ball_HOME = "1/15"
    Feather_Ball_HOME = "f/fe"
    Wing_Ball_HOME = "0/07"
    Jet_Ball_HOME = "d/d5"
    Origin_Ball_HOME = "c/c7"
    Strange_Ball_HOME = "9/9c"

    @property
    def url(self):
        return f"https://archives.bulbagarden.net/media/upload/{self.value}/Bag_{self.name}_Sprite.png"

    @property
    def label(self):
        return self.name.replace("_", " ").replace("HOME", "Hisui")
