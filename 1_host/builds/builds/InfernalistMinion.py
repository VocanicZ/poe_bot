from ..build import *

import time
from math import dist

import sys
sys.path.append('...')
from utils.utils import getAngle
from utils.skill import SkillWithDelay, DodgeRoll

class Build(Build):
  """ """

  poe_bot: PoeBot

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

    # raging spririts count
    self.max_srs_count = 7

    self.minion_arconist_dd = None
    self.minion_reaver_enrage = None
    self.minion_sniper_gas_arrow = None

    minion_command_internal_name = "command_minion"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name_raw = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name_raw != minion_command_internal_name:
        continue
      skill_base_cast_time = next(
        (list(sd.values())[0] for sd in poe_bot.game_data.skills.descriptions[skill_index] if "BaseSpellCastTimeMs" in sd.keys()),
        None,
      )
      if skill_base_cast_time is None:
        continue
      elif self.minion_arconist_dd is None and skill_base_cast_time == 600:
        print(f"[InfernalistMinion.__init__] found minion_arconist_dd_index {skill_index}")
        self.minion_arconist_dd = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(3.0, 4.0),
          display_name="minion_arconist_dd",
          can_use_earlier=False,
        )
      elif self.minion_reaver_enrage is None and skill_base_cast_time == 1000:
        print(f"[InfernalistMinion.__init__] found minion_reaver_enrage_index {skill_index}")
        self.minion_reaver_enrage = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(3.0, 4.0),
          display_name="minion_reaver_enrage",
          can_use_earlier=False,
        )
      elif self.minion_sniper_gas_arrow is None and skill_base_cast_time == 1250:
        print(f"[InfernalistMinion.__init__] found minion_sniper_gas_arrow_index {skill_index}")
        self.minion_sniper_gas_arrow = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(2.5, 3.0),
          display_name="minion_sniper_gas_arrow",
          can_use_earlier=False,
        )

    unearth_internal_name = "bone_cone"
    unearth_index = unearth_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      unearth_internal_name
    )
    print(f"unearth_index {unearth_index}")
    self.unearth = None
    if unearth_index is not False:
      self.unearth = combat.SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=unearth_index,
        min_delay=random.uniform(0.1, 0.2),
        display_name="unearth",
        can_use_earlier=True,
      )

    detonate_dead_internal_name = "detonate_dead"
    detonate_dead_index = (
      detonate_dead_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(detonate_dead_internal_name)
    )
    print(f"detonate_dead_index {detonate_dead_index}")
    self.detonate_dead = None
    if detonate_dead_index is not False:
      self.detonate_dead = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=detonate_dead_index,
        min_delay=random.uniform(0.5, 1.5),
        display_name="detonate_dead",
        can_use_earlier=False,
      )

    offering_internal_name = "pain_offering"
    offerening_index = offering_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      offering_internal_name
    )
    print(f"offerening_index {offerening_index}")
    self.offering = None
    if offerening_index is not False:
      self.offering = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=offerening_index,
        min_delay=random.uniform(6.0, 8.0),
        display_name="offering",
        can_use_earlier=False,
      )

    flammability_internal_name = "fire_weakness"
    flammability_index = (
      flammability_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flammability_internal_name)
    )
    print(f"flammability_index {flammability_index}")
    self.flammability = None
    if flammability_index is not False:
      self.flammability = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=flammability_index,
        min_delay=random.uniform(2.0, 3.0),
        display_name="flammability",
        can_use_earlier=False,
      )

    flame_wall_internal_name = "firewall"
    flame_wall_index = (
      flame_wall_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flame_wall_internal_name)
    )
    print(f"flame_wall_index {flame_wall_index}")
    self.flame_wall = None
    if flame_wall_index is not False:
      self.flame_wall = SkillWithDelay(
        poe_bot=poe_bot,
        skill_index=flame_wall_index,
        min_delay=random.uniform(0.5, 1),
        display_name="flame_wall",
        can_use_earlier=False,
      )

    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)

    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.useFlasks()

    # if we are moving
    if mover is not None:
      entity_to_explode: Entity = None
      entity_to_unearth: Entity = None
      search_radius = 25
      search_angle = 40

      attacking_skill_delay = random.uniform(0.35, 0.5)

      self.last_explosion_loc = [0, 1, 0, 1]
      self.last_explosion_time = 0

      self.useBuffs()

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 40)
      if corpses:
        if self.last_explosion_time + 1 < time.time():
          self.last_explosion_loc = [0, 1, 0, 1]

        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))
        corpses = list(filter(lambda e: e.attack_value > 4, corpses))
        corpses = list(filter(lambda e: not e.isInZone(*self.last_explosion_loc), corpses))

        if corpses:
          corpses.sort(key=lambda e: e.attack_value, reverse=True)
          entity_to_explode = corpses[0]
          print(f"found valuable corpse to explode {entity_to_explode.raw}")

      if entity_to_explode and self.detonate_dead.canUse() and self.detonate_dead.last_use_time + attacking_skill_delay < time.time():
        self.detonate_dead.use(updated_entity=entity_to_explode)
        self.last_explosion_time = time.time()
        self.last_explosion_loc = [
          entity_to_explode.grid_position.x - 20,
          entity_to_explode.grid_position.x + 20,
          entity_to_explode.grid_position.y - 20,
          entity_to_explode.grid_position.y + 20,
        ]
        return True

      corpses = poe_bot.game_data.entities.getCorpsesArountPoint(poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 35)
      if corpses:
        p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        corpses = list(
          filter(
            lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle,
            corpses,
          )
        )
        list(map(lambda e: e.calculateValueForAttack(search_radius), corpses))

        if len(corpses) > 5:
          corpses.sort(key=lambda e: e.attack_value > 1, reverse=True)
          entity_to_unearth = corpses[0]
          print(f"found valuable corpse to unearth {entity_to_unearth.raw}")

      if entity_to_unearth and self.unearth.canUse() and self.unearth.last_use_time + attacking_skill_delay + 1 < time.time():
        self.unearth.use(updated_entity=entity_to_unearth)
        return True

      nearby_enemies = list(
        filter(
          lambda e: e.distance_to_player < 90 and e.isInRoi() and e.is_hostile,
          poe_bot.game_data.entities.attackable_entities,
        )
      )
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 45, nearby_enemies))

      enemy_to_attack = None
      if len(really_close_enemies) != 0:
        enemy_to_attack = really_close_enemies[0]
      elif len(nearby_enemies):
        nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
        # nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
        if len(nearby_enemies) != 0:
          enemy_to_attack = nearby_enemies[0]

      if enemy_to_attack is not None:
        if self.flame_wall and self.flame_wall.canUse() and self.flame_wall.last_use_time + attacking_skill_delay < time.time():
          alive_srs_nearby = list(
            filter(
              lambda e: not e.is_hostile
              and e.life.health.current != 0
              and e.distance_to_player < 150
              and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
              self.poe_bot.game_data.entities.all_entities,
            )
          )
          if len(alive_srs_nearby) < self.max_srs_count:
            self.flame_wall.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        if self.flammability and self.flammability.canUse() and self.flammability.last_use_time + attacking_skill_delay < time.time():
          self.flammability.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        if (
          self.minion_sniper_gas_arrow
          and self.minion_sniper_gas_arrow.canUse()
          and self.minion_sniper_gas_arrow.last_use_time + attacking_skill_delay < time.time()
        ):
          self.minion_sniper_gas_arrow.use(updated_entity=enemy_to_attack, wait_for_execution=False)

        # Get nearby allies
        nearby_allies = [
          e
          for e in poe_bot.game_data.entities.all_entities
          if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
        ]
        if nearby_allies:
          try:
            middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
            middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
            mover.move(middle_x, middle_y)
          except Exception:
            pass

      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)

      # if len(really_close_enemies) > 1:
      #  go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      #  poe_bot.mover.move(*go_back_point)
      #  return True

      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 15, nearby_enemies))
      enemies_on_way = list(
        filter(
          lambda e: e.distance_to_player < 45 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 35,
          nearby_enemies,
        )
      )

      if extremley_close_entities:
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)
        self.dodge_roll.use(wait_for_execution=False)
        return True
      elif enemies_on_way:
        nearby_allies = [
          e
          for e in poe_bot.game_data.entities.all_entities
          if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
        ]
        if nearby_allies:
          try:
            middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
            middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
            mover.move(middle_x, middle_y)
            return True
          except Exception:
            pass

      # elif really_close_enemies or enemies_on_way and enemies_on_way[0].distance_to_player < 35:
      #  go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
      #  mover.move(*go_back_point)
      #  return True
      elif enemy_to_attack is not None:
        # point = self.poe_bot.game_data.terrain.pointToRunAround(enemy_to_attack.grid_position.x, enemy_to_attack.grid_position.y, 40, reversed=random.choice([True, False]))
        # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
        return True

  def prepareToFight(self, entity: Entity):
    print(f"[InfernalistMinion.prepareToFight] call {time.time()}")
    self.poe_bot.refreshInstanceData()
    self.useFlasks()
    return True

  def killUsual(
    self,
    entity: Entity,
    is_strong=False,
    max_kill_time_sec=random.randint(200, 300) / 10,
    *args,
    **kwargs,
  ):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id

    self.useFlasks()

    min_distance = 35  # distance which is ok to start attacking
    keep_distance = 55  # if our distance is smth like this, kite
    critical_distance = 15
    distance_range = 5

    start_time = time.time()
    poe_bot.last_action_time = 0

    entity_to_kill = next(
      (e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id),
      None,
    )
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True

    print(f"entity_to_kill {entity_to_kill}")

    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True

    distance_to_entity = dist(
      (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
      (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
    )
    print(f"distance_to_entity {distance_to_entity} in killUsual")
    if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False

    if entity_to_kill.isInLineOfSight() is False:
      print("entity_to_kill.isInLineOfSight() is False")
      return False

    entity_to_kill.hover(wait_till_executed=False)

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass  # TODO kite?

      entity_to_kill = next(
        (e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id),
        None,
      )
      if not entity_to_kill:
        print("cannot find desired entity to kill")
        break

      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y),
        (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")
      if distance_to_entity > min_distance:
        print("getting closer in killUsual ")
        break
      current_time = time.time()

      # TODO: some logic how and when to use skills, currently -> if ememy then use skill

      if skill_used is False and self.flame_wall and self.flame_wall.canUse():
        alive_srs_nearby = list(
          filter(
            lambda e: not e.is_hostile
            and e.life.health.current != 0
            and e.distance_to_player < 150
            and "Metadata/Monsters/RagingSpirit/RagingSpiritPlayerSummoned" in e.path,
            self.poe_bot.game_data.entities.all_entities,
          )
        )
        if len(alive_srs_nearby) < self.max_srs_count:
          print(f"[Generic summoner] need to raise srs, current count {len(alive_srs_nearby)}")
          if self.flame_wall.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
            skill_used = True

      if skill_used is False and self.offering and self.offering.canUse():
        minions_around = list(
          filter(
            lambda e: e.is_hostile is False and e.distance_to_player < 35,
            poe_bot.game_data.entities.all_entities,
          )
        )
        if len(minions_around) != 0:
          if self.offering.use(updated_entity=minions_around[0], wait_for_execution=False) is True:
            skill_used = True

      if skill_used is False and self.flammability and self.flammability.canUse():
        if self.flammability.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
        if self.minion_reaver_enrage.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
        if self.minion_sniper_gas_arrow.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      if skill_used is False and self.minion_arconist_dd and self.minion_arconist_dd.canUse():
        if self.minion_arconist_dd.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
          skill_used = True

      p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)

      if distance_to_entity < critical_distance:
        # distance_to_entity is below the critical distance
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)
        self.dodge_roll.use(wait_for_execution=False)

      if distance_to_entity < keep_distance - distance_range:
        # distance_to_entity is below the range
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        mover.move(*go_back_point)

      # Calculate middlepoint of nearby allies and move there
      nearby_allies = [
        e
        for e in poe_bot.game_data.entities.all_entities
        if not e.is_hostile and e.distance_to_player < 60 and e.grid_position and e.life.health.current != 0
      ]
      if nearby_allies:
        try:
          middle_x = sum(e.grid_position.x for e in nearby_allies) / len(nearby_allies)
          middle_y = sum(e.grid_position.y for e in nearby_allies) / len(nearby_allies)
          mover.move(middle_x, middle_y)
        except Exception:
          pass

      # elif distance_to_entity > keep_distance + distance_range:
      # distance_to_entity is above the range
      # mover.goToPoint(p1)
      # mover.goToEntity(entity_to_kill, keep_distance)
      # point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, distance_range, check_if_passable=True, reversed=random.choice([True, False]))
      # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])
      # else:
      # distance_to_entity is within the range
      # mover.goToPoint(p1)
      # break
      # mover.goToEntity(entity_to_kill, keep_distance)

      # point = self.poe_bot.game_data.terrain.pointToRunAround(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, kite_distance+random.randint(-3,3), check_if_passable=True, reversed=reversed_run)
      # mover.move(grid_pos_x = point[0], grid_pos_y = point[1])

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break

    return True