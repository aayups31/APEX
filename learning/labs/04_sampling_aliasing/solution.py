import numpy as np

for hz in [5, 12, 40]:
    t=np.arange(0,2,1/hz)
    signal=np.sin(2*np.pi*8*t)
    print(hz, "Hz samples:", np.round(signal[:8],3))
