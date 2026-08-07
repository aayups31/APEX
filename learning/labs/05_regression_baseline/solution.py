import numpy as np
from sklearn.linear_model import Ridge

rng=np.random.default_rng(4)
speed=rng.uniform(20,80,1000)
throttle=rng.uniform(0,1,1000)
brake=rng.uniform(0,1,1000)
y=speed + 0.7*throttle - 1.1*brake - 0.0008*speed**2 + rng.normal(0,0.05,1000)
X=np.column_stack([speed,throttle,brake])
model=Ridge(alpha=1.0).fit(X[:800],y[:800])
print("coefficients:", model.coef_)
print("test MAE:", np.mean(np.abs(model.predict(X[800:])-y[800:])))
