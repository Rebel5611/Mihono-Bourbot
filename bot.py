import discord
from discord.ext import commands
import os
from apikeys import *

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='/', intents=intents)

@client.event
async def on_ready():
    print("Ready")

initial_extensions = []
for filename in os.listdir('cogs'):
    if filename.endswith('.py'):
        initial_extensions.append("cogs." + filename[:-3])

if __name__ == '__main__':
    client.load_extensions(initial_extensions)

client.run(BOTTOKEN)