from education.core import CarState, step_car

state = CarState(0.0, 0.0, 40.0)
for i in range(5):
    state = step_car(state, throttle=0.7, brake=0.0, dt=0.1)
    print(i, state)
