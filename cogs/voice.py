import asyncio
import discord
from discord.ext import commands
from discord import app_commands, Interaction, FFmpegPCMAudio
from apikeys import guild_ids

class Voice(commands.Cog):
    voice = app_commands.Group(name="voice", description="Commands related to voice channels")

    def __init__(self, client):
        self.client = client

    @voice.command(name= "join", description = "Have Mihono Bourbot join your voice channel")
    async def join(self, interaction: Interaction):
        await interaction.response.defer(ephemeral= True) 
        if interaction.user.voice:
            voice_client = await interaction.user.voice.channel.connect()
            await interaction.followup.send("Joined!")
        else:
            await interaction.followup.send("You are not in a voice channel!")
            
    @voice.command(name= "leave", description= "Have Mihono Bourbot leave the voice channel")
    async def leave(self, interaction: Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("Left!", ephemeral= True)
        else:
            await interaction.response.send_message("I am not in a voice channel!", ephemeral= True)

async def setup(client):
    await client.add_cog(Voice(client))