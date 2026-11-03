import pytest

from apexsim.research.tyre_wear import wear_step


def test_wear_is_irreversible_and_sensitive_to_heat_and_energy():
    start = .2
    assert wear_step(start, 0, 330) == start
    base = wear_step(start, 50000, 330)
    assert start < base < wear_step(start, 100000, 330) < 1
    assert base < wear_step(start, 50000, 350)
    assert wear_step(1, 50000, 350) == 1


def test_held_input_can_be_subdivided_without_changing_wear():
    half = wear_step(.2, 50000, 330)
    assert wear_step(half, 50000, 330) == pytest.approx(wear_step(.2, 100000, 330), abs=1e-14)


@pytest.mark.parametrize("energy,temperature", [(-1, 330), (0, 0), (float("nan"), 330)])
def test_invalid_wear_forcing_rejected(energy, temperature):
    with pytest.raises(ValueError):
        wear_step(0, energy, temperature)
