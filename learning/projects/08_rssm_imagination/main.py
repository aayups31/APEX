import torch
from torch import nn

cell=nn.GRUCell(5,8); prior=nn.Linear(8,4); posterior=nn.Linear(8+3,4)
h=torch.zeros(2,8); prev_z=torch.zeros(2,2); action=torch.randn(2,3); obs_embed=torch.randn(2,3)
h=cell(torch.cat([prev_z,action],-1),h)
prior_stats=prior(h); post_stats=posterior(torch.cat([h,obs_embed],-1))
print("h",h.shape,"prior",prior_stats.shape,"posterior",post_stats.shape)
