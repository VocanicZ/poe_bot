from ..build import *

import time
from math import dist
import numpy as np

from ...utils import createLineIteratorWithValues
from ...utils.combat import SkillWithDelay, SKILL_KEYS_WASD, DodgeRoll

class Build(Build):
  def __init__(self, poe_bot:PoeBot):
    super().__init__(poe_bot)
    self.auto_flasks.life_flask_recovers_es = True
    self.auto_flasks.hp_thresh = 0.75
    self.can_use_flask_after = 0.0
    self.barrier_charged_at = 0.0
    self.es_thresh_for_loop = 0.5
    self.stop_spamming_condition_func = lambda: poe_bot.game_data.player.life.energy_shield.getPercentage() < self.es_thresh_for_loop

    self.barrier_invocation: SkillWithDelay
    self.curse: SkillWithDelay
    self.demon_form: SkillWithDelay

    demon_form = next((s for s in poe_bot.game_data.skills.internal_names if s == "demon_transformation"), None)
    if demon_form:
      print("found demon form")
      skill_index = poe_bot.game_data.skills.internal_names.index("demon_transformation")
      self.demon_form = SkillWithDelay(poe_bot, skill_index)
      self.demon_form.overriden_cast_time = 0.1
    else:
      raise Exception("demon form not found")
    curse = next((s for s in poe_bot.game_data.skills.internal_names if s == "cold_weakness"), None)
    if curse:
      print("found curse")
      skill_index = poe_bot.game_data.skills.internal_names.index("cold_weakness")
      self.curse = SkillWithDelay(poe_bot, skill_index, min_delay=0.1)
    else:
      raise Exception("cwdt activator not found")

    barrier_button = next((s for s in poe_bot.game_data.skills.internal_names if s == "barrier_invocation"), None)
    for i in range(3, 8):
      if self.poe_bot.game_data.skills.internal_names[i] == "barrier_invocation":
        barrier_button = SKILL_KEYS_WASD[i]
        print(f"barrier button is {barrier_button}")
        break
    if barrier_button is None:
      poe_bot.raiseLongSleepException("barrier set to mouse, couldnt find barrier on keyboard qwert, press it on qwert")

    if barrier_button:
      print("found barrier_invocation")
      skill_index = poe_bot.game_data.skills.internal_names.index("barrier_invocation")
      self.barrier_invocation = SkillWithDelay(poe_bot, skill_index, min_delay=0.1)
    else:
      raise Exception("cwdt trigger not found")

    self.cwdt_loop = LoopController(poe_bot, self)

    self.dodge = DodgeRoll(self.poe_bot)

  def useFlasks(self):
    self.cwdt_loop.keepLoopingFor()

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.useFlasks()
    self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    pos_x_to_go, pos_y_to_go = mover.nearest_passable_point[0], mover.nearest_passable_point[1]
    if len(nearby_enemies) != 0:
      list(map(lambda e: e.calculateValueForAttack(), nearby_enemies))
      nearby_enemies.sort(key=lambda e: e.attack_value, reverse=True)
      # nearby_enemies.sort(key=lambda e: e.distance_to_player)
      nearby_enemies[0].hover(wait_till_executed=False)
    else:
      # move mouse towards direction
      screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(pos_y_to_go, pos_x_to_go)
      screen_pos_x, screen_pos_y = poe_bot.game_window.convertPosXY(screen_pos_x, screen_pos_y)
      poe_bot.bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, False)
    if self.isInDemonForm() is True and mover.distance_to_target > 50:
      # distance to next step on screen
      distance_to_next_step = dist((poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go))
      print(f"distance_to_next_step {distance_to_next_step}")
      if distance_to_next_step > 20:
        path_values = createLineIteratorWithValues(
          (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (pos_x_to_go, pos_y_to_go), poe_bot.game_data.terrain.passable
        )
        path_without_obstacles = np.all(path_values[:, 2] > 0)
        print(f"path_without_obstacles {path_without_obstacles}")
        if path_without_obstacles:
          mover.move(pos_x_to_go, pos_y_to_go)
          if self.dodge.use(wait_for_execution=False):
            return True
          return True

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

    keep_distance = 30  # if our distance is smth like this, kite
    start_time = time.time()
    kite_distance = random.randint(35, 45)
    reversed_run = random.choice([True, False])

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
      self.useBuffs()
      entity_to_kill.hover()
      if entity_to_kill.distance_to_player > keep_distance:
        print("[build.killUsual] kiting around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        poe_bot.mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
        if self.isInDemonForm() is True:
          self.dodge.use(wait_for_execution=False)
      else:
        print("[build.killUsual] kiting away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    return True
  
    def generateStacks(self, stacks_count=60):
    poe_bot = self.poe_bot
    demon_stacks = poe_bot.combat_module.build.getDemonFormStacks()
    while demon_stacks < stacks_count:
      poe_bot.refreshInstanceData()
      demon_stacks = self.getDemonFormStacks()
      print(f"[generateDemonFormStacks] generating stacks, {demon_stacks}/{stacks_count} ")
      is_barrier_charged = "invocation_skill_ready" in poe_bot.game_data.player.buffs

      if demon_stacks < 5 or is_barrier_charged is False:
        self.useFlasks()
      else:
        if poe_bot.game_data.player.life.energy_shield.getPercentage() < 0.65:
          self.auto_flasks.useFlasks()
        else:
          self.barrier_invocation.use()
        time.sleep(0.75)

  def getDemonFormStacks(self):
    poe_bot = self.poe_bot
    return len(list(filter(lambda b: b == "demon_form_buff", poe_bot.game_data.player.buffs)))

  def isInDemonForm(self):
    return "demon_form_spell_gem_buff" in self.poe_bot.game_data.player.buffs

class LoopController:
  def __init__(self, poe_bot: Poe2Bot, build):
    self.poe_bot = poe_bot
    self.running = False

    self.build: Build = build

    self.last_analyzed_timestamp = 0.0

    self.keep_thread_alive_till = 0.0
    self.hold_till = 0.0
    self.terminate_thread_after_inactivity_secs = 2.0
    self.terminate_thread_due_to_expired_data_secs = 0.33

  def start(self):
    poe_bot = self.poe_bot
    self.running = True
    print("[LoopController.start] thread starting")

    barrier_uses_history = [0 for x in range(10)]
    barrier_loop_running = False
    expected_change_history = [False for x in range(10)]
    change_result_history = [False for x in range(10)]

    def startLooping():
      pass

    while self.running:
      if time.time() > poe_bot.game_data.last_update_time + self.terminate_thread_due_to_expired_data_secs:
        # if time.time() + self.terminate_thread_due_to_expired_data_secs > poe_bot.game_data.last_update_time:
        print("[LoopController.start] terminating thread due to expired data")
        break

      if time.time() > self.keep_thread_alive_till:
        print("[LoopController] terminating thread due to inactivity")
        break

      if self.last_analyzed_timestamp == poe_bot.game_data.last_update_time:
        # nothing changed
        time.sleep(0.02)
        continue
      self.last_analyzed_timestamp = poe_bot.game_data.last_update_time

      barrier_uses_history.pop(0)
      barrier_uses = poe_bot.game_data.skills.total_uses[self.build.barrier_invocation.skill_index]
      barrier_uses_history.append(barrier_uses)

      expected_change_history.pop(0)
      expected_change_history.append(barrier_loop_running)

      change_result_history.pop(0)
      change_result_history.append(barrier_uses_history[-1] != barrier_uses_history[-2])
      # print(f'{barrier_uses_history}')
      # print(f'{expected_change_history}')
      # print(f'{change_result_history}')
      buffs = poe_bot.game_data.player.buffs
      is_ignited = "ignited" in buffs
      is_in_demon_form = "demon_form_spell_gem_buff" in buffs
      is_barrier_charged = "invocation_skill_ready" in buffs

      active_flask_effects_count = len(list(filter(lambda e: e == "flask_effect_life", poe_bot.game_data.player.buffs)))
      print(f"[BarrierInvocationInfernalist.useFlasks] flask_effects_active_count: {active_flask_effects_count}")

      pressed_smth = False
      if pressed_smth is False and is_in_demon_form is False:
        print("[BarrierInvocationInfernalist.useFlasks] need to activate demon form")
        if self.build.demon_form.canUse():
          self.build.demon_form.use()

      if (is_ignited or barrier_loop_running) and time.time() > self.build.can_use_flask_after:
        if active_flask_effects_count < 5:
          for flask in poe_bot.game_data.player.life_flasks:
            if flask.can_use is True:
              if flask.index > 5 or flask.index < 0:
                continue
              print(f"[AutoFlasks] using life flask {flask.name} {flask.index} {type(flask.index)}")
              self.poe_bot.bot_controls.keyboard.pressAndRelease(
                f"DIK_{flask.index + 1}", delay=random.randint(15, 35) / 100, wait_till_executed=False
              )
              self.build.can_use_flask_after = time.time() + random.uniform(0.40, 0.50)
              break
      else:
        self.build.auto_flasks.useFlasks()
      barrier_invocation_key = self.build.barrier_invocation.skill_key
      if self.build.stop_spamming_condition_func() is False:
        # if poe_bot.game_data.player.life.energy_shield.getPercentage() > 0.75:
        if barrier_loop_running is False and is_barrier_charged is False:
          print("barrier is not charged")
          self.build.curse.use()
        else:
          barrier_loop_running = True
          if (barrier_invocation_key in poe_bot.bot_controls.keyboard.pressed) is False:
            print(f"pressing button {barrier_invocation_key}")
            poe_bot.bot_controls.keyboard_pressKey(barrier_invocation_key, False)
            pressed_smth = True
      else:
        print(f"seems like hp is < {self.build.es_thresh_for_loop} cant do loop thing")
        if self.build.barrier_invocation.skill_key in poe_bot.bot_controls.keyboard.pressed:
          print(f"releasing button {self.build.barrier_invocation.skill_key}")
          poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)
          pressed_smth = True
          barrier_loop_running = False

      if barrier_loop_running:
        if all(expected_change_history[-3:]):
          changed_in_past = any(change_result_history[-3:])
          print(f"barrier running for 3+ cycles already {changed_in_past}")
          if changed_in_past is False:
            poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)
            barrier_loop_running = False

      time.sleep(0.05)

    print("[LoopController.start] thread finished")
    if self.build.barrier_invocation.skill_key in poe_bot.bot_controls.keyboard.pressed:
      print(f"releasing button {self.build.barrier_invocation.skill_key}")
      poe_bot.bot_controls.keyboard_releaseKey(self.build.barrier_invocation.skill_key, False)

    self.running = False
    self.last_analyzed_timestamp = 0

  def keepAlive(self):
    self.keep_thread_alive_till = time.time() + self.terminate_thread_after_inactivity_secs

  def keepLoopingFor(self, t=5.0):
    self.keepAlive()
    self.hold_till = time.time() + t
    if self.running is False:
      _thread.start_new_thread(self.start, ())

  def forceStopHolding(self):
    self.keepAlive()
    self.hold_till = 0.0
