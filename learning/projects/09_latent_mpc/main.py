import numpy as np

rng=np.random.default_rng(0); horizon=6; mean=np.full(horizon,0.5); std=np.full(horizon,0.3)
for it in range(5):
    actions=np.clip(rng.normal(mean,std,(500,horizon)),0,1)
    speed=40+np.cumsum(2*actions-0.4,axis=1)
    score=-(speed[:,-1]-48)**2-0.1*np.sum(np.diff(actions,axis=1)**2,axis=1)
    elite=actions[np.argsort(score)[-50:]]
    mean,std=elite.mean(0),elite.std(0)+1e-3
    print(it,mean.round(2),score.max().round(3))
