from ..build import *

import time
import numpy as np

import sys
sys.path.append("...")
from utils.skill import SKILL_KEYS_WASD, Skill
from utils.utils import createLineIteratorWithValues, getAngle

class Build(Build):
  def __init__(self, poe_bot: "PoeBot"):
    super().__init__(poe_bot)
    self.attack_travel_distance = 200  # adjust it
    # find tempest flurry
    # only one on keyboard
    attack_button = None
    print("looking for Bow Shot button on keyboard")
    for i in range(3, 8):
      print(self.poe_bot.game_data.skills.internal_names[i])
      if self.poe_bot.game_data.skills.internal_names[i] == "player_melee_bow":
        attack_button = SKILL_KEYS_WASD[i]
        print(f"Bow Shot button is {attack_button}")
        break
    if attack_button is None:
      poe_bot.raiseLongSleepException("set to wasd, press it on qwert")
    self.attacking_skill = Skill(poe_bot=poe_bot, skill_index=self.poe_bot.game_data.skills.internal_names.index("player_melee_bow"))
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  """
  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.useFlasks()
    hold_attack = False
    nearby_enemy = next((e for e in poe_bot.game_data.entities.attackable_entities if e.isInRoi() and e.isInLineOfSight()), None)
    while True:
      print(f"nearby enemy {nearby_enemy}")
      if nearby_enemy:
        hold_attack = True
        break
      if mover.distance_to_target > self.attack_travel_distance:
        hold_attack = True
        break
      break
    while True:
      if hold_attack:
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
        self.attack_button_holder.holdFor(0.33)
        return True
      break

    return False
  """
  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    if ("Hideout" in poe_bot.game_data.area_raw_name):
      return False
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      min_hold_duration = random.randint(25, 55) / 100

      nearby_enemies = list(filter(lambda e: e.isInRoi() and e.distance_to_player < 300, poe_bot.game_data.entities.attackable_entities))
      #print(f"nearby_enemies: {nearby_enemies}")

      entities_to_hold_skill_on: list[Entity] = []
      if nearby_enemies:
        for _ in range(1):
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
          min_hold_duration = 0.1
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.press()
        entities_to_hold_skill_on[0].hover()
        print(f"self.attacking_skill.getCastTime() {self.attacking_skill.getCastTime()}")
        hold_duration = self.attacking_skill.getCastTime() * random.randint(25, 35) / 10
        # hold_duration = random.randint(int(self.attacking_skill.getCastTime() * 120), int(self.attacking_skill.getCastTime() * 160))/100
        print(f"hold_duration {hold_duration}")
        while time.time() - hold_duration < hold_start_time:
          poe_bot.refreshInstanceData()
          self.auto_flasks.useFlasks()
          entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id in entities_to_hold_skill_on_ids), None)
          if entity_to_kill:
            entity_to_kill.hover()
          else:
            if not time.time() + 0.1 > hold_start_time + min_hold_duration:
              time.sleep(0.1)
            break
        self.attacking_skill.release()
        return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
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
      self.attacking_skill.press()
      entity_to_kill.hover()
      time.sleep(0.1)
      self.attacking_skill.release()
      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    return True