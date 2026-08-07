from education.core import CarState, step_car

def run():
    state=CarState(0,0,0)
    trace=[]
    for i in range(100):
        state=step_car(state,0.8 if i<60 else 0.0,0.0 if i<60 else 0.5,0.1)
        trace.append(state)
    assert trace[-1].speed_mps >= 0
    print(trace[-1])
if __name__=='__main__': run()
