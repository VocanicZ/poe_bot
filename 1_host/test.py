from utils.gamehelper import Poe2Bot
import time
from utils.loot_filter import PickableItemLabel

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

REMOTE_IP = "xxx.xxx.xxx.xxx"

poe_bot = Poe2Bot(unique_id="test", remote_ip=REMOTE_IP)
poe_bot.mover.setMoveType("wasd")
#poe_bot.combat_module.build = GenericBuild2(poe_bot=poe_bot) # This is optional if you have a build
poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()
poe_bot.ui.inventory.update()
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]
while True: # Main loop
    poe_bot.refreshInstanceData() 
    """"
    your follower bot logic here
    """
    poe_bot.loot_picker.collectLoot(combat=False, max_distance=10) # This will collect loot
    time.sleep(1)