import poebot

PoeBot = poebot.PoeBot

class QuestFlags:
  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot
    self.quest_flags_raw: dict = None

  def getOrUpdate(self):
    if self.quest_flags_raw is None:
      self.update()
    return self.quest_flags_raw

  def update(self):
    self.quest_flags_raw = self.poe_bot.backend.getQuestFlags()

  def get(self, force_update=False):
    if force_update is not False:
      self.update()
    return self.getOrUpdate()
