from typing import Optional

from discord.ext import commands
from discord.ext.commands import Context, CheckFailure

from helpers.file import config


def is_owner_user(user_id):
    return user_id == int(config.get('OWNER_ID'))


def is_owner(ctx: Context):
    if not is_owner_user(ctx.author.id):
        raise OwnerOnly()
    return True


def owner_check():
    def predicate(ctx):
        return is_owner(ctx)
    return commands.check(predicate)


class OwnerOnly(CheckFailure):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'You have to be the owner to execute this command.')
