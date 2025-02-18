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


from discord import Interaction
from discord.ui import Select, View, select

from src.structures.bot import CustomBot
from src.utils.etc import LIST_EMOJI


class PollView(View):
    def __init__(
        self,
        *,
        options: dict[str, list[int]],
        min_values: int = 1,
        max_values: int = 1,
        required: bool = False,
    ) -> None:
        super(PollView, self).__init__(timeout=None)
        self.options = options
        self.required = required
        self.poll.min_values = min(min_values, len(options))
        self.poll.max_values = min(max_values, len(options))
        self.format()

    def format(self):
        if amount := sum(map(len, self.options.values())):
            participants = len(set.union(*map(set, self.options.values())))
        else:
            amount, participants = 1, 0

        self.poll.options.clear()
        self.poll.placeholder = f"Poll Participants: {participants:02d}"

        for k, v in sorted(self.options.items(), key=lambda x: (-len(x[1]), x[0])):
            ref = round(16 * len(v) / amount)
            aux = (ref * "▓") + ((16 - ref) * "░")
            description = f"{aux} {len(v)/amount:.1%}"
            self.poll.add_option(label=k, description=description, emoji=LIST_EMOJI)

        return self

    @property
    def data(self):
        return dict(
            min_values=self.poll.min_values,
            max_values=self.poll.max_values,
            options=self.options,
            required=self.required,
        )

    @select(placeholder="Poll", custom_id="poll")
    async def poll(self, ctx: Interaction[CustomBot], sct: Select):
        db = ctx.client.mongo_db("Poll")

        previous = {k for k, v in self.options.items() if ctx.user.id in v}
        self.options = {k: [x for x in v if x != ctx.user.id] for k, v in self.options.items()}
        for item in sct.values:
            self.options.setdefault(item, [])
            if item not in previous or self.required:
                self.options[item].append(ctx.user.id)

        await ctx.response.edit_message(view=self.format())
        await db.replace_one(key := {"id": ctx.message.id}, key | self.data, upsert=True)
