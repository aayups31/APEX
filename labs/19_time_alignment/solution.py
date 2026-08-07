import pandas as pd

car=pd.DataFrame({'t':[0.0,0.2,0.4,0.6],'speed':[10,12,14,16]})
weather=pd.DataFrame({'t':[0.05,0.55],'rain':[0.0,0.3]})
aligned=pd.merge_asof(car.sort_values('t'),weather.sort_values('t'),on='t',direction='backward',tolerance=0.3)
print(aligned)
