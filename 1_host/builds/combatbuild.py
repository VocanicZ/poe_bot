from build import Build

from .builds import GenericBuilds, GenericBuilds2, InfernalistMinion, TempestFlurry, TemporalisBlinker, BarrierInvocationInfernalist, InfernalistZoomancer, PathfinderPoisonConc2

COMBAT_BUILDS = {
  "": GenericBuild.,
  "barrier_invocation_infernalist": BarrierInvocationInfernalist.Build,
  "temporalis_blinker": TemporalisBlinker,
  "tempest_flurry": TempestFlurry,
  "infernalist_minion": InfernalistMinion,
  "infernalist_zoomancer": InfernalistZoomancer,
  "pathfinder_poison_con_2": PathfinderPoisonConc2,
}

COMBAT_BUILDS_LIST = list(COMBAT_BUILDS.keys())

def getBuild(build: str) -> Build:
  return COMBAT_BUILDS[build]