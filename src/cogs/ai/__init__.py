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


import base64
import os
from io import BytesIO
from typing import Optional

from discord import Attachment, Embed, File, app_commands
from discord.ext import commands
from novelai import Action, Metadata, Model, NAIClient, Resolution, Sampler

from src.structures.bot import CustomBot


class GenerateFlags(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
    prompt: str = commands.flag(
        default="",
        positional=True,
        description="Prompt for the AI to generate an image from",
    )
    negative_prompt: str = commands.flag(
        default="",
        aliases=["neg_prompt", "negative", "neg"],
        description="Negative prompt for the AI to generate an image from",
    )
    model: Model = commands.flag(
        default=Model.FURRYV3,
        description="Model to use for generating the image",
    )
    seed: commands.Range[int, 0, 4294967295 - 7] = commands.flag(
        default=0,
        description="Seed for the AI to generate the image from",
    )
    size: Resolution = commands.flag(
        default=Resolution.NORMAL_SQUARE,
        description="Size of the image to generate",
    )
    sampler: Sampler = commands.flag(
        default=Sampler.EULER_ANC,
        description="Sampler to use for generating the image",
    )
    steps: commands.Range[int, 1, 28] = commands.flag(
        default=28,
        aliases=["step"],
        description="Number of steps to generate the image",
    )


class AiCog(commands.Cog):

    def __init__(self, bot: CustomBot):
        self.bot = bot
        self.client = NAIClient(
            os.environ["NOVELAI_USERNAME"],
            os.environ["NOVELAI_PASSWORD"],
            proxy=None,
        )

    async def cog_load(self) -> None:
        await self.client.init(timeout=30, auto_close=True)

    async def cog_unload(self) -> None:
        await self.client.close()

    @app_commands.guilds(1196879060173852702)
    @commands.max_concurrency(1, wait=False)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.hybrid_group(invoke_without_command=True)
    async def ai(self, ctx: commands.Context, *, flags: GenerateFlags):
        await ctx.invoke(self.generate, flags=flags)

    @ai.command()
    async def generate(self, ctx: commands.Context, *, flags: GenerateFlags):
        """Generate an image from a prompt"""
        await ctx.defer(ephemeral=True)

        payload = Metadata(
            prompt=flags.prompt,
            negative_prompt=flags.negative_prompt,
            res_preset=flags.size,
            model=flags.model,
            seed=flags.seed,
            action=Action.GENERATE,
            sampler=flags.sampler,
            steps=flags.steps,
            ucPreset=3,
        )

        if result := payload.calculate_cost(is_opus=True):
            return await ctx.send(f"Estimated cost: {result} credits", ephemeral=True)

        files, embeds = [], []
        for img in await self.client.generate_image(payload, is_opus=True):
            embed = Embed(title="Result", color=ctx.author.color)
            embeds.append(embed.set_image(url=f"attachment://{img.filename}"))
            files.append(
                File(
                    fp=BytesIO(img.data),
                    filename=img.filename,
                    description=str(img.metadata.model_dump_json(indent=2))[:1024],
                )
            )

        await ctx.send(embeds=embeds, files=files, ephemeral=True)

    @ai.command()
    async def img2img(
        self,
        ctx: commands.Context,
        image: Attachment,
        mask: Optional[Attachment] = None,
        strength: commands.Range[float, 0.01, 0.99] = 0.6,
        noise: commands.Range[float, 0, 1] = 0.1,
        *,
        flags: GenerateFlags,
    ):
        """Generate an image from an image

        Parameters
        ----------
        image : Attachment
            Attachment to use for the image
        mask : Optional[Attachment], optional
            Attachment to use for the mask, by default None
        strength : commands.Range[float, 0.01, 0.99], optional
            Strength of the image, by default 0.6
        noise : commands.Range[float, 0, 1], optional
            Noise of the image, by default 0.1
        """
        await ctx.defer(ephemeral=True)

        if not (image is not None and str(image.content_type).startswith("image/")):
            raise commands.BadArgument("Invalid image attachment")

        data = base64.b64encode(await image.read()).decode("utf-8")

        if mask is not None and str(mask.content_type).startswith("image/"):
            mask_data = base64.b64encode(await mask.read()).decode("utf-8")
        else:
            mask_data = None

        height, width = flags.size.value
        payload = Metadata(
            prompt=flags.prompt,
            negative_prompt=flags.negative_prompt,
            model=flags.model,
            seed=flags.seed,
            action=Action.IMG2IMG,
            height=height,
            width=width,
            sampler=flags.sampler,
            noise=noise,
            steps=flags.steps,
            mask=mask_data,
            image=data,
            strength=strength,
            ucPreset=3,
        )

        if result := payload.calculate_cost(is_opus=True):
            return await ctx.send(f"Estimated cost: {result} credits", ephemeral=True)

        files, embeds = [], []
        for img in await self.client.generate_image(payload, is_opus=True):
            embed = Embed(title="Result", color=ctx.author.color)
            embeds.append(embed.set_image(url=f"attachment://{img.filename}"))
            files.append(
                File(
                    fp=BytesIO(img.data),
                    filename=img.filename,
                    description=str(img.metadata.model_dump_json(indent=2))[:1024],
                )
            )

        await ctx.send(embeds=embeds, files=files, ephemeral=True)

    @ai.command()
    async def inpaint(
        self,
        ctx: commands.Context,
        image: Attachment,
        mask: Attachment,
        add_original_image: bool = False,
        strength: commands.Range[float, 0.01, 0.99] = 0.6,
        noise: commands.Range[float, 0, 1] = 0.1,
        *,
        flags: GenerateFlags,
    ):
        """Generate an image from a prompt

        Parameters
        ----------
        image : Attachment
            Attachment to use for the image
        mask : Optional[Attachment], optional
            Attachment to use for the mask, by default None
        strength : commands.Range[float, 0.01, 0.99], optional
            Strength of the image, by default 0.6
        noise : commands.Range[float, 0, 1], optional
            Noise of the image, by default 0.1
        """
        await ctx.defer(ephemeral=True)

        if not (image is not None and str(image.content_type).startswith("image/")):
            raise commands.BadArgument("Invalid image attachment")

        if not (mask is not None and str(mask.content_type).startswith("image/")):
            raise commands.BadArgument("Invalid mask attachment")

        data = base64.b64encode(await image.read()).decode("utf-8")
        mask_data = base64.b64encode(await mask.read()).decode("utf-8")

        height, width = flags.size.value
        payload = Metadata(
            prompt=flags.prompt,
            negative_prompt=flags.negative_prompt,
            model=flags.model,
            seed=flags.seed,
            action=Action.INPAINT,
            height=height,
            width=width,
            sampler=flags.sampler,
            noise=noise,
            add_original_image=add_original_image,
            steps=flags.steps,
            mask=mask_data,
            image=data,
            strength=strength,
            ucPreset=3,
        )

        if result := payload.calculate_cost(is_opus=True):
            return await ctx.send(f"Estimated cost: {result} credits", ephemeral=True)

        files, embeds = [], []
        for img in await self.client.generate_image(payload, is_opus=True):
            embed = Embed(title="Result", color=ctx.author.color)
            embeds.append(embed.set_image(url=f"attachment://{img.filename}"))
            files.append(
                File(
                    fp=BytesIO(img.data),
                    filename=img.filename,
                    description=str(img.metadata.model_dump_json(indent=2))[:1024],
                )
            )

        await ctx.send(embeds=embeds, files=files, ephemeral=True)


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(AiCog(bot))
