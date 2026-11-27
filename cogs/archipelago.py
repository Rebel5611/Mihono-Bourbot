from archipelago_instance import ArchipelagoInstance
import asyncio
import database
import discord
import docker
import glob
import io
import os
import requests
import shutil
import zipfile
from websockets.protocol import State
from requests.exceptions import ReadTimeout, ConnectionError
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
        if role in interaction.user.roles and interaction.guild.id in self.archipelago_instances:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.response.send_message(f"The address for the Archipelago game is: {ip}:{self.archipelago_instances[interaction.guild.id].port}", ephemeral=True)
        elif interaction.guild.id not in self.archipelago_instances:
            await interaction.response.send_message("There is no running server.", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have access to this server.", ephemeral=True)

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
    async def set_server_password(self, interaction: Interaction, archipelago_password: str):
        if interaction.user.guild_permissions.manage_guild:
            server = database.get_server(interaction.guild.id)
            server.archipelago_password = archipelago_password
            database.commit()
            await interaction.response.send_message(f"Saved {archipelago_password} as the server's password", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have permission to run this command!", ephemeral=True)

    @archipelago.command(name="set_aliases", description = "Set your Archipelago aliases as a comma seperated list")
    async def set_aliases(self, interaction: Interaction, aliases: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        user.aliases = set([alias for raw_alias in aliases.split(',') if (alias := raw_alias.strip())])
        database.commit()
        await interaction.response.send_message(f"Saved!", ephemeral=True)

    @archipelago.command(name="add_aliases", description = "Add to your current Archipelago aliases with a comma seperated list")
    async def add_aliases(self, interaction: Interaction, aliases: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        user.aliases.extend(set([alias for raw_alias in aliases.split(',') if (alias := raw_alias.strip())]))
        user.aliases = set(user.aliases)
        database.commit()
        await interaction.response.send_message(f"Saved!", ephemeral=True)

    @archipelago.command(name="remove_aliases", description = "Remove Archipelago aliases with a comma seperated list")
    async def remove_aliases(self, interaction: Interaction, aliases: str):
        user = database.get_user(interaction.guild.id, interaction.user.id)
        for alias in set([alias for raw_alias in aliases.split(',') if (alias := raw_alias.strip())]):
            if alias in user.aliases:
                user.aliases.remove(alias)
        database.commit()
        await interaction.response.send_message(f"Saved!", ephemeral=True)

    @archipelago.command(name="upload_yamls", description = "Upload yamls to use when generating a new Archipelago game")
    async def upload_yamls(self, interaction: Interaction, attachment: discord.Attachment):
        name, extension = os.path.splitext(attachment.filename)
        if extension.lower() == ".zip":
            files = glob.glob(f"/server/archipelago/{interaction.guild.id}/Players/*")
            for f in files:
                os.remove(f)
    
            await attachment.save(fp=attachment.filename)

            with zipfile.ZipFile(attachment.filename, 'r') as zip_ref:
                zip_ref.extractall(f"/server/archipelago/{interaction.guild.id}/Players/")
                
            os.remove(attachment.filename)
            await interaction.response.send_message("Files saved!", ephemeral=True)
        elif extension.lower() == ".yaml":
            files = glob.glob(f"/server/archipelago/{interaction.guild.id}/Players/*")
            for f in files:
                os.remove(f)

            os.makedirs(f"/server/archipelago/{interaction.guild.id}/Players/", exist_ok=True)
            await attachment.save(fp=f"/server/archipelago/{interaction.guild.id}/Players/" + attachment.filename)
            await interaction.response.send_message("File saved!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid file type! Please upload a .zip file or a single .yaml", ephemeral=True)
            
    @archipelago.command(name="upload_apworlds", description = "Upload custom apworlds to use when generating a new Archipelago game")
    async def upload_apworlds(self, interaction: Interaction, attachment: discord.Attachment):
        name, extension = os.path.splitext(attachment.filename)
        if extension.lower() == ".zip":
            files = glob.glob(f"/server/archipelago/{interaction.guild.id}/Worlds/*")
            for f in files:
                os.remove(f)
    
            await attachment.save(fp=attachment.filename)

            with zipfile.ZipFile(attachment.filename, 'r') as zip_ref:
                zip_ref.extractall(f"/server/archipelago/{interaction.guild.id}/Worlds/")
                
            os.remove(attachment.filename)
            await interaction.response.send_message("Files saved!", ephemeral=True)
        elif extension.lower() == ".apworld":
            files = glob.glob(f"/server/archipelago/{interaction.guild.id}/Worlds/*")
            for f in files:
                os.remove(f)

            os.makedirs(f"/server/archipelago/{interaction.guild.id}/Worlds/", exist_ok=True)
            await attachment.save(fp=f"/server/archipelago/{interaction.guild.id}/Worlds/" + attachment.filename)
            await interaction.response.send_message("File saved!", ephemeral=True)
        else:
            await interaction.response.send_message("Invalid file type! Please upload a .zip file or a single .apworld", ephemeral=True)

    @archipelago.command(name="generate_game", description = "Generate a new Archipelago game")
    async def generate_game(self, interaction: Interaction):
        if interaction.guild.id in self.archipelago_instances and (instance := self.archipelago_instances[interaction.guild.id]) and instance.check_server_status():
            await interaction.response.send_message("There is a running server. Please stop the server before generating a new game.", ephemeral=True)
        else:
            await interaction.response.send_message("Generating game...")
            server_path = f"/server/archipelago/{interaction.guild.id}"
            files = glob.glob(f"{server_path}/output/*")
            for f in files:
                os.remove(f)
            
            
            os.makedirs(f"{server_path}/Players/", exist_ok=True)
            os.makedirs(f"{server_path}/Worlds/", exist_ok=True)
            shutil.copy2("/server/apworld/Mihono Bourbot.yaml", f"{server_path}/Players/")
            temp = shutil.make_archive(base_name=f"{server_path}/Worlds/mihonobourbot", format='zip', root_dir="/server/apworld", base_dir="mihonobourbot")
            os.rename(temp, f"{server_path}/Worlds/mihonobourbot.apworld")
            
            try:
                prev_container = self.docker_client.containers.get(f"archipelago-generate-{interaction.guild.id}")
                prev_container.remove(force=True)
            except docker.errors.NotFound:
                print("No old container found, proceeding...")
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
            
            
            result = await asyncio.to_thread(self.generate_multiworld, interaction.guild.id)
            
            if result['StatusCode'] == 0:
                output_filepath = glob.glob(f"{server_path}/output/*")[0]
        
                await interaction.channel.send("Multiworld generated", file=discord.File(output_filepath))
                
                with zipfile.ZipFile(output_filepath, 'r') as zip_ref:
                    zip_ref.extractall(f"{server_path}/output/")
                files = glob.glob(f"{server_path}/output/*")
                for f in files:
                    name, extension = os.path.splitext(f)
                    if extension.lower() == ".archipelago":
                        os.rename(f, f"{server_path}/output/server.archipelago")
                    else:
                        os.remove(f)
                        
                server = database.get_server(interaction.guild.id)
                server.players.clear()
                server.games.clear()
                database.commit()
            else:
                await interaction.channel.send("Multiworld generation failed")

    @bounty_board.command(name= "add_bounty", description = "Add a bounty for one of your Archipelago items")
    async def add_bounty(self, interaction: Interaction, item_name: str, alias: str | None, quantity: int=1, notify_on_each: bool=True):
        if alias:
            players = [database.get_player_by_alias(interaction.guild.id, alias)]
        else:
            players = database.get_players_by_user(database.get_user(interaction.guild.id, interaction.user.id))
        
        if players:
            result = self._add_bounty(item_name, players, quantity=quantity, notify_on_each=notify_on_each)
            await interaction.response.send_message(result[0].strip(), ephemeral=result[1])
        else:
            await interaction.response.send_message("No player found. Either your alias is incorrect, or I haven't connected to the server", ephemeral=True)

    @bounty_board.command(name= "add_bounties", description = "Add a bounty for one or more of your Archipelago items, as a comma seperated list")
    async def add_bounties(self, interaction: Interaction, item_names: str, aliases: str | None):
        if aliases:
            aliases = set([alias for raw_alias in aliases.split(',') if (alias := raw_alias.strip())])
            players = [database.get_player_by_alias(interaction.guild.id, alias) for alias in aliases]
        else:
            players = database.get_players_by_user(database.get_user(interaction.guild.id, interaction.user.id))
        
        if players:
            ephemeral = True
            response = ""
            item_names = set([item_name for raw_item_name in item_names.split(',') if (item_name := raw_item_name.strip())])
            for item_name in item_names:
                result = self._add_bounty(item_name, players)
                response += result[0]
                ephemeral = False if not result[1] else ephemeral
            await interaction.response.send_message(response.strip(), ephemeral=ephemeral)
        else:
            await interaction.response.send_message("No player found. Either your aliases are incorrect, or I haven't connected to the server", ephemeral=True)

    def _add_bounty(self, item_name: str, players: list[database.Player], quantity: int=1, notify_on_each: bool=True) -> tuple[str, bool]:
        player_items = []
        for player in players:
            if (item := database.get_item_by_name(player, item_name)):
                player_items.append((player, item))

        if len(player_items) == 0:
            return (f"No such item '{item_name}' exists in your game(s). The item name may be different in the randomizer.\n", True)
        elif len(player_items) > 1:
            return (f"More than 1 possible item found for item '{item_name}'. Use or modify the aliases argument to narrow your search.\n", True)
        else:
            player_item = player_items[0]
            if database.get_bounty(player_item[0], player_item[1]) is None:
                database.create_bounty(player_item[0], player_item[1], quantity, notify_on_each)
                database.commit()
                users = database.get_users_by_player(player_item[0])
                if users:
                    names = ", ".join([f"<@{user.user_id}>" for user in users])
                else:
                    names = player_item[0].archipelago_alias
                return (f"Bounty added for {names}'s {item_name}{f" ({quantity}x)" if quantity > 1 else ""}!\n", False)
            else:
                return (f"Bounty already exists for your {item_name}\n", True)

    @bounty_board.command(name= "remove_bounties", description = "Remove one or more of your Archipelago bounties, as a comma seperated list")
    async def remove_bounties(self, interaction: Interaction, item_names: str, aliases: str | None):
        if aliases:
            aliases = set([alias for raw_alias in aliases.split(',') if (alias := raw_alias.strip())])
            players = [database.get_player_by_alias(interaction.guild.id, alias) for alias in aliases]
        else:
            players = database.get_players_by_user(database.get_user(interaction.guild.id, interaction.user.id))
            
        if players:
            ephemeral = True
            response = ""
            item_names = set([item_name for raw_item_name in item_names.split(',') if (item_name := raw_item_name.strip())])
            for item_name in item_names:
                result = self._remove_bounty(item_name, players)
                response += result[0]
                ephemeral = False if not result[1] else ephemeral
            await interaction.response.send_message(response.strip(), ephemeral=ephemeral)
        else:
            await interaction.response.send_message("No player found. Either your aliases are incorrect, or I haven't connected to the server", ephemeral=True)

    def _remove_bounty(self, item_name: str, players: list[database.Player]) -> tuple[str, bool]:
        player_bounties = []
        for player in players:
            if (item := database.get_item_by_name(player, item_name)) and (bounty := database.get_bounty(player, item)):
                player_bounties.append((player, bounty))
        
        if len(player_bounties) == 0:
            return (f"No bounty for item '{item_name}' exists\n", True)
        elif len(player_bounties) > 1:
            return (f"More than 1 possible bounty found for item '{item_name}'. Use or modify the aliases argument to narrow your search.\n", True)
        else:
            player_bounty = player_bounties[0]
            player_bounty[0].bounties.remove(player_bounty[1])
            database.commit()
            return (f"Bounty for {", ".join([f"<@{user.user_id}>" for user in database.get_users_by_player(player_bounty[0])])}'s {item_name} removed!\n", False)


    @bounty_board.command(name= "show_bounties", description = "Get the current Archipelago bounties")
    async def show_bounties(self, interaction: Interaction):
        server = database.get_server(interaction.guild.id)
        bounties = ""
        
        for player in server.players:
            if player.bounties:
                if users := [f"<@{user.user_id}>" for user in database.get_users_by_player(player)]:
                    bounties += f"{", ".join(users)}'s {player.game_name}:\n"
                else:
                    bounties += f"{player.archipelago_alias}'s {player.game_name}:\n"

                for bounty in player.bounties:
                    bounties += f"\t\t{bounty.item.item_name}{f" ({bounty.quantity}x)" if bounty.quantity > 1 else ""}\n"
            
        bounties = bounties.strip()
        if bounties != '':
            await interaction.response.send_message(f"The current bounties are:\n{bounties}", ephemeral=True)
        else:
            await interaction.response.send_message("There are no current bounties!", ephemeral=True)
            
    @archipelago.command(name= "get_item_lists", description = "Get the list of item names for your game(s)")
    async def get_item_lists(self, interaction: Interaction, alias: str | None):
        await interaction.response.defer(ephemeral=True)
        server = database.get_server(interaction.guild.id)
        if alias:
            players = [database.get_player_by_alias(interaction.guild.id, alias)]
        else:
            players = database.get_players_by_user(database.get_user(interaction.guild.id, interaction.user.id))
        
        if len(players) == 1:
            game = database.get_game(server_id=server.server_id, game_name=players[0].game_name)
            content = "\n".join([item.item_name for item in game.items])
            outfile = discord.File(io.BytesIO(content.encode('utf-8')), filename=f"{players[0].game_name} Items.txt")
            await interaction.followup.send("Item list:", file=outfile, ephemeral=True)
        elif players:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for player in players:
                    game = database.get_game(server_id=server.server_id, game_name=player.game_name)
                    content = "\n".join([item.item_name for item in game.items])
                    zip_file.writestr(f"{player.game_name} Items.txt", content)
            zip_buffer.seek(0)
            outfile = discord.File(fp=zip_buffer, filename="Item Lists.zip")
            await interaction.followup.send("Item lists:", file=outfile, ephemeral=True)
        else:
            await interaction.followup.send("No player found. Either your alias is incorrect, or I haven't connected to the server", ephemeral=True)
            
    @server.command(name="start", description = "Start the Archipelago server")
    async def start(self, interaction: Interaction):
        await interaction.response.defer()
        
        if len(glob.glob(f"/server/archipelago/{interaction.guild.id}/output/*")) == 0:
            await interaction.followup.send("No game found. Upload your yamls with /archipelago upload_yamls and then generate one with /archipelago generate_game")
        elif interaction.guild.id in self.archipelago_instances.keys() and self.archipelago_instances[interaction.guild.id].check_server_status():
            await interaction.followup.send("A server is already running. Please stop it first with /archipelago server stop")
        elif interaction.guild.id not in self.archipelago_instances.keys():
            port = 56113
            open_port = False
            while not open_port:
                open_port = True
                for instance in self.archipelago_instances.values():
                    if instance.port == port:
                        open_port = False
                if not open_port:
                    port += 1
                    
            if port > 56119:
                await interaction.followup.send("There are no available ports.")
                return
            else:
                self.archipelago_instances[interaction.guild.id] = ArchipelagoInstance(server_id=interaction.guild.id, discord_client=self.client, port=port, docker_client=self.docker_client)

        self.archipelago_instances[interaction.guild.id].start_server()
        await interaction.followup.send("Server started")
            
    @server.command(name="stop", description = "Stop the Archipelago server")
    async def stop(self, interaction: Interaction):
        await interaction.response.defer()
         
        if not interaction.guild.id in self.archipelago_instances or not (instance := self.archipelago_instances[interaction.guild.id]) or not instance.check_server_status():
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

            socket = instance.server.attach_socket(params={'stdin': 1, 'stream': 1})
            socket._sock.sendall(b"/exit\n")
            socket.close()
            
            try:
                instance.server.wait(timeout=5)
            except (ReadTimeout, ConnectionError):
                try:
                    instance.server.stop(timeout=2)
                except docker.errors.NotFound:
                    pass
            except docker.errors.NotFound:
                pass
            await interaction.followup.send("Server stopped")  

    def generate_multiworld(self, server_id: int):
        self.docker_client.images.build(path="/server/archipelago/", dockerfile="Generate", tag="archipelago-generate", rm=True)
        return self.docker_client.containers.run("archipelago-generate", name=f"archipelago-generate-{server_id}", remove=True, detach=True, volumes=[f"/home/rebel5611/mihono_bourbot/serverdata/archipelago/{server_id}/output:/server/output", f"/home/rebel5611/mihono_bourbot/serverdata/archipelago/{server_id}/Players:/server/Players", f"/home/rebel5611/mihono_bourbot/serverdata/archipelago/{server_id}/Worlds:/server/custom_worlds"]).wait()

async def setup(client):
    await client.add_cog(Archipelago(client))
