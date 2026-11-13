from worlds.generic.Rules import set_rule
from BaseClasses import MultiWorld

# Sets rules on completion condition
def set_completion_rules(multiworld: MultiWorld, player: int):
    multiworld.completion_condition[player] = lambda state: True
