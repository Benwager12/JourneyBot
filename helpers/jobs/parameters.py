import json

from helpers.checks import HasOwnRunpodKey
from helpers.database import user_settings
from helpers.jobs import prompt


def make_params(user_id, use_prompt) -> dict:
    width = user_settings.get(user_id, "width")
    if width is None:
        width = 512

    height = user_settings.get(user_id, "height")
    if height is None:
        height = 512

    model_id = user_settings.get(user_id, "model_id")
    negative_prompts = user_settings.get(user_id, "negative_prompt")

    if negative_prompts is None:
        negative_prompt = ""
    else:
        negative_prompt = json.loads(negative_prompts).get(str(model_id), "")

    settings_output = {
        "prompt": use_prompt,
        "width": width,
        "height": height,
        "negative_prompt": negative_prompt
    }

    output_prompt, prompt_overrides = prompt.parse(
        use_prompt,
        ["width", "height", "negative", "model", "steps", "batch"]
    )

    if 'negative' in prompt_overrides:
        prompt_overrides['negative_prompt'] = prompt_overrides['negative']
        del prompt_overrides['negative']

    if 'batch' in prompt_overrides and isinstance(prompt_overrides['batch'], int):
        prompt_overrides['num_outputs'] = min(10, max(prompt_overrides['batch'], 1))
        del prompt_overrides['batch']

    if 'steps' in prompt_overrides and isinstance(prompt_overrides['steps'], int):
        prompt_overrides['num_inference_steps'] = min(100, max(prompt_overrides['steps'], 20))\
            if HasOwnRunpodKey.has_own_runpod_key(user_id) is None else min(499, max(prompt_overrides['steps'], 20))
        del prompt_overrides['steps']

    prompt_overrides['prompt'] = output_prompt

    final_params = {**settings_output, **prompt_overrides}

    for dim in ["width", "height"]:
        if final_params[dim] not in [128, 256, 384, 448, 512, 576, 640, 704, 768]:
            final_params[dim] = 512

    if final_params['negative_prompt'] == "":
        del final_params['negative_prompt']

    return {
        "input": final_params
    }
