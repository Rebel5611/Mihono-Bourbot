import discord
import requests
from discord.ext import commands
from discord import Interaction
from apikeys import guild_ids

class terraria(commands.Cog):

    def __init__(self, client):
        self.client = client

    @discord.slash_command(name= "terraria", guild_ids= guild_ids)
    async def terraria(self, interaction: Interaction):
        pass
    
    @terraria.subcommand(name="get_server_address", description = "Get the address to join the Terraria server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Terraria")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.send(f"The address for the Terraria world is:\n\tAddress: {ip}\n\tPort: 56111", ephemeral=True)
        else:
            await interaction.send("You do not have access to this server.", ephemeral=True)

def setup(client):
    client.add_cog(terraria(client))
