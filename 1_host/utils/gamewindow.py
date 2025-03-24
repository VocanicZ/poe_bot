from typing import List

import poebot
from .utils import cropLine

PoeBot = poebot.PoeBot

class GameWindow:
  """
  about the game window itself
  """
  poe_bot: PoeBot
  debug: bool
  raw: dict = {}
  pos_x = 0
  pos_y = 0
  width = 0
  height = 0
  center_point = [0, 0]  # [x,y]

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.debug = poe_bot.debug

  def convertPosXY(self, x, y, safe=True, custom_borders: List[int] = None):
    """
    converts gamve_window x,y to machines display x,y
    """
    if safe is not False:
      if custom_borders:
        borders = custom_borders
      else:
        borders = self.borders
      if y < borders[2] or y > borders[3] or x < borders[0] or x > borders[1]:
        if self.debug:
          print(f"y < borders[2] or y > borders[3] or x < borders[0] or x > borders[1] out of bounds {x, y}")
        x, y = cropLine(start=self.center_point, end=(int(x), int(y)), borders=borders)
        if self.debug:
          print(f"after fix {x, y}")
    pos_x = int(x + self.pos_x)
    pos_y = int(y + self.pos_y)
    return (pos_x, pos_y)

  def isInRoi(self, x, y, custom_borders: List[int] = None):
    if custom_borders:
      borders = custom_borders
    else:
      borders = self.borders
    if x > borders[0]:
      if x < borders[1]:
        if y > borders[2]:
          if y < borders[3]:
            return True
    return False

  def update(self, refreshed_data):
    self.raw = refreshed_data["w"]
    self.pos_x = refreshed_data["w"][0]
    self.pos_x2 = refreshed_data["w"][1]
    self.pos_y = refreshed_data["w"][2]
    self.pos_y2 = refreshed_data["w"][3]
    self.width = self.pos_x2 - self.pos_x
    self.height = self.pos_y2 - self.pos_y
    if self.poe_bot.check_resolution and (self.width != 1024 or self.height != 768):
      self.poe_bot.raiseLongSleepException(f"game window width or height are {self.width}x{self.height} rather than 1024x768")
    # X, Y
    self.center_point = [int(self.width / 2), int(self.height / 2)]
    self.borders = [
      25,  # left
      self.width - 55,  # right
      60,  # top
      self.height - 150,  # bot
    ]

  def __str__(self):
    return f"{self.raw}"
