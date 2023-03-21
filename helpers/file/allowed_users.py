from helpers.file.utility import File

_allowed_users = File('allowed_users.txt')


def get():
    """Get the allowed users list."""
    return list(iter(_allowed_users))


def add(user_id):
    """Add a user to the allowed users list."""
    _allowed_users.add_line(user_id)


def is_allowed(user_id):
    """Check if a user is allowed."""
    return user_id in _allowed_users

