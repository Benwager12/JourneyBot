from helpers.file.utility import File

_allowed_users = File('allowed_users.txt')


def get():
    """Get the allowed users list."""

    return [int(usr) for usr in (iter(_allowed_users)) if usr.isdigit()]


def add(user_id: int):
    """Add a user to the allowed users list."""
    if user_id in get():
        return False
    _allowed_users.add_line(str(user_id))
    return True


def remove(user_id):
    """Remove a user from the allowed users list."""
    with open(_allowed_users.filename) as file:
        lines = file.readlines()
    if not (str(user_id) + '\n' in lines or str(user_id) in lines):
        return False

    lines = [line for line in lines if line != str(user_id) + '\n' and line != str(user_id)]
    if lines[-1].endswith('\n'):
        lines[-1] = lines[-1][:-1]
    with open(_allowed_users.filename, 'w') as file:
        file.writelines(lines)
    return True
