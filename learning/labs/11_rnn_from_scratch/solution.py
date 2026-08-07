import torch

torch.manual_seed(0); W=torch.randn(3,2); U=torch.randn(3,3); b=torch.zeros(3); h=torch.zeros(3)
sequence=torch.tensor([[1.,0.],[0.,1.],[1.,1.]])
for t,x in enumerate(sequence):
    h=torch.tanh(W@x+U@h+b); print(t,h.numpy().round(3))
