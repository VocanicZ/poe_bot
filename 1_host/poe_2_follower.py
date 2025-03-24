import random
import sys
import time
import math
from ast import literal_eval

from utils.autoflask import AutoFlasks
from utils.entity import Entity
from utils.poebot import Poe2Bot
from utils.components import Posx1x2y1y2, UiElement
from utils.utils import sortByHSV

from utils.loot_filter import PickableItemLabel

poe_bot_class = Poe2Bot
poe_bot: poe_bot_class

default_config = {
  "REMOTE_IP": "127.0.0.1",
  "UNIQUE_ID": "follower",
  "force_reset_temp": False,
}

try:
  i = sys.argv[1]
  print(i)
  parsed_config = literal_eval(i)
  print("successfully parsed cli config")
  print(f"parsed_config: {parsed_config}")
except:
  print("cannot parse config from cli, using default\dev one")
  notebook_dev = True
  parsed_config = default_config

config = {}

for key in default_config.keys():
  config[key] = parsed_config.get(key, default_config[key])

print(f"config to run {config}")

UNIQUE_ID = config["UNIQUE_ID"]
REMOTE_IP = config["REMOTE_IP"]
force_reset_temp = config["force_reset_temp"]
print(f"running follower using: REMOTE_IP: {REMOTE_IP} force_reset_temp: {force_reset_temp}")

def checkIfCanTeleportToPartyMember(party_member_to_follow) -> bool:
  game_img = poe_bot.getImage()
  party_leader_img = game_img[
    party_member_to_follow["sz"][2] : party_member_to_follow["sz"][3], party_member_to_follow["sz"][0] : party_member_to_follow["sz"][1]
  ]
  teleport_to_img = party_leader_img[30:43, 5:17]
  sorted_img = sortByHSV(teleport_to_img, 76, 118, 109, 116, 213, 196)
  len(sorted_img[sorted_img != 0])
  can_teleport = len(sorted_img[sorted_img != 0]) > 30
  return can_teleport

def getTeleportButtonArea(poe_bot: Poe2Bot, party_member_to_follow) -> UiElement:
  party_member_area = party_member_to_follow["sz"][:]
  party_member_area[0] += 5
  party_member_area[1] = party_member_area[0] + 13
  party_member_area[2] += 30
  party_member_area[3] = party_member_area[2] + 13
  return UiElement(poe_bot, Posx1x2y1y2(*party_member_area))

def get_portal_positions(map_device_pos, radius = 20):
    start_angle = 210
    num_points = 6
    portal_pos = []
    for i in range(num_points):
        angle_rad = math.radians(start_angle - i * 60)
        x = round(map_device_pos[0] + radius * math.cos(angle_rad))
        y = round(map_device_pos[1] + radius * math.sin(angle_rad))
        portal_pos.append([x, y])
    return portal_pos

def get_map_device(poe_bot):
    es = poe_bot.game_data.entities.all_entities

    for e in es:
        if e.type == "IngameIcon":
            if e.render_name == "Map Device":
                return e
    return None

def get_map_device_pos(poe_bot):
    map = get_map_device(poe_bot)
    if map is None:
        return None
    return [map.grid_position.x, map.grid_position.y]

poe_bot = Poe2Bot(unique_id=UNIQUE_ID,remote_ip=REMOTE_IP)
poe_bot.refreshAll()
poe_bot.game_data.terrain.getCurrentlyPassableArea()

auto_flasks = AutoFlasks(poe_bot)

def useFlasksOutsideOfHideout():
  if poe_bot.game_data.area_raw_name[:7] != "Hideout":
    auto_flasks.useFlasks()

def mover_default_func(*args, **kwargs):
  useFlasksOutsideOfHideout()
  return False

ARTS_TO_PICK = ["Art/2DItems/Maps/DeliriumSplinter.dds", "Art/2DItems/Maps/"]
# big piles of gold
COIN_MIN = 10 #2-17
COUIN_MAX = 17 #2-17
for tier in range(COIN_MIN, COUIN_MAX):
  ARTS_TO_PICK.append(f"Art/2DItems/Currency/Ruthless/CoinPileTier{tier}.dds")

def isItemHasPickableKey(item_label: PickableItemLabel):
  if item_label.icon_render in ARTS_TO_PICK:
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Currency/") and "/Ruthless/" not in item_label.icon_render: # All currency
    return True
  elif item_label.icon_render.startswith("Art/2DItems/Maps/EndgameMaps/"): # All maps
    return True
  return False

poe_bot.mover.default_continue_function = mover_default_func

poe_bot.mover.setMoveType("wasd")
poe_bot.ui.inventory.update()
poe_bot.loot_picker.loot_filter.special_rules = [isItemHasPickableKey]

refresh_area_frequency = 10
min_distance_to_follow = 20

entity_to_follow_ign = None

auto_flasks.life_flask_recovers_es = True
auto_flasks.hp_thresh = 0.75

entity_to_follow: Entity = None
id_to_follow: int = None
change_area = False
afk_counter = 100
entered_map = False
afk = False
while True:
  if afk:
     time.sleep(5)
  else:
    time.sleep(0.1)

  if entered_map:
    if afk_counter <= 0:
      afk_counter = 100
      entered_map = False
    afk_counter -= 1
    continue

  ign_to_follow: str = None

  party_raw = poe_bot.backend.getPartyInfo()

  if party_raw is None:
    afk_counter = 100
    afk = True
    continue
  
  party_leader = next((pm for pm in party_raw["party_members"] if pm["is_leader"] is True), None)
  if party_leader is None:
    afk_counter = 100
    afk = True
    continue
  ign_to_follow = party_leader["ign"]
  follow_loc = party_leader["area_raw_name"]

  if follow_loc is not None: 
    transitions_and_portals = []
    transitions_and_portals.extend(poe_bot.game_data.entities.town_portals)
    transitions_and_portals.extend(poe_bot.game_data.entities.area_transitions)

    portals_with_similar_area_name = next((e for e in transitions_and_portals if e.render_name == follow_loc), None)
    if portals_with_similar_area_name:
      poe_bot.mover.goToEntitysPoint(portals_with_similar_area_name, release_mouse_on_end=True)
      poe_bot.mover.enterTransition(portals_with_similar_area_name)
      change_area = True
    else:
      can_teleport = checkIfCanTeleportToPartyMember(party_leader)
      if can_teleport is not False:
        teleport_button = getTeleportButtonArea(poe_bot, party_leader)
        teleport_button.click()
        time.sleep(random.uniform(0.05, 0.15))
        accept_button_element = UiElement(poe_bot, Posx1x2y1y2(*[575, 635, 390, 400]))
        accept_button_element.click()
        change_area = True
  elif change_area:
      change_area = False
      poe_bot.refreshAll()
      poe_bot.game_data.terrain.getCurrentlyPassableArea()
  else:
    poe_bot.refreshInstanceData()

  useFlasksOutsideOfHideout()
  #poe_bot.loot_picker.collectLoot(combat=False, max_distance=100)

  id_to_follow = poe_bot.backend.getEntityIdByPlayerName(ign_to_follow)
  prev_entity_to_follow = entity_to_follow
  entity_to_follow = next((e for e in poe_bot.game_data.entities.all_entities if e.id == id_to_follow), None)

  if entity_to_follow:
    if entity_to_follow.distance_to_player > min_distance_to_follow:
      if entity_to_follow.isInRoi() and entity_to_follow.isInLineOfSight():
        poe_bot.mover.move(*entity_to_follow.grid_position.toList())
      else:
        poe_bot.mover.goToEntity(entity_to_follow, min_distance=min_distance_to_follow)
      afk = False
      afk_counter = 100
    else:
      poe_bot.mover.stopMoving()
    
      if ("Hideout" in poe_bot.game_data.area_raw_name):
        map_device = get_map_device(poe_bot)
        if map_device is not None:
          if map_device.distance_to_player <= min_distance_to_follow * 2:
            try:
              map_device_pos = get_map_device_pos(poe_bot)
              if map_device_pos is None:
                  print("map device not found")
                  continue
              portal_pos = get_portal_positions(map_device_pos)
              for p in portal_pos:
                  poe_bot.refreshInstanceData()
                  user = next((e for e in poe_bot.game_data.entities.all_entities if e.id == id_to_follow), None)
                  if user.distance_to_player > 50:
                     break
                  poe_bot.mover.goToPoint(p, release_mouse_on_end=True, min_distance=5)
                  for i in get_portal_positions(p, radius=5):
                      path = poe_bot.pather.generatePath(
                          (int(poe_bot.game_data.player.grid_pos.y), int(poe_bot.game_data.player.grid_pos.x)),
                          (i[0], i[1]),
                          )
                      point = path[int(len(path) / 2)]
                      pos_to_click = poe_bot.getPositionOfThePointOnTheScreen(point[0], point[1])
                      print(f"middle point {point} screen pos {pos_to_click}")
                      pos_x, pos_y = poe_bot.convertPosXY(int(pos_to_click[0]), int(pos_to_click[1]))
                      poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
                      time.sleep(random.uniform(0.05, 0.15))
                      poe_bot.bot_controls.mouse.click()
                      time.sleep(random.uniform(0.15, 0.2))
                  time.sleep(random.uniform(0.5, 1))
                  entered_map = True
            except Exception as e:
                entered_map = True
            afk = False
            afk_counter = 100
            continue
  if afk_counter <= 0:
    afk_counter = 100
    afk = True
    print("Afk")
  else:
     afk_counter -= 1