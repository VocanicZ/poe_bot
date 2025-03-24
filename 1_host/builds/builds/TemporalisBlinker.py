from ..build import *

from ...utils.combat import DodgeRoll

class Build(Build):
  def __init__(self, poe_bot:PoeBot):
    super().__init__(poe_bot)
    self.dodge = DodgeRoll(self.poe_bot)