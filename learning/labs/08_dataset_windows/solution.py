import numpy as np
from education.core import sliding_windows

values=np.arange(30,dtype=float).reshape(10,3)
x,y=sliding_windows(values,history=4,horizon=2)
print("x",x.shape,"y",y.shape)
print("first history\n",x[0]); print("first future\n",y[0])
