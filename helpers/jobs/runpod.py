import asyncio
import json
import os

import requests
from discord import Message, User

from helpers.database import images, user_settings
from helpers.file import models, config

BASE_URL = "https://api.runpod.ai/v1"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {config.get('RUNPOD_KEY', 'NO_KEY')}"
}


def make_job(params, user_id) -> int:
    user_model = user_settings.get_default(user_id, "model_id", 0)
    run_url = f"{BASE_URL}/{models.get(user_model)['endpoint_id']}/run"
    user_runpod = user_settings.get(user_id, "runpod_key")
    this_headers = headers.copy()
    if user_runpod:
        this_headers['Authorization'] = f"Bearer {user_runpod}"

    print(this_headers)

    response = requests.post(run_url, headers=this_headers, json=params)
    response_json = response.json()
    print(response_json)
    return response_json['id']


def get_job_status(job_id, user_id) -> (int, str):
    user_model = user_settings.get_default(user_id, "model_id", 0)

    status_url = f"{BASE_URL}/{models.get(user_model)['endpoint_id']}/status/{job_id}"

    this_headers = headers.copy()

    user_runpod = user_settings.get(user_id, "runpod_key")
    if user_runpod:
        this_headers['Authorization'] = f"Bearer {user_runpod}"

    response = requests.post(status_url, headers=this_headers)

    print(response.text)
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

    if len(output) > 1:
        os.mkdir(f"images/{job_id}")
        for index, image in enumerate(output):
            image_url = image['image']
            r = requests.get(image_url)

            with open(f"images/{job_id}/{index}.png", "wb") as f:
                f.write(r.content)
    else:
        image_url = output[0]['image']
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

    job_id = make_job(params, author.id)
    output, message = await wait_job(message, job_id, author.id)

    for image in output:
        images.insert_image(job_id, image['seed'], params, author.id, model_id)
    return job_id


def get_job_id_from_task(task):
    ids = []
    for t in task:
        for ti in t:
            ids.append(ti.result())
    return ids

def job_location(job_id):
    if os.path.isdir(f"images/{job_id}"):
        return [f"images/{job_id}/{file}" for file in os.listdir(f"images/{job_id}")]
    else:
        return [f"images/{job_id}.png"]
