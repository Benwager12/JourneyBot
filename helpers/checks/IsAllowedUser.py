from typing import Optional

from discord.ext import commands
from discord.ext.commands import Context, CheckFailure

from helpers.file import config, allowed_users


def is_allowed():
    def predicate(ctx: Context):
        return str(ctx.author.id) in allowed_users.get() or ctx.author.id == int(config.get('OWNER_ID'))
    return commands.check(predicate)


class AllowedUserOnly(CheckFailure):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'You are not on the allowed user list.')
