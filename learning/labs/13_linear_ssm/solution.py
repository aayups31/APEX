import numpy as np
A=np.array([[0.95,0.0],[0.1,0.85]]); B=np.array([[0.2],[0.05]]); x=np.zeros(2)
for u in [1,1,0,0,0]:
    x=A@x+B[:,0]*u; print(x.round(3))
