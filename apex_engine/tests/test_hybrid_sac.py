from dataclasses import replace
from math import log, pi

import numpy as np
import pytest
import torch

from apexsim.research.fienia_strategy import PaperStrategyAction, PaperStrategyModel, TireWearCoefficients
from apexsim.research.hybrid_sac import HybridSAC, SACSettings, soft_value, tanh_log_density
from apexsim.research.sac_env import DRY, StrategyLearningEnv, sac_task_model
from apexsim.research.sac_training import StrategyReplayBuffer, train_strategy_sac
from apexsim.sim_core.types import TyreCompound


def small_settings(seed=11):
    return SACSettings(seed=seed, steps=36, hidden=16, batch_size=4, warmup=8, replay_capacity=16)


def test_density_analytic_and_extreme_values():
    zero = torch.zeros(2, 2, dtype=torch.float64)
    assert tanh_log_density(zero, zero, zero).tolist() == pytest.approx([-log(2*pi)] * 2)
    raw = torch.tensor([[.3, -.7]], dtype=torch.float64)
    expected = (-.5 * (raw.square() + log(2*pi)) - torch.log(1-raw.tanh().square())).sum(-1)
    assert torch.allclose(tanh_log_density(raw, raw, torch.zeros_like(raw)), expected)
    extreme = torch.tensor([[100., -100.]])
    assert torch.isfinite(tanh_log_density(extreme, zero[:1].float(), zero[:1].float())).all()


def test_exact_categorical_entropy_and_energy_density():
    probs = torch.tensor([[.25, .75, 0., 0.]], dtype=torch.float64)
    log_probs = torch.tensor([[log(.25), log(.75), -1e9, -1e9]], dtype=torch.float64)
    q = torch.tensor([[2., 4., 999., 999.]], dtype=torch.float64)
    expected = .25*2 + .75*4 - .1*(.25*log(.25) + .75*log(.75)) + .05
    assert soft_value(q, probs, log_probs, torch.tensor([-.5]), .1).item() == pytest.approx(expected)


def test_learning_mask_and_reward_invariants():
    env = StrategyLearningEnv()
    observation, mask = env.reset(TyreCompound.MEDIUM)
    assert observation.shape == (10,) and observation.dtype == np.float32
    assert observation[[0, 1, 2, 9]].tolist() == [1., 1., 1., 1.]
    assert mask.tolist() == [True]*4
    rewards = 0.
    result = env.step([0., 0.], 0)
    rewards += result.reward
    assert result.mask.tolist() == [False, True, False, True]
    before = env.state
    with pytest.raises(ValueError, match="mask"):
        env.step([0., 0.], 2)
    assert env.state is before
    result = env.step([0., 0.], 1)
    rewards += result.reward
    assert result.mask.tolist() == [True, False, False, False]
    result = env.step([1., 1.], 0)
    rewards += result.reward
    assert result.terminated and env.model.final_state_is_legal(env.state)
    assert rewards == pytest.approx(3 * env.model.p.nominal_lap_time_s - env.smooth_time_s)
    assert result.observation[-1] == 0.
    with pytest.raises(RuntimeError, match="terminated"):
        env.step([0., 0.], 0)


@pytest.mark.parametrize("energy,pit", [([2., 0.], 0), ([np.nan, 0.], 0), ([0.], 0), ([0., 0.], True), ([0., 0.], 4)])
def test_learning_rejects_bad_requests_without_state_change(energy, pit):
    env = StrategyLearningEnv()
    env.reset()
    before = env.state
    with pytest.raises(ValueError):
        env.step(energy, pit)
    assert env.state is before and env.smooth_time_s == 0.


def test_learning_wear_clip_is_rejected_before_commit():
    model = sac_task_model()
    model = PaperStrategyModel(model.p, wear_coefficients={c: TireWearCoefficients(1., 0., 2.) for c in DRY})
    env = StrategyLearningEnv(model)
    env.reset()
    before = env.state
    with pytest.raises(ValueError, match="wear"):
        env.step([0., 0.], 0)
    assert env.state is before


def test_learning_inverse_roundoff_and_real_domain_violation():
    env = StrategyLearningEnv()
    p = env.model.p
    energy = env.physical_to_energy(PaperStrategyAction(1.1*p.nominal_fuel_energy_mj(), -.5))
    assert energy[0] == 1.
    with pytest.raises(ValueError, match="domain"):
        env.physical_to_energy(PaperStrategyAction(1.101*p.nominal_fuel_energy_mj(), -.5))


def test_learning_matches_smooth_scalar_and_symbolic_replay():
    pytest.importorskip("casadi")
    from apexsim.research.strategy_solver import FixedPlanProblem, energy_starts

    env = StrategyLearningEnv()
    env.reset()
    start = energy_starts(env.model)[1]
    actions = []
    for i in range(3):
        action = PaperStrategyAction(start[i]*env.model.p.nominal_fuel_energy_mj(), start[3+i], TyreCompound.SOFT if i == 0 else None)
        actions.append(env.step(env.physical_to_energy(action), 1 if i == 0 else 0).transition.applied_action)
    controls = [a.fuel_energy_mj/env.model.p.nominal_fuel_energy_mj() for a in actions] + [a.battery_delta_mj for a in actions]
    problem = FixedPlanProblem(env.model, (TyreCompound.SOFT, None, None))
    replay = problem.replay(controls)
    assert env.smooth_time_s == pytest.approx(replay.smooth_race_time_s, abs=1e-10)
    assert float(problem.objective(controls)) == pytest.approx(env.smooth_time_s, abs=1e-10)
    assert env.state.race_time_s == pytest.approx(replay.original_race_time_s)


def terminal_batch():
    return {"observation": torch.ones(4, 10), "next_observation": torch.ones(4, 10),
            "energy": torch.zeros(4, 2), "mask": torch.ones(4, 4, dtype=torch.bool),
            "next_mask": torch.tensor([[True, False, False, False]]*4),
            "pit": torch.zeros(4, dtype=torch.long), "reward": torch.tensor([1., 2., 3., 4.]), "done": torch.ones(4)}


def test_terminal_no_bootstrap_real_gradients_and_polyak_update():
    state = torch.random.get_rng_state().clone()
    agent = HybridSAC(small_settings())
    assert torch.equal(state, torch.random.get_rng_state())
    old_actor = [p.clone() for p in agent.actor.parameters()]
    old_target = [p.clone() for p in agent.target.parameters()]
    metrics = agent.update(terminal_batch())
    assert metrics["target_mean"] == 2.5  # terminal rewards only, irrespective of target Q
    assert metrics["actor_gradient_norm"] > 0 and metrics["critic_gradient_norm"] > 0
    assert any(not torch.equal(a, b) for a, b in zip(old_actor, agent.actor.parameters(), strict=True))
    for old, target, online in zip(old_target, agent.target.parameters(), agent.critics.parameters(), strict=True):
        assert torch.allclose(target, old*(1-agent.settings.target_mix) + online*agent.settings.target_mix)
    assert np.isfinite(list(metrics.values())).all() and agent.updates == 1


def test_nonterminal_soft_target_matches_scalar_expectation():
    agent = HybridSAC(small_settings())
    with torch.no_grad():
        for p in agent.actor.parameters():
            p.zero_()
        for p in agent.target.parameters():
            p.zero_()
        agent.target.q1[-1].bias.fill_(2.)
        agent.target.q2[-1].bias.fill_(3.)
    batch = terminal_batch()
    batch["done"] = torch.tensor([0., 1., 0., 1.])
    batch["next_mask"] = torch.ones(4, 4, dtype=torch.bool)
    generator = torch.Generator().set_state(agent.generator.get_state())
    noise = torch.randn((4, 2), generator=generator).numpy()
    # Independent Gaussian/tanh density and uniform categorical entropy.
    density = (-.5*(noise**2 + log(2*pi)) - np.log(1-np.tanh(noise)**2)).sum(axis=1)
    values = 2. + agent.settings.alpha*log(4) - agent.settings.alpha*density
    expected = np.mean(np.array([1., 2., 3., 4.]) + np.array([1., 0., 1., 0.])*values)
    assert agent.update(batch)["target_mean"] == pytest.approx(expected, abs=1e-6)


def test_inference_masks_and_deterministic_rng():
    agent, env = HybridSAC(small_settings()), StrategyLearningEnv()
    obs, _ = env.reset()
    mask = np.array([False, True, False, False])
    state = agent.generator.get_state().clone()
    assert agent.act(obs, mask, True)[1] == 1
    assert torch.equal(state, agent.generator.get_state())
    assert all(agent.act(obs, mask)[1] == 1 for _ in range(10))
    with pytest.raises(ValueError):
        agent.act(obs, np.zeros(4, dtype=bool))


@pytest.mark.parametrize("field,value", [("energy", torch.full((4, 2), 2.)), ("reward", torch.full((4,), float("nan"))),
                                         ("pit", torch.ones(4, dtype=torch.long)*4), ("mask", torch.zeros(4, 4, dtype=torch.bool)),
                                         ("done", torch.full((4,), .5))])
def test_update_rejects_bad_replay(field, value):
    agent, batch = HybridSAC(small_settings()), terminal_batch()
    batch[field] = value
    with pytest.raises(ValueError):
        agent.update(batch)
    assert agent.updates == 0


def test_replay_ring_sampling_and_mask_validation():
    buffer = StrategyReplayBuffer(4, 19)
    with pytest.raises(ValueError):
        buffer.sample(1)
    for i in range(8):
        buffer.add(np.full(10, i, dtype=np.float32), np.ones(4, dtype=bool), np.zeros(2), 0,
                   float(i), np.ones(10), np.ones(4, dtype=bool), False)
    batch = buffer.sample(4)
    assert sorted(batch["reward"].tolist()) == [4., 5., 6., 7.]
    assert batch["observation"].dtype == torch.float32 and batch["pit"].dtype == torch.long
    with pytest.raises(ValueError, match="masked"):
        buffer.add(np.ones(10), np.array([True, False, False, False]), np.zeros(2), 1, 0., np.ones(10), np.ones(4, dtype=bool), False)


def test_seeded_training_checkpoint_and_global_rng_isolation(tmp_path):
    torch_state, np_state = torch.random.get_rng_state().clone(), np.random.get_state()
    agent, report, trace = train_strategy_sac(small_settings())
    other, other_report, _ = train_strategy_sac(small_settings())
    assert torch.equal(torch_state, torch.random.get_rng_state())
    after_np = np.random.get_state()
    assert np_state[0] == after_np[0] and np.array_equal(np_state[1], after_np[1]) and np_state[2:] == after_np[2:]
    assert report["completed_episodes"] == 12 and report["initial_compound_episodes"] == {c.value: 4 for c in DRY}
    assert report["updates"] == 28 and report["evaluation_transitions_in_replay"] == 0
    assert report["actor_parameter_change_l2"] > 0 and report["critic_parameter_change_l2"] > 0
    assert report["last_100_mean_return"] == other_report["last_100_mean_return"] and trace[-1]["step"] == 36
    assert all(torch.equal(a, b) for a, b in zip(agent.actor.parameters(), other.actor.parameters(), strict=True))
    path = tmp_path / "policy.pt"
    agent.save_inference_checkpoint(path, report["environment"])
    restored = HybridSAC.load_inference_checkpoint(path, report["environment"])
    env = StrategyLearningEnv()
    for compound in DRY:
        obs, mask = env.reset(compound)
        expected, actual = agent.act(obs, mask, True), restored.act(obs, mask, True)
        assert np.array_equal(expected[0], actual[0]) and expected[1] == actual[1]
    with pytest.raises(FileExistsError):
        agent.save_inference_checkpoint(path, report["environment"])
    with pytest.raises(ValueError, match="mismatch"):
        HybridSAC.load_inference_checkpoint(path, {"other": "environment"})
    payload = torch.load(path, weights_only=True)
    next(iter(payload["actor"].values())).fill_(float("nan"))
    torch.save(payload, tmp_path / "corrupt.pt")
    with pytest.raises(ValueError, match="nonfinite"):
        HybridSAC.load_inference_checkpoint(tmp_path / "corrupt.pt", report["environment"])


@pytest.mark.parametrize("change", [{"gamma": .99}, {"steps": 100001}, {"alpha": 0.}, {"target_mix": 2.}, {"warmup": 1}, {"seed": True}])
def test_settings_fail_closed(change):
    with pytest.raises(ValueError):
        replace(small_settings(), **change)
