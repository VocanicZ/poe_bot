from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
  from .poebot import PoeBot
from .flask import Flask
from .components import PosXY, Life

class Player:
  life: Life
  grid_pos: PosXY
  buffs: List[str]
  all_flasks: List[Flask]
  life_flasks: List[Flask]
  mana_flasks: List[Flask]
  utility_flasks: List[Flask]

  def __init__(self, poe_bot: "PoeBot") -> None:
    self.poe_bot = poe_bot

  def update(self, refreshed_data):
    self.raw = refreshed_data
    self.grid_pos = PosXY(x=refreshed_data["gp"][0], y=self.poe_bot.game_data.terrain.terrain_image.shape[0] - refreshed_data["gp"][1]) # invert Y axis
    self.life = Life(refreshed_data["l"])
    self.debuffs = refreshed_data["db"]
    self.buffs = refreshed_data["b"]

  def getEnemiesInRadius(self, radius: int = None, visible_only: bool = True):
    ignore_radius = not radius is not None
    ignore_visibility = visible_only is not True
    nearby_enemies = list(
      filter(
        lambda e: (ignore_radius or e.distance_to_player < radius) and (ignore_visibility or e.isInRoi()),
        self.poe_bot.game_data.entities.attackable_entities,
      )
    )
    return nearby_enemies

  def isInZone(self, x1, x2, y1, y2):
    if self.grid_pos.x > x1:
      if self.grid_pos.x < x2:
        if self.grid_pos.y > y1:
          if self.grid_pos.y < y2:
            return True
    return False
