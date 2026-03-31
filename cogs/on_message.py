import database
import discord
import json
import os
import random
from discord.ext import commands
from discord import Interaction
from apikeys import guild_ids

class on_message(commands.Cog):
    def __init__(self, client):
        self.client = client

    @discord.slash_command("set_memes_channel", guild_ids= guild_ids)
    async def set_memes_channel(self, interaction: Interaction):
        if interaction.user.guild_permissions.manage_guild:
            server = database.get_server(interaction.guild.id)
            server.memes_channel = interaction.channel_id
            await interaction.response.send_message("Saved as memes channel")
        else:
            await interaction.response.send_message("You do not have permission to run this command!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        reactionImages = os.listdir('images/replies')
        server = database.get_server(message.guild.id)
        if message.author != self.client.user and message.channel.id == server.memes_channel and (int) (random.random() * 25) == 0:
            await message.reply(file = discord.File(
                'images/replies/' + reactionImages[(int) (random.random() * len(reactionImages))]))
                
def setup(client):
    client.add_cog(on_message(client))