from ..build import *

import sys
sys.path.append("...")
from utils.skill import SkillWithDelay, DodgeRoll

GENERIC_BUILD_ATTACKING_SKILLS = [
  "spark",
  "lightning_arrow",
  "tempest_flurry",
  "storm_wave",
  "quarterstaff_combo_attack",
]

class GenericBuild2(Build):
  def __init__(self, poe_bot):
    super().__init__(poe_bot)
    self.last_action_time = 0
    self.attacking_skill: SkillWithDelay = None  # smth like la or sparks
    self.supporting_skill: SkillWithDelay = None  # smth like lightning rod or flame wall

    main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s in GENERIC_BUILD_ATTACKING_SKILLS), None)
    if main_attacking_skill is None:
      self.poe_bot.raiseLongSleepException(f"[GenericBuild2.init] couldnt find skills from {GENERIC_BUILD_ATTACKING_SKILLS}")

    print(f"[GenericBuild2] main attacking skill {main_attacking_skill}")
    skill_index = self.poe_bot.game_data.skills.internal_names.index(main_attacking_skill)
    self.attacking_skill = SkillWithDelay(
      poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1, 5) / 100, display_name=main_attacking_skill, min_mana_to_use=0
    )
    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)
    self.dodge_roll.min_delay = 0.75

  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # _t = time.time()
    # if self.dodge_roll.last_use_time + 0.35 > _t or self.pconc.last_use_time + (self.pconc.getCastTime() / 2) > _t:
    #   print(f'probably casting smth atm')
    #   return False
    self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    if len(nearby_enemies) == 0:
      return False

    nearby_enemies.sort(key=lambda e: e.distance_to_player)
    self.attacking_skill.use(updated_entity=nearby_enemies[0], wait_for_execution=False)
    return False

  def killUsual(self, entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    poe_bot = self.poe_bot
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()
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
    self.attacking_skill.press(wait_till_executed=False)
    poe_bot.last_action_time = 0
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
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
      else:
        print("[build.killUsual] kiting away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if time.time() > start_time + max_kill_time_sec:
        print("[build.killUsual] exceed time")
        break
    self.attacking_skill.release()
    return True

class GenericBuild2Cautious(GenericBuild2):
  def usualRoutine(self, mover: Mover):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    can_do_action = True
    moving_back = False
    dodging = False

    _t = time.time()
    if self.dodge_roll.last_use_time + 0.35 > _t or self.attacking_skill.last_use_time + (self.attacking_skill.getCastTime() / 2) > _t:
      print("probably casting smth atm")
      can_do_action = False
    if can_do_action:
      self.useBuffs()
    nearby_enemies = list(filter(lambda e: e.isInRoi() and e.isInLineOfSight(), poe_bot.game_data.entities.attackable_entities))
    if len(nearby_enemies) == 0:
      return moving_back
    nearby_enemies.sort(key=lambda e: e.distance_to_player)
    enemies_in_radius_50 = list(filter(lambda e: e.distance_to_player < 50, nearby_enemies))
    if len(enemies_in_radius_50) > 1:
      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      poe_bot.mover.move(*go_back_point)
      moving_back = True
      if can_do_action and len(list(filter(lambda e: e.distance_to_player < 15, enemies_in_radius_50))) != 0:
        dodging = self.dodge_roll.use(wait_for_execution=False)
    if can_do_action and dodging is not True:
      self.attacking_skill.use(updated_entity=nearby_enemies[0], wait_for_execution=False)
    return moving_back