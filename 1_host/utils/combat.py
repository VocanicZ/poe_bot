from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .poebot import Poe2Bot, PoeBot
  from .entity import Entity
  from .mover import Mover

import _thread
import random
import time
from typing import List

from .constants import AURAS_SKILLS_TO_BUFFS,  SKILL_KEYS
from .skill import BlessingSkill

import sys
sys.path.append("..")
from builds.combatbuild import getBuild
from builds.build import Build

class CombatModule:
  build: Build

  def __init__(self, poe_bot: "PoeBot", build: str = None) -> None:
    self.poe_bot = poe_bot
    if build:
      self.build = getBuild(build)(poe_bot)
      print(f"assigned build {build}")
    else:
      print("build is not assigned, using any functions may throw errors")
    self.entities_to_ignore_path_keys: List[str] = []
    self.aura_manager = AuraManager(poe_bot=poe_bot)

  def assignBuild(self, build: str):
    self.build = getBuild(build)(self.poe_bot)

  def killUsualEntity(self, entity: Entity, min_hp=0, max_kill_time_sec=90, is_strong=False, step_size=random.randint(30, 35)):
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f"#killUsualEntity {entity}")
    first_attack_time = None
    # if "/LeagueBestiary/" in entity['Path']:
    #   print(f'/LeagueBestiary/ in entity path, forcing min_hp = 1')
    #   min_hp = 1
    if entity.life.health.current == min_hp:
      print("willing to kill dead entity")
      return True

    def killEntityFunctionForMover(mover: Mover):
      nonlocal first_attack_time
      print(f"first_attack_time {first_attack_time}")
      _t = time.time()
      res = build.killUsual(entity, is_strong, max_kill_time_sec)

      if res is False:
        res = build.usualRoutine(mover)

      elif res is True and first_attack_time is None:
        first_attack_time = _t
      return res

    def entityIsDead(mover: Mover):
      _t = time.time()

      entity_to_kill = list(filter(lambda e: e.id == entity.id, poe_bot.game_data.entities.attackable_entities))
      if len(entity_to_kill) != 0:
        entity_to_kill = entity_to_kill[0]
        print(f"check first_attack_time {first_attack_time}")
        if first_attack_time is not None:
          print(f"first_attack_time + max_kill_time_sec < _t {first_attack_time} + {max_kill_time_sec} < {_t}")
          if first_attack_time + max_kill_time_sec < _t:
            print(f"killUsualEntity max_kill_time_sec {max_kill_time_sec} passed, breaking")
            return True

        if min_hp != 0:
          if entity_to_kill.life.health.current <= min_hp:
            print(f"entity_to_kill.life.health.current <= min_hp <= {min_hp}")
            return True
        return False
      else:
        print("entities_to_kill not found, looks like dead")
        return True

    res = build.killUsual(entity, is_strong, max_kill_time_sec)
    if res is True:
      return True
    # get to entity first
    if entity.distance_to_player > 100:
      print("getting closer to entity")
      mover.goToEntitysPoint(
        entity_to_go=entity,
        min_distance=100,
        custom_continue_function=build.usualRoutine,
        # custom_break_function=entityIsDead,
        step_size=step_size,
      )

    print("killing it")
    # kill it
    mover.goToEntity(
      entity_to_go=entity,
      min_distance=-1,
      custom_continue_function=killEntityFunctionForMover,
      custom_break_function=entityIsDead,
      step_size=step_size,
    )

    is_dead = entityIsDead(mover=mover)
    return is_dead

  def killTillCorpseOrDisappeared(self, entity: Entity, clear_around_radius=40, max_kill_time_sec=300, step_size=random.randint(30, 35)):
    poe_bot = self.poe_bot
    mover = self.poe_bot.mover
    build = self.build
    entity_to_kill = entity
    entity_to_kill_id = entity_to_kill.id
    if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
      print("entity_to_kill is not attackable or not targetable, going to it and activating it")
      while True:
        res = mover.goToPoint(
          (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
          min_distance=20,
          custom_continue_function=build.usualRoutine,
          # custom_break_function=collectLootIfFound,
          release_mouse_on_end=False,
          step_size=step_size,
        )
        if res is None:
          break
      entity_to_kill = next((e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
      if entity_to_kill is None:
        print("entity_to_kill is None corpse disappeared:")
        return True
      last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
      while True:
        entity_to_kill = next((e for e in poe_bot.game_data.entities.all_entities if e.id == entity_to_kill_id), None)
        if entity_to_kill is None:
          print("entity_to_kill is None corpse disappeared:")
          return True

        if entity_to_kill.life.health.current == 0:
          print("entity_to_kill is dead")
          return True
        if entity_to_kill.is_targetable is False or entity_to_kill.is_attackable is False:
          print("boss is not attackable or not targetable, going to it clearing around it")
          killed_someone = self.clearLocationAroundPoint(
            {"X": entity_to_kill.grid_position.x, "Y": entity_to_kill.grid_position.y}, detection_radius=clear_around_radius
          )
          if killed_someone is False:
            point = poe_bot.game_data.terrain.pointToRunAround(
              point_to_run_around_x=last_boss_pos_x,
              point_to_run_around_y=last_boss_pos_y,
              distance_to_point=15,
            )
            mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
            poe_bot.refreshInstanceData()
        else:
          print("boss is attackable and targetable, going to kill it")
          self.killUsualEntity(entity_to_kill, max_kill_time_sec=30)
          last_boss_pos_x, last_boss_pos_y = entity_to_kill.grid_position.x, entity_to_kill.grid_position.y
    else:
      print("entity_to_kill is attackable and targetable, going to kill it")
      if entity_to_kill.distance_to_player > 40:
        while True:
          res = mover.goToPoint(
            (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
            min_distance=35,
            custom_continue_function=build.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=step_size,
            # possible_transition = self.current_map.possible_transition_on_a_way_to_boss
          )
          if res is None:
            break
      self.killUsualEntity(entity_to_kill)

  def clearLocationAroundPoint(self, point_to_run_around, detection_radius=20, till_no_enemies_around=False, ignore_keys=[]):
    """
    point_to_run_around
    {"X":1, "Y":1}
    """
    poe_bot = self.poe_bot
    mover = poe_bot.mover
    build = self.build
    print(f"#clearLocationAroundPoint around point {point_to_run_around} ignore_keys: {ignore_keys}")
    print(f"going to {point_to_run_around}")
    point_to_go = [point_to_run_around["X"], point_to_run_around["Y"]]
    mover.goToPoint(
      point=point_to_go, min_distance=40, release_mouse_on_end=False, custom_continue_function=build.usualRoutine, step_size=random.randint(25, 33)
    )
    poe_bot.last_action_time = 0

    def enemiesAroundPoint() -> List[Entity]:
      """
      returns entities around point
      """
      lower_x = point_to_run_around["X"] - detection_radius
      upper_x = point_to_run_around["X"] + detection_radius
      lower_y = point_to_run_around["Y"] - detection_radius
      upper_y = point_to_run_around["Y"] + detection_radius
      # enemies_around = list(filter(lambda entity:entity['IsTargetable'] is True and  entity['IsHostile'] is True and entity['GridPosition']['X'] > lower_x and entity['GridPosition']['X'] < upper_x and entity['GridPosition']['Y'] > lower_y and entity['GridPosition']['Y'] < upper_y ,  poe_bot.sorted_entities['alive_enemies']))
      enemies_around = list(
        filter(
          lambda e: e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y,
          poe_bot.game_data.entities.attackable_entities,
        )
      )
      enemies_around = list(filter(lambda e: e.isOnPassableZone(), enemies_around))
      # enemies_around = list(filter(lambda e: e.grid_position.x > lower_x and e.grid_position.x < upper_x and e.grid_position.y > lower_y and e.grid_position.y < upper_y ,  poe_bot.game_data.entities.attackable_entities))

      return enemies_around

    entities_to_kill = enemiesAroundPoint()
    if len(entities_to_kill) == 0:
      return False
    print(f"entities_to_kill around point {entities_to_kill} ")
    # in theory it may spawn essences with the same metadata but white, not rare
    killed_someone = False
    for entity in entities_to_kill:
      if any(list(map(lambda _k: _k in entity.path, ignore_keys))):
        print(f"skipping {entity.raw} cos its in ignore keys")
        continue
      killed_someone = True
      self.killUsualEntity(entity, min_hp=1, max_kill_time_sec=3)
    return killed_someone

  def clearAreaAroundPoint(self, point, detection_radius=20, till_no_enemies_around=False, ignore_keys=[]):
    point_dict = {"X": point[0], "Y": point[1]}
    return self.clearLocationAroundPoint(
      point_to_run_around=point_dict, detection_radius=detection_radius, till_no_enemies_around=till_no_enemies_around, ignore_keys=ignore_keys
    )

class AuraManager:
  def __init__(self, poe_bot: "PoeBot") -> None:
    self.poe_bot = poe_bot
    self.aura_skills = []
    self.blessing_skill: BlessingSkill = None

  def checkAuras(self):
    pass

  def activateAurasIfNeeded(self):
    """
    bool if activated
    """
    if not self.aura_skills:
      aura_keys = AURAS_SKILLS_TO_BUFFS.keys()
      self.aura_skills = []
      for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
        skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
        if skill_name in aura_keys:
          is_blessing = next(
            (
              sd
              for sd in self.poe_bot.game_data.skills.descriptions[skill_index]
              if "SkillIsBlessingSkill" in sd.keys() or "SupportGuardiansBlessingAuraOnlyEnabledWhileSupportMinionIsSummoned" in sd.keys()
            ),
            None,
          )
          if is_blessing:
            self.blessing_skill = BlessingSkill(poe_bot=self.poe_bot, skill_index=skill_index, skill_name=skill_name, display_name=skill_name)
            print(f"{skill_name} is blessing")
            continue
          self.aura_skills.append(skill_name)
      # self.aura_skills = list(filter(lambda skill_name: skill_name in aura_keys, self.poe_bot.game_data.skills.internal_names))
      self.aura_skills = set(self.aura_skills)
    auras_to_activate = []
    for skill in self.aura_skills:
      skill_effect = AURAS_SKILLS_TO_BUFFS[skill]
      if skill_effect in self.poe_bot.game_data.player.buffs:
        print(f"{skill} already activated")
      else:
        print(f"need to activate {skill}")
        auras_to_activate.append(skill)
    print(f"total need to activate {auras_to_activate}")
    if auras_to_activate:
      indexes_to_activate = list(map(lambda skill: self.poe_bot.game_data.skills.internal_names.index(skill), auras_to_activate))
      print(f"indexes to activate {indexes_to_activate}")
      keys_to_activate = list(map(lambda skill_index: SKILL_KEYS[skill_index], indexes_to_activate))
      print(f"keys to activate {keys_to_activate}")
      first_panel_skills = list(filter(lambda key: "DIK_" in key and "CTRL+" not in key, keys_to_activate))
      second_panel_skills = list(filter(lambda key: "CTRL+DIK_" in key, keys_to_activate))
      if second_panel_skills:
        self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
        time.sleep(random.randint(5, 15) / 100)
        for key in second_panel_skills:
          key_str = key.split("CTRL+")[1]
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10, 20) / 100)
        self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
        time.sleep(random.randint(20, 40) / 100)
      if first_panel_skills:
        for key in first_panel_skills:
          key_str = key
          self.poe_bot.bot_controls.keyboard.tap(key_str)
          time.sleep(random.randint(10, 20) / 100)
        time.sleep(random.randint(20, 40) / 100)
      return True
    return False

  def activateBlessingsIfNeeded(self):
    if self.blessing_skill:
      print(f"activating blessing {self.blessing_skill}")
      self.blessing_skill.use()

class CombatManager:
  def __init__(self, poe_bot: "PoeBot" = None) -> None:
    pass

class ButtonHolder:
  def __init__(self, poe_bot: "Poe2Bot", button: str, max_hold_duration=10.0, custom_break_function=lambda: False):
    self.poe_bot = poe_bot
    self.thread_finished = [False]
    self.can_hold_till = [0]
    self.custom_break_function = custom_break_function

    self.button = button
    self.press_func = poe_bot.bot_controls.keyboard_pressKey
    self.release_func = poe_bot.bot_controls.keyboard_releaseKey

    self.max_hold_duration = max_hold_duration

    self.keep_thread_till = 0.0
    self.terminate_thread_after_inactivity_secs = 2.0

    self.running = False

  def start(self):
    self.running = True
    poe_bot = self.poe_bot
    print(f"[ButtonHolder.start] started at {time.time()}")
    while self.thread_finished[0] is not True:
      if time.time() < self.can_hold_till[0]:
        if (self.button in poe_bot.bot_controls.keyboard.pressed) is False:
          print(f"pressing button {self.button}")
          self.press_func(self.button, False)
      else:
        if self.button in poe_bot.bot_controls.keyboard.pressed:
          print(f"releasing button {self.button}")
          self.release_func(self.button, False)

      if time.time() > self.keep_thread_till:
        print("terminating thread due to inactivity")
        break

      if self.custom_break_function() is True:
        print("breaking because of condition")
        break
      time.sleep(0.02)
    if self.button in poe_bot.bot_controls.keyboard.pressed:
      print(f"releasing button {self.button}")
      self.release_func(self.button, False)
    print(f"[ButtonHolder.start] finished at {time.time()}")
    self.running = False

  def keepAlive(self):
    self.keep_thread_till = time.time() + self.terminate_thread_after_inactivity_secs

  def forceStopPress(self):
    self.keepAlive()
    self.can_hold_till[0] = 0
    print("releasing")

  def holdFor(self, t: float):
    self.keepAlive()
    self.can_hold_till[0] = time.time() + t
    print(f"will hold till {self.can_hold_till[0]}")
    if self.running is not True:
      _thread.start_new_thread(self.start, ())