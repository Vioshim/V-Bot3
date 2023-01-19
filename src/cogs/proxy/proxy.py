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


import random
from abc import ABC, abstractmethod
from datetime import timedelta, timezone
from typing import Optional

import d20
import dateparser
from discord import Embed, Interaction
from discord.app_commands import Choice
from discord.app_commands.transformers import Transform, Transformer
from discord.ext import commands
from discord.utils import format_dt
from motor.motor_asyncio import AsyncIOMotorCollection
from rapidfuzz import process

from src.structures.mon_typing import TypingEnum
from src.structures.move import Move
from src.structures.proxy import NPC, Proxy, ProxyExtra


class ProxyFunction(ABC):
    aliases: list[str]
    ignore_caps: bool
    requires_strip: bool

    def __init_subclass__(
        cls,
        *,
        aliases: list[str] = None,
        ignore_caps: bool = True,
        requires_strip: bool = True,
    ) -> None:
        cls.aliases, cls.ignore_caps, cls.requires_strip = aliases or [], ignore_caps, requires_strip

    @classmethod
    def all(cls):
        return cls.__subclasses__()

    @classmethod
    async def lookup(
        cls,
        ctx: commands.Context,
        npc: NPC | Proxy | ProxyExtra,
        text: str,
    ) -> Optional[tuple[NPC | Proxy | ProxyExtra, str, Optional[Embed]]]:
        items = {alias: item for item in cls.__subclasses__() for alias in item.aliases}
        name, *args = text.split(":")
        if name and (x := process.extractOne(name, choices=list(items), score_cutoff=90)):
            item = items[x[0]]
            if item.ignore_caps:
                args = [x.lower() for x in args]
            if item.requires_strip:
                args = [x.strip() for x in args]
            try:
                return await item.parse(ctx, npc, args)
            except Exception as e:
                ctx.bot.logger.exception("ProxyFunction error: %s", args, exc_info=e)
                return npc, f"`Error: {e}`", None

    @classmethod
    @abstractmethod
    async def parse(cls, ctx: commands.Context, npc: NPC | Proxy | ProxyExtra, text: str, args: list[str]):
        """This is the abstract parsing methods

        Parameters
        ----------
        bot : CustomBot
            Client Instance
        user : Member
            User that interacts
        npc : NPC | Proxy | ProxyExtra
            NPC to keep or replace
        args : list[str]
            Args to evaluate

        Returns
        -------
        Optional[tuple[NPC | Proxy | ProxyExtra, str, Optional[Embed]]]
            Result
        """


class MoveFunction(ProxyFunction, aliases=["Move"]):
    @classmethod
    async def parse(cls, _: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :<any>                 | move
        :<any>:embed           | move w/embed
        :<any>:max             | max move
        :<any>:max:embed       | max move w/embed
        :<any>:max:<any>       | max move different type
        :<any>:max:<any>:embed | max move different type w/embed
        :<any>:z               | z move
        :<any>:z:embed         | z move w/embed
        :<any>:z:<any>         | z move different type
        :<any>:z:<any>:embed   | z move different type w/embed
        :<any>:<any>           | move different type
        :<any>:<any>:embed     | move different type w/embed
        Examples
        • {{move:ember}}
        • {{move:ember:embed}}
        • {{move:ember:max}}
        • {{move:ember:max:embed}}
        • {{move:ember:max:water}}
        • {{move:ember:max:water:embed}}
        • {{move:ember:z}}
        • {{move:ember:z:embed}}
        • {{move:ember:z:water}}
        • {{move:ember:z:water:embed}}
        • {{move:ember:water}}
        • {{move:ember:water:embed}}
        """
        match args:
            case [move]:
                if item := Move.deduce(move):
                    return npc, f"{item.emoji}`{item.name}`", None
            case [move, "embed"]:
                if item := Move.deduce(move):
                    return npc, f"{item.emoji}`{item.name}`", item.embed
            case [move, "max"]:
                if item := Move.deduce(move):
                    return npc, f"{item.max_move_type.emoji}`{item.max_move_base}〛{item.max_move_name}`", None
            case [move, "max", "embed"]:
                if item := Move.deduce(move):
                    return npc, f"{item.max_move_type.emoji}`{item.max_move_name}`", item.max_move_embed
            case [move, "max", move_type]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    name = item.max_move_name if item.type == move_type else f"{item.max_move_name}*"
                    emoji, effect = item.max_move_type_for(item).emoji, item.calculated_base(move_type.max_move_range)
                    return npc, f"{emoji}`{effect}〛{name}`", None
            case [move, "max", move_type, "embed"]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    embed = item.max_move_embed_for(move_type)
                    name = item.max_move_name if item.type == move_type else f"{item.max_move_name}*"
                    return npc, f"{item.max_move_type_for(item).emoji}`{name}`", embed
            case [move, "z"]:
                if item := Move.deduce(move):
                    if effect := item.z_effect:
                        effect, _ = effect
                    else:
                        effect = item.z_move_base
                    return npc, f"{item.emoji}`{effect}〛{item.type.z_move}`", None
            case [move, "z", "embed"]:
                if item := Move.deduce(move):
                    return npc, f"{item.emoji}`{item.type.z_move}`", item.z_move_embed
            case [move, "z", move_type]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    if effect := item.z_effect:
                        effect, _ = effect
                    else:
                        effect = item.calculated_base_z(move_type.z_move_range)
                    name = move_type.z_move if item.type == move_type else f"{move_type.z_move}*"
                    return npc, f"{move_type.emoji}`{effect}〛{name}`", None
            case [move, "z", move_type, "embed"]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    if effect := item.z_effect:
                        effect, _ = effect
                    else:
                        effect = item.calculated_base_z(move_type.z_move_range)
                    name = move_type.z_move if item.type == move_type else f"{move_type.z_move}*"
                    return npc, f"{move_type.emoji}`{effect}〛{name}`", item.z_move_embed_for(move_type)
            case [move, move_type]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    name = f"{item.name}*" if move_type != item.type else item.name
                    return npc, f"{move_type.emoji}`{name}`", None
            case [move, move_type, "embed"]:
                if item := Move.deduce(move):
                    move_type = TypingEnum.deduce(move_type) or item.type
                    return npc, f"{move_type.emoji}`{item.name}`", item.embed_for(move_type)


class DateFunction(ProxyFunction, aliases=["Date", "Time"], ignore_caps=False):
    @classmethod
    async def parse(cls, ctx: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :             | today's date
        :<mode>       | today's date w/ discord mode
        :<any>        | date, if tz not specified, will use database
        :<mode>:<any> | date w/ discord mode
        Examples
        • {{date}}
        • {{date:R}}
        • {{date:Dec 13th 2020:R}}
        • {{date:in 16 minutes:T}}
        • {{date:in two hours and one minute:D}}
        """
        db: AsyncIOMotorCollection = ctx.bot.mongo_db("AFK")
        now = ctx.message.created_at
        settings = dict(
            PREFER_DATES_FROM="future",
            TIMEZONE="utc",
            RELATIVE_BASE=now,
        )
        tz_info: Optional[timezone] = None
        match args:
            case []:
                return npc, format_dt(now), None
            case ["t" | "T" | "d" | "D" | "f" | "F" | "R" as mode]:
                return npc, format_dt(now, mode), None
            case [*params, "t" | "T" | "d" | "D" | "f" | "F" | "R" as mode]:
                if aux := await db.find_one({"user": ctx.author.id}):
                    tz_info = timezone(offset=timedelta(hours=aux["offset"]))
                    settings["RELATIVE_BASE"] = now.astimezone(tz=tz_info)
                    settings["TIMEZONE"] = str(tz_info)
                if item := dateparser.parse(":".join(params), settings=settings):
                    return npc, format_dt(item.replace(tzinfo=tz_info), style=mode), None
            case [*params]:
                if aux := await db.find_one({"user": ctx.author.id}):
                    tz_info = timezone(offset=timedelta(hours=aux["offset"]))
                    settings["RELATIVE_BASE"] = now.astimezone(tz=tz_info)
                    settings["TIMEZONE"] = str(tz_info)
                if item := dateparser.parse(":".join(params), settings=settings):
                    return npc, format_dt(item.replace(tzinfo=tz_info)), None


class MetronomeFunction(ProxyFunction, aliases=["Metronome"]):
    @classmethod
    async def parse(cls, _: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :           | random metronome move
        :embed      | random metronome move w/embed
        :full       | random full metronome move
        :full:embed | random full metronome move w/embed
        :z          | random metronome z move
        :z:embed    | random metronome z move w/embed
        :max        | random metronome max move
        :max:embed  | random metronome max move w/embed
        Examples
        • {{metronome}}
        • {{metronome:embed}}
        • {{metronome:full}}
        • {{metronome:full:embed}}
        • {{metronome:z}}
        • {{metronome:z:embed}}
        • {{metronome:max}}
        • {{metronome:max:embed}}
        """
        match args:
            case []:
                item = random.choice([x for x in Move.all() if x.metronome])
                return npc, f"{item.emoji}`{item.name}`", None
            case ["embed"]:
                item = random.choice([x for x in Move.all() if x.metronome])
                return npc, f"`{item.name}`", item.embed
            case ["full"]:
                item = random.choice([x for x in Move.all() if not (x.is_max_move() or x.is_z_move())])
                return npc, f"{item.emoji}`{item.name}`", None
            case ["full", "embed"]:
                item = random.choice([x for x in Move.all() if not (x.is_max_move() or x.is_z_move())])
                return npc, f"`{item.name}`", item.embed
            case ["z"]:
                item = random.choice([x for x in Move.all() if x.metronome])
                if effect := item.z_effect:
                    effect, _ = effect
                else:
                    effect = item.z_move_base
                return npc, f"{item.emoji}`{effect}〛{item.type.z_move}`", None
            case ["z", "embed"]:
                item = random.choice([x for x in Move.all() if x.metronome])
                return npc, f"{item.emoji}`{item.type.z_move}`", item.z_move_embed
            case ["max"]:
                item = random.choice([x for x in Move.all() if x.metronome])
                return npc, f"{item.max_move_type.emoji}`{item.max_move_base}〛{item.max_move_name}`", None
            case ["max", "embed"]:
                item = random.choice([x for x in Move.all() if x.metronome])
                return npc, f"{item.max_move_type.emoji}`{item.max_move_name}`", item.max_move_embed


class TypeFunction(ProxyFunction, aliases=["Type", "Chart"]):
    @classmethod
    async def parse(cls, _: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :                            | returns a random type
        :<any>                       | returns a type's emoji
        :<any>:attack:<any>*         | calculates damage against types
        :<any>:attack:inverse:<any>* | calculates inverse damage against types
        :<any>:defend:<any>*         | calculates resistance against types
        :<any>:defend:inverse:<any>* | calculates inverse resistance against types
        Examples
        • {{type}}
        • {{type:Dragon}}
        • {{type:Fairy:attack:Dragon:Dark}}
        • {{type:Fairy:attack:inverse:Dragon}}
        • {{Chart:Rock:defend:Normal}}
        • {{Chart:Rock:defend:inverse:Normal}}
        """
        match args:
            case [item_type]:
                if item := TypingEnum.deduce(item_type):
                    return npc, str(item.emoji), None
            case [item_type, "attack" | "attacking", "inverse", *item_types]:
                item = TypingEnum.deduce(item_type)
                data = TypingEnum.deduce_many(*item_types)
                if item and data:
                    calc = item.when_attacking(*data, inverse=True)
                    text = "".join(x.emoji for x in data)
                    return npc, f"{item.emoji} > {text} = {calc:.0%}", None
            case [item_type, "defend" | "defense" | "defending", "inverse", *item_types]:
                item = TypingEnum.deduce(item_type)
                data = TypingEnum.deduce_many(*item_types)
                if item and data:
                    calc = item.when_attacked_by(*data, inverse=True)
                    text = "".join(x.emoji for x in data)
                    return npc, f"{item.emoji} < {text} = {calc:.0%}", None
            case [item_type, "attack" | "attacking", *item_types]:
                item = TypingEnum.deduce(item_type)
                data = TypingEnum.deduce_many(*item_types)
                if item and data:
                    calc = item.when_attacking(*data, inverse=False)
                    text = "".join(x.emoji for x in data)
                    return npc, f"{item.emoji} > {text} = {calc:.0%}", None
            case [item_type, "defend" | "defense" | "defending", *item_types]:
                item = TypingEnum.deduce(item_type)
                data = TypingEnum.deduce_many(*item_types)
                if item and data:
                    calc = item.when_attacked_by(*data, inverse=False)
                    text = "".join(x.emoji for x in data)
                    return npc, f"{item.emoji} < {text} = {calc:.0%}", None


class MoodFunction(ProxyFunction, aliases=["Mood", "Mode", "Form"], ignore_caps=False):
    @classmethod
    async def parse(cls, _: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :<any> | checks for a variant that matches
        Examples
        • {{mood:Happy}}
        • {{mood:Angry}}
        • {{mode:Mega}}
        • {{mode:Devolved}}
        • {{Form:Midnight}}
        """
        if not isinstance(npc, Proxy):
            return

        match args:
            case [item]:
                if data := process.extractOne(
                    item,
                    choices=list(npc.extras),
                    score_cutoff=60,
                    processor=lambda x: x.name if isinstance(x, ProxyExtra) else x,
                ):
                    item = data[0]
                    username = f"{npc.name} ({item.name})" if npc.name != item.name else npc.name
                    if item.name.endswith("*") or len(username) > 80:
                        username = item.name.removesuffix("*") or npc.name
                    return NPC(name=username, image=item.image or npc.image), "", None


class RollFunction(ProxyFunction, aliases=["Roll"], ignore_caps=False):
    @classmethod
    async def parse(cls, _: commands.Context, npc: NPC | Proxy | ProxyExtra, args: list[str]):
        """
        :             | rolls a d20
        :embed        | rolls a d20 w/embed
        :<any>        | rolls a given expression
        :<any>:embed  | rolls a given expression w/embed
        :<any>:<any>* | randomly selects a choice
        Examples
        • {{roll}}
        • {{roll:embed}}
        • {{roll:d6}}
        • {{roll:d3+2:embed}}
        • {{roll:North:South:East:West}}
        """
        match args:
            case []:
                value = d20.roll(expr="d20")
                return npc, f"`🎲{value.total}`", None
            case ["embed" | "Embed"]:
                value = d20.roll(expr="d20")
                return npc, f"`🎲{value.total}`", Embed(description=value.result)
            case [item]:
                try:
                    value = d20.roll(expr=item, allow_comments=True)
                except Exception as e:
                    return npc, f"`🎲 {e}`", None
                return npc, f"`🎲{value.total}`", None
            case [item, "embed" | "Embed"]:
                try:
                    value = d20.roll(expr=item, allow_comments=True)
                except Exception as e:
                    return npc, f"`🎲 {e}`", None
                if len(value.result) > 4096:
                    d20.utils.simplify_expr(value.expr)
                return npc, f"`🎲{value.total}`", Embed(description=value.result)
            case ["choices", amount, *items]:
                if items := [o for x in items if (o := x.strip())]:
                    amount = int(amount) if amount.isdigit() else 1
                    return npc, f"`🎲{'|'.join(random.choices(items, k=amount))}`", None
            case ["sample", amount, *items]:
                if items := [o for x in items if (o := x.strip())]:
                    amount = int(amount) if amount.isdigit() else 1
                    return npc, f"`🎲{'|'.join(random.sample(items, k=amount))}`", None
            case [*items]:
                if items := [o for x in items if (o := x.strip())]:
                    return npc, f"`🎲{random.choice(items)}`", None
                if args == items:
                    value = d20.roll(expr="d20")
                    return npc, f"`🎲{value.total}`", None


class ProxyVariantTransformer(Transformer):
    async def transform(self, _: Interaction, value: str, /):
        return value or ""

    async def autocomplete(self, ctx: Interaction, value: str, /) -> list[Choice[str]]:
        db: AsyncIOMotorCollection = ctx.client.mongo_db("Proxy")
        items: list[ProxyExtra] = []
        if item := await db.find_one(
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
