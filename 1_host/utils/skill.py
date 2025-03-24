import random
import time

from math import dist
from typing import List

import poebot
import entity
from .constants import SKILL_KEYS_WASD, SKILL_KEYS, AURAS_SKILLS_TO_BUFFS
from .utils import extendLine

PoeBot = poebot.PoeBot
Entity = entity.Entity

NON_INSTANT_MOVEMENT_SKILLS = ["shield_charge", "whirling_blades"]

INSTANT_MOVEMENT_SKILLS = ["frostblink", "flame_dash"]

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

class Skills:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.can_use_skills_indexes_raw = [1 for i in range(14)]
    self.cast_time = [0 for i in range(14)]
    self.internal_names: List[str] = []
    self.total_uses: list[int] = []
    self.descriptions: List[dict] = []

  def update(self, refreshed_data: dict = None):
    if refreshed_data is None:
      refreshed_data = self.poe_bot.backend.getSkillBar()
    new_indexes = refreshed_data["c_b_u"]
    if new_indexes is not None:
      self.can_use_skills_indexes_raw = new_indexes
    else:
      print('refreshed_data["c_b_u"] is None')
    self.cast_time = []
    for casts_per_100_seconds in refreshed_data["cs"]:
      if casts_per_100_seconds != 0:
        self.cast_time.append(100 / casts_per_100_seconds)
      else:
        self.cast_time.append(0)
    if refreshed_data["i_n"]:
      self.internal_names = refreshed_data["i_n"]
    if refreshed_data["d"]:
      self.descriptions = refreshed_data["d"]
    if refreshed_data["tu"]:
      self.total_uses = refreshed_data["tu"]

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
