import numpy as np

def run(n=600):
    progress=np.linspace(0,1,n,endpoint=False); curvature=0.02+0.12*(np.sin(6*np.pi*progress)**2)
    target=np.clip(90/(1+10*curvature),20,90); speed=np.empty(n); speed[0]=30
    for i in range(1,n): speed[i]=speed[i-1]+0.08*np.clip(target[i]-speed[i-1],-8,3)
    print('speed range',float(speed.min()),float(speed.max()))
    return progress,curvature,speed
if __name__=='__main__': run()
