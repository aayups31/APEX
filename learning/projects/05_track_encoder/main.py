import torch
from torch import nn

class TrackEncoder(nn.Module):
    def __init__(self):
        super().__init__(); self.net=nn.Sequential(nn.Conv1d(3,8,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool1d(1))
    def forward(self,x): return self.net(x).squeeze(-1)
if __name__=='__main__':
    x=torch.randn(4,3,64); print(TrackEncoder()(x).shape)
