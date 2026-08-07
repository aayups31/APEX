import numpy as np

dt = 0.2
time = np.arange(0, 5, dt)
speed = 20 + 4*np.sin(time)
accel = np.gradient(speed, dt)
reconstructed = speed[0] + np.cumsum(accel)*dt
print("first accelerations:", accel[:5].round(3))
print("max reconstruction error:", float(np.max(np.abs(reconstructed-speed))))
