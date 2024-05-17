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

from discord import Attachment, File, app_commands
from discord.ext import commands
from novelai import (
    Action,
    Metadata,
    Model,
    NAIClient,
    Resolution,
    Sampler,
    UndesiredPreset,
)

from src.structures.bot import CustomBot


class GenerateFlags(commands.FlagConverter, case_insensitive=True, prefix="--", delimiter=" "):
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
    strength: commands.Range[float, 0.01, 0.99] = commands.flag(
        default=0.6,
        description="Strength of the image",
        aliases=["str"],
    )
    noise: commands.Range[float, 0, 1] = commands.flag(
        default=0.1,
        description="Noise of the image",
        aliases=["noisy"],
    )
    add_original_image: bool = commands.flag(
        default=False,
        description="Add the original image to the generated image",
        aliases=["add_original"],
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
        await self.client.init(timeout=30)

    async def cog_unload(self) -> None:
        await self.client.close()

    @app_commands.guilds(1196879060173852702)
    @app_commands.default_permissions(administrator=True)
    @commands.has_guild_permissions(administrator=True)
    @commands.max_concurrency(1, wait=False)
    @commands.hybrid_command()
    async def ai(
        self,
        ctx: commands.Context,
        prompt: str,
        image: Optional[Attachment] = None,
        mask: Optional[Attachment] = None,
        *,
        flags: GenerateFlags,
    ):
        """Generate images using the AI

        Parameters
        ----------
        ctx: commands.Context
            Context
        prompt: str
            Prompt for the AI to generate an image from
        image: Optional[Attachment]
            Image to generate from
        mask: Optional[Attachment]
            Mask for the image
        """
        await ctx.typing(ephemeral=False)

        if image is None:
            payload = Metadata(
                prompt=prompt,
                negative_prompt=flags.negative_prompt,
                res_preset=flags.size,
                model=flags.model,
                seed=flags.seed,
                sm=False,
                action=Action.GENERATE,
                sampler=flags.sampler,
                steps=flags.steps,
                ucPreset=UndesiredPreset.HEAVY,
            )
        elif mask is not None:
            data = base64.b64encode(await image.read()).decode("utf-8")
            mask_data = base64.b64encode(await mask.read()).decode("utf-8")

            height, width = flags.size.value
            payload = Metadata(
                prompt=prompt,
                negative_prompt=flags.negative_prompt,
                model=flags.model,
                seed=flags.seed,
                action=Action.INPAINT,
                height=height,
                width=width,
                sampler=flags.sampler,
                noise=flags.noise,
                sm=False,
                add_original_image=flags.add_original_image,
                steps=flags.steps,
                mask=mask_data,
                image=data,
                strength=flags.strength,
                ucPreset=UndesiredPreset.HEAVY,
            )
        else:
            data = base64.b64encode(await image.read()).decode("utf-8")
            height, width = flags.size.value
            payload = Metadata(
                prompt=prompt,
                negative_prompt=flags.negative_prompt,
                model=flags.model,
                seed=flags.seed,
                action=Action.IMG2IMG,
                height=height,
                width=width,
                sampler=flags.sampler,
                noise=flags.noise,
                sm=False,
                steps=flags.steps,
                image=data,
                strength=flags.strength,
                ucPreset=UndesiredPreset.HEAVY,
            )

        if result := payload.calculate_cost(is_opus=True):
            return await ctx.send(f"Estimated cost: {result} credits", ephemeral=True)

        await ctx.send(
            files=[
                File(
                    fp=BytesIO(img.data),
                    filename=img.filename,
                    description="\n".join(
                        (
                            f"Prompt: {img.metadata.prompt}",
                            f"Seed: {img.metadata.seed}",
                            f"Negative Prompt: {img.metadata.negative_prompt}",
                        )
                    )[:1024],
                )
                for img in await self.client.generate_image(payload, is_opus=True, verbose=True)
            ]
        )


async def setup(bot: CustomBot) -> None:
    """Default Cog loader

    Parameters
    ----------
    bot: CustomBot
        Bot
    """
    await bot.add_cog(AiCog(bot))
