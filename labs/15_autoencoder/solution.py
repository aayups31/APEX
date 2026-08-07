import torch
from torch import nn

torch.manual_seed(3); x=torch.randn(256,12)
enc=nn.Linear(12,3); dec=nn.Linear(3,12); opt=torch.optim.Adam(list(enc.parameters())+list(dec.parameters()),lr=0.03)
for _ in range(80):
    opt.zero_grad(); z=torch.tanh(enc(x)); recon=dec(z); loss=((recon-x)**2).mean(); loss.backward(); opt.step()
print("latent",z.shape,"loss",float(loss))
