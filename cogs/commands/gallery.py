from discord.ext import commands
from discord.ext.commands import dm_only

from helpers.database import images


class Gallery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @dm_only()
    @commands.command(name="gallery", aliases=["g", "viewall"])
    async def _gallery(self, ctx, page_number: int = 1):
        reply, embed = images.get_gallery_embed(ctx.author.id, page_number, 5)
        await ctx.send(reply, embed=embed)


async def setup(bot):
    await bot.add_cog(Gallery(bot))
