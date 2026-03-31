import discord
from discord.ext import commands
from discord import Interaction
from apikeys import guild_ids

class leave(commands.Cog):

    def __init__(self, client):
        self.client = client

    @discord.slash_command(name= "leave", description= "Have Mihono Bourbot leave the voice channel", guild_ids= guild_ids)
    async def leave(self, interaction: Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Left!", ephemeral= True)
        else:
            await interaction.response.send_message("I am not in a voice channel!", ephemeral= True)

def setup(client):
    client.add_cog(leave(client))