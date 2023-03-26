from discord.ext import commands
from discord.ext.commands import dm_only

from helpers.database import images
from helpers.views.page_view import PaginatedView


class Gallery(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @dm_only()
    @commands.command(name="gallery", aliases=["g", "viewall"])
    async def _gallery(self, ctx, page_number: int = 1):
        page_amount = images.get_page_amount(ctx.author.id)

        page_number = max(1, min(page_number, page_amount))

        reply, embed = images.get_gallery_embed(ctx.author.id, page_number)
        await ctx.send(reply, embed=embed, view=PaginatedView())


async def setup(bot):
    await bot.add_cog(Gallery(bot))
