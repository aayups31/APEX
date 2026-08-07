import torch

torch.manual_seed(2); cell=torch.nn.GRUCell(2,4); h=torch.zeros(1,4)
for x in [torch.tensor([[1.,0.]]),torch.tensor([[0.,1.]]),torch.tensor([[0.,1.]])]:
    h=cell(x,h); print(h.detach().numpy().round(3))
