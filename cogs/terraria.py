import discord
import requests
from discord.ext import commands
from discord import app_commands, Interaction

class Terraria(commands.Cog):
    terraria = app_commands.Group(name="terraria", description="Commands related to Terraria")

    def __init__(self, client):
        self.client = client
    
    @terraria.command(name="get_server_address", description="Get the address to join the Terraria server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Terraria")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.response.send_message(f"The address for the Terraria world is:\n\tAddress: {ip}\n\tPort: 56111", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have access to this server.", ephemeral=True)

async def setup(client):
    await client.add_cog(Terraria(client))
