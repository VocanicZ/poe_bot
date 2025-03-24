import time
import sys
import threading
import random
import traceback

from .constants import CURRENT_LEAGUE, IS_LOADING_KEY
from .controller import VMHostPuppeteer
from .temps import AfkTempData, Logger
from .backend import Backend
from .combat import CombatModule
from .ui import Ui
from .mover import Mover
from .pathing import Pather
from .gamewindow import GameWindow
from .gamedata import GameData
from .helper_functions import HelperFunctions
from .loot_filter import LootPicker
from .utils import raiseLongSleepException

class PoeBot:
  """ """

  version = "0.1.1"
  unique_id: str
  remote_ip: str
  debug: bool
  password: str

  area_raw_name = ""

  last_action_time = 0
  last_data = None
  last_req: dict = None
  last_res: dict = None

  on_death_function = None
  on_stuck_function = None
  on_disconnect_function = None
  on_unexpected_area_change_function = None
  allowed_exception_values = [
    "area is loading on partial request",
    "Area changed but refreshInstanceData was called before refreshAll",
    "character is dead",
    "logged in, success",
  ]

  def __init__(self, unique_id, remote_ip, debug=False, password=None) -> None:
    self.league = CURRENT_LEAGUE
    self.unique_id = unique_id
    self.remote_ip = remote_ip
    self.password = password
    self.aps_limit = 1 / 10
    self.debug = debug
    self.check_resolution = True

    self.bot_controls = VMHostPuppeteer(remote_ip)

    self.afk_temp = AfkTempData(unique_id=unique_id)
    self.logger = Logger(self.unique_id)

    self.backend = Backend(self)
    self.game_window = GameWindow(self)
    self.game_data = GameData(self)
    self.ui = Ui(self)
    self.pather = Pather(self)
    self.helper_functions = HelperFunctions(self)
    self.mover = Mover(self)
    self.combat_module = CombatModule(self)
    self.loot_picker = LootPicker(self)

    self.discovery_radius = 75
    self.init_time = time.time()
    self.on_death_function = self.defaultOnDeathFunction
    sys.excepthook = self.customExceptionHandler
    print(f"poe bot, v: {self.version} init at {self.init_time}")

    self._refresh_thread = None
    self._running = False

    # self.start_refresh_thread()

  def __del__(self):
    self.stop_refresh_thread()

  @staticmethod
  def parseDictArguments(data: dict):
    unique_id: str = None
    remote_ip: str = None
    return unique_id, remote_ip

  def start_refresh_thread(self):
    self._running = True
    self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
    self._refresh_thread.start()

  def stop_refresh_thread(self):
    self._running = False
    if self._refresh_thread and self._refresh_thread.is_alive():
      self._refresh_thread.join()

  def _refresh_loop(self):
    while self._running:
      try:
        # Call with force=True to bypass aps_limit check
        self.refreshInstanceData(force=True)
      except Exception as e:
        if e == "Area changed but refreshInstanceData was called before refreshAll":
          self.refreshAll()
      time.sleep(self.aps_limit)

  def update(self):
    pass

  def updateTerrain(self):
    pass

  def customExceptionHandler(self, exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
      sys.__excepthook__(exc_type, exc_value, exc_traceback)
      return
    string_exc_value = str(exc_value)
    if string_exc_value not in self.allowed_exception_values:
      self.logger.writeLine(string_exc_value)
      if exc_traceback:
        format_exception = traceback.format_tb(exc_traceback)
        for line in format_exception:
          self.logger.writeLine(repr(line))
    else:
      print(exc_value)

  def relogRestartSetActive(self):
    self.on_disconnect_function()
    # self.raiseLongSleepException('area is loading for too long')

  def getData(self, request_type="partial"):
    if request_type == "partial":
      get_data_func = self.backend.getPartialData
    else:
      get_data_func = self.backend.getWholeData
    i = 0
    got_data = False
    while got_data is False:
      i += 1
      refreshed_data = get_data_func()
      if refreshed_data["area_raw_name"] is None:
        if refreshed_data["g_s"] == 0:
          self.raiseLongSleepException("poe client is closed or hud is broken")
        elif self.on_disconnect_function is not None:
          self.on_disconnect_function()
        else:
          self.raiseLongSleepException("self.on_disconnect_function is not specified")
      if i == 100:
        self.relogRestartSetActive()
      if refreshed_data["pi"] is None or refreshed_data["pi"]["gp"] is None or refreshed_data["pi"]["gp"][0] is None:
        print(f'backend sends wrong data about playerpos  refreshed_data["pi"] is: {refreshed_data["pi"]}')
        time.sleep(0.1)
        continue
      if refreshed_data[IS_LOADING_KEY] is False:
        break
      else:
        if request_type == "partial":
          self.bot_controls.releaseAll()
          raise Exception("area is loading on partial request")
        else:
          time.sleep(0.1)
        print(f"[PoeBot.getData] area is loading {i}")
    return refreshed_data

  def getPositionOfThePointOnTheScreen(self, y, x):
    """
    supposed to translate grid pos (y, x) to position in a game window
    returns [x,y] on a game window, not the display, use self.convertPosXY(x,y)
    """
    # cos maps is upside down
    y = self.game_data.terrain.terrain_image.shape[0] - y # invert Y axis
    data = self.backend.getPositionOfThePointOnTheScreen(y, x)
    return data
  def refreshAll(self, refresh_visited=True):
    print(f"[poebot] #refreshAll call at {time.time()}")
    refreshed_data = self.getData(request_type="full")
    if refreshed_data["w"][1] == 0:
      print("refreshed_data['WindowArea']['Client']['Bottom'] == 0 backend error sleep 99999999999")
      self.raiseLongSleepException("refreshed_data['WindowArea']['Client']['Bottom'] == 0 backend error")
    self.game_window.update(refreshed_data=refreshed_data)
    self.game_data.update(refreshed_data=refreshed_data, refresh_visited=refresh_visited)
    self.pather.refreshWeightsForAStar(self.game_data.terrain.terrain_image)
    # below to remove
    self.area_raw_name = refreshed_data["area_raw_name"]
    self.refreshInstanceData(refreshed_data=refreshed_data)
  def refreshInstanceData(self, refreshed_data=None, force=False, reset_timer=False, raise_if_loading=False):
    if self.debug is True:
      print(f"#PoeBot.refreshInstanceData call {time.time()}")
    if force is False and reset_timer is False:
      time_now = time.time()
      time_passed_since_last_action = time_now - self.last_action_time
      if time_passed_since_last_action < self.aps_limit:
        wait_till_next_action = self.aps_limit - time_passed_since_last_action
        if self.debug is True:
          print(f"too fast, sleep for {wait_till_next_action}")
        time.sleep(wait_till_next_action)
    if refreshed_data is None:
      refreshed_data = self.getData("partial")
      # disconnect?
      if refreshed_data["area_raw_name"] is None:
        if refreshed_data["g_s"] == 0:
          self.raiseLongSleepException("poe client is closed or hud is broken")
        elif self.on_disconnect_function is not None:
          self.on_disconnect_function()
        else:
          self.raiseLongSleepException("self.on_disconnect_function is not specified")

      self.game_data.update(refreshed_data=refreshed_data)
    self.last_action_time = time.time()
    if refreshed_data["area_raw_name"] != self.area_raw_name:
      self.bot_controls.releaseAll()
      raise Exception("Area changed but refreshInstanceData was called before refreshAll")
    self.area_raw_name = refreshed_data["area_raw_name"]
    if raise_if_loading:
      if self.game_data.is_loading is True:
        self.bot_controls.releaseAll()
        raise Exception("is loading")
    self.is_alive = None
    if self.game_data.player.life.health.current == 0:
      self.bot_controls.releaseAll()
      if self.on_death_function is not None:
        self.on_death_function()
      else:
        raise Exception("player is dead")
    if self.debug is True:
      print(f"#PoeBot.refreshInstanceData return {time.time()}")
    if reset_timer is True:
      self.last_action_time = 0

  # aliases
  def convertPosXY(self, x, y, safe=True):
    return self.game_window.convertPosXY(x, y, safe)

  def getImage(self):
    return self.bot_controls.getScreen(
      self.game_window.pos_x,
      self.game_window.pos_y,
      self.game_window.pos_x + self.game_window.width,
      self.game_window.pos_y + self.game_window.height,
    )

  def getPartialImage(self, y1_offset, y2_offset, x1_offset, x2_offset):
    """
    works the same as numpy arrays, calling this with (100, 200, 300, 400) will be equal to [100:200, 300:400]
    """
    game_window_x1 = self.game_window.pos_x + x1_offset
    game_window_y1 = self.game_window.pos_y + y1_offset
    if x2_offset > 0:
      game_window_x2 = self.game_window.pos_x + x2_offset
    else:
      game_window_x2 = self.game_window.pos_x + self.game_window.width + x2_offset

    if y2_offset > 0:
      game_window_y2 = self.game_window.pos_y + y2_offset

    else:
      game_window_y2 = self.game_window.pos_y + self.game_window.height + y2_offset

    return self.bot_controls.getScreen(game_window_x1, game_window_y1, game_window_x2, game_window_y2)

  def raiseLongSleepException(self, text: str = None, *args, **kwargs):
    self.bot_controls.disconnect()
    if text is not None:
      self.logger.writeLine(text)
    raiseLongSleepException(text)

  def defaultOnDeathFunction(self):
    self.resurrectAtCheckpoint()
    raise Exception("character is dead")

  def clickResurrect(self):
    pos_x, pos_y = random.randint(430, 580), random.randint(225, 235)
    pos_x, pos_y = self.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    self.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    self.bot_controls.mouse.click()
    time.sleep(random.randint(30, 60) / 100)
    return True

  def resurrectAtCheckpoint(self, check_if_area_changed=False):
    self.logger.writeLine(f"#resurrectAtCheckpoint call {time.time()}")
    poe_bot = self
    resurrect_panel = self.ui.resurrect_panel

    refreshed_data = poe_bot.backend.getPartialData()
    initial_area_instance = refreshed_data["area_raw_name"]
    print(f"initial_area_instance {initial_area_instance}")

    print("waiting for resurrect panel to appear")
    i = 0
    while True:
      i += 1
      if i == 5:
        self.backend.forceRefreshArea()
      if i > 20:
        # poe_bot.raiseLongSleepException('if i > 20:')
        self.logger.writeLine("resurrect button didnt appear in 4 seconds, stuck")
        poe_bot.on_stuck_function()
      time.sleep(0.2)
      resurrect_panel.update()
      if resurrect_panel.visible is True:
        print("resurrect panel appeared")
        break

    i = 0
    while True:
      i += 1
      if i > 20:
        self.logger.writeLine("didnt change location after clicking on resurrect button after 20 iterations, stuck")
        poe_bot.on_stuck_function()
      resurrect_panel.update()
      if resurrect_panel.visible is False:
        print("resurrect panel disappeared")
        break
      current_area = poe_bot.backend.getPartialData()["area_raw_name"]
      print(f"current_area {current_area}")
      if current_area != initial_area_instance:
        break

      resurrect_panel.clickResurrect(town=False)

    if check_if_area_changed is True:
      i = 0
      while True:
        i += 1
        if i == 40:
          print("i == 40 in current_area != initial_area_instance, clicking again")
          resurrect_panel.update()
          if resurrect_panel.visible is True:
            print("resurrect panel is visible, clicking it again")
            resurrect_panel.clickResurrect(town=False)
        if i > 100:
          poe_bot.raiseLongSleepException("if i > 100:")
        time.sleep(0.1)
        print(f"waiting for area to change at {time.time()}")
        updated_data = self.getData()
        current_area = updated_data["area_raw_name"]
        game_state = updated_data["g_s"]
        if game_state == 1:
          print("main menu")
          self.on_disconnect_function()
        if current_area != initial_area_instance:
          break

    print(f"#resurrectAtCheckpoint return {time.time()}")
    time.sleep(random.randint(20, 40) / 10)


class Poe2Bot(PoeBot):
  def __init__(self, unique_id, remote_ip, debug=False, password=None):
    super().__init__(unique_id, remote_ip, debug, password)

    from .ui import Ui2

    self.ui = Ui2(self)

  def respawnAtCheckPoint(self):
    poe_bot = self
    poe_bot.bot_controls.keyboard.tap("DIK_ESCAPE")
    time.sleep(random.randint(40, 80) / 100)
    pos_x, pos_y = random.randint(450, 550), random.randint(289, 290)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(40, 80) / 100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30, 60) / 100)

    pos_x, pos_y = random.randint(580, 640), random.randint(408, 409)
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    time.sleep(random.randint(20, 80) / 100)
    poe_bot.bot_controls.mouse.click()
    time.sleep(random.randint(30, 60) / 100)
    return True
