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
from itertools import groupby
from typing import Optional, Union

from discord import (
    Interaction,
    InteractionResponse,
    Member,
    Message,
    SelectOption,
    TextChannel,
    Webhook,
)
from discord.ui import Button, Select, View, button, select
from discord.utils import remove_markdown
from humanize import naturaltime

from src.pagination.complex import Complex
from src.structures.bot import CustomBot

__all__ = ("InviterView",)

HUB1 = """
__𝐂𝐫𝐞𝐬𝐜𝐞𝐧𝐭 𝐑𝐨𝐥𝐞𝐩𝐥𝐚𝐲 𝐇𝐮𝐛__

𝙰𝚍𝚟𝚎𝚛𝚝𝚒𝚜𝚒𝚗𝚐; 𝚁𝚎𝚟𝚘𝚕𝚞𝚝𝚒𝚘𝚗𝚒𝚣𝚎𝚍

[✦] 𝑾𝒉𝒂𝒕 𝒊𝒔 𝒕𝒉𝒊𝒔? [✦]

Two breath-taking communities that have combined their essence and mission to create one perfect place of gathering for roleplayers of all types! Crescent is the gathering place for artists of any craft, but primarily, we focus on partnering and growing roleplay communities! No matter your server's size or genre, partnering here means growth, guaranteed!

Our mission is simple; to connect and protect the roleplay community at large, and to offer unique and creative means through which you can grow your server. So, how do we do this? 

[ :crescent_moon: ] ⇻ A partnering system designed to help YOU get the most out of your partnership, with unique pings representing each genre of RP!

[ :crescent_moon: ] ⇻ A strong community with community events such as game nights, movie nights, and many opportunities to earn nitro and other gifts!

[ :crescent_moon: ] ⇻ Drop-In Advertisements, post 4 post partnering, AND channel 4 channel partnering - with tiers to display your server's playerbase!

[ :crescent_moon: ] ⇻ Resources for aspiring artists, writers, and musicians to get their name out there and show others their creations and dedication!

[ :crescent_moon: ] ⇻ Growth consultations for supporters and small servers from the minds behind Crescent, designed to help everyone reach their mark!

[ :crescent_moon: ] ⇻ A strong system to report dangers to the community or toxic and heinous individuals, with a ticket system to keep your report private!

**[ Banner Link: ]** https://cdn.discordapp.com/attachments/742602526326521926/899746669824978984/MOSHED-2021-10-18-14-48-32.gif

**[ Owner IDs: ]** 198118592632455168 (Sovereign I), 248049930428481536 (Sovereign II), 205100036760141825 (Sovereign III), 207729013693743104 (Sovereign IV), 282602243348365313 (Sovereign V)

**[ Mentions: ]** @everyone

**[ Server Invite: ]** https://discord.gg/Ms8kFU5TDA
""".strip()

HUB2 = """
**The Simple Roleplay Hub**

Tired of complicated RP hubs? Do you want to find new and great RP servers? Are you a server owner and you just want a simple everyone ping to advertise your server? Look no further than the Simple Roleplay Hub! This ad like the server will be kept simple. We will ping everyone regardless of size and we have 6 different tiers depending on the size of your server. What are you waiting for? Join today!

https://discord.gg/G6Nz5jW
""".strip()


def get_title(message: Message):
    if isinstance(title := message.embeds[0].title, str):
        title = remove_markdown(title)
        return title.split("partnered with ")[-1]

    return "Unknown"


def get_date(message: Message):
    return naturaltime(message.created_at.replace(tzinfo=None)).title()


def msg_parser(msg: Message):
    return get_title(msg), get_date(msg)


class InvitePaginator(Complex):
    def __init__(
        self,
        bot: CustomBot,
        member: Member,
        target: Union[Interaction, Webhook, TextChannel],
        messages: set[Message],
    ):
        super(InvitePaginator, self).__init__(
            bot=bot,
            member=member,
            target=target,
            values=messages,
            timeout=None,
            parser=msg_parser,
            keep_working=True,
            sort_key=get_title,
        )
        self.embed.title = "Select Partner"

    async def custom_choice(self, ctx: Interaction, sct: Select):
        response: InteractionResponse = ctx.response
        index = sct.values[0]
        amount = self.entries_per_page * self._pos
        chunk = self.values[amount : amount + self.entries_per_page]
        item: Message = chunk[int(index)]
        embed = item.embeds[0]
        view = View.from_message(item)
        if not response.is_done():
            await response.send_message(
                content=item.content,
                embed=embed,
                view=view,
                ephemeral=True,
            )
        else:
            await response.edit_message(
                content=item.content,
                embed=embed,
                view=view,
            )

    @property
    def choice(self) -> Optional[Message]:
        """Method Override

        Returns
        -------
        set[Move]
            Desired Moves
        """
        if value := super(InvitePaginator, self).choice:
            return value


class InviterView(View):
    def __init__(
        self,
        bot: CustomBot,
        messages: list[Message],
    ):
        super().__init__(timeout=None)
        self.bot = bot
        messages = [x for x in messages if x.embeds]
        self.data: dict[str, set[Message]] = {
            k: set(v)
            for k, v in groupby(
                messages,
                key=lambda x: x.embeds[0].footer.text,
            )
            if k and v
        }
        self.setup()

    def setup(self):
        sct: Select = self.partners
        sct.options.clear()
        for item in self.data:
            sct.add_option(
                label=item,
                value=item,
                description=f"See partnered {item} servers.",
                emoji="\N{HANDSHAKE}",
            )
        if not sct.options:
            sct.append_option(SelectOption(label="Empty", value="Empty"))
            sct.disabled = True
        else:
            sct.disabled = False

    @button(
        label="𝐂𝐫𝐞𝐬𝐜𝐞𝐧𝐭 𝐑𝐨𝐥𝐞𝐩𝐥𝐚𝐲 𝐇𝐮𝐛 - Click here to read more",
        row=0,
        emoji="\N{HANDSHAKE}",
        custom_id="hub1",
    )
    async def hub1(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message(content=HUB1, ephemeral=True)

    @button(
        label="The Simple Roleplay Hub - Click here to read more",
        row=1,
        emoji="\N{HANDSHAKE}",
        custom_id="hub2",
    )
    async def hub2(self, ctx: Interaction, _: Button):
        resp: InteractionResponse = ctx.response
        await resp.send_message(content=HUB2, ephemeral=True)

    @select(
        placeholder="Partnerships by Category",
        row=2,
        custom_id="partners",
    )
    async def partners(self, ctx: Interaction, sct: Select):
        resp: InteractionResponse = ctx.response
        item = sct.values[0]
        if items := self.data.get(sct.values[0], set()):
            view = InvitePaginator(
                bot=self.bot,
                member=ctx.user,
                target=ctx,
                messages=items,
            )
            embed = view.embed
            embed.title = title = f"{item} Partnerships".title()
            async with view.send(ephemeral=True):
                self.bot.logger.info(
                    "User %s is reading %s",
                    str(ctx.user),
                    title,
                )
        else:
            await resp.send_message(
                "No values were found that match this category.", ephemeral=True
            )
