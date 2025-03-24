from ..build import *

import sys
sys.path.append('...')
from utils.skill import SkillWithDelay, DodgeRoll
if TYPE_CHECKING:
  from utils.poebot import Poe2Bot

class Build(Build):
  """ """
  def __init__(self, poe_bot: "Poe2Bot") -> None:
    self.poe_bot = poe_bot

    self.last_explosion_loc = [0, 1, 0, 1]
    self.last_explosion_locations = {
      # "use_time": [grid pos area x1 x2 y1 y2]
    }
    self.pconc_area = 20
    self.pconc_area_reset_timer_sec = 4
    self.pconc_area_in_legs_reset_timer_sec = 2

    self.pconc: SkillWithDelay = None
    self.curse: SkillWithDelay = None
    self.wither_totem: SkillWithDelay = None

    pconc_internal_name = "throw_flask_poison"
    curse_internal_names = ["despair"]
    wither_totem_internal_name = "dark_effigy"

    pconc_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s == pconc_internal_name), None)
    if pconc_on_panel is not None:
      print(pconc_on_panel)
      pconc_index = self.poe_bot.game_data.skills.internal_names.index(pconc_on_panel)
      # print(pconc_on_panel, pcon)
      self.pconc = SkillWithDelay(
        poe_bot=poe_bot, skill_index=pconc_index, min_delay=random.randint(1, 5) / 100, display_name=pconc_internal_name, min_mana_to_use=0
      )
      self.pconc.sleep_multiplier = 0.2

    curse_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s in curse_internal_names), None)
    if curse_on_panel is not None:
      curse_index = self.poe_bot.game_data.skills.internal_names.index(curse_on_panel)
      self.curse = SkillWithDelay(poe_bot=poe_bot, skill_index=curse_index, min_delay=random.randint(30, 50) / 10, display_name=curse_on_panel)

    wither_totem_on_panel = next((s for s in self.poe_bot.game_data.skills.internal_names if s == wither_totem_internal_name), None)
    if wither_totem_on_panel is not None:
      wither_totem_index = self.poe_bot.game_data.skills.internal_names.index(wither_totem_on_panel)
      self.wither_totem = SkillWithDelay(
        poe_bot=poe_bot, skill_index=wither_totem_index, min_delay=random.randint(30, 50) / 10, display_name=wither_totem_on_panel
      )
    self.dodge_roll = DodgeRoll(poe_bot=poe_bot)
    super().__init__(poe_bot)
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    self.auto_flasks.hp_thresh = 0.75

  def useBuffs(self):
    return False

  def usualRoutine(self, mover: Mover = None):
    poe_bot = self.poe_bot
    self.auto_flasks.useFlasks()

    # if we are moving
    if mover is not None:
      print("calling usual routine")

      _t = time.time()
      if self.dodge_roll.last_use_time + 0.35 > _t or self.pconc.last_use_time + (self.pconc.getCastTime() / 2) > _t:
        print("probably casting smth atm")
        return False

      need_dodge = False
      throw_pconc_at = None  # [x,y] grid pos
      enemy_to_attack: Entity = None
      really_close_enemies_distance = 50
      pconc_explode_area = self.pconc_area
      search_angle = 90
      search_angle_half = search_angle / 2

      self.useBuffs()

      # either throw pconc on enemies whose attack val > 2 and didnt throw in that zone for kinda long time
      # or if didnt use pconc for long time throw pconc
      # or if surrounded throw pconc in legs

      # if surrounded and did throw pconc in legs recently, and did use pconc recentley, and if last time dodged > 1.5 sec -> dodge forward

      # if clear is bad, remove explosion zone stuff, since it's good when does it according to cd but not explosion zones
      # self.last_explosion_locations = {}

      # reset explosion areas
      for k in list(self.last_explosion_locations.keys()):
        if k + self.pconc_area_reset_timer_sec < _t:
          print(f"removing explosion zone {k} with {self.last_explosion_locations[k]} , expired")
          del self.last_explosion_locations[k]

      last_explosion_locations = list(self.last_explosion_locations.values())

      # nearby_enemies = list(filter(lambda e: e.distance_to_player < 50 and e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      nearby_enemies = list(filter(lambda e: e.isInRoi(), poe_bot.game_data.entities.attackable_entities))
      print(f"nearby_enemies: {nearby_enemies}")
      really_close_enemies = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))
      extremley_close_entities = list(filter(lambda e: e.distance_to_player < 20, nearby_enemies))

      # surrounded
      if len(extremley_close_entities) > 2:
        print("surrounded")
        for _i in range(1):
          did_throw_pconc_in_legs_recently = False
          # #recently for throw in legs reduced timer
          # last_explosion_locations_in_legs_keys = list(filter(lambda k: k + self.pconc_area_in_legs_reset_timer_sec > _t, list(self.last_explosion_locations.keys()) ))
          # last_explosion_locations_in_legs = list(map(lambda k: self.last_explosion_locations[k], last_explosion_locations_in_legs_keys))
          # for zone in last_explosion_locations_in_legs:
          #   if self.poe_bot.game_data.player.isInZone(*zone):
          #     did_throw_pconc_in_legs_recently = True
          #     print(f'did throw pconc nearby recently')
          #     break

          # TODO add cooldown to it?
          if did_throw_pconc_in_legs_recently is False:
            # throw pconc in nearest entity or legs
            entities_in_los = list(filter(lambda e: e.isInLineOfSight(), extremley_close_entities))
            if entities_in_los:
              ent = entities_in_los[0]
              throw_pconc_at = [ent.grid_position.x, ent.grid_position.y]
            else:
              # extend line from mover and use 25% or smth close to it
              throw_pconc_at = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
            break
          # if dodged recently and not throwing pconc atm
          if self.dodge_roll.last_use_time + 1 < _t:
            need_dodge = True

      # throw pconc for clear
      if need_dodge is not True and throw_pconc_at is None and len(nearby_enemies) != 0:
        print("going to clear")
        for _i in range(1):
          really_close_enemies = list(filter(lambda e: e.distance_to_player < really_close_enemies_distance, nearby_enemies))
          # internal cd for clear
          if len(really_close_enemies) != 0:
            pass
          else:
            pass

          # if self.pconc.last_use_time + skill_cd > _t:
          #   print(f'internal cd for clear {skill_cd}')
          #   break

          # sort enemies, if visible and not in last explosion zones
          enemies_for_clear: List[Entity] = []
          for e in nearby_enemies:
            if e.isInLineOfSight() is not True:
              continue
            was_in_explosion_area = False
            for zone in last_explosion_locations:
              if e.isInZone(*zone):
                was_in_explosion_area = True
                break
            if was_in_explosion_area is not True:
              enemies_for_clear.append(e)
          if len(enemies_for_clear) == 0:
            print("no enemies outside of the zone")
            break

          really_close_enemies = list(filter(lambda e: e.distance_to_player < really_close_enemies_distance, enemies_for_clear))

          if really_close_enemies:
            pass
          else:
            pass

          # if didnt use pconc for long, throw somewhere even if theres 1 attack val
          if True:
            # if self.pconc.last_use_time + skill_cd * 2 < _t:
            print("didnt use pconc for long, throw somewhere even if theres 1 attack val")
            enemies_for_clear.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
            enemy_to_attack = enemies_for_clear[0]
            print(f"enemy_to_attack.attack_value {enemy_to_attack.attack_value} {enemy_to_attack.raw}")
            # min 1, max 4
            attack_val_mult = min(max(enemy_to_attack.attack_value, 1), 3)
            if enemy_to_attack.attack_value > 4:
              pconc_explode_area = int(self.pconc_area * attack_val_mult)
            # if enemies_for_clear[0].attack_value > 1:
            #   enemy_to_attack = enemies_for_clear[0]
          else:
            # if someone in radius 20, throw at him, but attack value > 2
            if really_close_enemies:
              print("someone in radius 20, throw at him, but attack value > 2")
              really_close_enemies.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
              if really_close_enemies[0].attack_value > 1:
                enemy_to_attack = really_close_enemies[0]
            # else calculate val for explosion and throw, attack value > 2
            else:
              print("else calculate val for explosion and throw, attack value > 2")
              p0 = (mover.grid_pos_to_step_x, mover.grid_pos_to_step_y)
              p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
              enemies_in_sector = list(
                filter(lambda e: getAngle(p0, p1, (e.grid_position.x, e.grid_position.y), abs_180=True) < search_angle_half, enemies_for_clear)
              )
              if len(enemies_in_sector) != 0:
                enemies_in_sector.sort(key=lambda e: e.calculateValueForAttack(), reverse=True)
                if enemies_in_sector[0].attack_value > 1:
                  enemy_to_attack = enemies_in_sector[0]

      # result action
      enemy_to_attack_cropped_pos = False
      if enemy_to_attack:
        # TODO convert entity pos into grid pos
        throw_pconc_at = [enemy_to_attack.grid_position.x, enemy_to_attack.grid_position.y]
        # TODO crop line if distance is long
        if dist(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at) > 15:
          throw_pconc_at = extendLine(poe_bot.game_data.player.grid_pos.toList(), throw_pconc_at, 0.75)
          print(f"pconc throw reduced to {throw_pconc_at}")
          enemy_to_attack_cropped_pos = True

      if throw_pconc_at:
        if self.pconc.canUse() and self.pconc.use(pos_x=throw_pconc_at[0], pos_y=throw_pconc_at[1], wait_for_execution=True) is True:
          self.last_explosion_locations[_t] = [
            throw_pconc_at[0] - pconc_explode_area,
            throw_pconc_at[0] + pconc_explode_area,
            throw_pconc_at[1] - pconc_explode_area,
            throw_pconc_at[1] + pconc_explode_area,
          ]
          print(f"adding explosion zone {_t} with {self.last_explosion_locations[_t]}")
          if enemy_to_attack_cropped_pos:
            self.last_explosion_locations[_t + 0.001] = [
              enemy_to_attack.grid_position.x - pconc_explode_area,
              enemy_to_attack.grid_position.x + pconc_explode_area,
              enemy_to_attack.grid_position.y - pconc_explode_area,
              enemy_to_attack.grid_position.y + pconc_explode_area,
            ]

          # return True
          return False

      if need_dodge:
        self.dodge_roll.use(pos_x=mover.grid_pos_to_step_x, pos_y=mover.grid_pos_to_step_y)
        return False
        # return True

      return False

    # if we are staying and waiting for smth
    else:
      for iii in range(100):
        print("combatmodule build mover is none")
      self.staticDefence()

    return False

  def prepareToFight(self, entity: Entity):
    print(f"[PathfinderPoisonConc2.prepareToFight] call {time.time()}")
    return True

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=random.randint(200, 300) / 10, *args, **kwargs):
    print(f"#build.killUsual {entity}")
    poe_bot = self.poe_bot
    mover = self.mover
    entity_to_kill_id = entity.id

    self.auto_flasks.useFlasks()

    keep_distance = 15  # if our distance is smth like this, kite

    entity_to_kill = next((e for e in poe_bot.game_data.entities.attackable_entities if e.id == entity_to_kill_id), None)
    if not entity_to_kill:
      print("cannot find desired entity to kill")
      return True

    print(f"entity_to_kill {entity_to_kill}")

    if entity_to_kill.life.health.current < 0:
      print("entity is dead")
      return True
    if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
      # if distance_to_entity > min_distance:
      print("getting closer in killUsual ")
      return False

    start_time = time.time()
    entity_to_kill.hover(wait_till_executed=False)
    kite_distance = random.randint(35, 45)
    reversed_run = random.choice([True, False])
    res = True
    poe_bot.last_action_time = 0

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
      if entity_to_kill.isInRoi() is False or entity_to_kill.isInLineOfSight() is False:
        print("getting closer in killUsual ")
        break
      distance_to_entity = dist(
        (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
      )
      print(f"distance_to_entity {distance_to_entity} in killUsual")

      current_time = time.time()
      skill_used = self.useBuffs()
      skill_use_delay = random.randint(20, 30) / 10
      print(f"skill_use_delay {skill_use_delay}")

      if skill_used is False and self.pconc and self.pconc.last_use_time + (self.pconc.getCastTime() / 2) < time.time():
        if self.pconc.use(updated_entity=entity_to_kill, wait_for_execution=False) is not False:
          skill_used = True

      print("kiting")
      if distance_to_entity > keep_distance:
        print("around")
        point = self.poe_bot.game_data.terrain.pointToRunAround(
          entity_to_kill.grid_position.x,
          entity_to_kill.grid_position.y,
          kite_distance + random.randint(-1, 1),
          check_if_passable=True,
          reversed=reversed_run,
        )
        mover.move(grid_pos_x=point[0], grid_pos_y=point[1])
      else:
        print("away")
        p0 = (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y)
        p1 = (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
        go_back_point = self.poe_bot.pather.findBackwardsPoint(p1, p0)
        poe_bot.mover.move(*go_back_point)

      if current_time > start_time + max_kill_time_sec:
        print("exceed time")
        break
    return res
