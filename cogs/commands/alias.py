from discord.ext import commands
from discord.ext.commands import Context, dm_only

from helpers.database import images
from helpers.string import subcommand


class Alias(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="alias", aliases=["aliases"], help="Create aliases for your jobs.")
    async def _alias(self, ctx: Context):
        if ctx.invoked_subcommand is not None:
            return
        subcommand_str = subcommand.subcommand_string(self._alias)
        await ctx.reply(f"No subcommand specified. Try using {subcommand_str}.")

    @_alias.command(aliases=["set", "create"])
    async def add(self, ctx: Context, job_id: str = None, alias: str = None):
        if job_id is None:
            await ctx.reply("You must specify a job ID.")
            return

        if alias is None:
            await ctx.reply("You must specify an alias.")
            return

        job = images.lookup_job(job_id)
        if job is None:
            await ctx.reply("That job ID does not exist.")
            return

        if not images.belongs_to(job, ctx.author.id):
            await ctx.reply("You can only add aliases to your own jobs.")
            return

        if images.alias_exists(alias, ctx.author.id):
            await ctx.reply("That alias already exists for you.")
            return

        await ctx.reply(f"Added alias `{alias}` to job `{job_id}`.")
        images.set_alias(job_id, alias)

    @_alias.command(aliases=["remove", "destroy"])
    async def delete(self, ctx: Context, alias: str = None):
        if alias is None:
            await ctx.reply("You must specify an alias.")
            return

        job = images.lookup_alias(alias, ctx.author.id)
        if job is None:
            await ctx.reply("That alias does not exist.")
            return

        if not images.belongs_to(job, ctx.author.id):
            await ctx.reply("You can only remove aliases from your own jobs.")
            return

        await ctx.reply(f"Removed alias `{alias}`.")
        images.remove_alias(alias, ctx.author.id)

    @_alias.command(aliases=["show"])
    @dm_only()
    async def list(self, ctx: Context):
        aliases = images.get_aliases(ctx.author.id)
        if len(aliases) == 0:
            await ctx.reply("You have no aliases.")
            return

        alias_str = ""
        for alias in aliases:
            alias_str += f"`{alias[6]}`: `{alias[0]}`\n"

        await ctx.reply(f"Your aliases:\n{alias_str}")


async def setup(bot):
    await bot.add_cog(Alias(bot))
