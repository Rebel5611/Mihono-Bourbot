import asyncio
import certifi
import database
import docker
from docker import DockerClient
import enum
import json
import ssl
import typing
import uuid
import urllib
import websockets
from websockets.protocol import State


class ArchipelagoInstance():
    server_id: int
    discord_client = None
    port: int
    docker_client: DockerClient
    
    server: typing.Container = None
    archipelago_client: asyncio.Task = None
    socket: websockets.WebSocketClientProtocol = None
    default_reconnect_delay: int = 5
    reconnect_delay = default_reconnect_delay
    disconnected_intentionally: bool = False
    autoreconnect_task: asyncio.Task = None
    
    def __init__(self, server_id: int, discord_client, port: int, docker_client: DockerClient):
        self.server_id = server_id
        self.discord_client = discord_client
        self.port = port
        self.docker_client = docker_client
        
        self.decode = json.JSONDecoder(object_hook=self._object_hook).decode
        self.custom_hooks = {
            "Version": self.get_any_version
        }
        self.allowlist = {
            "NetworkPlayer": NetworkPlayer,
            "NetworkItem": NetworkItem,
            "NetworkSlot": NetworkSlot
        }
        self._encode = json.JSONEncoder(
            ensure_ascii=False,
            check_circular=False,
            separators=(',', ':'),
        ).encode
        
    
    def start_server(self):
        try:
            prev_container = self.docker_client.containers.get(f"archipelago-run-{self.server_id}")
            prev_container.remove(force=True)
        except docker.errors.NotFound:
            print("No old container found, proceeding...")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

        self.docker_client.images.build(path="/server/archipelago/", dockerfile="Run", tag="archipelago-run", rm=True)
        self.server = self.docker_client.containers.run("archipelago-run", name=f"archipelago-run-{self.server_id}", stdin_open=True, tty=True, remove=True, detach=True, ports={'38281/tcp': self.port}, volumes=[f"/home/rebel5611/mihono_bourbot/serverdata/archipelago/{self.server_id}/output:/server/output"], network="archipelago")
        self.archipelago_client = asyncio.create_task(self.connect_to_multiworld(f"ws://archipelago-run-{self.server_id}:38281"), name="archipelago client")
    
    def check_server_status(self):
        if self.server != None:
            try:
                self.server.reload()
            except:
                self.server = None
        
        return self.server != None and self.server.attrs["State"]["Status"] in ["created", "running"]
    
    async def connect_to_multiworld(self, address: str):
        if self.autoreconnect_task:
            self.autoreconnect_task.cancel()
            self.autoreconnect_task = None

        parsed_address = urllib.parse.urlparse(address)
        try:
            port = parsed_address.port or 38281  # raises ValueError if invalid
            socket = await websockets.connect(address, port=port, ping_timeout=None, ping_interval=None,
                                            ssl=ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certifi.where()) if address.startswith("wss://") else None,
                                            max_size=16*1024*1024)
            self.socket = socket
            self.reconnect_delay = self.default_reconnect_delay
            self.disconnected_intentionally = False
            async for data in socket:
                for msg in self.decode(data):
                    await self.process_server_cmd(msg)
            print("Disconnected from multiworld server")
        except websockets.InvalidMessage:
            # probably encrypted
            if address.startswith("ws://"):
                # try wss
                await self.connect_to_multiworld(f"ws{address[1:]}")
            else:
                print("Lost connection to the multiworld server due to InvalidMessage")
        except ConnectionRefusedError:
            print("Connection refused by the server.\nMay not be running Archipelago on that address or port.")
        except websockets.InvalidURI:
            print("Failed to connect to the multiworld server (invalid URI)")
        except OSError:
            print("Failed to connect to the multiworld server")
        # except Exception:
        #     print("Lost connection to the multiworld server")
        finally:
            if self.socket is not None:
                await self.socket.close()
            self.socket = None
            self.archipelago_client = None
            if address and not self.disconnected_intentionally:
                print(f"... automatically reconnecting in {self.reconnect_delay} seconds")
                assert self.autoreconnect_task is None
                self.autoreconnect_task = asyncio.create_task(self.server_autoreconnect(), name="archipelago auto reconnect")
                self.reconnect_delay *= 2
        

    async def process_server_cmd(self, args: dict):
        try:
            cmd = args["cmd"]
        except:
            print(f"Could not get command from {args}")
            raise

        if cmd == 'RoomInfo':
            payload = {
                'cmd': 'Connect',
                'password': database.get_server(self.server_id).archipelago_password, 
                'spectator': True, 
                'version': self.tuplize_version("0.5.0"),
                'tags': {"AP", "TextOnly"}, 
                'items_handling': 0b000,
                'uuid': uuid.getnode(), 
                'game': "", 
                "slot_data": False,
            }
            if args['password']:
                payload.update(args['password'])

            await self.socket.send(self.encode([{"cmd": "GetDataPackage", "games": [game]} for game in set(args["games"])]))

            if not self.socket or self.socket.state is not State.OPEN:
                return
            await self.socket.send(self.encode([payload]))
        
        elif cmd == 'DataPackage':
            for game, game_data in args['data']["games"].items():
                database.set_game_items_and_locations(self.server_id, game, game_data["item_name_to_id"], game_data["location_name_to_id"])

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
                raise Exception('Invalid password')
            elif errors:
                raise Exception(f"Unknown connection errors: {str(errors)}")
            else:
                raise Exception('Connection refused by the multiworld host, no reason provided')

        elif cmd == 'Connected':
            await self.send_message("Connected to multiworld server")
            for player in args["players"]:
                if not database.get_player(self.server_id, player.slot):
                    database.create_player(self.server_id, player.slot, player.alias, args['slot_info'].get(str(player.slot)).game)
                
        elif cmd == 'PrintJSON':
            if 'type' in args.keys() and args['type'] == 'ItemSend':
                receiving_player = database.get_player(self.server_id, int(args['receiving']))
                item = database.get_item(self.server_id, int(args['item'].item))
                location = database.get_location(self.server_id, int(args['item'].location))
                database.create_received_item(self.server_id, receiving_player.slot, item.item_id, location.location_id)
                database.commit()
                
                if len(item.bounties) > 0:
                    bounty = item.bounties[0]
                    receiving_user = database.get_user_by_player(receiving_player)
                    finding_player = database.get_player(self.server_id, int(args['item'].player))
                    finding_user = database.get_user_by_player(finding_player)

                    finder = f"<@{finding_user.user_id}>" if finding_user else finding_player.archipelago_alias
                    receiver = f"<@{receiving_user.user_id}>" if finding_user else receiving_player.archipelago_alias
                    await self.send_message(f"{finder} has found {receiver}'s {bounty.item.item_name} at their {location.location_name}!")
                    receiving_player.bounties.remove(bounty)
                    database.commit()

        elif cmd == 'InvalidPacket':
            print(f"Invalid Packet of {args['type']}: {args['text']}")

    async def server_autoreconnect(self):
        await asyncio.sleep(self.reconnect_delay)
        if self.archipelago_client is None:
            self.archipelago_client = asyncio.create_task(self.connect_to_multiworld(f"ws://archipelago-run-{self.server_id}:38281"), name="archipelago client")

    async def send_message(self, msg: str):
        if reporting_channel := database.get_server(self.server_id).reporting_channel:
            await self.discord_client.get_channel(reporting_channel).send(msg)
        
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
    received_items: dict
    bounties: dict
    def __init__(self, slot: int, alias: str, name: str, game: str, team: int,
                 mention: str = None, received_items: dict = {}, bounties: dict = {}):
        self.slot = slot
        self.alias = alias
        self.name = name
        self.game = game
        self.team = team
        self.mention = alias if mention is None else mention
        self.received_items = received_items
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
                    "received_items": o.received_items,
                    "bounties": o.bounties
                }
            return super(Player.Encoder, self).default(o)
    
    class Decoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

        def object_hook(self, o):
            if "_type" in o:
                if o["_type"] == "Player":
                    return Player(slot=o["slot"], alias=o["alias"], name=o["name"], game=o["game"], team=o["team"], mention=o["mention"], received_items=o["received_items"], bounties=o["bounties"])
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