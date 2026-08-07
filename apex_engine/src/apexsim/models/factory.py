from __future__ import annotations

from torch import nn

from apexsim.config import ModelConfig
from apexsim.models.gru_world_model import GRUWorldModel
from apexsim.models.rssm import RSSMWorldModel
from apexsim.models.ssm_world_model import SSMWorldModel


def build_model(config: ModelConfig, input_dim: int, state_dim: int) -> nn.Module:
    if config.kind == "gru":
        return GRUWorldModel(input_dim, state_dim, config.hidden_dim, config.layers, config.dropout)
    if config.kind == "ssm":
        return SSMWorldModel(input_dim, state_dim, config.hidden_dim, config.layers)
    if config.kind == "rssm":
        return RSSMWorldModel(input_dim, state_dim, config.hidden_dim, config.latent_dim)
    raise ValueError(f"Model kind {config.kind!r} is not a neural world model")
