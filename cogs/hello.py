import discord
from discord.ext import commands
from discord import app_commands, Interaction
from apikeys import guild_ids

class Hello(commands.Cog):

    def __init__(self, client):
        self.client = client

    @app_commands.command(name= "hello", description= "Say hello to Mihono Bourbot")
    async def hello(self, interaction: Interaction):
        await interaction.response.send_message(file= discord.File('images/Gundam.png'))

async def setup(client):
    await client.add_cog(Hello(client))
