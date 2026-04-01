import discord
import os
from apikeys import *
from discord.ext import commands

class MihonoBourbot(commands.Bot):
    async def setup_hook(self):
        for filename in os.listdir("cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                await self.load_extension(f"cogs.{filename[:-3]}")

intents = discord.Intents.default()
intents.message_content = True

client = MihonoBourbot(command_prefix="/", intents=intents)

@client.event
async def on_ready():
    for guild_id in guild_ids:
        guild = discord.Object(id=guild_id)
        try:
            client.tree.copy_global_to(guild=guild)
            await client.tree.sync(guild=guild)
            print(f"Synced commands to guild {guild_id}")
        except discord.Forbidden:
            print(f"Skipping guild {guild_id} (not in server or missing access)")
    print("Ready")

client.run(BOTTOKEN)