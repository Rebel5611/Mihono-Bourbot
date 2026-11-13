from BaseClasses import Location
import typing


class AdvData(typing.NamedTuple):
    id: int
    region: str = "Bot"


class MihonoBourbotLocation(Location):
    game: str = "Mihono Bourbot"


advancement_table = { }
lookup_id_to_name: typing.Dict[int, str] = {data.id: item_name for item_name, data in advancement_table.items()}
