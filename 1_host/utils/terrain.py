import numpy as np
import cv2
from math import dist
import time

from .poebot import PoeBot
from .components import PosXY
from .utils import createLineIteratorWithValues, getFourPoints

class Terrain:
  poe_bot: PoeBot
  terrain_image: np.ndarray  # np array
  passable: np.ndarray  # nparray
  currently_passable_area: np.ndarray = None
  visited_passable_areas: np.ndarray
  visited_area: np.ndarray  # np array

  def __init__(self, poe_bot: PoeBot) -> None:
    self.poe_bot = poe_bot

  def markAsVisited(self, pos_x: int, pos_y: int, radius: int = None):
    if radius is not None:
      area = radius
    else:
      area = self.poe_bot.discovery_radius
    # cv2.circle(self.terrain.visited_area, (int(self.player.grid_pos.x), int(self.player.grid_pos.y)), self.poe_bot.discovery_radius, 127, -1); return
    visited_lower_x = pos_x - area
    if visited_lower_x < 0:
      visited_lower_x = 0
    visited_upper_x = pos_x + area

    visited_lower_y = pos_y - area
    if visited_lower_y < 0:
      visited_lower_y = 0
    visited_upper_y = pos_y + area
    self.visited_area[visited_lower_y:visited_upper_y, visited_lower_x:visited_upper_x] = 127

  def update(self, refreshed_data: dict, refresh_visited=True):
    terrain_data = refreshed_data["terrain_string"].split("\r\n")[:-1]
    img = np.asarray(list(map(lambda l: np.fromstring(l, "int8"), terrain_data)))
    self.terrain_image = img

    # 1 passable, 0 - non passable
    ret, self.passable = cv2.threshold(cv2.convertScaleAbs(self.terrain_image), 49, 1, cv2.THRESH_BINARY)  # ?
    # self.passable = (cv2.convertScaleAbs(self.terrain_image) != 49).astype(int) # != is faster than >=
    if refresh_visited is True:
      self.resetVisitedArea()

    return img

  def getGridPosition(self, x, y):
    return PosXY(x, self.terrain_image.shape[0] - y)

  def getFurtherstPassablePoint(
    self,
  ):
    poe_bot = self.poe_bot
    currently_passable_area = self.getCurrentlyPassableArea()
    # plt.imshow(currently_passable_area);plt.show()
    currently_passable_area_for_discovery = currently_passable_area
    data = np.where(currently_passable_area_for_discovery == 1)
    passable_points = list(zip(data[0], data[1]))
    max_distance = 0
    furthest_unvisited = [0, 0]  # TODO ARRAY OF 5 random points
    # TODO arr[:-int(len(arr)/4)].shuffle()[0]
    for point in passable_points:
      distance = dist([point[0], point[1]], [poe_bot.game_data.player.grid_pos.y, poe_bot.game_data.player.grid_pos.x])
      if distance > max_distance:
        max_distance = distance

        furthest_unvisited = point
    grid_pos_to_go_y, grid_pos_to_go_x = furthest_unvisited[0], furthest_unvisited[1]
    return [grid_pos_to_go_x, grid_pos_to_go_y]

  def getCurrentlyPassableArea(self, dilate_kernel_size=10):
    """
    generates a passable zone for current area
    - returns
    2dnumpy, 0 unpassable, 1 passable
    """
    poe_bot = self.poe_bot
    # plt.imshow(poe_bot.generateCurrentlyPassableArea());plt.show()
    all_passable = poe_bot.game_data.terrain.passable.copy()
    # plt.imshow(terrain_image);plt.show()

    # kernel = np.ones((3,3), int)
    # eroded = cv2.erode(terrain_image,kernel ,iterations = 1)
    # dilated = cv2.dilate(eroded,kernel ,iterations = 1)
    # ret, currently_passable = cv2.threshold(cv2.convertScaleAbs(dilated),0,1,cv2.THRESH_BINARY)
    if dilate_kernel_size > 0:
      kernel = np.ones((10, 10), int)
      all_passable = cv2.dilate(all_passable, kernel, iterations=1)
    # plt.imshow(all_passable);plt.show()
    ret, currently_passable_dilated = cv2.threshold(cv2.convertScaleAbs(all_passable), 0, 1, cv2.THRESH_BINARY)
    # plt.imshow(currently_passable_dilated);plt.show()

    player_pos_cell_size = 10
    current_grid_pos_x = poe_bot.game_data.player.grid_pos.x
    current_grid_pos_y = poe_bot.game_data.player.grid_pos.y
    # print(current_grid_pos_x, current_grid_pos_y)
    nearest_passable_player_points = np.where(
      currently_passable_dilated[
        int(current_grid_pos_y) - player_pos_cell_size : int(current_grid_pos_y) + player_pos_cell_size,
        int(current_grid_pos_x) - player_pos_cell_size : int(current_grid_pos_x) + player_pos_cell_size,
      ]
      == 1
    )
    nearest_passable_player_point = list(list(zip(nearest_passable_player_points[0], nearest_passable_player_points[1]))[0])
    nearest_passable_player_point[0] = int(current_grid_pos_y) + nearest_passable_player_point[0] - player_pos_cell_size
    nearest_passable_player_point[1] = int(current_grid_pos_x) + nearest_passable_player_point[1] - player_pos_cell_size
    floodval = 128
    cv2.floodFill(currently_passable_dilated, None, (nearest_passable_player_point[1], nearest_passable_player_point[0]), floodval)
    # Extract filled area alone
    currently_passable_area = ((currently_passable_dilated == floodval) * 1).astype(np.uint8)
    # plt.imshow(currently_passable);plt.show()
    self.currently_passable_area = currently_passable_area
    self.visited_passable_areas[self.currently_passable_area != 0] = 1
    return currently_passable_area

  def resetVisitedArea(self):
    self.visited_area = np.zeros((self.terrain_image.shape[0], self.terrain_image.shape[1]), dtype=np.uint8)
    self.visited_passable_areas = np.zeros((self.terrain_image.shape[0], self.terrain_image.shape[1]), dtype=np.uint8)

  def pointToRunAround(self, point_to_run_around_x: int, point_to_run_around_y: int, distance_to_point=15, reversed=False, check_if_passable=False):
    poe_bot = self.poe_bot
    our_pos = [poe_bot.game_data.player.grid_pos.x, poe_bot.game_data.player.grid_pos.y]
    # entity pos
    pos_x, pos_y = point_to_run_around_x, point_to_run_around_y
    """
    111
    101
    112
    """
    points_around = [
      [pos_x + distance_to_point, pos_y],  # 90
      [int(pos_x + distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],  # 45
      [pos_x, pos_y - distance_to_point],  # 0
      [int(pos_x - distance_to_point * 0.7), int(pos_y - distance_to_point * 0.7)],  # 315
      [pos_x - distance_to_point, pos_y],  # 270
      [int(pos_x - distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],  # 215
      [pos_x, pos_y + distance_to_point],  # 180
      [int(pos_x + distance_to_point * 0.7), int(pos_y + distance_to_point * 0.7)],  # 135
    ]
    if reversed is True:
      points_around.reverse()

    distances = list(map(lambda p: dist(our_pos, p), points_around))
    nearset_pos_index = distances.index(min(distances))
    # TODO check if next point is passable
    current_pos_index = nearset_pos_index + 1
    if current_pos_index > len(points_around) - 1:
      current_pos_index -= len(points_around)
    point = points_around[current_pos_index]
    if check_if_passable is True:
      if self.checkIfPointPassable(point[0], point[1], radius=1) is False:
        start_index = current_pos_index + 1
        point_found = False
        for i in range(len(points_around) - 2):
          current_index = start_index + i
          if current_index > len(points_around) - 1:
            current_index -= len(points_around)
          point = points_around[current_index]
          if self.checkIfPointPassable(point[0], point[1], radius=1) is True:
            point_found = True
            break
        if point_found is True:
          pass
    return point

  def checkIfPointPassable(self, grid_pos_x, grid_pos_y, radius=10):
    poe_bot = self.poe_bot
    if poe_bot.game_data.terrain.currently_passable_area is None:
      self.getCurrentlyPassableArea()
    if radius != 0:
      currently_passable_area = poe_bot.game_data.terrain.currently_passable_area
      currently_passable_area_around_entity = currently_passable_area[
        grid_pos_y - radius : grid_pos_y + radius, grid_pos_x - radius : grid_pos_x + radius
      ]
      nearby_passable_points = np.where(currently_passable_area_around_entity != 0)
      if len(nearby_passable_points[0]) > 1:
        return True
      else:
        return False
    else:
      print(
        f"poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] != 0 {poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] == 0}"
      )
      return poe_bot.game_data.terrain.currently_passable_area[grid_pos_y, grid_pos_x] == 0

  def checkIfPointIsInLineOfSight(self, grid_pos_x, grid_pos_y):
    path_values = createLineIteratorWithValues(
      (self.poe_bot.game_data.player.grid_pos.x, self.poe_bot.game_data.player.grid_pos.y), (grid_pos_x, grid_pos_y), self.passable
    )
    path_without_obstacles = bool(np.all(path_values[2:, 2] != 0)) #TODO test if ok "path_values[:, 2]" if affects too much
    return path_without_obstacles

  def isPointVisited(self, grid_pos_x, grid_pos_y):
    five_points = getFourPoints(grid_pos_x, grid_pos_y, radius=35)
    need_to_explore = False
    for point in five_points:
      if self.visited_area[point[1], point[0]] == 0:
        need_to_explore = True
    return need_to_explore

  def getPassableAreaDiscoveredForPercent(self, total=False):
    """
    return the percent of discovered map

    """
    if self.poe_bot.debug:
      print(f"#passableAreaDiscoveredForPercent call {time.time()}")
    if total is True:
      currently_passable = self.visited_passable_areas
    else:
      currently_passable = self.getCurrentlyPassableArea()
    all_possible_discovery_points = np.where(currently_passable != 0)
    if len(all_possible_discovery_points[0]) == 0:
      return 0

    discovered_area = currently_passable.copy()

    discovered_area[self.visited_area != 127] = [0]
    # plt.imshow(discovered_area)
    discovered_points = np.where(discovered_area != 0)
    discover_percent = len(discovered_points[0]) / len(all_possible_discovery_points[0])
    print(f"map discovered for {discover_percent}%")
    if self.poe_bot.debug:
      print(f"#passableAreaDiscoveredForPercent return {time.time()}")
    return discover_percent
