import torch
from torch import nn

torch.manual_seed(1); x=torch.randn(128,3); y=x.sum(1,keepdim=True)
model=nn.Linear(3,1); opt=torch.optim.Adam(model.parameters(),lr=0.05)
for epoch in range(8):
    model.train(); opt.zero_grad(); pred=model(x); loss=((pred-y)**2).mean(); loss.backward()
    grad=float(model.weight.grad.norm()); opt.step()
    model.eval();
    with torch.no_grad(): val=((model(x)-y)**2).mean()
    print(epoch,float(loss),grad,float(val))
