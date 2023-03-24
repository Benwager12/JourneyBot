from typing import Optional

from discord.ext import commands
from discord.ext.commands import CheckFailure, Context

from helpers.checks import IsOwnerId
from helpers.database import user_settings


def has_own_runpod_key(user_id):
    return user_settings.get(user_id, "runpod_key") is not None or IsOwnerId.is_owner_user(user_id)


def has_runpod_key(ctx: Context):
    if not has_own_runpod_key(ctx.author.id):
        raise UserNoIndividualRunpod()
    return True


def runpod_key_check():
    def predicate(ctx):
        return has_own_runpod_key(ctx)
    return commands.check(predicate)


class UserNoIndividualRunpod(CheckFailure):
    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'You do not have your own runpod key.')
