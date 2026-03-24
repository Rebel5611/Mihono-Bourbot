import json
import nextcord
import os
import random
from nextcord.ext import commands
from nextcord import Interaction
from apikeys import guild_ids

class on_message(commands.Cog):
    def __init__(self, client):
        self.client = client

        if not os.path.isfile("bot_data.json"):
            with open("bot_data.json", "w") as f:
                json.dump(dict({}), f)

        with open("bot_data.json", "r") as f:
            self.bot_data = json.load(f)
        if "memes_channel" not in self.bot_data.keys():
            self.bot_data["memes_channel"] = ''

    @nextcord.slash_command("set_memes_channel", guild_ids= guild_ids)
    async def set_memes_channel(self, interaction: Interaction):
        if interaction.user.guild_permissions.manage_guild:
            with open("bot_data.json", "r") as f:
                self.bot_data = json.load(f)
            self.bot_data["memes_channel"] = interaction.channel_id
            with open("bot_data.json", 'w') as f:
                json.dump(self.bot_data, f, indent=2)
            await interaction.response.send_message("Saved as memes channel")
        else:
            await interaction.response.send_message("You do not have permission to run this command!")

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        reactionImages = os.listdir('images/replies')
        if message.author != self.client.user and message.channel.id == self.bot_data["memes_channel"] and (int) (random.random() * 25) == 0:
            await message.reply(file = nextcord.File(
                'images/replies/' + reactionImages[(int) (random.random() * len(reactionImages))]))
                
def setup(client):
    client.add_cog(on_message(client))