from BaseClasses import Region, Entrance, Tutorial, ItemClassification
from .Items import MihonoBourbotItem, item_table
from .Locations import MihonoBourbotLocation, advancement_table
from Options import PerGameCommonOptions
from .Rules import set_completion_rules
from worlds.AutoWorld import World, WebWorld

client_version = 7


class MihonoBourbotWeb(WebWorld):
    tutorials = [ ]


class MihonoBourbotWorld(World):
    """
    Mihono Bourbot is a discord bot that creates and manages archipelago games, while providing a bounty board system which notifies players via discord when their items are found.
    This game has no items.
    """
    game = "Mihono Bourbot"
    options_dataclass = PerGameCommonOptions
    web = MihonoBourbotWeb()

    item_name_to_id = {name: data.code for name, data in item_table.items()}
    location_name_to_id = {name: data.id for name, data in advancement_table.items()}

    def create_regions(self):
        bot = Region("Bot", self.player, self.multiworld)
        bot.locations += [ ]
        
        self.multiworld.regions.append(bot)

    def create_items(self):
        self.multiworld.itempool += [ ]

    def set_rules(self):
        set_completion_rules(self.multiworld, self.player)

    def fill_slot_data(self):
        return {
            "world_seed": self.random.getrandbits(32),
            "seed_name": self.multiworld.seed_name,
            "player_name": self.player_name,
            "player_id": self.player,
            "client_version": client_version,
            "race": self.multiworld.is_race,
        }

    def create_item(self, name: str) -> MihonoBourbotItem:
        item_data = item_table[name]
        return MihonoBourbotItem(name, ItemClassification.progression, item_data.code, self.player)
