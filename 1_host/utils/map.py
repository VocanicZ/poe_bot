from .components import PoeBotComponent

class MapInfo(PoeBotComponent):
  raw: dict = {}
  location_name: str = "unknown"
  map_completed: bool = False

  def update(self, data: dict = None):
    if data is None:
      data = self.poe_bot.backend.getMapInfo()
    self.raw: dict = data
    self.location_name: str = data["elements"][0]["t"]
    self.map_completed = False
    if data["elements"][-1]["t"] == "Map Complete" and data["elements"][-1]["v"] == 1:
      self.map_completed = True

class MinimapIcon:
  def __init__(self, data_raw: dict):
    self.id: int = data_raw["i"]
    self.path: str = data_raw["p"]
    self.name: str = data_raw["n"]
    self.is_visible: bool = bool(data_raw["v"])
    self.is_hidden: bool = bool(data_raw["h"])
    # {
    #   "i": 920,
    #   "p": "Metadata/Terrain/Leagues/Ritual/RitualRuneInteractable",
    #   "n": "RitualRune",
    #   "v": 1,
    #   "h": 0
    # }

class MinimapIcons(PoeBotComponent):
  def update(self, data: dict = None):
    if data is None:
      data = self.poe_bot.backend.getMinimapIcons()
    self.raw: dict = data
    self.icons = list(map(lambda icon_raw: MinimapIcon(icon_raw), data))