import nextcord
import requests
from nextcord.ext import commands
from nextcord import Interaction
from apikeys import guild_ids

class minecraft(commands.Cog):

    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name= "minecraft", guild_ids= guild_ids)
    async def minecraft(self, interaction: Interaction):
        pass
    
    @minecraft.subcommand(name="get_server_address", description = "Get the address to join the Minecraft server")
    async def get_server_address(self, interaction: Interaction):
        role = nextcord.utils.get(interaction.guild.roles, name="Minecraft")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.send(f"The address for the Minecraft world is: {ip}:56110", ephemeral=True)
        else:
            await interaction.send("You do not have access to this server.", ephemeral=True)

def setup(client):
    client.add_cog(minecraft(client))
