import torch
from torch import nn

class SelectiveCell(nn.Module):
    def __init__(self,d):
        super().__init__(); self.decay=nn.Linear(d,d); self.write=nn.Linear(d,d)
    def forward(self,x,h):
        a=torch.sigmoid(self.decay(x))*0.99
        b=torch.tanh(self.write(x))
        return a*h+(1-a)*b
cell=SelectiveCell(3); h=torch.zeros(1,3)
for x in torch.eye(3): h=cell(x[None],h); print(h.detach().numpy().round(3))
