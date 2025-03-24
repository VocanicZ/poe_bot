import typing

if typing.TYPE_CHECKING:
  from ..utils.gamehelper import Entity, Poe2Bot, PoeBot
  from ..utils.mover import Mover

from typing import List
from math import dist
import random
import time

from ..utils import extendLine
from ..utils.combat import AutoFlasks, Skill
from ..utils.constants import DANGER_ZONE_KEYS

class Build:
  poe_bot: PoeBot
  chaos_immune = False
  buff_skills: List[Skill] = []
  restricted_mods: List[str] = []

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.mover = self.poe_bot.mover
    self.auto_flasks = AutoFlasks(poe_bot=poe_bot)
    # actions done during usual walking
    if getattr(self, "usualRoutine", None) is None:
      raise NotImplementedError
    # actions how does it behave during killing
    if getattr(self, "killUsual", None) is None:
      raise NotImplementedError
    # actions how does it behave during killing strong entity, suchs as simulacrum boss or whatever
    if getattr(self, "killStrong", None) is None:
      self.killStrong = self.killUsual
    # summon zombies, whatever

  def useBuffs(self):
    for buff in self.buff_skills:
      if buff.use() is True:
        return True
    return False

  def useFlasks(self):
    # smth to keep it alive, usually just enough to keep flasks,
    # but smth like cwdt needs to use flasks + tap barrier button
    self.auto_flasks.useFlasks()

  def staticDefence(self):
    poe_bot = self.poe_bot
    self.useFlasks()
    mover = self.poe_bot.mover
    detection_range = 30
    danger_zones = list(
      filter(
        lambda e: e.distance_to_player < detection_range and any(list(map(lambda key: key in e.path, DANGER_ZONE_KEYS))),
        poe_bot.game_data.entities.all_entities,
      )
    )
    if len(danger_zones) != 0:
      print(f"danger zone in range {detection_range}")
      danger_zone_str = list(map(lambda e: e.path, danger_zones))
      print(danger_zone_str)
      if self.chaos_immune is False and any(list(map(lambda s: "/LeagueArchnemesis/ToxicVolatile" in s, danger_zone_str))):
        print("dodging caustic orbs")
        # caustic orbs logic
        print("get behind nearest")
        min_move_distance = 35
        distance_to_jump = 15

        caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, danger_zones))
        sorted_caustic_orbs = sorted(caustic_orbs, key=lambda e: e.distance_to_player)
        nearest_caustic_orb = sorted_caustic_orbs[0]

        need_distance = nearest_caustic_orb.distance_to_player + distance_to_jump
        if need_distance < min_move_distance:
          need_distance = min_move_distance

        multiplier = need_distance / nearest_caustic_orb.distance_to_player
        grid_pos_x, grid_pos_y = extendLine(
          (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y),
          (nearest_caustic_orb.grid_position.x, nearest_caustic_orb.grid_position.y),
          multiplier,
        )

        poe_bot.last_action_time = 0
        mover.goToPoint(
          point=(int(grid_pos_x), int(grid_pos_y)),
          min_distance=25,
          custom_continue_function=self.usualRoutine,
          # custom_break_function=collectLootIfFound,
          release_mouse_on_end=False,
          step_size=random.randint(25, 33),
        )
        print("got behind closest")

        print("going behind center of all others")

        poe_bot.last_action_time = 0
        poe_bot.refreshInstanceData()
        poe_bot.last_action_time = 0

        caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))
        while len(caustic_orbs) != 0:
          print(f"there are still {len(caustic_orbs)} caustic orbs left, going behind them")
          if len(caustic_orbs) == 0:
            print("no caustic orbs left")
            return True

          print(f"playerpos {poe_bot.game_data.player.grid_pos.x} {poe_bot.game_data.player.grid_pos.y}")
          print(
            f"list(map(lambda e: e.grid_position.x, caustic_orbs)) {list(map(lambda e: e.grid_position.x, caustic_orbs))}  {list(map(lambda e: e.grid_position.y, caustic_orbs))}"
          )
          center_x = sum(list(map(lambda e: e.grid_position.x, caustic_orbs))) / len(caustic_orbs)
          center_y = sum(list(map(lambda e: e.grid_position.y, caustic_orbs))) / len(caustic_orbs)
          caustic_orbs_center = [center_x, center_y]
          print(f"caustic_orbs_center {caustic_orbs_center}")
          caustic_orbs_center_distance_to_player = dist(
            caustic_orbs_center, (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y)
          )
          need_distance = caustic_orbs_center_distance_to_player + distance_to_jump
          if need_distance < min_move_distance:
            need_distance = min_move_distance

          multiplier = need_distance / caustic_orbs_center_distance_to_player
          grid_pos_x, grid_pos_y = extendLine(
            (poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y), (center_x, center_y), multiplier
          )

          mover.goToPoint(
            point=(int(grid_pos_x), int(grid_pos_y)),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25, 33),
          )

          poe_bot.last_action_time = 0
          poe_bot.refreshInstanceData()
          poe_bot.last_action_time = 0
          caustic_orbs = list(filter(lambda e: "/LeagueArchnemesis/ToxicVolatile" in e.path, poe_bot.game_data.entities.all_entities))

        #
        pass
      elif self.chaos_immune is False and any(list(map(lambda s: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in s, danger_zone_str))):
        print("dodging living crystals")
        living_crystals = list(
          filter(lambda e: "Metadata/Monsters/LeagueArchnemesis/LivingCrystal" in e.path and e.distance_to_player < 20, danger_zones)
        )
        if len(living_crystals) != 0:
          center_x = int(sum(list(map(lambda e: e.grid_position.x, living_crystals))) / len(living_crystals))
          center_y = int(sum(list(map(lambda e: e.grid_position.y, living_crystals))) / len(living_crystals))
          possible_points_to_dodge = []
          jump_range = 35
          print(f"living crystal center x:{center_x} y:{center_y}")
          for ix in range(-1, 2):
            for iy in range(-1, 2):
              possible_points_to_dodge.append([center_x + ix * jump_range, center_y + iy * jump_range])

          random.shuffle(possible_points_to_dodge)
          point_to_dodge = None
          for point in possible_points_to_dodge:
            is_passable = poe_bot.helper_functions.checkIfEntityOnCurrenctlyPassableArea(point[0], point[1])
            if is_passable is True:
              point_to_dodge = point
              break
          if point_to_dodge is None:
            point_to_dodge = [
              int(poe_bot.game_data.player.grid_pos.x + random.randint(-1, 1) * jump_range),
              poe_bot.game_data.player.grid_pos.y + random.randint(-1, 1) * jump_range,
            ]
          mover.goToPoint(
            point=(int(point_to_dodge[0]), int(point_to_dodge[1])),
            min_distance=25,
            custom_continue_function=self.usualRoutine,
            # custom_break_function=collectLootIfFound,
            release_mouse_on_end=False,
            step_size=random.randint(25, 33),
          )
        else:
          print("they are too far away from us")
    pass

  def pointToRunAround(self, point_to_run_around_x, point_to_run_around_y, distance_to_point=15):
    poe_bot = self.poe_bot
    our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
    # entity pos
    pos_x, pos_y = point_to_run_around_x, point_to_run_around_y

    points_around = [
      [pos_x + distance_to_point, pos_y],
      [int(pos_x + distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],
      [pos_x, pos_y - distance_to_point],
      [int(pos_x - distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],
      [pos_x - distance_to_point, pos_y],
      [int(pos_x - distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],
      [pos_x, pos_y + distance_to_point],
      [int(pos_x + distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],
      [pos_x + distance_to_point, pos_y],
    ]
    distances = list(map(lambda p: dist(our_pos, p), points_around))
    nearset_pos_index = distances.index(min(distances))
    # TODO check if next point is possible
    point = points_around[nearset_pos_index + 1]
    return point

  def prepareToFight(self, entity: Entity):
    # actions to do before some strong fight, such as placing totems before the essence opened or whatever
    print("prepareToFight is not defined")

  def canAttackEntity(self, entity_to_kill:Entity, min_distance=100):
    if not entity_to_kill:
      print('cannot find desired entity to kill')
      return False
    print(f'entity_to_kill {entity_to_kill}')
    if entity_to_kill.life.health.current < 1:
      print('entity is dead')
      return False
    distance_to_entity = dist( (entity_to_kill.grid_position.x, entity_to_kill.grid_position.y), (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y) )
    print(f'distance_to_entity {distance_to_entity} in killUsual')
    if distance_to_entity > min_distance:
      print('getting closer in killUsual ')
      return False
    
  def swapWeaponsIfNeeded(self):
    poe_bot = self.poe_bot
    for i in range(99):
      # poe_bot.skills.update()
      portal_gem_in_skills = "town_portal" in poe_bot.backend.getSkillBar()["i_n"]
      print(f"portal_gem_in_skills {portal_gem_in_skills}")
      if portal_gem_in_skills is False:
        print("weapons swapped")
        break
      if i == 10:
        poe_bot.raiseLongSleepException("cannot swap weapon for 10 iterations")
      print("swapping weapons")

      poe_bot.bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10, 20) / 10)
    return True

  def usualRoutine(self, mover: Mover = None):
    self.poe_bot.raiseLongSleepException("usualRoutine is not defined in build")

  def killUsual(self, entity: Entity, is_strong=False, max_kill_time_sec=10, *args, **kwargs):
    pass

  def doPreparations(self):
    poe_bot = self.poe_bot

    for i in range(99):
      # poe_bot.skills.update()
      portal_gem_in_skills = "town_portal" in poe_bot.backend.getSkillBar()["i_n"]
      print(f"portal_gem_in_skills {portal_gem_in_skills}")
      if portal_gem_in_skills is False:
        print("weapons swapped")
        break
      if i == 10:
        poe_bot.raiseLongSleepException("cannot swap weapon for 10 iterations")
      print("swapping weapons")

      poe_bot.bot_controls.keyboard.tap("DIK_X")
      time.sleep(random.randint(10, 20) / 10)
    poe_bot.combat_module.aura_manager.activateAurasIfNeeded()