import torch
from torch import nn

class GRUForecaster(nn.Module):
    def __init__(self,f=6,h=32,o=2):
        super().__init__(); self.gru=nn.GRU(f,h,batch_first=True); self.head=nn.Linear(h,o)
    def forward(self,x): return self.head(self.gru(x)[0][:,-1])
if __name__=='__main__': print(GRUForecaster()(torch.randn(8,20,6)).shape)
