import numpy as np

speed_kmh = np.array([0.0, 72.0, 144.0])
speed_mps = speed_kmh / 3.6
telemetry = np.stack([speed_mps, np.array([0.0, 0.5, 1.0])], axis=1)
print("speed_mps:", speed_mps)
print("telemetry shape [time, features]:", telemetry.shape)
assert telemetry.shape == (3, 2)
