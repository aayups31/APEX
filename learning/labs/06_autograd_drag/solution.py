import torch

speed=torch.linspace(5,70,200)
true_drag=0.002
target=-true_drag*speed**2
drag=torch.tensor(0.01,requires_grad=True)
opt=torch.optim.SGD([drag],lr=1e-7)
for step in range(200):
    opt.zero_grad()
    pred=-drag*speed**2
    loss=((pred-target)**2).mean()
    loss.backward(); opt.step()
print("learned drag:", drag.item(), "loss:", loss.item())
