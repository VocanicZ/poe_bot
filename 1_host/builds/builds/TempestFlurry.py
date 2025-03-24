from ..build import *

import time
import numpy as np

import sys
sys.path.append('...')
if TYPE_CHECKING:
  from utils.combat import ButtonHolder
from utils.skill import SKILL_KEYS_WASD
from utils.utils import createLineIteratorWithValues

class Build(Build):
  def __init__(self, poe_bot: "PoeBot"):
    super().__init__(poe_bot)
    self.tempest_flurry_travel_distance = 20  # adjust it
    # find tempest flurry
    # only one on keyboard
    flurry_button = None
    print("looking for tempest flurry button on keyboard")
    for i in range(3, 8):
      if self.poe_bot.game_data.skills.internal_names[i] == "tempest_flurry":
        flurry_button = SKILL_KEYS_WASD[i]
        print(f"flurry button is {flurry_button}")
        break
    if flurry_button is None:
      poe_bot.raiseLongSleepException("set to wasd, press it on qwert")
    self.tempest_flurry_button_holder: "ButtonHolder" = ButtonHolder(self.poe_bot, flurry_button, max_hold_duration=0.33)
    text = "###README### \nButtonHolder class has an issue, it basically sends the hold action to the machine, but not checks if it's registered in poe. if in somehow your poe window will lag and wont register the hold action, itll think that its holding it, there was an issue when i was testing cwdt. i was managed to deal with it by checking the history of poe_bot.game_data.skills.total_uses[self.build.barrier_invocation.skill_index], so if the value isnt changed for several cycles, it means that the button isnt holding"
    for z in range(10):
      print(text)
    # override mover.stopMoving, so itll release tempest flurry as well
    tempset_flurry_button_holder = self.tempest_flurry_button_holder

    def customStopMoving(self):
      q = [lambda: self.__class__.stopMoving(self), lambda: tempset_flurry_button_holder.forceStopPress()]
      random.shuffle(q)
      while len(q) != 0:
        action = q.pop()
        action()

    self.poe_bot.mover.stopMoving = customStopMoving.__get__(self.poe_bot.mover)

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.useFlasks()
    hold_flurry = False
    nearby_enemy = next((e for e in poe_bot.game_data.entities.attackable_entities if e.isInRoi() and e.isInLineOfSight()), None)
    while True:
      if nearby_enemy:
        hold_flurry = True
        break
      if mover.distance_to_target > self.tempest_flurry_travel_distance:
        hold_flurry = True
        break
      break
    while True:
      if hold_flurry:
        pos_x_to_go, pos_y_to_go = mover.nearest_passable_point[0], mover.nearest_passable_point[1]
        # if no enemies around, make a check if it's direct
        if nearby_enemy is not None:
          path_values = createLineIteratorWithValues(
            (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go), poe_bot.game_data.terrain.passable
          )
          path_without_obstacles = np.all(path_values[:, 2] > 0)
          if not path_without_obstacles:
            break

        screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(pos_y_to_go, pos_x_to_go)
        screen_pos_x, screen_pos_y = poe_bot.game_window.convertPosXY(screen_pos_x, screen_pos_y)
        poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, False)
        self.tempest_flurry_button_holder.holdFor(0.33)
        return True
      break

    return False

  def killUsual(self, entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    poe_bot = self.poe_bot
    entity_to_kill_id = entity.id
    self.useFlasks()
    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("[build.killUsual] cannot find desired entity to kill")
      return True
    if entity_to_kill.life.health.current == 0:
      print("[build.killUsual] entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      print("[build.killUsual] getting closer in killUsual")
      return False
    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    while True:
      poe_bot.refreshInstanceData()
      self.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("[build.killUsual] cannot find desired entity to kill")
        break
      print(f"[build.killUsual] entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current == 0:
        print("[build.killUsual] entity is dead")
        break
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("[build.killUsual] getting closer in killUsual ")
        break
      entity_to_kill.hover()
      self.tempest_flurry_button_holder.holdFor(0.33)
      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    return True