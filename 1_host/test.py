from utils.poebot import Poe2Bot
import time
from utils.loot_filter import PickableItemLabel
from builds.combatbuild import getBuild
from utils.combat import CombatModule

def isItemHasPickableKey(item_label: PickableItemLabel): # define your loot filter here
  if item_label.icon_render in ARTS_TO_PICK:
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Currency/") and "/Ruthless/" not in item_label.icon_render: # All currency
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Maps/EndgameMaps/"): # All maps
    return True
  return False

ARTS_TO_PICK = ["Art/2DItems/Maps/DeliriumSplinter.dds", "Art/2DItems/Maps/"] # add Maps & Delirium Splinters to loot filter

for tier in range(2, 17):
  ARTS_TO_PICK.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds") # add Coin Piles to loot filter from tier 2 to 17

REMOTE_IP = "127.0.0.1"
BUILD_NAME = "deadeye_auto_attack"

poe_bot = Poe2Bot(unique_id="test", remote_ip=REMOTE_IP)
poe_bot.mover.setMoveType("wasd")
poe_bot.refreshAll()
poe_bot.combat_module = CombatModule(poe_bot, BUILD_NAME)
poe_bot.mover.default_continue_function = poe_bot.combat_module.build.usualRoutine

poe_bot.game_data.terrain.getCurrentlyPassableArea()
poe_bot.ui.inventory.update()
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]
while True: # Main loop
    poe_bot.refreshInstanceData() 
    in_instance = "Hideout" not in poe_bot.game_data.area_raw_name  # and not "_town_" in poe_bot.game_data.area_raw_name
    #print(f"[Mapper2.run] current instance: {poe_bot.game_data.area_raw_name} in_instance {in_instance}")
    poe_bot.combat_module.build.usualRoutine(poe_bot.mover)
    time.sleep(1)