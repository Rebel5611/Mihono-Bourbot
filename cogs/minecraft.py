import discord
import requests
from discord.ext import commands
from discord import app_commands, Interaction
from apikeys import guild_ids

class Minecraft(commands.Cog):
    minecraft = app_commands.Group(name="minecraft", description="Commands related to Minecraft")

    def __init__(self, client):
        self.client = client

    @minecraft.command(name="get_server_address", description = "Get the address to join the Minecraft server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Minecraft")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.send(f"The address for the Minecraft world is: {ip}:56110", ephemeral=True)
        else:
            await interaction.send("You do not have access to this server.", ephemeral=True)

async def setup(client):
    await client.add_cog(Minecraft(client))
