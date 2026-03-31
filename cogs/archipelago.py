import asyncio
import bidict
import certifi
import docker
import enum
import glob
import json
import discord
import os
import requests
import ssl
import typing
import urllib
import websockets
import zipfile
from apikeys import guild_ids
from discord.ext import commands
from discord import Interaction

class archipelago(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.bot_data = None
        
        self.docker_client = docker.from_env()
        self.archipelago_server = None
        self.archipelago_socket = None
        self.server_watcher = None

        self.load_data()
    
    @discord.slash_command(name= "archipelago", guild_ids= guild_ids)
    async def archipelago(self, interaction: Interaction):
        pass
    
    @archipelago.subcommand(name="get_server_address", description = "Get the address to join the Archipelago server")
    async def get_server_address(self, interaction: Interaction):
        role = discord.utils.get(interaction.guild.roles, name="Archipelago")
        if role in interaction.user.roles:
            ip = requests.get('https://checkip.amazonaws.com').text.strip()
            await interaction.send(f"The address for the Archipelago game is: {ip}:56112", ephemeral=True)
        else:
            await interaction.send("You do not have access to this server.", ephemeral=True)

    @archipelago.subcommand(name="set_reporting_channel", description = "Set the current channel as the Archipelago reporting channel")
    async def set_reporting_channel(self, interaction: Interaction):
        if interaction.user.guild_permissions.manage_guild:
            def funct(): self.bot_data["reporting_channel"] = interaction.channel_id
            self.change_data(funct)
            await interaction.response.send_message("Saved as reporting channel")
        else:
            await interaction.response.send_message("You do not have permission to run this command!")
    
    @archipelago.subcommand(name="set_alias")
    async def set_alias(self, interaction: Interaction, alias: str):
        def funct(): self.bot_data["players"][interaction.user.mention].alias = alias
        self.change_data(funct)
        await interaction.response.send_message(f"Saved '{alias}' as your Archipelago alias", ephemeral=True)

    @archipelago.subcommand(name="upload_yamls")
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

    @archipelago.subcommand(name="generate_game")
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
        else:
            await interaction.followup.send("Multiworld generation failed")

    @archipelago.subcommand(name= "bounty_board")
    async def bounty_board(self, interaction: Interaction):
        pass

    @bounty_board.subcommand(name= "add_bounty")
    async def add_bounty(self, interaction: Interaction, item: str):
        if interaction.user.mention in self.bot_data["players"] and self.bot_data["players"][interaction.user.mention].alias:
            if item in self.bot_data["item_name_to_id"][self.bot_data["players"][interaction.user.mention].game]:
                def funct(): self.bot_data["players"][interaction.user.mention].bounties[str(self.bot_data["item_name_to_id"][self.bot_data["players"][[interaction.user.mention]].game][item])] = item
                self.change_data(funct)
                await interaction.response.send_message(f"Bounty added for {interaction.user.mention}'s {item}!")
            else:
                await interaction.response.send_message(f"No such item '{item}' exists in your game.\n"
                                                    "The item name may be different in the randomizer.", ephemeral=True)
        else:
            await interaction.response.send_message("No player found. Have you run '/archipelago set_alias' yet?", ephemeral=True)
    
    @bounty_board.subcommand(name= "remove_bounty")
    async def remove_bounty(self, interaction: Interaction, item: str):
        if interaction.user.mention in self.bot_data["players"] and self.bot_data["players"][interaction.user.mention].alias:
            def funct(): return self.bot_data["players"][interaction.user.mention].bounties.pop(str(self.bot_data["item_name_to_id"][self.bot_data["players"][[interaction.user.mention]].game][item]), None)
            removed_bounty = self.change_data(funct)
            if removed_bounty is not None:
                await interaction.response.send_message(f"Bounty for {interaction.user.mention}'s {item} removed!")
                return
        await interaction.response.send_message(f"No bounty for item '{item}' exists", ephemeral=True)

    @bounty_board.subcommand(name= "get_bounties")
    async def get_bounties(self, interaction: Interaction):
        bounties = ""
        for mention in self.bot_data["players"].keys():
            player = self.bot_data["players"][mention]
            if len(player.bounties) > 0:
                bounties += f"{mention}:\n"
                for bounty in player.bounties.values():
                    bounties += f"\t{bounty}\n"
        bounties = bounties.strip()
        if bounties != '':
            await interaction.response.send_message(f"The current bounties are:\n{bounties}")
        else:
            await interaction.response.send_message("There are no current bounties!")

    @archipelago.subcommand(name= "server")
    async def server(self, interaction: Interaction):
        pass

    @server.subcommand(name="start")
    async def start(self, interaction: Interaction):
        await interaction.response.defer()
        
        if len(glob.glob('/server/archipelago/serverdata/output/*')) == 0:
            await interaction.followup.send("No game found. Upload your yamls with /archipelago upload_yamls and then generate one with /archipelago generate_game")
        elif self.check_server_status():
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
            self.archipelago_server = self.docker_client.containers.run("archipelago-run", name="archipelago-run", stdin_open=True, tty=True, remove=True, detach=True, ports={'38281/tcp': 56112}, volumes=["/home/rebel5611/mihono_bourbot/serverdata/archipelago/serverdata:/server"])
            self.archipelago_socket = self.archipelago_server.attach_socket(params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1})
            #self.server_watcher = asyncio.create_task(self.process_server_output(), name="server watcher")
            await interaction.followup.send("Server started")
            
    @server.subcommand(name="stop")
    async def stop(self, interaction: Interaction):
        await interaction.response.defer()
        
        if not self.check_server_status():
            await interaction.followup.send("There is no running server")
        else:
            self.archipelago_server.stop()
            await interaction.followup.send("Server stopped")
      
    def check_server_status(self):
        if self.archipelago_server != None:
            try:
                self.archipelago_server.reload()
            except:
                self.archipelago_server = None
        
        return self.archipelago_server != None and self.archipelago_server.attrs["State"]["Status"] in ["created", "running"]
          
    #async def process_server_output(self):
        

    async def process_server_cmd(self, args: dict):
        try:
            cmd = args["cmd"]
        except:
            print(f"Could not get command from {args}")
            raise
        if cmd == 'RoomInfo':
            payload = {
                'cmd': 'Connect',
                'password': str(self.bot_data["password"]), 
                'name': str(self.bot_data["username"]), 
                'version': self.tuplize_version("0.5.0"),
                'tags': {"AP", "TextOnly"}, 
                'items_handling': 0b111,
                'uuid': self.bot_data["uuid"], 
                'game': "", 
                "slot_data": False,
            }
            if args['password']:
                payload.update(args['password'])

            await self.socket.send(self.encode([{"cmd": "GetDataPackage", "games": [game]} for game in set(args["games"])]))

            if not self.socket or not self.socket.open or self.socket.closed:
                return
            await self.socket.send(self.encode([payload]))
        
        elif cmd == 'DataPackage':
            def funct():
                for game, game_data in args['data']["games"].items():
                    self.bot_data["item_name_to_id"][game] = game_data["item_name_to_id"]
                    self.bot_data["location_name_to_id"][game] = game_data["location_name_to_id"]
            self.change_data(funct)

        elif cmd == 'ConnectionRefused':
            errors = args["errors"]
            if 'InvalidSlot' in errors:
                self.disconnected_intentionally = True
                await self.send_message("Invalid username")
                raise Exception('Invalid username')
            elif 'IncompatibleVersion' in errors:
                raise Exception('Server reported your client version as incompatible. '
                                'This probably means you have to update.')
            elif 'InvalidItemsHandling' in errors:
                raise Exception('The item handling flags requested by the client are not supported')
            elif 'InvalidPassword' in errors:
                self.disconnected_intentionally = True
                await self.send_message("Invalid password")
                def funct(): self.bot_data["password"] = ""
                self.change_data(funct)
                raise Exception('Invalid password')
            elif errors:
                raise Exception(f"Unknown connection errors: {str(errors)}")
            else:
                raise Exception('Connection refused by the multiworld host, no reason provided')

        elif cmd == 'Connected':
            await self.send_message("Connected to multiworld server")
            for player in args["players"]:
                def funct():
                    if str(player.slot) not in self.bot_data["players"]:
                        self.bot_data["players"][str(player.slot)] = Player(slot=player.slot,
                                                                    alias=player.alias,
                                                                    name=player.name,
                                                                    game=args["slot_info"][str(player.slot)].game,
                                                                    team=player.team)
                    else:
                        self.bot_data["players"][str(player.slot)] = Player(slot=player.slot,
                                                                    alias=player.alias,
                                                                    name=player.name,
                                                                    game=args["slot_info"][str(player.slot)].game,
                                                                    team=player.team,
                                                                    mention=self.bot_data["players"][str(player.slot)].mention,
                                                                    recieved_items=self.bot_data["players"][str(player.slot)].recieved_items,
                                                                    bounties=self.bot_data["players"][str(player.slot)].bounties)
                self.change_data(funct)
            def funct(): self.bot_data["hint_cost"] = args["hint_points"]
            self.change_data(funct)
                
        elif cmd == 'ReceivedItems':
            recieved_items = {}
            for network_item in args["items"]:
                if str(network_item.player) not in recieved_items:
                    recieved_items[str(network_item.player)] = {}
                recieved_items[str(network_item.player)][str(network_item.location)] = str(network_item.item)
            for player in recieved_items:
                for location in self.bot_data["players"][player].recieved_items:
                    recieved_items[player].pop(location, None)
                def funct(): self.bot_data["players"][player].recieved_items.update(recieved_items[player])
                self.change_data(funct)
                for location in recieved_items[player]:
                    bounty_found = None
                    bounty_user = None
                    for user in self.bot_data["players"]:
                        if bounty_found == None:
                            def funct(): return self.bot_data["players"][user].bounties.pop(recieved_items[player][location], None)
                            bounty_found = self.change_data(funct)
                            if bounty_found != None:
                                bounty_user = self.bot_data["players"][user].mention
                    if bounty_found is not None:
                        await self.send_message(f"{self.bot_data['players'][player].mention} has found {bounty_user}'s {bounty_found} at their " +
                                                f"{bidict.bidict(self.bot_data['location_name_to_id'][self.bot_data['players'][player].game]).inverse[int(location)]}!")

        elif cmd == "RoomUpdate":
            print(args)
            if "hint_points" in args:
                def funct(): self.bot_data["hint_cost"] = args["hint_points"]
                self.change_data(funct)

        elif cmd == 'InvalidPacket':
            print(f"Invalid Packet of {args['type']}: {args['text']}")

    async def server_autoreconnect(self):
        await asyncio.sleep(self.reconnect_delay)
        if self.bot_data["address"] and self.multiworld_connection is None:
            self.multiworld_connection = asyncio.create_task(self.connect_to_multiworld(self.bot_data["address"]), name="server loop")

    async def send_message(self, msg: str):
        await self.client.get_channel(self.bot_data["reporting_channel"]).send(msg)

    def change_data(self, funct):
        self.load_data()
        ret = funct()
        self.save_data()
        return ret

    def save_data(self):
        with open("bot_data.json", "w") as f:
            json.dump(self.bot_data, f, indent=2, cls=Player.Encoder)

    def load_data(self):
        if not os.path.isfile("bot_data.json"):
            with open("bot_data.json", "w") as f:
                json.dump(dict({}), f)

        with open("bot_data.json", "r") as f:
            self.bot_data = json.load(f, cls=Player.Decoder)
        if "reporting_channel" not in self.bot_data:
            self.bot_data["reporting_channel"] = ''
        if "world_save" not in self.bot_data:
            self.bot_data["world_save"] = ''
        if "address" not in self.bot_data:
            self.bot_data["address"] = ''
        if "password" not in self.bot_data:
            self.bot_data["password"] = ''
        if "username" not in self.bot_data:
            self.bot_data["username"] = ''
        if "hint_cost" not in self.bot_data:
            self.bot_data["hint_cost"] = None
        if "uuid" not in self.bot_data:
            import uuid
            self.bot_data["uuid"] = uuid.getnode()
            self.save_data()
        if "players" not in self.bot_data:
            self.bot_data["players"] = {}
        if "item_name_to_id" not in self.bot_data:
            self.bot_data["item_name_to_id"] = {}
        if "location_name_to_id" not in self.bot_data:
            self.bot_data["location_name_to_id"] = {}

    def _object_hook(self, o: typing.Any) -> typing.Any:
        if isinstance(o, dict):
            hook = self.custom_hooks.get(o.get("class", None), None)
            if hook:
                return hook(o)
            cls = self.allowlist.get(o.get("class", None), None)
            if cls:
                for key in tuple(o):
                    if key not in cls._fields:
                        del (o[key])
                return cls(**o)

        return o
    
    class Version(typing.NamedTuple):
        major: int
        minor: int
        build: int

    def get_any_version(self, data: dict) -> Version:
        data = {key.lower(): value for key, value in data.items()}  # .NET version classes have capitalized keys
        return self.Version(int(data["major"]), int(data["minor"]), int(data["build"]))
    
    def encode(self, obj: typing.Any) -> str:
        return self._encode(self._scan_for_TypedTuples(obj))
    
    def _scan_for_TypedTuples(self, obj: typing.Any) -> typing.Any:
        if isinstance(obj, tuple) and hasattr(obj, "_fields"):  # NamedTuple is not actually a parent class
            data = obj._asdict()
            data["class"] = obj.__class__.__name__
            return data
        if isinstance(obj, (tuple, list, set, frozenset)):
            return tuple(self._scan_for_TypedTuples(o) for o in obj)
        if isinstance(obj, dict):
            return {key: self._scan_for_TypedTuples(value) for key, value in obj.items()}
        return obj
    
    def tuplize_version(self, version: str) -> Version:
        return self.Version(*(int(piece, 10) for piece in version.split(".")))
    
class Player():
    """Represents a player in the game."""
    slot: int
    alias: str
    name: str
    game: str
    team: int
    mention: str
    recieved_items: dict
    bounties: dict
    def __init__(self, slot: int, alias: str, name: str, game: str, team: int,
                 mention: str = None, recieved_items: dict = {}, bounties: dict = {}):
        self.slot = slot
        self.alias = alias
        self.name = name
        self.game = game
        self.team = team
        self.mention = alias if mention is None else mention
        self.recieved_items = recieved_items
        self.bounties = bounties

    class Encoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, Player):
                return {
                    "_type": "Player",
                    "slot": o.slot,
                    "alias": o.alias,
                    "name": o.name,
                    "game": o.game,
                    "team": o.team,
                    "mention": o.mention,
                    "recieved_items": o.recieved_items,
                    "bounties": o.bounties
                }
            return super(Player.Encoder, self).default(o)
    
    class Decoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

        def object_hook(self, o):
            if "_type" in o:
                if o["_type"] == "Player":
                    return Player(slot=o["slot"], alias=o["alias"], name=o["name"], game=o["game"], team=o["team"], mention=o["mention"], recieved_items=o["recieved_items"], bounties=o["bounties"])
            return o
            
            
        

class ByValue:
    """
    Mixin for enums to pickle value instead of name (restores pre-3.11 behavior). Use as left-most parent.
    See https://github.com/python/cpython/pull/26658 for why this exists.
    """
    def __reduce_ex__(self, prot):
        return self.__class__, (self._value_, )
    
class SlotType(ByValue, enum.IntFlag):
    spectator = 0b00
    player = 0b01
    group = 0b10

    @property
    def always_goal(self) -> bool:
        """Mark this slot as having reached its goal instantly."""
        return self.value != 0b01
    
class NetworkPlayer(typing.NamedTuple):
    """Represents a particular player on a particular team."""
    team: int
    slot: int
    alias: str
    name: str


class NetworkSlot(typing.NamedTuple):
    """Represents a particular slot across teams."""
    name: str
    game: str
    type: SlotType
    group_members: typing.Union[typing.List[int], typing.Tuple] = ()  # only populated if type == group


class NetworkItem(typing.NamedTuple):
    item: int
    location: int
    player: int
    flags: int = 0

def setup(client):
    client.add_cog(archipelago(client))
