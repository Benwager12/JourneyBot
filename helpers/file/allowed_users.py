from helpers.file.utility import File

_allowed_users = File('allowed_users.txt')


def get():
    """Get the allowed users list."""
    return [int(usr) for usr in (iter(_allowed_users))]


def add(user_id):
    """Add a user to the allowed users list."""
    _allowed_users.add_line(user_id)
