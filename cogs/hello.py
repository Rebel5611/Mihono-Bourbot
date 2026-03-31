import discord
from discord.ext import commands
from discord import Interaction
from apikeys import guild_ids

class hello(commands.Cog):

    def __init__(self, client):
        self.client = client

    @discord.slash_command(name= "hello", description= "Say hello to Mihono Bourbot", guild_ids= guild_ids)
    async def hello(self, interaction: Interaction):
        await interaction.response.send_message(file= discord.File('images/Gundam.png'))

def setup(client):
    client.add_cog(hello(client))
