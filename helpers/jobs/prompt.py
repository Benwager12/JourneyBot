
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

        if tokens[token_index] == "--":
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
        if tokens[index] == "--":
            del tokens[index]
            tokens[index] = "--" + tokens[index]
        index += 1

    for key, value in parameters.items():
        if value.lower() == "true":
            parameters[key] = True
        elif value.lower() == "false":
            parameters[key] = False
        elif value.isnumeric():
            parameters[key] = int(value)

    return " ".join(tokens), parameters
