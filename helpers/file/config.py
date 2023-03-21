from helpers.file.utility import JsonFile

_config = JsonFile('config.json')


def get(key, default=None):
    """Get a config value."""
    return _config.get(key, default)


def get_file():
    _config.fetch_file()
    return _config.file


def get_json():
    return _config.data


def set(key, value):
    """Set a config value."""
    _config.set(key, value)


def save():
    """Save the config to disk."""
    _config.save()
    _config.fetch_file()
