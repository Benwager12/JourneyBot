import os

from helpers.file.utility import JsonFile

_config = JsonFile('config.json')


def get(key, default=None):
    """Get a config value."""
    if not _config.file_exists():
        return os.getenv(key, default)
    return _config.get(key, default)


def get_file():
    if not _config.file_exists():
        return None

    return _config.fetch_file()


def get_json():
    if not _config.file_exists():
        return None
    return _config.data


def set(key, value):
    """Set a config value."""
    if not _config.file_exists():
        os.environ[key] = value
    _config.set(key, value)


def save():
    """Save the config to disk."""
    if not _config.file_exists():
        return
    _config.save()
    _config.fetch_file()


def file_exists():
    return _config.file_exists()
