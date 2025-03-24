import time
import random
from typing import List, TYPE_CHECKING
from math import dist

if TYPE_CHECKING:
  from .poebot import PoeBot
from .animation import Animation
from .components import PosXY, PosXYZ, Life
from .utils import lineContainsCharacters

class Entity:
  raw: dict
  location_on_screen: PosXY
  path: str
  rarity: str
  id: int
  is_opened: bool
  is_hostile: bool
  is_targetable: bool
  is_targeted: bool
  is_attackable: bool
  bound_center_pos: int
  grid_position: PosXY
  world_position: PosXYZ
  life: Life
  # animated_property_metadata:str
  render_name: str
  distance_to_player: float
  attack_value: int = None
  animation:Animation


  def __init__(self, poe_bot: "PoeBot", raw_json: dict) -> None:
    self.poe_bot = poe_bot
    self.raw = raw_json
    self._location_on_screen: PosXY = None
    # self.location_on_screen = PosXY(x=raw_json["ls"][0], y=raw_json["ls"][1])
    self.path = raw_json.get("p", None)
    self.rarity = raw_json.get("r", None)
    self.id = raw_json.get("i", None)
    self.is_opened = bool(raw_json.get("o", None))
    self.is_hostile = bool(raw_json.get("h", None))
    self.is_attackable = bool(raw_json.get("ia", None))
    self.is_targetable = bool(raw_json.get("t", None))
    self.is_targeted = bool(raw_json.get("it", None))
    self.essence_monster = bool(raw_json.get("em", None))
    self.bound_center_pos = raw_json.get("b", None)
    self.grid_position = PosXY(x=raw_json["gp"][0], y=raw_json["gp"][1])
    self.world_position = PosXYZ(x=raw_json["wp"][0], y=raw_json["wp"][1], z=raw_json["wp"][2])
    self.life = Life(raw_json.get("l", None))
    # self.animated_property_metadata = raw_json.get('a', None)
    self.render_name = raw_json.get("rn", None)
    self.type = raw_json.get("et", None)
    self.distance_to_player = raw_json.get("distance_to_player", None)

  def __str__(self) -> str:
    return str(self.raw)

  @property
  def location_on_screen(self):
    if self._location_on_screen is None:
      self._location_on_screen = PosXY(*self.poe_bot.game_data.camera.getScreenLocation(*self.world_position.toList()))
    return self._location_on_screen
  
  def updateLocationOnScreen(self):
    screen_loc = self.poe_bot.backend.getLocationOnScreen(self.world_position.x, self.world_position.y, self.world_position.z)
    self._location_on_screen = PosXY(screen_loc[0], screen_loc[1])
    return self.location_on_screen

  def click(self, hold_ctrl=False, update_screen_pos=False):
    poe_bot = self.poe_bot
    if update_screen_pos:
      self.updateLocationOnScreen()
    if hold_ctrl is True:
      poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
    pos_x, pos_y = poe_bot.convertPosXY(self.location_on_screen.x, self.location_on_screen.y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y, False)
    poe_bot.bot_controls.mouse.click()
    if hold_ctrl is True:
      poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")

  def hover(self, update_screen_pos=False, wait_till_executed=True, x_offset=0, y_offset=0):
    poe_bot = self.poe_bot
    if update_screen_pos:
      self.updateLocationOnScreen()
    pos_x, pos_y = poe_bot.convertPosXY(self.location_on_screen.x + x_offset, self.location_on_screen.y + y_offset)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y, wait_till_executed)

  def openWaypoint(self):
    poe_bot = self.poe_bot
    world_map = poe_bot.ui.world_map
    self_id = self.id
    i = 0
    while True:
      i += 1
      if i > 100:
        poe_bot.raiseLongSleepException("cannot open waypoint")
      world_map.update()
      if world_map.visible is True:
        break
      poe_bot.refreshInstanceData(reset_timer=True)
      targets = list(filter(lambda e: e.id == self_id, poe_bot.game_data.entities.all_entities))
      target = targets[0]
      target.click()
      time.sleep(random.randint(50, 70) / 100)

  def clickTillNotTargetable(self, custom_break_condition=lambda *args, **kwargs: False):
    print(f"[Entity.clickTillNotTargetable] call {time.time()} {self.raw}")
    while True:
      res = self.poe_bot.mover.goToPoint(
        point=[self.grid_position.x, self.grid_position.y],
        min_distance=30,
        release_mouse_on_end=False,
        # custom_continue_function=self.poe_bot.combat_module.build.usualRoutine,
        step_size=random.randint(25, 33),
      )
      if custom_break_condition() is True:
        return True
      if res is None:
        break

    i = 0
    print("arrived to activator")
    while True:
      i += 1
      if i > 80:
        self.poe_bot.raiseLongSleepException("cannot activate activator on map")
      activator_found = False
      if custom_break_condition() is True:
        return True
      for activator_search_i in range(20):
        activator = next((e for e in self.poe_bot.game_data.entities.all_entities if e.id == self.id), None)
        if activator:
          activator_found = True
          break
        else:
          print(f"activator disappeared, trying to find it again {activator_search_i}")
          self.poe_bot.refreshInstanceData()
          if activator_search_i % 6 == 0:
            self.poe_bot.backend.forceRefreshArea()
      if activator_found is False:
        data = self.poe_bot.backend.getPartialData()
        print(data)
        print("activator disappeared")
        self.poe_bot.raiseLongSleepException("activator disappeared")
      if activator.is_targetable is not False:
        activator.click()
        self.poe_bot.refreshInstanceData()
      else:
        break
    return True

  def openDialogue(self, skip_texts=True, timeout_secs=10):
    start_time = time.time()
    self.poe_bot.ui.npc_dialogue.update()
    # talk and skip text dialogue
    while self.poe_bot.ui.npc_dialogue.visible is False or self.poe_bot.ui.npc_dialogue.text is not None:
      self.click(update_screen_pos=True)
      self.poe_bot.refreshInstanceData()
      time.sleep(random.uniform(0.3, 0.6))
      self.poe_bot.ui.npc_dialogue.update()
      if self.poe_bot.ui.npc_dialogue.visible is True and self.poe_bot.ui.npc_dialogue.text is not None:
        self.poe_bot.ui.closeAll()
        time.sleep(random.uniform(0.2, 0.4))
      if time.time() - start_time > timeout_secs:
        self.poe_bot.raiseLongSleepException("Couldnt start dialogue and skip texts")
    return True

  def calculateValueForAttack(self, search_radius=17):
    self.attack_value = 0
    lower_x = self.grid_position.x - search_radius
    upper_x = self.grid_position.x + search_radius
    lower_y = self.grid_position.y - search_radius
    upper_y = self.grid_position.y + search_radius
    entities_around = list(
      filter(
        lambda entity: entity.grid_position.x > lower_x
        and entity.grid_position.x < upper_x
        and entity.grid_position.y > lower_y
        and entity.grid_position.y < upper_y,
        self.poe_bot.game_data.entities.attackable_entities,
      )
    )
    self.attack_value += len(entities_around)
    if "Metadata/Monsters/Totems/TotemAlliesCannotDie" in self.path:
      self.attack_value += 10
    return self.attack_value

  def isInRoi(self):
    if self.location_on_screen.x > self.poe_bot.game_window.borders[0]:
      if self.location_on_screen.x < self.poe_bot.game_window.borders[1]:
        if self.location_on_screen.y > self.poe_bot.game_window.borders[2]:
          if self.location_on_screen.y < self.poe_bot.game_window.borders[3]:
            return True
    return False

  def isInLineOfSight(self):
    return self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(self.grid_position.x, self.grid_position.y)

  def isOnPassableZone(self):
    return self.poe_bot.game_data.terrain.checkIfPointPassable(self.grid_position.x, self.grid_position.y)

  def isInZone(self, x1, x2, y1, y2):
    if self.grid_position.x > x1:
      if self.grid_position.x < x2:
        if self.grid_position.y > y1:
          if self.grid_position.y < y2:
            return True
    return False

class Entities:
  poe_bot: "PoeBot"
  raw: dict

  def __init__(self, poe_bot: "PoeBot") -> None:
    self.poe_bot = poe_bot
    self.reset()

  def reset(self):
    self.all_entities: List[Entity] = []
    self.attackable_entities: List[Entity] = []
    self.corpses: List[Entity] = []
    self.essence_monsters: List[Entity] = []
    self.unique_entities: List[Entity] = []
    self.attackable_entities_blue: List[Entity] = []
    self.attackable_entities_rares: List[Entity] = []
    self.attackable_entities_uniques: List[Entity] = []
    self.beasts: List[Entity] = []
    self.broken_entities: List[Entity] = []
    self.world_items: List[Entity] = []
    self.pickable_items: List[Entity] = []
    self.area_transitions: List[Entity] = []
    self.area_transitions_all: List[Entity] = []
    self.npcs: List[Entity] = []
    self.town_portals: List[Entity] = []
    self.coffins: List[Entity] = []

  def update(self, refreshed_data: dict):
    self.reset()
    self.raw = refreshed_data["awake_entities"]
    player_grid_pos = self.poe_bot.game_data.player.grid_pos
    for raw_entity in refreshed_data["awake_entities"]:
      raw_entity["gp"][1] = self.poe_bot.game_data.terrain.terrain_image.shape[0] - raw_entity["gp"][1] # invert Y axis
      raw_entity["distance_to_player"] = dist([raw_entity["gp"][0], raw_entity["gp"][1]], [player_grid_pos.x, player_grid_pos.y])
      entity = Entity(self.poe_bot, raw_entity)
      if entity.grid_position.x == 0 or entity.grid_position.y == 0 or lineContainsCharacters(entity.render_name):
        print(f"found broken entity {entity.raw}")
        self.broken_entities.append(entity)
        continue

      if entity.rarity == "Unique":
        self.unique_entities.append(entity)

      if entity.is_attackable is True:
        if entity.is_targetable is not True or entity.life is None:
          self.broken_entities.append(entity)
          continue
        else:
          self.attackable_entities.append(entity)
          if entity.rarity == "Rare":
            if entity.essence_monster is True:
              self.essence_monsters.append(entity)
            if "/LeagueBestiary/" in entity.path:
              self.beasts.append(entity)
            else:
              self.attackable_entities_rares.append(entity)
          elif entity.rarity == "Magic":
            self.attackable_entities_blue.append(entity)
          elif entity.rarity == "Unique":
            self.attackable_entities_uniques.append(entity)

      if entity.type == "Npc":
        self.npcs.append(entity)
      elif entity.type == "at":
        if entity.render_name != "Empty":
          if entity.is_targetable is True:
            self.area_transitions.append(entity)
          self.area_transitions_all.append(entity)
      elif entity.type == "wi":
        self.world_items.append(entity)
        if entity.bound_center_pos != 0 and entity.grid_position.x != 0 and entity.grid_position.y != 0:
          self.pickable_items.append(entity)
      elif entity.type == "TownPortal":
        self.town_portals.append(entity)
      self.all_entities.append(entity)

  def getCorpsesArountPoint(self, grid_pos_x, grid_pos_y, radius=25):
    lower_x = grid_pos_x - radius
    upper_x = grid_pos_x + radius
    lower_y = grid_pos_y - radius
    upper_y = grid_pos_y + radius

    corpses = list(
      filter(
        lambda e: e.type == "m"
        and e.life.health.current == 0
        and e.grid_position.x > lower_x
        and e.grid_position.x < upper_x
        and e.grid_position.y > lower_y
        and e.grid_position.y < upper_y,
        self.poe_bot.game_data.entities.all_entities,
      )
    )
    return corpses
