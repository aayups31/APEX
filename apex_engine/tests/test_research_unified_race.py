from apexsim.research.registry import default_registry, registry_frame
from apexsim.research.unified_race import UnifiedPitAction, UnifiedRaceState, rsrl_reward
from apexsim.sim_core.types import TyreCompound


def _state(**changes):
    values = dict(
        terminal=False,
        track_id=1,
        safety_car=False,
        position=5,
        race_progress=0.5,
        current_compound=TyreCompound.MEDIUM,
        tyre_degradation_s=1.0,
        soft_sets_remaining=2,
        medium_sets_remaining=1,
        hard_sets_remaining=1,
        gap_ahead_s=1.2,
        gap_behind_s=0.8,
        gap_leader_s=14.0,
        last_lap_relative_s=0.2,
        valid_finish=True,
    )
    values.update(changes)
    return UnifiedRaceState(**values)


def test_rsrl_reward_topology():
    state = _state()
    assert rsrl_reward(state, UnifiedPitAction.NO_PIT, _state()) == 1.0
    assert rsrl_reward(_state(soft_sets_remaining=0), UnifiedPitAction.PIT_SOFT, _state()) == -1000.0
    terminal = _state(terminal=True, position=1)
    assert rsrl_reward(state, UnifiedPitAction.NO_PIT, terminal) == 2500.0


def test_research_registry_has_priority_papers():
    frame = registry_frame()
    ids = set(frame.paper_id)
    assert {"FIENI_2025", "TODD_2025", "THOMAS_2025", "CAPPELLO_2025"}.issubset(ids)
    assert len(default_registry()) >= 15
