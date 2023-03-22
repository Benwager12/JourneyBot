from discord import Message


def parse(prompt: str, argument_list=None):
    if argument_list is None:
        argument_list = []

    tokens = []
    token_index = 0
    in_quotes = False
    parameter_locations = []

    for c in prompt:
        if len(tokens) == token_index:
            tokens.append("")

        if c == " " and not in_quotes:
            token_index += 1
            continue

        if c == "\"":
            in_quotes = not in_quotes
            continue

        if tokens[token_index] == "--" or tokens[token_index] == "—":
            parameter_locations.append(token_index)
            token_index += 1

        if len(tokens) == token_index:
            tokens.append("")

        tokens[token_index] += c

    parameters = {}

    for x in parameter_locations:
        if tokens[x + 1] in argument_list:
            parameters[tokens[x + 1]] = tokens[x + 2]

    for x in reversed(parameter_locations):
        if tokens[x + 1] in argument_list:
            for i in reversed(range(0, 3)):
                del tokens[x + i]

    index = 0
    while index < len(tokens):
        dash_chars = ['-', '—']
        for dash in dash_chars:
            if tokens[index] == dash:
                del tokens[index]
                tokens[index] = dash + tokens[index]
        index += 1

    for key, value in parameters.items():
        if value.lower() == "true":
            parameters[key] = True
        elif value.lower() == "false":
            parameters[key] = False
        elif value.isnumeric():
            parameters[key] = int(value)

    return " ".join(tokens), parameters


def parse_replace(prompt):
    arglist = []
    argindex = 0
    in_quotes = False
    parameter_locations = []

    for c in prompt:
        if len(arglist) == argindex:
            arglist.append("")

        if c == " " and not in_quotes:
            argindex += 1
            continue

        if arglist[argindex] == "[":
            parameter_locations.append(argindex)
            in_quotes = True

        if arglist[argindex] == "]":
            argindex += 1
            in_quotes = False
            continue

        if len(arglist) == argindex:
            arglist.append("")

        arglist[argindex] += c

    parameters = []

    for x in reversed(parameter_locations):
        param = arglist[x]

        if '=' not in param or param.count('=') > 1:
            continue
        parameters.append(param)
        del arglist[x]

    replacements = dict()

    for x in parameters:
        key, value = x[1:-1].split('=')
        replacements[key] = value
    return replacements

async def add_reaction_emojis(message: Message, emojis: list):
    for emoji in emojis:
        await message.add_reaction(emoji)


async def add_reaction_emojis_image(message: Message):
    await add_reaction_emojis(message, ["♻", "❌", "🅿"])


async def add_reaction_emojis_page(message: Message):
    await add_reaction_emojis(message, ["⏮", "⏭"])
