import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from apikeys import guild_ids

class hello(commands.Cog):

    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name= "hello", description= "Say hello to Mihono Bourbot", guild_ids= guild_ids)
    async def hello(self, interaction: Interaction):
        await interaction.response.send_message(file= nextcord.File('images/Gundam.png'))

def setup(client):
    client.add_cog(hello(client))
