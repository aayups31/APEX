import pandas as pd

REQUIRED={'time_s','speed_mps','throttle','brake'}
def validate(df):
    errors=[]
    if not REQUIRED.issubset(df): errors.append('missing columns')
    if not df.time_s.is_monotonic_increasing: errors.append('time not monotonic')
    if (df.speed_mps<0).any(): errors.append('negative speed')
    if not df.throttle.between(0,1).all(): errors.append('throttle range')
    return errors
def run():
    df=pd.DataFrame({'time_s':[0,0.1,0.2],'speed_mps':[0,3,4],'throttle':[0,1,0.5],'brake':[0,0,0]})
    assert validate(df)==[]; print('quality passed')
if __name__=='__main__': run()
