import torch

mu=torch.tensor([[0.2,-0.4]]); logvar=torch.tensor([[-1.0,0.5]])
std=torch.exp(0.5*logvar); eps=torch.randn_like(std); z=mu+std*eps
kl=-0.5*torch.sum(1+logvar-mu.pow(2)-logvar.exp(),dim=1)
print("mu",mu,"std",std,"sample",z,"KL",kl)
