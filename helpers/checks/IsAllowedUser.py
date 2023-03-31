from typing import Optional

from discord.ext import commands
from discord.ext.commands import CheckFailure, Context

from helpers.checks.IsOwnerId import is_owner_user
from helpers.database import allow_list


def is_allowed_user(user_id):
    return allow_list.is_user_allowed(user_id) or is_owner_user(user_id)


def is_allowed(ctx: Context):
    if not is_allowed_user(ctx.author.id):
        raise AllowedUsersOnly()
    return True


def allowed_check():
    def predicate(ctx):
        return is_allowed(ctx)
    return commands.check(predicate)


class AllowedUsersOnly(CheckFailure):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'You are not on the allowed user list.')
