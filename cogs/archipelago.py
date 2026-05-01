from archipelago_instance import ArchipelagoInstance
import database
import discord
import docker
import glob
import os
import requests
import zipfile
from websockets.protocol import State
from discord.ext import commands
from discord import app_commands, Interaction

class Archipelago(commands.Cog):
    archipelago = app_commands.Group(name="archipelago", description="Commands related to Archipelago")
    bounty_board = app_commands.Group(name="bounty_board", description="Commands related to the Archipelago bounty board", parent=archipelago)
    server = app_commands.Group(name="server", description="Commands related to the Archipelago server", parent=archipelago)
    
    def __init__(self, client):
        self.client = client
        self.docker_client = docker.from_env()
        
        self.archipelago_instances: dict[int, ArchipelagoInstance] = {}
    
    @archipelago.command(name="get_server_address", description = "Get the address to join the Archipelago server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Archipelago")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.send(f"The address for the Archipelago game is: {ip}:56112", ephemeral=True)
        else:
            await interaction.send("You do not have access to this server.", ephemeral=True)

    @archipelago.command(name="set_reporting_channel", description = "Set the current channel as the Archipelago reporting channel")
    async def set_reporting_channel(self, interaction: Interaction):
        if interaction.user.guild_permissions.manage_guild:
            server = database.get_server(interaction.guild.id)
            server.reporting_channel = interaction.channel_id
            database.commit()
            await interaction.response.send_message("Saved as reporting channel")
        else:
            await interaction.response.send_message("You do not have permission to run this command!", ephemeral=True)
            
    @archipelago.command(name="set_server_password", description = "Sets the password used to log in to the Archipelago server")
    async def set_reporting_channel(self, interaction: Interaction, archipelago_password: str):
        if interaction.user.guild_permissions.manage_guild:
            server = database.get_server(interaction.guild.id)
            server.archipelago_password = archipelago_password
            database.commit()
            await interaction.response.send_message(f"Saved {archipelago_password} as the server's password", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to run this command!", ephemeral=True)
    
    @archipelago.command(name="set_alias", description = "Set your Archipelago alias")
    async def set_alias(self, interaction: Interaction, alias: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        user.archipelago_alias = alias
        database.commit()
        await interaction.response.send_message(f"Saved '{alias}' as your Archipelago alias", ephemeral=True)

    @archipelago.command(name="upload_yamls", description = "Upload yamls to use for generating a new Archipelago game")
    async def upload_yamls(self, interaction: Interaction, attachment: discord.Attachment):
        name, extension = os.path.splitext(attachment.filename)
        if extension.lower() == ".zip":
            files = glob.glob('/server/archipelago/serverdata/Players/*')
            for f in files:
                os.remove(f)
    
            await attachment.save(fp=attachment.filename)

            with zipfile.ZipFile(attachment.filename, 'r') as zip_ref:
                zip_ref.extractall("/server/archipelago/serverdata/Players/")
                
            os.remove(attachment.filename)
            await interaction.response.send_message("Files saved!", ephemeral=True)
        elif extension.lower() == ".yaml":
            files = glob.glob('/server/archipelago/serverdata/Players/*')
            for f in files:
                os.remove(f)
    
            await attachment.save(fp='/server/archipelago/serverdata/Players/' + attachment.filename)
            await interaction.response.send_message("File saved!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid file type! Please upload a .zip file or a single .yaml", ephemeral=True)

    @archipelago.command(name="generate_game", description = "Generate a new Archipelago game")
    async def generate_game(self, interaction: Interaction):
        await interaction.response.defer()
        files = glob.glob('/server/archipelago/serverdata/output/*')
        for f in files:
            os.remove(f)
        self.docker_client.images.build(path="/server/archipelago/", dockerfile="Generate", tag="archipelago-generate", rm=True)
        
        try:
            prev_container = self.docker_client.containers.get("archipelago-generate")
            prev_container.remove(force=True)
        except docker.errors.NotFound:
            print("No old container found, proceeding...")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        
        result = self.docker_client.containers.run("archipelago-generate", name="archipelago-generate", remove=True, detach=True, volumes=["/home/rebel5611/mihono_bourbot/serverdata/archipelago/serverdata:/server"]).wait()
        if result['StatusCode'] == 0:
            output_filepath = glob.glob('/server/archipelago/serverdata/output/*')[0]
            await interaction.followup.send("Multiworld generated", file=discord.File(output_filepath))
            
            with zipfile.ZipFile(output_filepath, 'r') as zip_ref:
                zip_ref.extractall("/server/archipelago/serverdata/output/")
            files = glob.glob('/server/archipelago/serverdata/output/*')
            for f in files:
                name, extension = os.path.splitext(f)
                if extension.lower() == ".archipelago":
                    os.rename(f, "/server/archipelago/serverdata/output/server.archipelago")
                else:
                    os.remove(f)
                    
            server = database.get_server(interaction.guild.id)
            server.players.clear()
            server.games.clear()
            database.commit()
        else:
            await interaction.followup.send("Multiworld generation failed")

    @bounty_board.command(name= "add_bounty", description = "Add a bounty for one of your Archipelago items")
    async def add_bounty(self, interaction: Interaction, item_name: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        if player := database.get_player_by_user(user):
            if item := database.get_item_by_name(player, item_name):
                if not database.get_bounty(player, item):
                    database.create_bounty(player, item)
                    database.commit()
                    await interaction.response.send_message(f"Bounty added for {interaction.user.mention}'s {item_name}!")
                else:
                    await interaction.response.send_message(f"Bounty already exists for your {item_name}", ephemeral=True)
            else:
                await interaction.response.send_message(f"No such item '{item_name}' exists in your game.\n"
                                                    "The item name may be different in the randomizer.", ephemeral=True)
        else:
            await interaction.response.send_message("No player found. Either your alias is incorrect, or I haven't connected to the server", ephemeral=True)
    
    @bounty_board.command(name= "remove_bounty", description = "Remove one of your Archipelago bounties")
    async def remove_bounty(self, interaction: Interaction, item_name: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        if (player := database.get_player_by_user(user)) and (item := database.get_item_by_name(player, item_name)) and (bounty := database.get_bounty(player, item)):
            player.bounties.remove(bounty)
            database.commit()
            await interaction.response.send_message(f"Bounty for {interaction.user.mention}'s {item_name} removed!")
            return
        await interaction.response.send_message(f"No bounty for item '{item_name}' exists", ephemeral=True)

    @bounty_board.command(name= "get_bounties", description = "Get the current Archipelago bounties")
    async def get_bounties(self, interaction: Interaction):
        server = database.get_server(interaction.guild.id)
        player_tuples = [(user, player) for user in server.users if (player := database.get_player_by_user(user))]
        for player_tuple in player_tuples:
            if len(player_tuple[1].bounties) > 0:
                bounties += f"{player_tuple[0].user_id}:\n"
                for bounty in player_tuple[1].bounties:
                    bounties += f"\t{bounty.item.item_name}\n"
        bounties = bounties.strip()
        if bounties != '':
            await interaction.response.send_message(f"The current bounties are:\n{bounties}")
        else:
            await interaction.response.send_message("There are no current bounties!")

    @server.command(name="start", description = "Start the Archipelago server")
    async def start(self, interaction: Interaction):
        await interaction.response.defer()
        
        if len(glob.glob('/server/archipelago/serverdata/output/*')) == 0:
            await interaction.followup.send("No game found. Upload your yamls with /archipelago upload_yamls and then generate one with /archipelago generate_game")
        elif interaction.guild.id in self.archipelago_instances.keys() and self.archipelago_instances[interaction.guild.id].check_server_status():
            await interaction.followup.send("A server is already running. Please stop it first with /archipelago server stop")
        else:
            try:
                prev_container = self.docker_client.containers.get("archipelago-run")
                prev_container.remove(force=True)
            except docker.errors.NotFound:
                print("No old container found, proceeding...")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            
            self.docker_client.images.build(path="/server/archipelago/", dockerfile="Run", tag="archipelago-run", rm=True)
            self.archipelago_instances[interaction.guild.id] = ArchipelagoInstance(server_id=interaction.guild.id, discord_client=self.client, docker_client=self.docker_client)
            self.archipelago_instances[interaction.guild.id].start_server()
            await interaction.followup.send("Server started")
            
    @server.command(name="stop", description = "Stop the Archipelago server")
    async def stop(self, interaction: Interaction):
        await interaction.response.defer()
        
        instance = self.archipelago_instances[interaction.guild.id]
        if not instance or not instance.check_server_status():
            await interaction.followup.send("There is no running server")
        else:
            instance.disconnected_intentionally = True
            if instance.autoreconnect_task:
                instance.autoreconnect_task.cancel()
                instance.autoreconnect_task = None
            if instance.socket and instance.socket.state is not State.CLOSED:
                await instance.socket.close()
            if instance.archipelago_client:
                await instance.archipelago_client
                
            instance.server.stop()
            await interaction.followup.send("Server stopped")

async def setup(client):
    await client.add_cog(Archipelago(client))
