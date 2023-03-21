from helpers.file.utility import JsonFile

_models = JsonFile('models.json')


def get(key, default=None):
    """Get a model value."""
    return _models.get(key, default)


def add_model(key, value):
    """Add a model value."""
    _models[key] = value


def add_alias(model_id, alias):
    """Add an alias to a model."""
    if model_id not in _models:
        return

    if 'aliases' not in _models[model_id]:
        _models[model_id]['aliases'] = list()

    _models[model_id]['aliases'].append(alias)
    _models.save()


def save():
    """Save the models to disk."""
    _models.save()


def get_model_names():
    """Get a list of models."""
    return [x['name'] for x in _models]


def get_file():
    _models.fetch_file()
    return _models.file


def get_json():
    return _models.data


def get_models_aliases():
    model_list = []
    for current_model in _models:
        model_list.append(
            f"**{current_model['name']}** - aliases: `{', '.join(current_model['aliases'])}`"
        )
    return "\n".join(model_list)


def get_model_from_alias(alias):
    for index, current_model in enumerate(_models):
        if alias.lower() in current_model['aliases'] or alias.lower() == current_model['name'].lower():
            return index
    return None


def get_raw():
    return _models
