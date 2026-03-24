import asyncio
import nextcord
from nextcord.ext import commands
from nextcord import Interaction
from nextcord import FFmpegPCMAudio
from apikeys import guild_ids

class join(commands.Cog):

    def __init__(self, client):
        self.client = client

    @nextcord.slash_command(name= "join", description = "Have Mihono Bourbot join your voice channel", guild_ids= guild_ids)
    async def join(self, interaction: Interaction):
        await interaction.response.defer(ephemeral= True) 
        if interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
            await interaction.followup.send("Joined!")
        else:
            await interaction.followup.send("You are not in a voice channel!")

def setup(client):
    client.add_cog(join(client))