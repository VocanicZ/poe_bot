from .components import PosXY

class Animation:
  def __init__(self):
    # which action
    self.actor_action:str
    self.actor_action_skill_name:str
    self.actor_animation:str

    # which destination
    self.actor_animation_destination:PosXY



    # how much time there is before the damage will happen? how dangerous is the action's destination
    # actor_animation_stage int?
    self.actor_animation_animation_controller_stage: int
    # actor_animation_progress %?
    self.actor_animation_animation_controller_progress: float 
    # time [start, end, current]
    self.progress: list[float]