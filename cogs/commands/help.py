from discord.ext import commands
from discord.ext.commands import Group


def all_command_string(commands: list):
    cmds = [f"`{cmd}`" for cmd in sorted(commands, key=lambda x: x.name)]

    if len(cmds) == 0:
        return "No commands found."
    if len(cmds) == 1:
        return f"`{cmds[0]}`"
    return ", ".join(cmds[:-1]) + f" and {cmds[-1]}"


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h", "commands"], help="View help for commands.")
    async def _help(self, ctx, command: str = None):
        if command is None:
            # List all commands
            cmds = self.bot.commands
            command_str = all_command_string(cmds)
            await ctx.reply(f"Here is a list of all commands: {command_str}")
            return

        command: Group = self.bot.get_command(command)
        if command is None:
            await ctx.reply("That command does not exist.")
            return

        print(f"Help for {command} requested by {ctx.author}. ({command.help})")
        await ctx.reply(f"The command `{command}` has the following help text: \"{command.help}\"")


async def setup(bot):
    await bot.add_cog(Help(bot))
