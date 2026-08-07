import torch
from torch import nn

class Transition(nn.Module):
    def __init__(self):
        super().__init__()
        self.net=nn.Sequential(nn.Linear(5,16),nn.ReLU(),nn.Linear(16,2))
    def forward(self,x): return self.net(x)

model=Transition(); x=torch.randn(4,5); y=model(x)
print(model); print("input",x.shape,"output",y.shape)

print("Extend this module with the dataset from Project 3.")
