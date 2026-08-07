import torch

from apexsim.models.gru_world_model import GRUWorldModel
from apexsim.models.rssm import RSSMWorldModel
from apexsim.models.ssm_world_model import SSMWorldModel


def test_models_produce_expected_shapes():
    history = torch.randn(2, 12, 16)
    future = torch.randn(2, 5, 16)
    gru = GRUWorldModel(16, 5, 24)
    ssm = SSMWorldModel(16, 5, 24, 2)
    rssm = RSSMWorldModel(16, 5, 24, 8)
    assert gru(history, future).shape == (2, 5, 5)
    assert ssm(history, future).shape == (2, 5, 5)
    pred, kl = rssm(history, future, torch.randn(2, 5, 5))
    assert pred.shape == (2, 5, 5)
    assert kl.ndim == 0
