import discord
import requests
from discord.ext import commands
from discord import app_commands, Interaction

class Hytale(commands.Cog):
    hytale = app_commands.Group(name="hytale", description="Commands related to Hytale")

    def __init__(self, client):
        self.client = client

    @hytale.command(name="get_server_address", description="Get the address to join the Hytale server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Hytale")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.response.send_message(f"The address for the Hytale world is: {ip}:56112", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have access to this server.", ephemeral=True)

async def setup(client):
    await client.add_cog(Hytale(client))
