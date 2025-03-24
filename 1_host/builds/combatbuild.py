from build import Build

from .builds import GenericBuilds, GenericBuilds2, InfernalistMinion, TempestFlurry, TemporalisBlinker, BarrierInvocationInfernalist, InfernalistZoomancer, PathfinderPoisonConc2

COMBAT_BUILDS = {
  "generic_hitter": GenericBuilds.GenericHitter,
  "generic_summoner": GenericBuilds.GenericSummoner,
  "generic_face_tank": GenericBuilds.GenericFacetank,
  "generic_hit_and_run": GenericBuilds.GenericHitAndRun,
  "generic_kite_around": GenericBuilds.GenericKiteAround,
  "generic_build_2": GenericBuilds2.GenericBuild2,
  "generic_build_2_cautious": GenericBuilds2.GenericBuild2Cautious,
  "barrier_invocation_infernalist": BarrierInvocationInfernalist,
  "temporalis_blinker": TemporalisBlinker,
  "tempest_flurry": TempestFlurry,
  "infernalist_minion": InfernalistMinion,
  "infernalist_zoomancer": InfernalistZoomancer,
  "pathfinder_poison_con_2": PathfinderPoisonConc2,
}

COMBAT_BUILDS_LIST = list(COMBAT_BUILDS.keys())

def getBuild(build: str) -> Build:
  if not build.startswith("generic_"):
    return COMBAT_BUILDS[build].Build
  return COMBAT_BUILDS[build]