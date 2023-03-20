# JourneyBot
A discord bot for all your synthography needs.

---

## Overview
This bot is designed to be used with the [RunPod](https://runpod.io) API, this bot is not affiliated with RunPod in any way.
This bot started and will continue to be a passion project. I am fairly new to Discord.py but not Python,
so if you see any issues or have any suggestions, please feel free to open an issue or pull request.

---

## Setup
1. Clone the repository
2. Install the dependencies with `pip install -r requirements.txt`
3. Generate a database file (using sqlite3) and paste in the tables from the .schema file
4. Edit the config file to your liking, an example is provided below
```json
{
	"DISCORD_TOKEN": "<YOUR BOT DISCORD TOKEN>",
	"RUNPOD_KEY": "<YOUR RUNPOD API KEY>",
	"OWNER_ID": 104244519838416896,
	"DATABASE_FILE": "database.sqlite3"
}
```
5. Make an `allowed_users.txt` file, and add the IDs of the users you want to be able to use the bot, this file works in the format of:
```
<USER_ID>
<USER_ID>
<USER_ID>
...
```
6. Run the bot with `python main.py`
7. Invite the bot to your server with the link provided in the console
8. Enjoy!
