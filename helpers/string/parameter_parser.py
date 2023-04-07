import json
import re

import discord

from helpers.checks.HasOwnRunpodKey import has_own_runpod_key
from helpers.database import user_settings


def replace_aliases(string: str, parameters: dict):
	for parameter_name, parameter_data in parameters.items():
		if 'aliases' not in parameter_data:
			continue

		aliases = [f"--{alias}" for alias in parameter_data['aliases']]
		for index, word in enumerate(string.split()):
			if word in aliases:
				string = string.replace(word, f"--{parameter_name}")
	return string


regex_pattern = r'".*"'


def parse(string: str, parameters: dict) -> (str, dict):
	string = replace_aliases(string, parameters)
	output = dict()
	for index, (parameter_name, parameter_value) in enumerate(parameters.items()):
		match = re.search(f" --{parameter_name} (\"[^\"]*\"|\S+)", string)

		if not match:
			continue

		if match.group(1).startswith("\"") and match.group(1).endswith("\""):
			output[parameter_name] = match.group(1)[1:-1]
		else:
			output[parameter_name] = match.group(1)
		string = string.replace(match.group(0), "")

		if output[parameter_name].isdigit():
			output[parameter_name] = int(output[parameter_name])

	return string, output


def parse_image_prompt(string: str, user_id: int) -> (str, dict, str):
	with open("parameters.json", "r") as f:
		parameters_json = json.loads(f.read())
		prompt, params = parse(string, parameters_json)

	old_params = [("model_id", 0), ("width", 512), ("height", 512)]
	for param, default in old_params:
		if param not in params:
			params[param] = user_settings.get_default(user_id, param, default)

	negative_prompt = user_settings.get(user_id, "negative_prompt")
	if 'negative_prompt' not in params and negative_prompt is not None:
		if str(params['model_id']) in json.loads(negative_prompt):
			params['negative_prompt'] = json.loads(negative_prompt)[str(params['model_id'])]

	if not has_own_runpod_key(user_id):
		param_limiter(parameters_json, params)

	model = params['model_id']
	del params['model_id']
	params['prompt'] = prompt

	return params, model


def param_limiter(parameters_json, params):
	for param_name, param_data in params.items():
		print(param_name, param_data)
		print
		if 'bounds' not in parameters_json[param_name]:
			continue

		if 'bound_type' not in parameters_json[param_name]:
			parameters_json[param_name]['bound_type'] = 'within'

		if parameters_json[param_name]['bound_type'] == 'within':
			if parameters_json[param_name]['bounds'][0] <= param_data <= parameters_json[param_name]['bounds'][1]:
				params[param_name] = param_data
			else:
				params[param_name] = max(parameters_json[param_name]['bounds'][0],
										 min(parameters_json[param_name]['bounds'][1],
											 params.get(param_name)))
