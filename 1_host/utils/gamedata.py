from math import dist
from typing import List
import time

from .poebot import PoeBot
from .terrain import Terrain
from .entity import Entity, Entities
from .player import Player
from flask import Flask
from .quest import QuestFlags
from .skill import Skills
from .gamehelper import Camera
from .map import MapInfo, MinimapIcons
from .components import PosXY, Life
from .constants import IS_LOADING_KEY, FLASK_NAME_TO_BUFF

class GameData:
  poe_bot: PoeBot
  game_state: int
  is_loading: bool
  invites_panel_visible: bool
  area_raw_name: str
  area_hash: int
  entities: Entities
  labels_on_ground_entities: List[Entity]
  player: Player
  skills: Skills
  # flasks:Flasks
  player_pos: PosXY
  player_life: Life
  last_update_time = 0.0

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.terrain = Terrain(self.poe_bot)
    self.entities = Entities(self.poe_bot)
    self.player = Player(self.poe_bot)
    self.skills = Skills(self.poe_bot)
    self.quest_states = QuestFlags(self.poe_bot)
    self.map_info = MapInfo(self.poe_bot)
    self.minimap_icons = MinimapIcons(self.poe_bot)
    self.camera = Camera(self.poe_bot)
    # self.flasks = Flasks(self.poe_bot)

  def update(self, refreshed_data: dict, refresh_visited=False):
    if refreshed_data["terrain_string"] is not None:
      self.terrain.update(refreshed_data=refreshed_data, refresh_visited=refresh_visited)
    self.last_update_time = time.time()
    # self.flasks.update(refreshed_data=refreshed_data["s"])
    if refreshed_data["f"] is not None:
      self.player.all_flasks = []
      self.player.life_flasks = []
      self.player.mana_flasks = []
      self.player.utility_flasks = []
      for flask_index in range(len(refreshed_data["f"]["n"])):
        new_flask = Flask()
        new_flask.name = refreshed_data["f"]["n"][flask_index]
        new_flask.index = refreshed_data["f"]["i"][flask_index]
        new_flask.can_use = bool(refreshed_data["f"]["cu"][flask_index])
        self.player.all_flasks.append(new_flask)
        flask_related_buff = FLASK_NAME_TO_BUFF.get(new_flask.name, None)
        new_flask.buff = flask_related_buff
        if flask_related_buff is None:
          continue
        elif flask_related_buff == "flask_effect_life":
          self.player.life_flasks.append(new_flask)
        elif flask_related_buff == "flask_effect_mana":
          self.player.mana_flasks.append(new_flask)
        else:
          self.player.utility_flasks.append(new_flask)
    self.area_raw_name = refreshed_data.get("area_raw_name", None)
    self.area_hash = refreshed_data.get("ah", None)
    self.is_loading = refreshed_data[IS_LOADING_KEY]
    self.invites_panel_visible = refreshed_data["ipv"]
    self.player.update(refreshed_data=refreshed_data["pi"])
    self.entities.update(refreshed_data=refreshed_data)
    self.skills.update(refreshed_data=refreshed_data["s"])
    self.camera.update(refreshed_data)
    self.updateLabelsOnGroundEntities(refreshed_data["vl"])
    self.terrain.markAsVisited(int(self.player.grid_pos.x), int(self.player.grid_pos.y))
    self.is_alive = None

  def updateLabelsOnGroundEntities(self, labels=None):
    if not labels is not None:
      labels = self.poe_bot.backend.getVisibleLabelOnGroundEntities()

    self.labels_on_ground_entities = []
    player_grid_pos = self.poe_bot.game_data.player.grid_pos
    for raw_entity in labels:
      raw_entity["gp"][1] = self.poe_bot.game_data.terrain.terrain_image.shape[0] - raw_entity["gp"][1] # invert Y axis
      raw_entity["distance_to_player"] = dist([raw_entity["gp"][0], raw_entity["gp"][1]], [player_grid_pos.x, player_grid_pos.y])
      entity = Entity(self.poe_bot, raw_entity)
      if entity.grid_position.x == 0 or entity.grid_position.y == 0:
        continue
      self.labels_on_ground_entities.append(entity)
