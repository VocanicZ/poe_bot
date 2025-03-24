from ..build import *

from ...utils.combat import SkillWithDelay, NON_INSTANT_MOVEMENT_SKILLS, MovementSkill
from ...utils.utils import getAngle

GENERIC_BUILD_ATTACKING_SKILLS = [
  "spark",
  "lightning_arrow",
  "tempest_flurry",
  "storm_wave",
  "quarterstaff_combo_attack",
]

class GenericHitter(Build):
  # lightning strike, splitting steel, frost blates, motlen strike, smite
  """
  venom gyre
  """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    self.attacking_skill = None
    self.attacking_buff = None

    self.movement_skill = None
    self.instant_movement_skill = None

    self.blood_rage = None
    main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s in GENERIC_BUILD_ATTACKING_SKILLS), None)
    if main_attacking_skill is not None:
      attacking_buff = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
      if attacking_buff:
        print(f"[GenericHitter] attacking buff {attacking_buff}")
        skill_index = self.poe_bot.game_data.skills.internal_names.index(attacking_buff)
        self.attacking_buff = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=attacking_buff
        )
    else:
      main_attacking_skill = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
    if main_attacking_skill is not None:
      print(f"[GenericHitter] main attacking skill {main_attacking_skill}")
      skill_index = self.poe_bot.game_data.skills.internal_names.index(main_attacking_skill)
      self.attacking_skill = SkillWithDelay(
        poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(1, 5) / 100, display_name=main_attacking_skill, min_mana_to_use=0
      )
    else:
      self.poe_bot.raiseLongSleepException(
        f"[GenericHitter] couldnt find main attacking skill, skills are {self.poe_bot.game_data.skills.internal_names} "
      )
    blood_rage = next((s for s in self.poe_bot.game_data.skills.internal_names if s == "smite"), None)
    if blood_rage is not None:
      skill_index = self.poe_bot.game_data.skills.internal_names.index(blood_rage)
      self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=blood_rage)
    self.movement_skill = None  # "new_new_shield_charge"
    self.instant_movement_skill = None  # "flame_dash"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name == "":
        continue
      print(skill_name, skill_index)
      if skill_name == "blood_rage":
        self.blood_rage = SkillWithDelay(poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(30, 50) / 10, display_name=skill_name)
      elif skill_name in NON_INSTANT_MOVEMENT_SKILLS:
        self.movement_skill = MovementSkill(poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30, 50) / 100)
        if skill_name == "whirling_blades":
          self.instant_movement_skill = MovementSkill(
            poe_bot=poe_bot, skill_index=skill_index, display_name=skill_name, min_delay=random.randint(30, 50) / 100
          )
    super().__init__(poe_bot)

  def useBuffs(self):
    poe_bot = self.poe_bot
    if self.blood_rage is not None:
      if (
        "blood_rage" not in poe_bot.game_data.player.buffs
        and poe_bot.game_data.player.life.health.current / poe_bot.game_data.player.life.health.total > 0.7
      ):
        self.blood_rage.use()
        return True
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()
    # if we are moving
    if mover is not None:
      self.useBuffs()
      search_angle_half = 60
      min_hold_duration = random.randint(25, 55) / 100

      nearby_enemies = list(filter(lambda e: e.isInRoi() and e.distance_to_player < 30, poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")

      entities_to_hold_skill_on: list[Entity] = []
      if nearby_enemies:
        for iiii in range(1):
          time_now = time.time()
          nearby_visible_enemies = list(filter(lambda e: e.isInLineOfSight(), nearby_enemies))
          if not nearby_visible_enemies:
            break
          # didnt attack for a long time
          if self.attacking_skill.last_use_time + random.randint(20, 30) / 10 < time_now:
            print("didnt attack for a long time")
            entities_to_hold_skill_on = sorted(nearby_visible_enemies, key=lambda e: e.distance_to_player)
            min_hold_duration = 0.1
            break
          # if surrounded
          # really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_visible_enemies))
          # if len(really_close_enemies) > 5:
          #   print(f'surrounded')
          #   entities_to_hold_skill_on = really_close_enemies
          #   break
          # on the way
          if self.attacking_skill.last_use_time + random.uniform(1.0, 1.5) < time_now:
            p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
            p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
            enemies_in_sector = list(
              filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, nearby_visible_enemies)
            )
            if enemies_in_sector:
              print("on the way")
              min_hold_duration = 0.1
              entities_to_hold_skill_on = enemies_in_sector
          break
      if entities_to_hold_skill_on:
        entities_to_hold_skill_on_ids = list(map(lambda e: e.id, entities_to_hold_skill_on))
        hold_start_time = time.time()
        self.attacking_skill.last_use_time = hold_start_time
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
      # use movement skill
      if self.movement_skill and mover.distance_to_target > 50:
        instant_movement_used = False
        if self.instant_movement_skill:
          instant_movement_used = self.instant_movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False)
          if instant_movement_used:
            return True
        if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
          return True
    # if we are staying and waiting for smth
    else:
      self.staticDefence()
    return False

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    self.attacking_skill.last_use_time = 0
    entity_to_kill_id = entity.id
    self.auto_flasks.useFlasks()

    min_distance = 40  # distance which is ok to start attacking

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True
    print(f"entity_to_kill {entity_to_kill}")
    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True
    distance_to_entity = dist(
      (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
    )
    print(f"distance_to_entity {distance_to_entity} in killUsual")
    if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False
    if entity_to_kill.isInLineOfSight() is False:
      print("entity_to_kill.isInLineOfSight() is False")
      return False

    start_time = time.time()
    entity_to_kill.hover()
    self.attacking_skill.press()
    poe_bot.last_action_time = 0
    last_dodge_use_time = time.time()
    dodge_delay = random.randint(80, 140) / 100
    res = True
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break
      print(f"entity_to_kill {entity_to_kill}")
      if entity_to_kill.life.health.current < 1:
        print("entity is dead")
        break
      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")
      if distance_to_entity > min_distance:
        print("getting closer in killUsual ")
        break
      current_time = time.time()
      self.useBuffs()
      entity_to_kill.hover()
      if self.instant_movement_skill:
        if self.attacking_skill.display_name != "flicker_strike" and current_time > last_dodge_use_time + dodge_delay:
          print("flicker strike")
          self.instant_movement_skill.tap()
          last_dodge_use_time = time.time()
      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    self.attacking_skill.release()
    return res

  def prepareToFight(self, entity: Entity):
    print(f"vg.preparetofight call {time.time()}")
    poe_bot = self.poe_bot
    bot_controls = self.poe_bot.bot_controls
    pos_x, pos_y = entity.location_on_screen.x, entity.location_on_screen.y
    pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
    bot_controls.mouse.setPosSmooth(pos_x, pos_y)
    self.attacking_skill.press()
    start_hold_time = time.time()
    min_hold_duration = random.randint(40, 60) / 100
    while True:
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      pos_x, pos_y = poe_bot.getPositionOfThePointOnTheScreen(y=entity.grid_position.y, x=entity.grid_position.x)
      pos_x, pos_y = poe_bot.convertPosXY(pos_x, pos_y)
      bot_controls.mouse.setPosSmooth(pos_x, pos_y)
      if time.time() > start_hold_time + min_hold_duration:
        break
    self.attacking_skill.release()

class GenericSummoner(Build):
  spectre_list = []
  poe_bot: PoeBot
  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    super().__init__(poe_bot)

class GenericFacetank(Build):
  """
  spams main skill till death
  """

  pass

class GenericHitAndRun(Build):
  """
  some spam skills
  # attacks several times and runs away
  """

  pass

class GenericKiteAround(Build):
  """
  totem, minions, brands
  """

  pass