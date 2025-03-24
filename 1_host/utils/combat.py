from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
  from .gamehelper import Entity, Poe2Bot, PoeBot
  from .mover import Mover

import _thread
import random
import time
from math import dist
from typing import List

from .constants import AURAS_SKILLS_TO_BUFFS, CONSTANTS, FLASK_NAME_TO_BUFF, SKILL_KEYS, SKILL_KEYS_WASD
from .utils import extendLine
from ..builds import combatbuild
from ..builds.build import Build

NON_INSTANT_MOVEMENT_SKILLS = ["shield_charge", "whirling_blades"]

INSTANT_MOVEMENT_SKILLS = ["frostblink", "flame_dash"]

class CombatModule:
  build: Build

  def __init__(self, poe_bot: PoeBot, build: str = None) -> None:
    self.poe_bot = poe_bot
    if build:
      self.build = combatbuild.getBuild(build)(poe_bot)
    else:
      print("build is not assigned, using any functions may throw errors")
    self.entities_to_ignore_path_keys: List[str] = []
    self.aura_manager = AuraManager(poe_bot=poe_bot)

  def assignBuild(self, build: str):
    self.build = combatbuild.getBuild(build)(self.poe_bot)

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

class AutoFlasks:
  def __init__(self, poe_bot: PoeBot, hp_thresh=0.5, mana_thresh=0.5, pathfinder=False, life_flask_recovers_es=False) -> None:
    self.poe_bot = poe_bot
    self.hp_thresh = hp_thresh
    self.mana_thresh = mana_thresh
    self.utility_flasks_delay = 1
    self.life_flasks_delay = 1
    self.mana_flasks_delay = 1
    self.flask_use_time = [0, 0, 0, 0, 0]
    self.can_use_flask_after_by_type = {
      "utility": 0,
      "mana": 0,
      "life": 0,
    }
    self.pathfinder = pathfinder
    self.life_flask_recovers_es = life_flask_recovers_es
    self.utility_flasks_use_order_reversed = random.choice([True, False])
    self.flask_delay = lambda: random.uniform(0.100, 0.200)

  def useFlask(self, flask_index, flask_type="utility"):
    time_now = time.time()
    self.can_use_flask_after_by_type[flask_type] = time_now + random.randint(100, 200) / 1000
    self.poe_bot.bot_controls.keyboard.pressAndRelease(f"DIK_{flask_index + 1}", delay=random.randint(15, 35) / 100, wait_till_executed=False)
    self.flask_use_time[flask_index] = time_now

  def useFlasks(self):
    if self.useLifeFlask() is True:
      return True
    if self.useManaFlask() is True:
      return True
    if self.useUtilityFlasks() is True:
      return True
    return False

  def useUtilityFlasks(self):
    poe_bot = self.poe_bot
    time_now = time.time()
    # to prevent it from insta flask usage
    if time_now < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.UTILITY]:
      return False

    sorted_flasks = sorted(poe_bot.game_data.player.utility_flasks, key=lambda f: f.index, reverse=self.utility_flasks_use_order_reversed)

    # for flask in poe_bot.game_data.player.utility_flasks:
    for flask in sorted_flasks:
      flask_related_buff = FLASK_NAME_TO_BUFF.get(flask.name, None)
      if flask_related_buff is None:
        continue
      if flask_related_buff == "flask_effect_life" or flask_related_buff == "flask_effect_mana":
        continue
      try:
        if time_now - self.flask_use_time[flask.index] < self.utility_flasks_delay or time_now - self.flask_use_time[flask.index] < 0.5:
          continue
      except Exception:
        try:
          poe_bot.logger.writeLine(f"flask bug {flask.index} {self.flask_use_time}")
        except Exception:
          poe_bot.logger.writeLine("flask bug couldnt catch")
        continue
      # check if flask buff is presented
      if flask_related_buff in poe_bot.game_data.player.buffs:
        continue
      # if avaliable on panel
      if flask.can_use is False:
        continue

      # else tap on flask
      #print(f"[AutoFlasks] using utility flask {flask.name} {flask.index} at {time.time()}")
      self.useFlask(flask.index)
      # if tapped, return, so it wont look like a flask macro
      return True

    return False

  def useLifeFlask(self):
    poe_bot = self.poe_bot
    need_to_use_flask = False
    if self.life_flask_recovers_es is True:
      health_component = poe_bot.game_data.player.life.energy_shield
    else:
      health_component = poe_bot.game_data.player.life.health
    #print(f"[AutoFlasks.useLifeFlask] {health_component.getPercentage()} {self.hp_thresh}")
    # life flask
    if self.pathfinder is True:
      # print(f'lifeflask pf')
      if "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs:
        print("[AutoFlasks] using lifeflask pf cos not in buffs")
        need_to_use_flask = True
      elif self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] < time.time():
        print("[AutoFlasks] using life flask pf upfront")
        need_to_use_flask = True
      if need_to_use_flask is True:
        avaliable_life_flask = next((f for f in poe_bot.game_data.player.life_flasks if f.can_use is not False), None)
        if avaliable_life_flask is not None:
          if avaliable_life_flask.index > 5 or avaliable_life_flask.index < 0:
            return False
          print(f"[AutoFlasks] using lifeflask pf {avaliable_life_flask.name} {avaliable_life_flask.index}")
          self.useFlask(avaliable_life_flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + random.randint(270, 330) / 100
          return True
        else:
          print("[AutoFlasks] dont have any avaliable life flask for pf")
          return False
    else:
      if health_component.getPercentage() < self.hp_thresh:
        # if we already have life flask
        if (
          "flask_effect_life" not in poe_bot.game_data.player.buffs
          and "flask_effect_life_not_removed_when_full" not in poe_bot.game_data.player.buffs
        ):
          if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
            print("[AutoFlasks] reached hp thresh but wont use life flask cos cd")
            return False
          for flask in poe_bot.game_data.player.life_flasks:
            if flask.can_use is True:
              if flask.index > 5 or flask.index < 0:
                continue
              print(f"[AutoFlasks] using life flask {flask.name} {flask.index} {type(flask.index)}")
              self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.LIFE)
              self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE] = time.time() + (random.randint(40, 60) / 100)
              return True
    return False

  def useManaFlask(self):
    poe_bot = self.poe_bot
    if len(poe_bot.game_data.player.mana_flasks) == 0:
      return False
    # mana flask
    if poe_bot.game_data.player.life.mana.getPercentage() < self.mana_thresh:
      # if we already have mana flask
      if (
        "flask_effect_mana" not in poe_bot.game_data.player.buffs and "flask_effect_mana_not_removed_when_full" not in poe_bot.game_data.player.buffs
      ):
        if time.time() < self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.LIFE]:
          print("[AutoFlasks] reached mana thresh but wont use life flask cos cd")
          return False
        for flask in poe_bot.game_data.player.mana_flasks:
          if flask.index > 5 or flask.index < 0:
            continue
          print(f"[AutoFlasks] using mana flask {flask.name} {flask.index}")
          self.useFlask(flask.index, flask_type=CONSTANTS.FLASKS.FLASK_TYPES.MANA)
          self.can_use_flask_after_by_type[CONSTANTS.FLASKS.FLASK_TYPES.MANA] = time.time() + (random.randint(40, 60) / 100)
          return True

    return False

class AuraManager:
  def __init__(self, poe_bot: PoeBot) -> None:
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
  def __init__(self, poe_bot: PoeBot = None) -> None:
    pass

# Skill bases
class Skill:
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="_deprecated",
    display_name="unnamed_skill",
    min_mana_to_use=0,
    sleep_multiplier=0.5,  # if skill will have cast time, it will sleep for some time
    mana_cost=0,
    life_cost=0,
  ) -> None:
    self.poe_bot = poe_bot
    self.skill_index = skill_index
    self.display_name = display_name
    self.min_mana_to_use = min_mana_to_use
    self.sleep_multiplier = sleep_multiplier
    self.overriden_cast_time = None
    self.mana_cost = mana_cost
    self.life_cost = life_cost
    self.holding = False

    bot_controls = self.poe_bot.bot_controls
    controller_keys = {
      "keyboard": {
        "press": bot_controls.keyboard_pressKey,
        "release": bot_controls.keyboard_releaseKey,
        "tap": bot_controls.keyboard.pressAndRelease,
      },
      "mouse": {
        "press": bot_controls.mouse.press,
        "release": bot_controls.mouse.release,
        "tap": bot_controls.mouse.click,
      },
    }

    if self.poe_bot.mover.move_type == "wasd":
      self.skill_key_raw = SKILL_KEYS_WASD[self.skill_index]
    else:
      self.skill_key_raw = SKILL_KEYS[self.skill_index]

    self.hold_ctrl = False
    key_type = "mouse"
    if "DIK" in self.skill_key_raw:
      key_type = "keyboard"
      if "CTRL" in self.skill_key_raw:
        self.hold_ctrl = True

    if self.hold_ctrl is True:
      self.skill_key = self.skill_key_raw.split("+")[1]
    else:
      self.skill_key = self.skill_key_raw

    self.key_type = key_type
    self.tap_func = controller_keys[key_type]["tap"]
    self.press_func = controller_keys[key_type]["press"]
    self.release_func = controller_keys[key_type]["release"]

  def update(self):
    """
    updates the info about last successful usage
    """
    pass

  def tap(self, wait_till_executed=True, delay=random.randint(5, 20) / 100, update=True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
      wait_till_executed = True  # to prevent it from missclicking
    self.tap_func(button=self.skill_key, wait_till_executed=wait_till_executed, delay=delay)
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    if update is not False:
      self.update()

  def press(self, wait_till_executed=True, update=True):
    """
    for holding the button, smth like LA spam on some mob
    """
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_pressKey("DIK_LCONTROL")
    self.press_func(button=self.skill_key)
    self.holding = True
    if update is not False:
      self.update()

  def release(self, wait_till_executed=True):
    if self.hold_ctrl is True:
      self.poe_bot.bot_controls.keyboard_releaseKey("DIK_LCONTROL")
    self.release_func(button=self.skill_key)
    self.holding = False

  def checkIfCanUse(self):
    if self.min_mana_to_use != 0 and self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use:
      print(f"[Skill] cant use skill {self.display_name} cos self.poe_bot.game_data.player.life.mana.current < self.min_mana_to_use")
      return False
    if self.poe_bot.game_data.skills.can_use_skills_indexes_raw[self.skill_index] == 0:
      print(f"[Skill] cant use skill {self.display_name} cos 0 in can_use_skills_indexes_raw")
      return False
    return True

  def use(self, grid_pos_x=0, grid_pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    """
    -wait_for_execution: 1
    -force: if True, itll ignore check skill usage on panel

    """
    poe_bot = self.poe_bot
    bot_controls = poe_bot.bot_controls
    print(f"[Skill {self.display_name}] using  at {time.time()}")
    if force is not True and self.checkIfCanUse() is not True:
      return False
    if updated_entity is not None or grid_pos_x != 0 or grid_pos_y != 0:  # if we need to move a mouse
      if updated_entity is not None:  # if its an entity
        screen_pos_x, screen_pos_y = updated_entity.location_on_screen.x, updated_entity.location_on_screen.y
      else:
        screen_pos_x, screen_pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=grid_pos_y, x=grid_pos_x)
      screen_pos_x, screen_pos_y = poe_bot.convertPosXY(screen_pos_x, screen_pos_y)
      bot_controls.mouse.setPosSmooth(screen_pos_x, screen_pos_y, wait_till_executed=False)
    start_time = time.time()
    if wait_for_execution is True:
      if self.overriden_cast_time:
        cast_time = self.overriden_cast_time
      else:
        cast_time = self.getCastTime()
      time_to_sleep = start_time - time.time() + cast_time
      if cast_time > 0:
        self.press(wait_till_executed=wait_for_execution, update=False)
        time.sleep(time_to_sleep * self.sleep_multiplier * (random.randint(9, 11) / 10))
        self.release(wait_till_executed=wait_for_execution)
      else:
        self.tap(wait_till_executed=wait_for_execution, update=False)
    else:
      self.tap(wait_till_executed=wait_for_execution, update=False)
    self.update()
    print(f"[Skill {self.display_name}] successfully used  at {time.time()}")
    return True

  def moveThenUse(self, grid_pos_x=0, grid_pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, use_first=False):
    # hover if needed
    # send press skill button
    # wait (shorter)
    # move
    # return True
    # send release skill button

    def use_func():
      return self.use(grid_pos_x, grid_pos_y, updated_entity, False, force)

    def move_func():
      return self.poe_bot.mover.move()

    """
    - #TODO check if it's possible to execute use func, like skill is executable and whatever
    - #TODO adjust the time, if wait_for_execution == True so itll:
      either cast skill, move, wait till skill cast time
      or move, release mouse(if mover.move_type == mouse), cast, wait till skill cast time 
    """

    queue = []
    queue.append(use_func)
    if use_first is True:
      queue.insert(-1, move_func)
    else:
      queue.insert(0, move_func)
    return True

  def getCastTime(self):
    return self.poe_bot.game_data.skills.cast_time[self.skill_index]

  def convertToPos(self, pos_x, pos_y, entity: Entity = None):
    if entity is not None:
      x, y = entity.grid_position.x, entity.grid_position.y
    else:
      x, y = pos_x, pos_y
    return x, y

class AreaSkill(Skill):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="tipo chtobi potom uzat skill po ego internal name",
    display_name="AreaSkill",
    area=15,
    duration=4,
  ) -> None:
    self.last_use_location = [0, 0]  # x, y
    self.last_use_time = 0
    self.area = area
    self.duration = duration
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_location = [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y]
    self.last_use_time = time.time()

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    dot_duration = self.duration
    if (
      dist(
        [self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y], [self.last_use_location[0], self.last_use_location[1]]
      )
      > self.area
    ):
      self.last_use_time = 0
    if time.time() - self.last_use_time < dot_duration:
      return False
    res = super().use(pos_x, pos_y, updated_entity, wait_for_execution, force=force)
    if res is True:
      x, y = self.convertToPos(pos_x, pos_y, updated_entity)
      self.last_use_location = [x, y]
    return res

class SkillWithDelay(Skill):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="SkillWithDelay",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
  ) -> None:
    self.min_delay = min_delay
    self.delay_random = delay_random
    self.can_use_earlier = can_use_earlier

    self.last_use_time = 0
    self.can_be_used_after = 0

    self.internal_cooldown = random.randint(100, 125) / 100
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_mana_to_use)

  def update(self):
    self.last_use_time = time.time()
    if self.can_use_earlier is not False:
      _rv = [1, 0, -1]
    else:
      _rv = [1, 0]
    self.can_be_used_after = self.last_use_time + self.min_delay + random.choice(_rv) * self.delay_random * self.min_delay
    print(f"[SkillWithDelay {self.display_name}]  can be used after {self.can_be_used_after} {self.last_use_time} {self.min_delay}")

  def canUse(self, force=False):
    if force is not True and time.time() < self.can_be_used_after:
      return False
    if force is True and time.time() - self.last_use_time < self.internal_cooldown:
      print(f"[SkillWithDelay {self.display_name}] internal cooldown on force use")
      return False
    return True

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.canUse(force) is not True:
      return False
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, False)

class MinionSkillWithDelay(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="SkillWithDelay",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
    minion_path_key: str | None = None,
  ) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)
    self.minion_path_key = minion_path_key

  def getMinionsCountInRadius(self, radius: int = 150) -> int:
    if self.minion_path_key is None:
      return 0
    else:
      return len(
        list(
          filter(
            lambda e: e.life.health.current != 0 and not e.is_hostile and e.distance_to_player < radius and self.minion_path_key in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
      )

class MovementSkill(Skill):
  def __init__(
    self, poe_bot: PoeBot, skill_index: int, skill_name="", display_name="MovementSkill", min_delay=random.randint(30, 40) / 10, can_extend_path=True
  ) -> None:
    self.min_delay = min_delay
    self.last_use_time = 0
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name)

  def update(self):
    self.last_use_time = time.time()

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path=True):
    path_without_obstacles = False
    if time.time() - self.last_use_time < self.min_delay:
      return False
    if pos_x != 0 or updated_entity is not None:
      x, y = self.convertToPos(pos_x, pos_y, updated_entity)
      distance_to_next_step = dist((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
      print(f"[Combat Movement Skill] distance_to_next_step {distance_to_next_step}")
      if distance_to_next_step < self.min_move_distance:
        return False
      path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
      print(f"[Combat Movement Skill] path_without_obstacles {path_without_obstacles}")
      if path_without_obstacles is not True:
        return False
      if self.can_extend_path is not False and extend_path is not False:
        pos_x, pos_y = extendLine((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
      else:
        pos_x, pos_y = x, y
    if path_without_obstacles:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
    else:
      return False

class MovementSkill_new(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="",
    display_name="MovementSkill",
    min_delay=random.randint(30, 40) / 10,
    delay_random=0.1,
    min_mana_to_use=0,
    can_use_earlier=True,
    can_extend_path=True,
  ) -> None:
    self.jump_multi = 2
    self.min_move_distance = 20
    self.can_extend_path = can_extend_path
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use, can_use_earlier)

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False, extend_path=True, use_as_movement_skill=True):
    if self.canUse(force) is not True:
      return False

    if use_as_movement_skill is not False:
      if pos_x != 0 or updated_entity is not None:
        x, y = self.convertToPos(pos_x, pos_y, updated_entity)
        distance_to_next_step = dist((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y))
        print(f"[Combat Movement Skill] distance_to_next_step {distance_to_next_step}")
        if distance_to_next_step < self.min_move_distance:
          return False
        path_without_obstacles = self.poe_bot.game_data.terrain.checkIfPointIsInLineOfSight(x, y)
        print(f"[Combat Movement Skill] path_without_obstacles {path_without_obstacles}")
        if path_without_obstacles is not True:
          return False
        if self.can_extend_path is not False and extend_path is not False:
          pos_x, pos_y = extendLine((self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (x, y), self.jump_multi)
        else:
          pos_x, pos_y = x, y
      if path_without_obstacles:
        return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)
      else:
        return False
    else:
      return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)

class BlessingSkill(SkillWithDelay):
  def __init__(
    self,
    poe_bot: PoeBot,
    skill_index: int,
    skill_name="tipo chtobi potom uzat skill po ego internal name",
    display_name="SkillWithDelay",
    min_delay=4,
    delay_random=0.1,
    min_mana_to_use=0,
  ) -> None:
    super().__init__(poe_bot, skill_index, skill_name, display_name, min_delay, delay_random, min_mana_to_use)
    self.buff_name = AURAS_SKILLS_TO_BUFFS[display_name]

  def use(self, pos_x=0, pos_y=0, updated_entity: Entity = None, wait_for_execution=True, force=False):
    if self.buff_name not in self.poe_bot.game_data.player.buffs:
      print(f"[Blessing skill] {self.buff_name} is not in buff list, forcing to cast it")
      force = True
    return super().use(pos_x, pos_y, updated_entity, wait_for_execution, force)

class Aura(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)

class MinionSkill(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)

class AttackingSkill(Skill):
  def __init__(self, poe_bot: PoeBot, bind_key=None, use_function=None, use_delay=4, skill_type=1, name="unnamed_skill", mana_cost=0) -> None:
    super().__init__(poe_bot, bind_key, use_function, use_delay, skill_type, name, mana_cost)

# poe2
class DodgeRoll(SkillWithDelay):
  def __init__(self, poe_bot: PoeBot):
    super().__init__(
      poe_bot=poe_bot,
      skill_index=3,
      skill_name="",
      display_name="DodgeRoll",
      min_delay=0.1,
      delay_random=0.1,
      min_mana_to_use=0,
      can_use_earlier=True,
    )
    self.skill_key = "DIK_SPACE"
    self.tap_func = poe_bot.bot_controls.keyboard.pressAndRelease
    self.press_func = poe_bot.bot_controls.keyboard_pressKey
    self.release_func = poe_bot.bot_controls.keyboard_releaseKey
    self.checkIfCanUse = lambda *args, **kwargs: True
    self.getCastTime = lambda *args, **kwargs: 0.5

class ButtonHolder:
  def __init__(self, poe_bot: Poe2Bot, button: str, max_hold_duration=10.0, custom_break_function=lambda: False):
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