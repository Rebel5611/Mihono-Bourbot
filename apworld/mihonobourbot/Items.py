from BaseClasses import Item
import typing


class ItemData(typing.NamedTuple):
    code: int
    progression: bool = True


class MihonoBourbotItem(Item):
    game: str = "Mihono Bourbot"


item_table = { }

lookup_id_to_name: typing.Dict[int, str] = {data.code: item_name for item_name, data in item_table.items()}
