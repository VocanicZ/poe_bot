import numpy as np

from .components import PoeBotComponent

class ItemLabels:
  def __init__(self) -> None:
    pass

class Camera(PoeBotComponent):
  failure_count = 0
  max_failures = 5
  
  def update(self, data:dict):
    # self.matrix = data["m"]
    matrix_data = data["m"]
    if matrix_data is None:
      # sometimes can be empty?
      print(f'[Camera.update] matrix data is None')
      self.failure_count += 1
      if self.failure_count == self.max_failures:
        raise ValueError(f"[Camera.update] failed to updated matrix for {self.max_failures} attempts in row")
    else:
      #print(f"[Camera.update] updating camera matrix with {matrix_data}")
      self.matrix = np.array(matrix_data, dtype=np.float32).reshape(4, 4)
      self.failure_count = 0

  def getScreenLocation(self, x,y,z):
    # https://github.com/Qvin0000/ExileApi/blob/master/Core/PoEMemory/MemoryObjects/Camera.cs#L36
    if x != 0 and y != 0:
      try:
        cord = np.array([x, y, z, 1.0], dtype=np.float32)
        cord = cord @ self.matrix  # row-vector multiplication 
        cord = cord / cord[3]  # Divide X, Y, Z by W
        screen_x = (cord[0] + 1.0) * self.poe_bot.game_window.center_point[0]
        screen_y = (1.0 - cord[1]) * self.poe_bot.game_window.center_point[1]
        return [int(screen_x), int(screen_y)]
      except Exception as ex:
        print(f"Error in getScreenLocation: {ex}")
        return [0,0]
    else:
      return [0,0]
