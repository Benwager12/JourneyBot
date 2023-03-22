from discord.ext import commands
from discord.ext.commands import Context


class OnCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command(self, ctx: Context):
        print(f"User {ctx.author} ({ctx.author.id}) used command {ctx.command}.")


async def setup(bot):
    await bot.add_cog(OnCommand(bot))
