import discord.ext.commands.core


def subcommand_string(group: discord.ext.commands.core.Group):
    subcommands = [f"`{subcommand.name}`" for subcommand in sorted(group.commands, key=lambda x: x.name)]
    if len(subcommands) == 0:
        return "no subcommands"
    if len(subcommands) == 1:
        return f"`{subcommands[0]}`"
    return ", ".join(subcommands[:-1]) + f" or {subcommands[-1]}"
