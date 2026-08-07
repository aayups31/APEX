import torch
from torch.nn import functional as F

pred=torch.tensor([0.,1.,2.,20.]); target=torch.tensor([0.,1.,2.,3.])
print("MSE",F.mse_loss(pred,target).item())
print("MAE",F.l1_loss(pred,target).item())
print("Huber",F.huber_loss(pred,target).item())
