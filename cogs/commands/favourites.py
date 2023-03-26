from discord.ext import commands
from discord.ext.commands import Context, dm_only

from helpers.database import images, user_settings
from helpers.string import subcommand
from helpers.views.page_view import PaginatedView


class Favourites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="favourites", aliases=["favs", "favourite", "fav"], help="View your favourite jobs.")
    async def _favourites(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._favourites)
        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_favourites.command()
    async def add(self, ctx: Context, job_id: str = None):
        if job_id is None:
            await ctx.reply("You must specify a job ID.")
            return

        job = images.lookup_job(job_id)
        if job is None:
            await ctx.reply("That job ID does not exist.")
            return

        if not images.belongs_to(job, ctx.author.id):
            await ctx.reply("You can only add your own jobs to your favourites.")
            return

        if user_settings.favourite_exists(job_id, ctx.author.id):
            await ctx.reply("That job is already a favourite.")
            return

        await ctx.reply(f"Added job `{job_id}` to favourites.")
        user_settings.set_favourite(job_id, ctx.author.id)

    @_favourites.command()
    async def remove(self, ctx: Context, job_id: str = None):
        if job_id is None:
            await ctx.reply("You must specify a job ID.")
            return

        job = images.lookup_job(job_id)
        if job is None:
            await ctx.reply("That job ID does not exist.")
            return

        if not images.belongs_to(job, ctx.author.id):
            await ctx.reply("You can only remove your own jobs from your favourites.")
            return

        if not user_settings.favourite_exists(job_id, ctx.author.id):
            await ctx.reply("That job is not a favourite.")
            return

        await ctx.reply(f"Removed job `{job_id}` from favourites.")
        user_settings.remove_favourite(job_id, ctx.author.id)

    @_favourites.command()
    async def list(self, ctx: Context, page_number: int = 1):
        favourites = user_settings.get_favourites(ctx.author.id)
        if len(favourites) == 0:
            await ctx.reply("You have no favourites.")
            return

        reply, embed = user_settings.get_favourites_embed(ctx.author.id, page_number)
        await ctx.send(
            content= reply,
            embed=embed,
            view= PaginatedView(user_settings.get_favourites_embed)
        )


async def setup(bot):
    await bot.add_cog(Favourites(bot))
