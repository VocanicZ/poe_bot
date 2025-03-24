from ..build import *

import sys
sys.path.append('...')
from utils.skill import SkillWithDelay, DodgeRoll
from utils.utils import getAngle

class Build(Build):
  """ """
  def __init__(self, poe_bot: "PoeBot", can_kite=True) -> None:
    self.poe_bot = poe_bot
    self.can_kite = can_kite
    self.max_srs_count = 10

    flame_wall_internal_name = "firewall"
    flame_wall_index = (
      flame_wall_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flame_wall_internal_name)
    )
    unearth_index = False

    self.minion_reaver_enrage = None

    self.minion_arconist_dd = None
    self.minion_reaver_enrage = None
    self.minion_sniper_gas_arrow = None

    minion_command_internal_name = "command_minion"
    for skill_index in range(len(self.poe_bot.game_data.skills.internal_names)):
      skill_name_raw = self.poe_bot.game_data.skills.internal_names[skill_index]
      if skill_name_raw != minion_command_internal_name:
        continue
      skill_base_cast_time = next(
        (list(sd.values())[0] for sd in poe_bot.game_data.skills.descriptions[skill_index] if "BaseSpellCastTimeMs" in sd.keys()), None
      )
      if skill_base_cast_time is None:
        continue
      elif self.minion_arconist_dd is None and skill_base_cast_time == 600:
        print(f"[InfernalistZoomancer.__init__] found minion_arconist_dd_index {skill_index}")
        self.minion_arconist_dd = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.randint(20, 30) / 10, display_name="minion_arconist_dd", can_use_earlier=False
        )
      elif self.minion_reaver_enrage is None and skill_base_cast_time == 1000:
        print(f"[InfernalistZoomancer.__init__] found minion_reaver_enrage_index {skill_index}")
        self.minion_reaver_enrage = SkillWithDelay(
          poe_bot=poe_bot, skill_index=skill_index, min_delay=random.uniform(2.5, 3.0), display_name="minion_reaver_enrage", can_use_earlier=False
        )
      elif self.minion_sniper_gas_arrow is None and skill_base_cast_time == 1250:
        print(f"[InfernalistZoomancer.__init__] found minion_sniper_gas_arrow_index {skill_index}")
        self.minion_sniper_gas_arrow = SkillWithDelay(
          poe_bot=poe_bot,
          skill_index=skill_index,
          min_delay=random.uniform(0.05, 0.15),
          display_name="minion_sniper_gas_arrow",
          can_use_earlier=False,
        )

    # TODO minion frenzy command
    # TODO minion gas arrow command

    dd_internal_name = "detonate_dead"
    detonate_dead_index = dd_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      dd_internal_name
    )
    offering_internal_name = "pain_offering"
    offerening_index = offering_internal_name in self.poe_bot.game_data.skills.internal_names and self.poe_bot.game_data.skills.internal_names.index(
      offering_internal_name
    )
    flammability_internal_name = "fire_weakness"
    flammability_index = (
      flammability_internal_name in self.poe_bot.game_data.skills.internal_names
      and self.poe_bot.game_data.skills.internal_names.index(flammability_internal_name)
    )

    self.fire_skills = []

    self.flame_wall = None
    if flame_wall_index is not False:
      self.flame_wall = SkillWithDelay(
        poe_bot=poe_bot, skill_index=flame_wall_index, min_delay=random.randint(20, 30) / 10, display_name="flame_wall", can_use_earlier=False
      )
      self.fire_skills.append(self.flame_wall)

    self.unearth = None
    if unearth_index is not False:
      self.unearth = SkillWithDelay(
        poe_bot=poe_bot, skill_index=unearth_index, min_delay=random.randint(20, 30) / 10, display_name="unearth", can_use_earlier=False
      )

    self.detonate_dead = None
    if detonate_dead_index is not False:
      self.detonate_dead = SkillWithDelay(
        poe_bot=poe_bot, skill_index=detonate_dead_index, min_delay=random.uniform(3.1, 4.5), display_name="detonate_dead", can_use_earlier=False
      )
      self.fire_skills.append(self.detonate_dead)

    self.offering = None
    if offerening_index is not False:
      self.offering = SkillWithDelay(
        poe_bot=poe_bot, skill_index=offerening_index, min_delay=random.randint(20, 30) / 10, display_name="offering", can_use_earlier=False
      )

    self.flammability = None
    if flammability_index is not False:
      self.flammability = SkillWithDelay(
        poe_bot=poe_bot, skill_index=flammability_index, min_delay=random.randint(20, 30) / 10, display_name="flammability", can_use_earlier=False
      )

    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)

    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    print("calling usual routine")
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      self.useBuffs()
      attacking_skill_delay = 2

      nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      if len(really_close_enemies) != 0:
        attacking_skill_delay = 0.7

      enemy_to_attack = None
      if len(really_close_enemies) != 0:
        enemy_to_attack = really_close_enemies[0]
      elif len(nearby_enemies):
        nearby_enemies = sorted(nearby_enemies, key=lambda e: e.distance_to_player)
        nearby_enemies = list(filter(lambda e: e.isInLineOfSight() is True, nearby_enemies))
        if len(nearby_enemies) != 0:
          enemy_to_attack = nearby_enemies[0]

      attack_skill_used = False
      if enemy_to_attack is not None:
        for _i in range(1):
          if self.flame_wall and self.flame_wall.last_use_time + attacking_skill_delay < time.time():
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
              if self.flame_wall.use(updated_entity=enemy_to_attack, wait_for_execution=False) is True:
                attack_skill_used = True
                break
          if self.detonate_dead and self.detonate_dead.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
              poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 40
            )
            corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
          if self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
            if self.minion_sniper_gas_arrow.use(updated_entity=enemy_to_attack, wait_for_execution=False) is True:
              attack_skill_used = True
              break
          if self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
            if self.minion_reaver_enrage.use(wait_for_execution=False) is True:
              attack_skill_used = True
              break
          if self.unearth and self.unearth.canUse():
            corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(
              poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y, 20
            )
            corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
            if len(corpses_around) != 0:
              corpses_around.sort(key=lambda e: e.calculateValueForAttack())
              if corpses_around[0].attack_value != 0:
                if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
          if self.offering and self.offering.canUse():
            offering_spikes = list(
              filter(lambda e: "Metadata/Monsters/OfferingSpike/PainOfferingSpike" in e.path, poe_bot.game_data.entities.all_entities)
            )
            if len(offering_spikes) == 0:
              alive_skeletons_nearby = list(
                filter(
                  lambda e: e.is_hostile is False and "Metadata/Monsters/Skeletons/PlayerSummoned/Skeleton", poe_bot.game_data.entities.all_entities
                )
              )
              if len(alive_skeletons_nearby) != 0:
                if self.offering.use(updated_entity=alive_skeletons_nearby[0], wait_for_execution=False) is not False:
                  attack_skill_used = True
                  break
        p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        # cast first then move back
        if self.can_kite and len(nearby_enemies) > 1:
          go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
          poe_bot.mover.move(*go_back_point)
          return True
        if attack_skill_used:
          return True

        # TODO add global cooldown, so itll be able to finish casting skills
        extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
        enemies_on_way = list(
          filter(
            lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies
          )
        )
        if extremley_close_entities or enemies_on_way:
          if self.dodge_roll.use(wait_for_execution=False) is True:
            return True

        # return True

      p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
      p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      # go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)

      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 10, really_close_enemies))
      enemies_on_way = list(
        filter(
          lambda e: e.distance_to_player < 15 and getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < 45, really_close_enemies
        )
      )
      if extremley_close_entities or enemies_on_way:
        if self.dodge_roll.use() is True:
          return True
      # # use movement skill
      # if self.movement_skill and mover.distance_to_target > 50:
      #   if self.movement_skill.use(mover.grid_pos_to_step_x, mover.grid_pos_to_step_y, wait_for_execution=False) is True:
      #     return True

    # if we are staying and waiting for smth
    else:
      self.staticDefence()

    return False

  def prepareToFight(self, entity: Entity):
    print(f"[InfernalistZoomancer.prepareToFight] call {time.time()}")
    for i in range(random.randint(2, 3)):
      self.poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      updated_entity = next((e for e in self.poe_bot.game_data.entities.all_entities if e.id == entity.id), None)
      if updated_entity is None:
        break

      self.flame_wall.use(updated_entity=updated_entity)
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover

    entity_to_kill_id = entity.id

    self.auto_flasks.useFlasks()

    min_distance = 70  # distance which is ok to start attacking
    keep_distance = 15  # if our distance is smth like this, kite

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
    entity_to_kill.hover(wait_till_executed=False)
    poe_bot.last_action_time = 0
    kite_distance = random.randint(35, 45)
    res = True
    reversed_run = random.choice([True, False])

    while True:
      skill_used = False
      poe_bot.refreshInstanceData()
      self.auto_flasks.useFlasks()
      if self.poe_bot.game_data.player.life.health.getPercentage() < self.auto_flasks.hp_thresh:
        pass  # TODO kite?

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
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")

      if skill_used is False and self.flame_wall and self.flame_wall.last_use_time + skill_use_delay < time.time():
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
          print("[Generic summoner] need to raise srs")
          if self.flame_wall.use(updated_entity=entity_to_kill, wait_for_execution=False) is True:
            skill_used = True
      if skill_used is False and self.detonate_dead and self.detonate_dead.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 40)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.detonate_dead.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
              skill_used = True
      if skill_used is False and self.unearth and self.unearth.canUse():
        corpses_around = poe_bot.game_data.entities.getCorpsesArountPoint(entity_to_kill.grid_position.x, entity_to_kill.grid_position.y, 20)
        corpses_around = list(filter(lambda e: e.isInLineOfSight() is not False, corpses_around))
        if len(corpses_around) != 0:
          corpses_around.sort(key=lambda e: e.calculateValueForAttack())
          if corpses_around[0].attack_value != 0:
            if self.unearth.use(updated_entity=corpses_around[0], wait_for_execution=False) is not False:
              skill_used = True
      if skill_used is False and self.minion_reaver_enrage and self.minion_reaver_enrage.canUse():
        if self.minion_reaver_enrage.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      if skill_used is False and self.minion_sniper_gas_arrow and self.minion_sniper_gas_arrow.canUse():
        if self.minion_sniper_gas_arrow.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      print("kiting")
      if distance_to_entity > keep_distance:
        print("away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)
      else:
        print("around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        mover.move(grid_pos_x=point[0], grid_pos_y=point[1])

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    return res