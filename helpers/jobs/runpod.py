import asyncio
import json

import requests
from discord import Message, User

from helpers.database import images
from helpers.file import models, config

BASE_URL = "https://api.runpod.ai/v1"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.get('RUNPOD_KEY', 'NO_KEY')}"
}

def make_job(params, user_model) -> int:
    run_url = f"{BASE_URL}/{models.get(user_model)['endpoint_id']}/run"
    response = requests.post(run_url, headers=headers, json=params)
    response_json = response.json()

    return response_json['id']

def get_job_status(job_id, user_model) -> (int, str):
    status_url = f"{BASE_URL}/{models.get(user_model)['endpoint_id']}/status/{job_id}"
    response = requests.post(status_url, headers=headers)

    response_json = response.json()

    if not response.status_code == 200:
        return 0, f"Error {response.status_code}"

    response_status = response_json['status']

    if response_status == "FAILED":
        return -1, response_json

    if response_status == "COMPLETED":
        return 1, response_json['output']

    if response_status == "IN_QUEUE":
        return 2, response_status

    if response_status == "IN_PROGRESS":
        return 3, response_status

    return 4, response_status


async def wait_job(message: Message, job_id: int, user_model: int):
    output = None
    message_beginning = message.content.split("\n")[0]
    if len(message_beginning.split("`")) < 4:
        job_ids = str(job_id)
    else:
        job_ids = message_beginning.split("`")[3]

    reference_message = await message.channel.fetch_message(message.reference.message_id)

    while output is None:
        await asyncio.sleep(5)
        code, response = get_job_status(job_id, user_model)

        match code:
            case 0:
                await message.edit(content=f"{message_beginning}\nHTTP request error!")
                return
            case 1:
                output = response
                await message.edit(content=f"{message_beginning.replace(job_ids, job_ids + ', ' + str(job_id))}"
                                           "\nImage has been generated, downloading...")
                print(f"Job {job_id} completed for user {reference_message.author} ({reference_message.id})")
                break
            case -1:
                await message.edit(content=f"{message_beginning}\nError: {response}")
                return
            case 2:
                await message.edit(content=f"{message_beginning}\nImage is in queue...")
                continue
            case 3:
                await message.edit(content=f"{message_beginning}\nImage is being generated...")
                continue

    for index, image in enumerate(output):
        image_url = image['image']
        r = requests.get(image_url)

        with open(f"images/{job_id}.png", "wb") as f:
            f.write(r.content)

    return output, message

async def create_image(params, model_id, message: Message, author: User):
    if "model" in params['input'].keys():
        new_model = models.get_model_from_alias(params['input']['model'])
        if new_model is not None:
            model_id = new_model
        del params['input']['model']

    print(f"User {author} ({author.id}) is creating an image with model {models.get(model_id)['name']} and prompt "
          f"\"{params['input']['prompt']}\".")

    job_id = make_job(params, model_id)
    output, message = await wait_job(message, job_id, model_id)

    for image in output:
        images.insert_image(job_id, image['seed'], params, author.id)
    return job_id


def get_job_ids_from_task(task):
    ids = []
    for t in task:
        for ti in t:
            ids.append(ti.result())
    return ids