import time
import random
from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from .poebot import PoeBot
from .constants import CONSTANTS, FLASK_NAME_TO_BUFF

class AutoFlasks:
  def __init__(self, poe_bot: "PoeBot", hp_thresh=0.5, mana_thresh=0.5, pathfinder=False, life_flask_recovers_es=False) -> None:
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
