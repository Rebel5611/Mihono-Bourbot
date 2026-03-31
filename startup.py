import json
import os
import subprocess
import sys
from cogs.archipelago import Player

if not os.path.isfile("bot_data.json"):
    with open("bot_data.json", "w") as f:
        json.dump({}, f)

with open("bot_data.json", "r") as f:
    bot_data = json.load(f, cls=Player.Decoder)

with open("bot_data.json", "w+") as f:
    json.dump(bot_data, f, indent=2, cls=Player.Encoder)

subprocess.run(
    [sys.executable, "-u", "bot.py"],
    check=True
)