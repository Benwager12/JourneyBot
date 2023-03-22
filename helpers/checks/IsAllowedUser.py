from typing import Optional

from discord.ext.commands import CheckFailure, Context

from helpers.file import allowed_users, config


def is_allowed(ctx: Context):
    output = ctx.author.id in allowed_users.get() or ctx.author.id == int(config.get('OWNER_ID'))
    if not output:
        raise AllowedUsersOnly()
    return output


class AllowedUsersOnly(CheckFailure):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'You are not on the allowed user list.')
