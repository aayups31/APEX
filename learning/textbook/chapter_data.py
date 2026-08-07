CHAPTERS=[]

CHAPTERS.append({
'title':'1. Build a Simulator Before You Build a Neural Network',
'figure':'01_simulation_loop.png',
'objective':'Understand simulation as repeated state transition, then build and inspect the smallest causal driving world.',
'problem':'''You want a model that can imagine an F1 car several seconds into the future. It is tempting to open PyTorch immediately. That would hide the central question: **what does it mean for the world to move forward by one step?** Before learning anything from data, we need a transparent transition rule whose mistakes we can see.''',
'prediction':'''A car is moving at 20 m/s. During the next 0.2 seconds, its acceleration is 3 m/s². Predict the next velocity and the distance travelled if we use the simplest Euler update. Then decide which quantity should be updated first.''',
'intuition':'''A simulator stores a description of the world, receives an intervention, applies a transition, and returns a new description. In our first world, the state is only velocity and position. The action is a throttle value. The transition is an equation. Repeating the equation produces a rollout.

This hand-written simulator is already a world model in the broad engineering sense: it predicts a future state from a present state and an action. It is not a *learned* world model. That difference matters. A learned model replaces part of the transition rule with parameters estimated from evidence. The interface should remain stable: state in, action in, next state out.

Starting here gives us an oracle for later debugging. If a neural network predicts that stronger braking increases velocity, we can compare it with the toy causal rule and ask whether the data contract, target alignment, or learned relationship is broken.''',
'concepts':[
{'name':'State','meaning':'The minimum information carried from one step to the next.','apex':'Speed, progress, tyre state and other dynamic variables.'},
{'name':'Action','meaning':'A controllable input applied during a transition.','apex':'Throttle, brake, steering and gear choices.'},
{'name':'Transition','meaning':'The rule that maps current state and action to next state.','apex':'Hand-written physics, a GRU, an SSM or an RSSM.'},
{'name':'Rollout','meaning':'Repeatedly applying the transition to create a future trajectory.','apex':'Imagining several seconds of future telemetry.'},
],
'worked':'''Euler integration uses

\[v_{t+1}=v_t+a_t\Delta t\]

and

\[x_{t+1}=x_t+v_t\Delta t.\]

With \(v_t=20\), \(a_t=3\), and \(\Delta t=0.2\):

1. Velocity change: \(3\times0.2=0.6\) m/s.
2. Next velocity: \(20+0.6=20.6\) m/s.
3. Distance using the current velocity: \(20\times0.2=4.0\) m.
4. Next position, if starting at zero: 4.0 m.

A semi-implicit variant updates velocity first and then position, producing \(20.6\times0.2=4.12\) m. Neither is universally “the answer”; the numerical method is an implementation choice whose error shrinks with smaller time steps.''',
'lab':'02_vectorized_kinematics',
'build':'A tiny vectorized integrator that converts an acceleration sequence into velocity and position. You will see that a rollout is just a loop with state carried between iterations.',
'line_notes':[
{'code':'dt = 0.1','meaning':'Define how much simulated time one transition represents.','watch':'Changing dt changes both numerical error and sequence length.'},
{'code':'velocity[i] = velocity[i-1] + acceleration[i-1] * dt','meaning':'Apply one causal state transition.','watch':'The action at step i−1 affects state i, not state i−1.'},
{'code':'position[i] = position[i-1] + velocity[i-1] * dt','meaning':'Integrate velocity into position.','watch':'This implementation uses explicit Euler.'},
],
'code_explanation':'The loop carries the last velocity and position forward. That carried value is the simulator memory.',
'trace':'''Trace one step with `velocity[0]=10`, `acceleration[0]=2`, and `dt=0.1`:

```text
before:  velocity = 10.0 m/s, position = 0.0 m
action:  acceleration = 2.0 m/s²
change:  Δv = 2.0 × 0.1 = 0.2 m/s
after:   velocity = 10.2 m/s
position change = 10.0 × 0.1 = 1.0 m
after:   position = 1.0 m
```

The array is merely a stored history of repeated state updates.''',
'break_it':'Change `dt` from 0.1 to 1.0 without changing the acceleration profile. Compare the trajectory. Then update position with the newly computed velocity and compare again.',
'diagnose':'If the two trajectories disagree, the code is not necessarily broken. The earliest changed contract is the numerical integration scheme and time resolution. Ask whether your result converges as `dt` becomes smaller.',
'repair':'Add a test that simulates constant acceleration for one second at several time steps. Assert that final velocity approaches the analytical value `v0 + a*t`. Document the position integrator you chose.',
'choices':[
{'option':'Explicit Euler','choose':'You need the simplest transparent baseline and small time steps.','avoid':'Long unstable rollouts or stiff dynamics.'},
{'option':'Semi-implicit Euler','choose':'Velocity drives position and you want slightly better stability at similar cost.','avoid':'You need high-order accuracy.'},
{'option':'Runge–Kutta','choose':'The hand-written dynamics are smooth and numerical accuracy matters.','avoid':'The transition is learned from discrete telemetry where solver precision is not the main bottleneck.'},
{'option':'Learned transition','choose':'Important dynamics are unknown but repeated observations are available.','avoid':'You have not defined state, action, timing or evaluation.'},
],
'decision':'For APEX, the toy simulator uses simple integration because its purpose is causal education and synthetic data generation. The learned model then predicts transitions on a fixed telemetry grid. We do not pretend the neural network is a high-fidelity rigid-body solver.',
'apex':'The production engine keeps the same conceptual interface: a history encodes the current world, future controls supply actions, and the model emits future states. The complexity grows, but the causal contract learned here should remain visible.',
'paths':'projects/01_car_integrator/main.py\napex_engine/src/apexsim/data/synthetic.py\napex_engine/src/apexsim/simulation.py',
'research':'Dreamer-style systems are sophisticated because they learn transition dynamics in a latent state, but they still depend on this repeated transition idea. If you cannot explain the toy rollout, an RSSM will only hide confusion behind distributions.',
'questions':['Why is a one-step transition different from a rollout?','What changes when `dt` is halved?','Why should actions at time t usually predict state at time t+1 rather than state at time t?'],
'solutions':['A one-step transition consumes one state/action pair; a rollout feeds predictions back repeatedly, so errors change later inputs.','There are twice as many transitions for the same physical duration, usually reducing integration error but increasing compute and sequence length.','The state at time t was observed before or at the moment the action is applied; using the same-time target can leak the answer or teach no causal delay.'],
'challenge':'Implement both explicit and semi-implicit Euler. Plot their position error against the analytical solution for five time steps. Write an ADR choosing one for the synthetic APEX generator.'
})

CHAPTERS.append({
'title':'2. State, Action, Context and the Markov Question',
'figure':'02_state_action_context.png',
'objective':'Design a causal telemetry schema and discover when the visible state is insufficient for predicting the future.',
'problem':'''Suppose two cars have the same speed and throttle. One is on fresh soft tyres in dry weather; the other is on worn hards in rain. A model that sees only speed and throttle receives identical input for futures that should differ. The failure is not “the neural network needs more layers.” The state description is incomplete.''',
'prediction':'''Classify each variable as state, action, context, target, or identifier: speed, throttle, rain intensity, driver number, tyre age, next speed, track name, brake. Explain any variable whose category could change depending on the system boundary.''',
'intuition':'''State is the information the transition needs to carry. Action is the intervention being chosen. Context changes the transition but is not controlled by the agent inside the model. Identifiers describe an entity or grouping and should not automatically become numeric features.

The Markov property says the next state is conditionally independent of the distant past once the present state and action are known. Real telemetry is rarely perfectly Markov. Tyre temperature, fuel mass, setup, and previous cornering load may be hidden. A recurrent model compensates by compressing history into memory. But recurrence is not permission to ignore schema design: hidden memory cannot recover information that was never observed.

A practical state contract should be sufficient, measurable, stable across data sources, and safe to use at inference time. A variable known only after the race cannot be an input to an online simulator.''',
'concepts':[
{'name':'Markov state','meaning':'A state that contains enough information to predict the next transition when combined with the action.','apex':'The ideal telemetry state; approximated using features plus history.'},
{'name':'Context','meaning':'An external condition that modifies dynamics.','apex':'Rain, track geometry, session phase and compound.'},
{'name':'Identifier','meaning':'A label used for grouping or lookup, not automatically a causal feature.','apex':'Session ID, driver code and event ID.'},
{'name':'Partial observability','meaning':'Important state exists but is not directly measured.','apex':'Tyre temperature or setup may need history, proxies or latent state.'},
],
'worked':'''Consider the transition

\[v_{t+1}=v_t + (4a_t-7b_t-0.02v_t-3r_t)\Delta t\]

where `a` is throttle, `b` is brake, and `r` is rain intensity. At `v=50 m/s`, throttle `0.8`, brake `0`, rain `0.5`, and `dt=0.2`:

1. Engine contribution: `4 × 0.8 = 3.2 m/s²`.
2. Drag contribution: `0.02 × 50 = 1.0 m/s²`.
3. Rain/grip penalty: `3 × 0.5 = 1.5 m/s²`.
4. Net acceleration: `3.2 − 1.0 − 1.5 = 0.7 m/s²`.
5. Speed change: `0.7 × 0.2 = 0.14 m/s`.
6. Next speed: `50.14 m/s`.

If rain were omitted, the same visible state/action would predict `50.44 m/s`. That 0.30 m/s discrepancy is a schema problem before it is a modelling problem.''',
'lab':'01_units_and_shapes',
'build':'A two-feature telemetry tensor with explicit time and feature axes. The point is not the arithmetic; it is learning to make shape and semantics part of the data contract.',
'line_notes':[
{'code':'speed_mps = speed_kmh / 3.6','meaning':'Convert a display unit into the canonical physical unit.','watch':'The numerical values change while the physical quantity does not.'},
{'code':'np.stack([...], axis=1)','meaning':'Create one row per time step and one column per feature.','watch':'`axis=1` establishes `[time, features]`.'},
{'code':'assert telemetry.shape == (3, 2)','meaning':'Turn the axis contract into an executable check.','watch':'A shape check cannot verify feature order or units by itself.'},
],
'code_explanation':'Each column needs a name and unit. A bare `(3,2)` array is not yet a trustworthy contract.',
'trace':'''```text
row 0 = [0.0 m/s, 0.0 throttle]
row 1 = [20.0 m/s, 0.5 throttle]
row 2 = [40.0 m/s, 1.0 throttle]
shape = [3 time steps, 2 features]
```

If you transpose it, the shape becomes `[2 features, 3 time steps]`; the numbers still exist, but every downstream interpretation changes.''',
'break_it':'Transpose the array and remove the shape assertion. Write a function that assumes rows are time. Observe that it can compute plausible but meaningless statistics.',
'diagnose':'The earliest failed contract is axis semantics, not the model. Print shape, feature names, units, and one known row before debugging anything downstream.',
'repair':'Create a dataclass or Pydantic model that stores `feature_names`, `units`, `sample_hz`, and the array. Add tests for feature order, legal ranges, and axis length.',
'choices':[
{'option':'Flat numeric vector','choose':'The state is small, fixed and well documented.','avoid':'Variables have complex structure or missingness semantics.'},
{'option':'Typed record / dataframe','choose':'You are ingesting and validating human-readable telemetry.','avoid':'You need high-throughput batched neural computation.'},
{'option':'History encoder','choose':'The observed frame is partially Markov and recent history contains useful proxies.','avoid':'Missing variables are unrelated to anything observed.'},
{'option':'Latent state model','choose':'Hidden dynamics and uncertainty must be inferred.','avoid':'A transparent state vector already predicts well enough.'},
],
'decision':'APEX uses named tabular records at ingestion, then ordered tensors for learning. Conversion happens at an explicit boundary so readability and computational efficiency are both preserved.',
'apex':'The canonical contract distinguishes state features, control features, context features and identifiers. The window builder constructs history and future-control tensors without exposing future target state.',
'paths':'apex_engine/src/apexsim/contracts.py\napex_engine/src/apexsim/data/features.py\napex_engine/src/apexsim/data/windows.py',
'research':'RSSMs exist partly because observations are incomplete. Their deterministic hidden state and stochastic latent state summarize what the agent believes about the world. That belief is only as good as the evidence and intervention contract supplied to it.',
'questions':['Can tyre age be state and context at the same time?','Why is driver ID dangerous as a direct numeric feature?','What evidence would show that a single telemetry frame is not Markov enough?'],
'solutions':['The label depends on the chosen boundary. If tyre age evolves inside the simulator, it is state; if supplied as a fixed scenario condition, it behaves like context.','Numeric encoding invents an ordering and can let the model memorize identities instead of dynamics. Use a justified embedding or group-specific analysis.','A history-aware model consistently outperforming an equal-capacity frame model, especially after controlling leakage, suggests the past carries missing state information.'],
'challenge':'Write the complete APEX V1 schema on paper. For every field, state its category, unit, legal range, availability at inference, and expected causal relationship.'
})

CHAPTERS.append({
'title':'3. Units, Forces and Numerical Integration',
'figure':'03_physics_integrator.png',
'objective':'Build a physically interpretable transition, use dimensional analysis to catch errors, and understand the limits of toy physics.',
'problem':'''Telemetry sources use kilometres per hour, metres per second, percentages, normalized controls, degrees, radians and timestamps in different formats. A model can fit unit mistakes without raising an exception. The result may look statistically smooth while violating the world.''',
'prediction':'''A formula subtracts `0.02 * speed²` from acceleration, but speed is supplied in km/h although the coefficient was fitted in m/s. Predict whether the drag is too large or too small and by what factor.''',
'intuition':'''Dimensional analysis asks whether the units on both sides of an equation agree. It is one of the cheapest and strongest debugging tools in simulation engineering. If force is in newtons and mass is in kilograms, acceleration is metres per second squared. If speed enters a squared term, a unit conversion error is squared too.

A toy longitudinal model combines engine force, braking force and drag. It will not reproduce downforce, tyre load sensitivity, energy recovery, differential behaviour or setup effects. That is fine when the model's purpose is to generate causal examples and test software contracts. It is dangerous if the UI presents the result as lap-time truth.

The hand-written model also teaches residual learning: instead of asking a neural network to rediscover every obvious relationship, we can predict the correction to a known physics approximation. Whether that helps is an empirical decision.''',
'concepts':[
{'name':'Dimensional analysis','meaning':'Check that quantities combined by an equation have compatible units.','apex':'Catches km/h–m/s and timestamp errors before training.'},
{'name':'Force balance','meaning':'Net force is the sum of propulsive and resisting forces.','apex':'Provides an interpretable synthetic transition.'},
{'name':'Residual model','meaning':'A learned correction added to a known baseline model.','apex':'Possible hybrid physics/ML architecture.'},
{'name':'Numerical stability','meaning':'Whether repeated computation remains bounded and sensible.','apex':'Critical for long autoregressive rollouts and SSM state.'},
],
'worked':'''Suppose the drag acceleration term is \(c v^2\). Converting from m/s to km/h multiplies speed by 3.6. Squaring multiplies the drag term by \(3.6^2=12.96\). The model therefore applies nearly thirteen times too much drag.

For a 50 m/s car with mass 800 kg:

- Engine force: 8,000 N
- Brake force: 0 N
- Drag: 2,500 N
- Net force: 5,500 N
- Acceleration: `5500 / 800 = 6.875 m/s²`
- At `dt=0.1`, velocity increases by `0.6875 m/s`

If speed were incorrectly treated as 180 in a coefficient calibrated for 50, the quadratic term would dominate and could create impossible negative velocity.''',
'lab':'03_force_model',
'build':'A longitudinal force model with engine, brake and aerodynamic drag contributions. You will inspect every term separately before summing them.',
'line_notes':[
{'code':'engine = max_engine_force * throttle','meaning':'Scale available forward force by a normalized control.','watch':'Throttle range must be validated as 0–1.'},
{'code':'drag = drag_coefficient * speed**2','meaning':'Apply a quadratic resistance that grows rapidly with speed.','watch':'The coefficient depends on the speed unit.'},
{'code':'acceleration = net_force / mass','meaning':'Use Newton’s second law to convert force into acceleration.','watch':'Mass must be positive and use kilograms.'},
],
'code_explanation':'Print engine, brake and drag separately. A total can look reasonable even when two wrong terms cancel.',
'trace':'''```text
throttle ──► engine force ─┐
brake ─────► brake force ──┼─► net force ─► divide by mass ─► acceleration
speed ─────► drag force ───┘
```

At every arrow, annotate the unit. That annotation is an executable design review even before a test exists.''',
'break_it':'Feed speed in km/h without conversion. Then set mass to zero or throttle above one. Observe which failures become exceptions and which silently produce nonsense.',
'diagnose':'Start with invariants: mass > 0, 0 ≤ controls ≤ 1, speed unit known, drag ≥ 0, and braking should not increase velocity. Then inspect individual force terms.',
'repair':'Introduce typed conversion functions, range validation, and property tests: increasing brake at fixed state must not increase next speed; increasing throttle must not decrease it in a regime without traction limits.',
'choices':[
{'option':'Pure hand-written physics','choose':'You need interpretability, counterfactual control and known equations.','avoid':'Unknown tyre/track interactions dominate error.'},
{'option':'Pure learned dynamics','choose':'You have broad representative data and care about predictive fit.','avoid':'Safety or extrapolation requires hard physical guarantees.'},
{'option':'Residual learning','choose':'A baseline captures broad physics and data can learn systematic corrections.','avoid':'The baseline is badly misspecified and constrains learning in the wrong direction.'},
{'option':'Physics-informed loss','choose':'Violations can be expressed as differentiable penalties.','avoid':'The penalty is only a weak proxy and overwhelms observed evidence.'},
],
'decision':'APEX V1 uses the toy force model to create controllable offline data, while the predictive models learn directly from canonical telemetry. Physical validity checks remain part of evaluation rather than being assumed from the architecture.',
'apex':'Inspect how the synthetic generator computes curvature demand, grip, drag, controls and state updates. Then compare those equations with the features available to the learned models.',
'paths':'projects/03_lap_physics/main.py\napex_engine/src/apexsim/data/synthetic.py\napex_engine/src/apexsim/evaluation.py',
'research':'World models often optimize data likelihood or prediction error, not the laws of mechanics. Adding inductive bias can improve sample efficiency, but every constraint is a claim that must be tested under the target domain.',
'questions':['Why can two unit errors cancel during training but still fail in deployment?','What is the advantage of predicting a residual?','Name one invariant that should hold for all APEX rollouts.'],
'solutions':['A model can learn coefficients adapted to the mistaken training scale; a different source or UI conversion changes the scale and exposes the mismatch.','The baseline supplies known structure, so the learner spends capacity on unmodelled effects and can be easier to interpret.','Examples include finite values, nonnegative speed, track progress wrapped into its legal interval, and controls within their defined range.'],
'challenge':'Add a tyre-grip limit to the force model. Show a case where more throttle no longer produces more acceleration, and explain why a monotonicity test must be conditional rather than universal.'
})

CHAPTERS.append({
'title':'4. Sampling, Aliasing and Time Alignment',
'figure':'04_sampling.png',
'objective':'Turn asynchronous telemetry into a defensible time grid without creating fake evidence or future leakage.',
'problem':'''Speed may arrive at one frequency, weather at another, and event data only when something changes. A neural network expects aligned rows. Joining by nearest timestamp can quietly attach a future weather measurement to an earlier car frame. Interpolation can make missing data look observed.''',
'prediction':'''An 8 Hz oscillation is sampled at 5 Hz. Sketch the samples. Will the observed sequence reveal an 8 Hz signal, a slower false signal, or no signal? Then decide what a model might learn from it.''',
'intuition':'''Sampling converts a continuous process into discrete observations. If the sample rate is too low for the dynamics, high-frequency behaviour aliases into a different pattern. No architecture can reconstruct information that the sensor never captured without additional assumptions.

Alignment chooses which measurements describe the same model time. A backward as-of join says: at each car timestamp, use the latest context that was already available. A nearest join may use the future. A tolerance limits how stale a matched measurement may be. These are causal policies, not dataframe trivia.

Resampling onto a uniform grid simplifies windows and batch training, but interpolation must respect feature type. Continuous speed may be linearly interpolated across short gaps. Gear and flags are categorical and generally require forward fill or explicit unknown values. Long gaps should be marked invalid, not painted over.''',
'concepts':[
{'name':'Sampling rate','meaning':'How many observations are recorded per second.','apex':'Defines temporal resolution and sequence length.'},
{'name':'Aliasing','meaning':'A high-frequency process appears as a different lower-frequency pattern.','apex':'Can hide braking spikes or steering oscillations.'},
{'name':'As-of join','meaning':'Match each timestamp with a nearby record under a direction and tolerance policy.','apex':'Aligns weather, position and telemetry streams.'},
{'name':'Staleness','meaning':'How old a context value is when reused.','apex':'A monitoring feature and validation rule.'},
],
'worked':'''The Nyquist guideline says a sinusoid of frequency \(f\) requires sampling above \(2f\) to avoid ambiguity. An 8 Hz oscillation needs more than 16 Hz. At 5 Hz, sample times are 0, 0.2, 0.4… seconds. The phase advances `8 × 0.2 = 1.6` cycles per sample, equivalent to an apparent 0.6-cycle advance after wrapping. The observed pattern therefore resembles a 3 Hz oscillation (`0.6 × 5`).

For alignment, suppose car timestamps are 0.0, 0.2, 0.4, 0.6 and rain observations are 0.05 and 0.55. A backward join at 0.4 uses rain from 0.05; a nearest join uses 0.55, leaking a future value by 0.15 seconds.''',
'lab':'19_time_alignment',
'build':'A backward `merge_asof` with an explicit tolerance. You will inspect which rain observation is attached to each car frame and identify unmatched stale rows.',
'line_notes':[
{'code':"sort_values('t')",'meaning':'Satisfy the ordered-time precondition of an as-of join.','watch':'Unsorted data can fail or produce invalid matches.'},
{'code':"direction='backward'",'meaning':'Use only context observations at or before the car timestamp.','watch':'This encodes online availability and blocks future leakage.'},
{'code':'tolerance=0.3','meaning':'Reject a match older than the allowed staleness.','watch':'Choose tolerance from domain timing, not convenience.'},
],
'code_explanation':'The resulting NaN is information: no acceptable context was available. Decide whether to mask, impute or drop it explicitly.',
'trace':'''```text
car t=0.00 ─► no earlier rain measurement ─► missing
car t=0.20 ─► rain at 0.05 (age 0.15 s) ─► valid
car t=0.40 ─► rain at 0.05 (age 0.35 s) ─► rejected by 0.30 s tolerance
car t=0.60 ─► rain at 0.55 (age 0.05 s) ─► valid
```

A table row should carry not only the matched value but ideally the age of that value.''',
'break_it':'Change `direction` to `nearest` and remove the tolerance. Add a future rain spike at 0.41. Observe how an earlier car frame receives information from the future.',
'diagnose':'Compare source timestamp, target timestamp and signed age. The earliest failed contract is availability time, not model performance.',
'repair':'Persist measurement timestamps and create a test asserting `context_time <= frame_time` for online features. Add a maximum staleness threshold and an explicit missingness mask.',
'choices':[
{'option':'Backward as-of','choose':'Features must reflect information available online.','avoid':'The quantity is defined as a symmetric offline estimate.'},
{'option':'Nearest join','choose':'Both streams are synchronized measurements and future use is scientifically acceptable.','avoid':'Forecasting, control or causal analysis.'},
{'option':'Linear interpolation','choose':'A continuous signal has short, well-sampled gaps.','avoid':'Categorical states, discontinuities or long outages.'},
{'option':'Forward fill','choose':'A discrete state remains active until changed.','avoid':'A rapidly varying continuous sensor.'},
],
'decision':'APEX chooses a canonical frequency, aligns source streams under causal policies, records staleness, and rejects gaps that exceed configured limits. The policy is part of the dataset version.',
'apex':'The FastF1 and OpenF1 adapters normalize timestamps and stream-specific fields before producing the canonical frame. Window construction assumes the alignment contract is already satisfied.',
'paths':'labs/04_sampling_aliasing/solution.py\nlabs/19_time_alignment/solution.py\napex_engine/src/apexsim/data/fastf1_adapter.py\napex_engine/src/apexsim/data/openf1_adapter.py',
'research':'Sequence models are often blamed for missing rapid dynamics that were already destroyed by low-rate or misaligned observations. Data acquisition defines the ceiling of learnable temporal behaviour.',
'questions':['Why does increasing model capacity not solve aliasing?','What does a join tolerance represent physically?','When can interpolation create false certainty?'],
'solutions':['The distinct high-frequency processes map to identical samples, so the information is absent from the data.','The maximum age or temporal mismatch at which a context measurement is still considered representative.','When it fills a long or discontinuous gap with smooth values and the training pipeline treats those values as directly observed.'],
'challenge':'Create two asynchronous synthetic streams with a known causal delay. Compare nearest, backward and interpolated alignment by measuring how well each preserves the known delay.'
})

CHAPTERS.append({
'title':'5. Canonical Contracts and Quality Gates',
'figure':'05_contract.png',
'objective':'Build one source-independent telemetry contract and make invalid evidence fail before it reaches a model.',
'problem':'''FastF1, OpenF1, synthetic data and future F1 25 UDP packets do not share identical names, units, timing or missingness. If every model contains source-specific branches, the system becomes impossible to test. We need a narrow boundary that all sources must cross.''',
'prediction':'''Imagine FastF1 supplies speed in km/h and a future UDP adapter supplies m/s. Both columns are called `speed`. Where should conversion happen: inside each model, inside the dataset, or inside the source adapter? Explain the consequences of each choice.''',
'intuition':'''A canonical contract is not merely a dataframe schema. It specifies names, types, units, legal ranges, timing semantics, missingness, identifiers and invariants. Source adapters are translators: they may parse and convert, but they should not secretly perform model-specific feature engineering.

A quality gate separates admissible evidence from rejected or quarantined evidence. Some checks are hard errors—missing timestamp, impossible unit, duplicate key. Others are warnings—unusual prevalence or a short gap. The distinction should reflect whether downstream interpretation remains valid.

Contracts also enable replaceability. You can test the entire pipeline with synthetic data, then swap to FastF1 without changing the window builder or model. This is the central architectural move that lets APEX start before F1 25 is available.''',
'concepts':[
{'name':'Canonical contract','meaning':'One stable internal representation accepted by all downstream components.','apex':'The source-independent telemetry frame.'},
{'name':'Adapter','meaning':'A boundary component translating one external source into the canonical representation.','apex':'FastF1, OpenF1 and future UDP adapters.'},
{'name':'Quality gate','meaning':'Executable rules deciding whether evidence may proceed.','apex':'Range, timing, duplicate, finite-value and schema checks.'},
{'name':'Quarantine','meaning':'Preserve questionable data separately instead of silently dropping or using it.','apex':'Allows investigation and reprocessing after a fix.'},
],
'worked':'''Suppose the canonical speed unit is m/s and the legal range is 0–105 m/s. A source row says 320 km/h.

1. Adapter recognizes source unit km/h.
2. Convert: `320 / 3.6 = 88.89 m/s`.
3. Validate finite: yes.
4. Validate range: yes.
5. Store canonical value with source provenance.

If conversion were delayed until model code, validation would see 320 and reject a valid record—or the range would be widened and allow truly impossible m/s values. Therefore conversion belongs at the adapter boundary.''',
'lab':'20_pipeline_contract',
'build':'A miniature pipeline that writes one immutable artifact per stage. Although small, it teaches the idea that every stage has named input/output and observable status.',
'line_notes':[
{'code':"stages=['ingest','validate','window','train','evaluate','publish']",'meaning':'Declare the lifecycle as distinct responsibilities.','watch':'A stage name should correspond to one recoverable contract.'},
{'code':"run/f'{i:02d}_{name}.json'",'meaning':'Give each output a deterministic path within a run.','watch':'Production artifacts also need version and content metadata.'},
{'code':"{'stage':name,'status':'succeeded'}",'meaning':'Persist machine-readable state instead of relying on console text.','watch':'Real status should be written atomically after success.'},
],
'code_explanation':'The file contents are trivial; the important idea is that progress becomes inspectable and rerunnable.',
'trace':'''```text
external row
   ↓ adapter parses names and units
canonical row
   ↓ validator checks invariants
admitted row + quality report
   ↓ window builder
model-ready example
```

Each arrow is a contract boundary with tests. A failure should name the earliest boundary it violates.''',
'break_it':'Rename one source column, duplicate a timestamp, insert infinite speed, and swap throttle/brake. Notice that only some defects are detectable from shape and range.',
'diagnose':'Validate in layers: schema → types → units → temporal keys → ranges → cross-field relationships → distribution warnings. A semantic swap may require known examples or correlation checks.',
'repair':'Create fixtures for one valid row and one row for every failure class. Make adapters produce the same canonical column order and metadata. Record source, adapter version and conversion policy.',
'choices':[
{'option':'Loose dataframe convention','choose':'Exploratory one-off analysis.','avoid':'Multiple sources, teams or production reuse.'},
{'option':'Pydantic/dataclass contract','choose':'You need typed configuration and row/batch metadata validation.','avoid':'Per-element validation becomes a throughput bottleneck; validate batches at boundaries.'},
{'option':'Schema registry','choose':'Many producers and consumers evolve independently.','avoid':'A small local project where the operational overhead exceeds value.'},
{'option':'Silent coercion','choose':'Almost never; only for explicitly documented benign parsing.','avoid':'Any conversion that can change scientific meaning.'},
],
'decision':'APEX adapters own source parsing and canonical conversion. Core training code imports only the canonical contract. Validation produces a report and blocks hard failures before sequence construction.',
'apex':'Read the contract and both adapters side by side. Confirm that training, evaluation and UI modules never call FastF1 or OpenF1 directly.',
'paths':'apex_engine/src/apexsim/contracts.py\napex_engine/src/apexsim/data/validate.py\napex_engine/src/apexsim/data/fastf1_adapter.py\napex_engine/src/apexsim/data/openf1_adapter.py',
'research':'Research code often assumes a fixed benchmark tensor. Production world models need a stronger boundary because source evolution can alter semantics without changing array shape.',
'questions':['Why should source adapters avoid model-specific feature engineering?','Give an example of a warning rather than a hard error.','What metadata is needed to reproduce a canonical dataset?'],
'solutions':['It couples data acquisition to one model and creates inconsistent versions across experiments; stable raw canonical features should precede reproducible transforms.','A session with unusually high rain or a slightly lower sample rate may be valid but deserves attention.','Source identifiers, retrieval time, adapter version, units, alignment policy, validation configuration, feature code version and dataset hash.'],
'challenge':'Define a canonical telemetry schema in JSON Schema or Pydantic. Implement two toy adapters with different names and units, and prove with tests that they produce identical canonical rows.'
})

CHAPTERS.append({
'title':'6. FastF1 and OpenF1: Ingest Real Evidence Without Polluting the Core',
'figure':'05_contract.png',
'objective':'Understand the complete data path from a public F1 source to canonical telemetry and learn to keep network concerns outside model code.',
'problem':'''APEX begins before you own F1 25, so historical evidence must come from public tooling. FastF1 is a Python library organized around events and sessions; OpenF1 exposes HTTP endpoints for telemetry, timing, position, weather and related records. Their access patterns differ. The engineering challenge is not “download a CSV”; it is to translate each source into evidence with the same meaning.''',
'prediction':'''A FastF1 session and an OpenF1 endpoint both provide speed, throttle and timestamps, but one uses relative session time and the other UTC timestamps. What information must an adapter preserve so the two sources can later be compared or combined?''',
'intuition':'''Network retrieval, caching, parsing, source-specific naming and canonical conversion are separate steps. Keeping them separate lets you replay raw responses when an adapter changes, test conversion without the network, and avoid rate-limit failures inside training.

The safest ingestion process lands raw evidence first. A second deterministic step creates canonical data. This gives you two forensic layers: “what did the source return?” and “how did our code interpret it?” A model run should point to both.

FastF1 and OpenF1 can overlap without being interchangeable. Differences in sampling, provenance and field definitions should be measured rather than assumed away. APEX treats each adapter as an independently tested producer of the canonical contract.''',
'concepts':[
{'name':'Landing zone','meaning':'Immutable storage of source-native responses before interpretation.','apex':'Cached session/API data used for reproducible adapter tests.'},
{'name':'Provenance','meaning':'Information describing where, when and how a record was obtained.','apex':'Source, event/session identifiers, driver, retrieval time and adapter version.'},
{'name':'Idempotent ingestion','meaning':'Repeating the same request does not create conflicting outputs.','apex':'Deterministic paths and hashes for source snapshots.'},
{'name':'Rate limit / cache','meaning':'External service constraints and local reuse strategy.','apex':'Prevents training from repeatedly hitting public services.'},
],
'worked':'''Suppose OpenF1 returns UTC timestamps `12:00:00.100`, `12:00:00.300`, and FastF1 returns session-relative seconds `5.2`, `5.4`. To combine them, you need a session start reference or a shared event clock. If session start is `11:59:54.900`, the UTC records map to `5.2` and `5.4` seconds.

The adapter should preserve:

1. Source timestamp exactly as received.
2. Parsed canonical timestamp.
3. Session and driver identifiers.
4. Source field names/units or adapter version.
5. Missingness and interpolation flags.

Without those fields, an apparent 0.2-second alignment error cannot be traced.''',
'lab':'19_time_alignment',
'build':'Use the alignment lab as an offline stand-in for real streams, then inspect the production FastF1 and OpenF1 adapters. The important skill is tracing a field from raw response to canonical column.',
'line_notes':[
{'code':'pd.merge_asof(...)','meaning':'Join asynchronous records after each source has been parsed into a common time representation.','watch':'Alignment belongs after timestamp normalization.'},
{'code':'direction="backward"','meaning':'Preserve online causal availability.','watch':'Offline retrospective analysis may choose another policy, but must label it.'},
{'code':'tolerance=...','meaning':'Prevent arbitrarily stale context from being treated as current.','watch':'Record unmatched rows rather than silently filling all gaps.'},
],
'code_explanation':'In the real adapters, follow one column from the source response through unit conversion, rename, type cast and validation.',
'trace':'''```text
network request
   ↓ raw JSON / library objects (cache this)
source parser
   ↓ typed source table
unit and timestamp conversion
   ↓ canonical columns
quality gate
   ↓ admitted canonical session + report
```

Training begins only after the last step. It should be possible to run everything after ingestion with no network.''',
'break_it':'Mock a source response where one field changes name, one timestamp is timezone-naive, and one speed column changes unit. Run the adapter tests and identify which change is detected.',
'diagnose':'Compare the raw snapshot with the canonical output. If the raw source is correct but canonical data is wrong, the adapter is the earliest failed boundary. If the raw response itself changed, update the source fixture and conversion policy deliberately.',
'repair':'Store representative source fixtures in tests. Assert exact canonical names, units, timestamp monotonicity and a few known values. Version adapter outputs whenever semantics change.',
'choices':[
{'option':'FastF1','choose':'Python-centric historical session analysis with convenient session abstractions and cached telemetry.','avoid':'You require an HTTP-only integration or fields outside its supported representation.'},
{'option':'OpenF1','choose':'Service-style access to historical/live endpoint data and independent stream retrieval.','avoid':'You assume every endpoint is synchronized or identical to FastF1.'},
{'option':'Both as separate datasets','choose':'You want cross-source validation or broader coverage.','avoid':'You have not measured semantic and temporal differences.'},
{'option':'Merge sources into one row','choose':'There is a justified key, timing policy and conflict-resolution rule.','avoid':'Matching is based only on similar column names.'},
],
'decision':'APEX V1 supports both adapters but does not require both for one run. Each produces the canonical contract; downstream code stays source-agnostic. Synthetic data remains the offline integration-test source.',
'apex':'Run an adapter command when network access is available, save canonical output, validate it, then call the same `run-canonical` pipeline used for any source.',
'paths':'apex_engine/src/apexsim/data/fastf1_adapter.py\napex_engine/src/apexsim/data/openf1_adapter.py\napex_engine/src/apexsim/cli.py\napex_engine/README.md',
'research':'Public datasets are observations, not the world itself. A world model trained on one source can inherit its sampling, filtering and missingness as if those were physical laws. Cross-source tests reveal some of these artifacts.',
'questions':['Why should raw source snapshots be immutable?','What should happen when an external field disappears?','Why is network retrieval inside a PyTorch Dataset a bad default?'],
'solutions':['They allow exact replay, adapter debugging and proof of what the source returned at run time.','The adapter should fail clearly or mark the field unavailable according to a versioned policy; silently substituting another field can change meaning.','It makes samples nondeterministic, slow, rate-limit dependent and difficult to retry or reproduce.'],
'challenge':'Create a recorded fixture for one mocked FastF1-like table and one OpenF1-like JSON response. Write adapters that produce byte-for-byte identical canonical CSV rows.'
})

CHAPTERS.append({
'title':'7. Windows, Session Splits and Normalization Without Leakage',
'figure':'06_windows.png',
'objective':'Turn canonical sessions into causal training examples while keeping validation and test evidence genuinely independent.',
'problem':'''A telemetry session yields thousands of overlapping windows. If you randomly split those windows, nearly identical frames from the same lap appear in both training and test. The test score becomes a measure of memorization under overlap, not generalization to a new session.''',
'prediction':'''A 100-frame session uses 20 history frames and 5 future frames with stride 1. How many windows can be created? If windows 1 and 2 are put in different splits, how many frames do they share?''',
'intuition':'''A sequence example has three distinct pieces: history observations, future interventions/context, and future target state. The model must not receive the future target inside its inputs. This sounds obvious, but dataframe slicing and feature lists can quietly duplicate it.

Split units should match the deployment claim. If the engine will simulate a new race session, split by session or event before making windows. A time-based holdout within one session answers a narrower question. Random windows almost always overstate performance when overlap is high.

Normalization must be fitted only on training data. Validation and test are transformed using stored training statistics. Otherwise the mean and variance leak information about future or held-out distributions, and deployment cannot reproduce the transform.''',
'concepts':[
{'name':'History length','meaning':'How many past frames are visible before a forecast begins.','apex':'Controls memory evidence and input cost.'},
{'name':'Forecast horizon','meaning':'How many future transitions are predicted.','apex':'Defines simulation duration and error accumulation.'},
{'name':'Split unit','meaning':'The independent entity assigned wholly to train, validation or test.','apex':'Usually session/event, not overlapping windows.'},
{'name':'Train-only normalizer','meaning':'Scaling statistics fitted exclusively on training observations.','apex':'Persisted with the model artifact.'},
],
'worked':'''For length `N=100`, history `H=20`, future `F=5`, stride 1, the first window consumes frames 0–24 and the last begins at 75, so the count is

\[N-H-F+1=100-20-5+1=76.\]

Window 1 uses frames 0–24; window 2 uses 1–25. They share 24 of 25 frames. Assigning them to different splits creates almost complete leakage.

For normalization, training speeds `[40, 50, 60]` have mean 50 and standard deviation about 8.165. A test speed 70 becomes `(70−50)/8.165 ≈ 2.45`. Recomputing the mean with test data would shrink that value and leak the test distribution.''',
'lab':'08_dataset_windows',
'build':'Create history/target windows and inspect shapes and boundaries. Then map the same logic to the production window builder, which also carries future controls and session identifiers.',
'line_notes':[
{'code':'for start in range(...)','meaning':'Enumerate valid causal cut points.','watch':'The upper bound must leave enough future target frames.'},
{'code':'history = data[start:start+H]','meaning':'Select only evidence available before forecast time.','watch':'Verify the last history timestamp precedes the first target timestamp.'},
{'code':'target = data[start+H:start+H+F]','meaning':'Select the future trajectory to learn.','watch':'Do not accidentally include target state in future inputs.'},
],
'code_explanation':'Print the exact source indices for the first and last window. Shape alone cannot prove causal slicing.',
'trace':'''```text
session frames:  0 1 2 3 4 5 6 7 8 9
history H=4:     [0 1 2 3]
future controls:         [4 5 6]
future targets:          [4 5 6]
next window:       [1 2 3 4] → [5 6 7]
```

Controls and target states share timestamps but not semantics. Future throttle may be supplied; future speed is what must be predicted.''',
'break_it':'Create all windows first and randomly split them. Train a nearest-neighbour or linear baseline. Compare its test score with a session-level split.',
'diagnose':'Inspect source session IDs and frame-index overlap across splits. If any raw session contributes to multiple splits, your claimed generalization unit is false.',
'repair':'Assign sessions/events deterministically to splits before windowing. Fit normalization on training windows only. Add tests for disjoint identifiers and for target columns absent from model inputs.',
'choices':[
{'option':'Random window split','choose':'Only for debugging shape/training code, never for a generalization claim with overlap.','avoid':'Any realistic telemetry evaluation.'},
{'option':'Session split','choose':'Deployment targets unseen sessions under similar tracks/drivers.','avoid':'You specifically study later portions of the same session.'},
{'option':'Event/track split','choose':'You need evidence of transfer to new circuits or events.','avoid':'The dataset is too small to support that claim.'},
{'option':'Rolling temporal split','choose':'Production learns from past sessions and forecasts future dates.','avoid':'Timestamp order does not correspond to deployment.'},
],
'decision':'APEX V1 splits by session before creating windows and stores the split assignment. Normalization statistics are versioned artifacts loaded by training, evaluation, simulation and UI.',
'apex':'Trace one `WindowDataset` sample. Print history, future inputs, targets, session ID, start timestamp and feature names. Then inspect the split tests.',
'paths':'apex_engine/src/apexsim/data/windows.py\napex_engine/src/apexsim/pipeline/stages.py\napex_engine/tests/test_windows.py\ndebugging_cases/04_random_window_split\ndebugging_cases/06_normalizer_leak',
'research':'World-model papers often report benchmark splits that already define episodes. In custom telemetry projects, defining the episode and independence unit is part of the research contribution, not preprocessing trivia.',
'questions':['Why can overlapping windows inflate scores even without exact duplicate rows?','Should validation statistics be used to choose normalization?','What deployment claim does a track holdout support?'],
'solutions':['They share most temporal context and local dynamics, so the model sees nearly the same trajectory during training.','No. Normalization is learned from training only; validation is used for model and hyperparameter selection under that fixed transform.','Evidence that the learned dynamics and representation transfer to an unseen circuit distribution, subject to the held-out tracks tested.'],
'challenge':'Implement a split audit that reports shared session IDs, shared raw frame identifiers, time overlap and distribution differences for every pair of splits.'
})

CHAPTERS.append({
'title':'8. Statistics, Baselines and Uncertainty as Engineering Controls',
'figure':'07_baseline.png',
'objective':'Use simple models and residual analysis to determine what the data contains before escalating to deep sequence architectures.',
'problem':'''A GRU can produce a low loss for the wrong reason: leaked targets, easy persistence, narrow test conditions or an imbalanced metric. A baseline is the control group that tells you whether complexity has earned its place.''',
'prediction':'''At 5 Hz, speed changes slowly between adjacent frames. Which will be harder to beat for one-step speed prediction: a constant mean, persistence (`next speed = current speed`), or a linear action-conditioned model? Explain how the answer may change at a longer horizon.''',
'intuition':'''Start with the distribution: means, spreads, missingness, correlations and conditional relationships. Then create baselines that correspond to real hypotheses. Persistence says the world changes slowly. Linear regression says the change is approximately additive in observed features. A physics baseline says known equations explain most of the transition.

Residuals—target minus prediction—show what the baseline failed to explain. Plot residuals against speed, curvature, rain, tyre age and horizon. Structured residuals are a blueprint for the next model. Random-looking residuals near measurement noise may mean a larger model has little room to help.

Uncertainty has several meanings. Aleatoric uncertainty reflects inherently variable outcomes or noisy measurements. Epistemic uncertainty reflects lack of knowledge, often rising outside the training distribution. A point predictor does not automatically communicate either.''',
'concepts':[
{'name':'Persistence baseline','meaning':'Predict that the next state equals the current state.','apex':'Strong short-horizon speed control.'},
{'name':'Residual','meaning':'Observed target minus model prediction.','apex':'Reveals missing nonlinearities, context or delay.'},
{'name':'Calibration','meaning':'Predicted uncertainty/probability matches empirical frequency or error.','apex':'Needed before presenting confidence in imagined futures.'},
{'name':'Distribution shift','meaning':'Deployment evidence differs from training evidence.','apex':'New tracks, weather, drivers or game telemetry.'},
],
'worked':'''Suppose true next speeds are `[50.2, 60.1, 69.7]` and persistence predicts `[50.0, 60.0, 70.0]`.

Absolute errors are `[0.2, 0.1, 0.3]`; MAE is `(0.2+0.1+0.3)/3 = 0.2 m/s`.

A neural model with MAE 0.18 improves by 0.02 m/s, or 10% relative. That gain might matter—or it might vanish on a new session, cost far more compute, and introduce physical violations. Compare by horizon, subgroup, latency and stability before declaring victory.

If residuals under braking average +0.8 m/s (targets are higher than predictions), the baseline is overestimating deceleration. That points to brake scaling, delay or grip context.''',
'lab':'05_regression_baseline',
'build':'Fit a Ridge transition model to synthetic speed, throttle and brake data, inspect coefficients and calculate test MAE.',
'line_notes':[
{'code':'X=np.column_stack([speed,throttle,brake])','meaning':'Construct one row per transition with named causal inputs.','watch':'Column order must match stored feature metadata.'},
{'code':'Ridge(alpha=1.0).fit(X[:800],y[:800])','meaning':'Estimate a regularized linear transition using training rows.','watch':'The split here is educational; real telemetry should split by session.'},
{'code':'model.coef_','meaning':'Expose the learned direction and relative scale of each feature.','watch':'Interpret coefficients only after accounting for units and scaling.'},
],
'code_explanation':'The data generator contains a quadratic speed term, so a purely linear model should leave speed-dependent residual structure. That is intentional.',
'trace':'''```text
[speed, throttle, brake]
          ↓ linear weighted sum
predicted next speed
          ↓ subtract observed next speed
residual
          ↓ group/plot by condition
model-improvement hypothesis
```

The residual is not merely an error score; it is evidence about missing structure.''',
'break_it':'Add the target next speed as an input feature and watch MAE collapse. Then randomize brake while preserving speed. Compare coefficient signs and residuals.',
'diagnose':'A suspiciously perfect baseline should trigger a feature audit and time-index trace before celebration. Check that every input is available at forecast time and that split entities are disjoint.',
'repair':'Maintain an allow-list of input features, unit-test target exclusion, and report persistence beside every model. Add residual plots by horizon and condition to evaluation artifacts.',
'choices':[
{'option':'Persistence','choose':'Very short horizons and slowly changing states.','avoid':'Actions or geometry cause rapid transitions.'},
{'option':'Linear / Ridge','choose':'You need interpretability, speed and a strong control.','avoid':'Residuals show substantial nonlinear or temporal structure.'},
{'option':'Gradient-boosted trees','choose':'Tabular nonlinearities dominate and fixed windows can summarize history.','avoid':'You need smooth autoregressive latent dynamics or differentiable planning.'},
{'option':'Probabilistic baseline','choose':'Forecast intervals or multi-modal outcomes matter.','avoid':'You have not first validated deterministic error and calibration.'},
],
'decision':'APEX keeps persistence and a linear transition baseline in the same evaluation harness as learned world models. A complex model is promoted only when it improves the relevant horizons without unacceptable violations or operational cost.',
'apex':'Open the baseline implementation and evaluation report. Add a residual plot against curvature and a table comparing relative improvement over persistence.',
'paths':'apex_engine/src/apexsim/models/baselines.py\napex_engine/src/apexsim/evaluation.py\napex_engine/src/apexsim/pipeline/stages.py\ndebugging_cases/03_target_leakage',
'research':'Strong baselines protect research from architecture-driven conclusions. If a latent world model cannot outperform persistence on the actual decision horizon, its representation may still be useful—but that claim needs a different evaluation.',
'questions':['Why is relative improvement over persistence more informative than a standalone MAE?','What does a curved residual-vs-speed plot suggest?','Can uncertainty be low while the prediction is wrong?'],
'solutions':['It shows how much predictable change the model captures beyond the natural smoothness of telemetry.','The transition contains nonlinear speed dependence or the feature scaling/model form is misspecified.','Yes. An uncalibrated model can be confidently wrong, especially under distribution shift.'],
'challenge':'Create persistence, linear and polynomial baselines under the same session split. Produce a one-page model card explaining which baseline wins at 1, 5 and 20 steps and why.'
})

CHAPTERS.append({
'title':'9. Tensors, Autograd and the Training Loop You Can Explain',
'figure':'08_autograd.png',
'objective':'Build a PyTorch training loop while understanding every tensor, gradient and parameter update rather than memorizing boilerplate.',
'problem':'''Many learners can write `loss.backward()` but cannot say what changed afterward. This becomes dangerous when gradients accumulate, validation tracks graphs, or tensor axes are swapped. We will turn the training loop into an observable state machine.''',
'prediction':'''Immediately after `loss.backward()` and before `optimizer.step()`, have the model weights changed? Where is the information needed to change them stored? What happens if `zero_grad()` is omitted for two iterations?''',
'intuition':'''A tensor is an array plus shape, dtype, device and—when requested—a connection to a computation graph. The forward pass applies parameterized operations. The loss reduces prediction error to a scalar. Backpropagation computes derivatives of that scalar with respect to leaf parameters and stores them in `.grad`. The optimizer then uses those gradients to update parameters.

Gradients accumulate by default. That enables deliberate gradient accumulation but causes a bug when forgotten. Evaluation must switch behaviour-sensitive layers with `model.eval()` and disable graph construction with `torch.no_grad()`.

The most effective way to learn this is to print parameter values, gradients and loss before and after each line on a tiny problem whose correct mapping is known.''',
'concepts':[
{'name':'Computation graph','meaning':'The recorded chain of operations connecting inputs, parameters and loss.','apex':'Enables gradient-based training of all world models.'},
{'name':'Gradient','meaning':'Local sensitivity of loss to a parameter.','apex':'Stored in each trainable parameter after backward.'},
{'name':'Optimizer state','meaning':'Extra memory used to turn gradients into updates.','apex':'Adam moments are checkpointed with the model during resumable training.'},
{'name':'Train/eval mode','meaning':'Switch for layers such as dropout and batch normalization.','apex':'Ensures deterministic, correctly normalized validation and rollout.'},
],
'worked':'''For a one-parameter model \(\hat y=wx\) with `x=2`, `y=6`, `w=1`, and squared loss \((\hat y-y)^2`:

1. Prediction: `1 × 2 = 2`.
2. Error: `2 − 6 = −4`.
3. Loss: `16`.
4. Gradient: `dL/dw = 2(wx−y)x = 2(−4)(2) = −16`.
5. With learning rate 0.1, SGD update: `w ← 1 − 0.1(−16) = 2.6`.
6. New prediction: `5.2`; new loss: `0.64`.

Backward computes −16; the optimizer performs the update to 2.6.''',
'lab':'10_training_loop',
'build':'Train a linear PyTorch module to sum three input features. Print training loss, gradient norm and validation loss each epoch.',
'line_notes':[
{'code':'opt.zero_grad()','meaning':'Clear gradients left by previous backward passes.','watch':'It does not reset model weights.'},
{'code':'pred=model(x)','meaning':'Run the forward computation using current parameters.','watch':'Inspect prediction shape against target shape.'},
{'code':'loss.backward()','meaning':'Populate `.grad` for parameters connected to the loss.','watch':'Weights have not yet changed.'},
{'code':'opt.step()','meaning':'Use gradients and optimizer state to update parameters.','watch':'Compare parameter values before and after.'},
{'code':'with torch.no_grad()','meaning':'Compute validation outputs without constructing a backward graph.','watch':'Also call `model.eval()` for mode-dependent layers.'},
],
'code_explanation':'The gradient norm is a diagnostic. Zero gradients, exploding gradients and NaNs point to different failure classes.',
'trace':'''```text
parameters θ₀
   ↓ forward
predictions ŷ
   ↓ loss
scalar L
   ↓ backward
θ.grad populated; θ still equals θ₀
   ↓ optimizer.step
parameters θ₁
```

Print `id(parameter)`, `parameter.detach()`, and `parameter.grad` around these steps once. That trace removes the mystery permanently.''',
'break_it':'Remove `zero_grad`, increase learning rate by 100×, and accidentally shape targets as `[B]` while predictions are `[B,1]`. Observe accumulation, divergence and broadcasting.',
'diagnose':'Check shapes first, then finite values, loss scale, gradient norms, parameter-update magnitude and mode. Debug the smallest batch before scaling to full telemetry.',
'repair':'Add assertions for exact prediction/target shape, finite loss and finite gradients. Add a one-batch overfit test and a deterministic seed. Make gradient accumulation an explicit configured feature if used.',
'choices':[
{'option':'SGD','choose':'You want transparent updates and can tune schedules carefully.','avoid':'Sparse/noisy gradients need faster adaptive progress.'},
{'option':'Adam/AdamW','choose':'A strong default for deep sequence models and fast iteration.','avoid':'You assume it removes the need for learning-rate and regularization experiments.'},
{'option':'Gradient clipping','choose':'Recurrent or long-horizon training shows occasional exploding norms.','avoid':'It hides systematically bad scaling or unstable architecture.'},
{'option':'Mixed precision','choose':'GPU throughput/memory matters and numerical checks pass.','avoid':'You have not established a stable full-precision reference.'},
],
'decision':'APEX training records seed, configuration, gradient-related settings, checkpoint metric and normalizer. Validation is performed under eval/no-grad and the best checkpoint is restored before test evaluation.',
'apex':'Trace one batch through the GRU training function. Print every shape and compare parameter checksum before backward, after backward and after step.',
'paths':'apex_engine/src/apexsim/training.py\napex_engine/src/apexsim/models/gru_world_model.py\ndebugging_cases/08_missing_eval_mode\ndebugging_cases/09_gradient_accumulation',
'research':'Research papers summarize optimization in a paragraph, but reproducing them depends on these details: gradient scale, target construction, optimizer state, evaluation mode, clipping, schedules and checkpoint selection.',
'questions':['What exactly does `backward()` mutate?','Why can broadcasting produce a low-looking loss with the wrong semantics?','What does successful one-batch overfitting prove and not prove?'],
'solutions':['It accumulates gradients into `.grad` fields of leaf tensors requiring gradients; it does not update parameter values.','PyTorch expands compatible dimensions silently, comparing unintended pairs while still returning a scalar.','It proves the data path, model and optimizer can memorize a tiny sample; it does not prove generalization, correct splits or realistic rollout behaviour.'],
'challenge':'Instrument a training step to write a JSON trace containing input shapes, loss, gradient norms and parameter-update norms. Use it to diagnose three intentionally broken configurations.'
})

CHAPTERS.append({
'title':'10. Transition Models and Why Rollouts Fail',
'figure':'09_rollout.png',
'objective':'Build a one-step neural transition, convert it into an autoregressive simulator, and measure error compounding honestly.',
'problem':'''A model can be excellent at predicting the next frame when given the true current frame, yet collapse when asked to simulate ten frames. During rollout it consumes its own imperfect predictions, a distribution it did not see during teacher-forced training.''',
'prediction':'''A model has a constant +0.1 m/s bias per predicted step and no corrective feedback. What speed bias do you expect after 20 autoregressive steps? What if the transition also multiplies the current error by 1.05 each step?''',
'intuition':'''One-step supervised training samples inputs from real data. Autoregressive inference samples later inputs from the model. This train–inference distribution shift is exposure bias. Even unbiased local noise can alter future controls' effects because the state enters nonlinear dynamics.

A rollout function must specify which future variables are known and which are predicted. In APEX, future controls/context can be provided by a scenario, while future state is generated. After each step, predicted state replaces the state portion of the next input; controls remain externally supplied.

Evaluation should report error by horizon rather than averaging all future steps. The shape of the curve distinguishes immediate bias, unstable compounding and long-memory failure.''',
'concepts':[
{'name':'Teacher forcing','meaning':'Train each transition using the true previous state.','apex':'Stable supervised training for GRU/RSSM components.'},
{'name':'Autoregressive rollout','meaning':'Feed predicted state back to generate later states.','apex':'The actual simulation mode.'},
{'name':'Exposure bias','meaning':'The model trains on true states but runs on its own imperfect states.','apex':'A central source of horizon degradation.'},
{'name':'Horizon curve','meaning':'Error reported separately at each future step.','apex':'Primary evidence for useful simulation duration.'},
],
'worked':'''With additive bias `e_{t+1}=e_t+0.1`, starting at zero, error after 20 steps is 2.0 m/s.

With amplification `e_{t+1}=1.05e_t+0.1`,

\[e_{20}=0.1\frac{1.05^{20}-1}{1.05-1}\approx3.31\text{ m/s}.\]

The one-step bias is still only 0.1, but the system dynamics amplify it. This is why one-step MAE cannot certify a simulator.''',
'lab':'07_pytorch_module',
'build':'Use a small PyTorch transition module as the building block, then write a loop that feeds predicted state back while taking future controls from an external sequence.',
'line_notes':[
{'code':'prediction = model(current_input)','meaning':'Predict the next state from current state/action/context.','watch':'Confirm output contains only target state variables.'},
{'code':'current_state = prediction','meaning':'Move the imagined world forward using its own result.','watch':'Detach only when appropriate; training through rollout may need gradients.'},
{'code':'next_input = concat(current_state, future_control[t])','meaning':'Combine generated state with externally specified intervention.','watch':'Never overwrite the future control with a predicted target column.'},
],
'code_explanation':'A simulator is not just a model class. It is the model plus a precise state-update loop and scenario-input policy.',
'trace':'''```text
real history → encoded state
step 1: predicted state₁ + supplied action₁ → input₂
step 2: predicted state₂ + supplied action₂ → input₃
step 3: predicted state₃ + supplied action₃ → input₄
```

At each step, log both normalized and physical-unit state. Violations may be hidden in normalized space.''',
'break_it':'During rollout, accidentally keep feeding the last real state instead of each prediction. The multi-step score may look surprisingly strong because you are not actually simulating.',
'diagnose':'Trace the source of every input tensor at every horizon. Mark each element as observed, supplied intervention, static context or model-generated. A rollout audit catches “teacher forcing at test time.”',
'repair':'Add a test with a deterministic transition where the exact multi-step trajectory is known. Assert that changing a predicted state changes later predictions. Report teacher-forced and free-running metrics separately.',
'choices':[
{'option':'One-step training','choose':'A stable starting point with abundant transition examples.','avoid':'You treat its metric as rollout certification.'},
{'option':'Multi-step loss','choose':'Long-horizon accuracy matters and compute allows unrolled training.','avoid':'Early training is unstable or the horizon curriculum is not controlled.'},
{'option':'Scheduled sampling','choose':'You want gradual exposure to model-generated states.','avoid':'You assume it guarantees consistent probabilistic learning.'},
{'option':'Direct multi-horizon model','choose':'Fixed-horizon forecasts matter more than a reusable transition.','avoid':'You need arbitrary-length interactive simulation.'},
],
'decision':'APEX trains a stable sequence world model and evaluates it under free-running rollouts. Any reported simulation horizon is tied to its error and violation curves, not a marketing duration.',
'apex':'Inspect `simulation.py` and identify the exact line where predicted state is inserted into the next model input. Add a debug mode that records provenance for every future feature.',
'paths':'projects/04_mlp_transition/main.py\napex_engine/src/apexsim/simulation.py\napex_engine/src/apexsim/evaluation.py\napex_engine/src/apexsim/models/gru_world_model.py',
'research':'World-model planning magnifies rollout weaknesses because a planner searches for trajectories that exploit them. Reliable imagination requires evaluating model-generated state distributions, not only posterior-conditioned reconstruction.',
'questions':['Why can zero-mean one-step noise still create biased long rollouts?','What future variables may legitimately be supplied to a simulator?','What does a flat horizon-error curve suggest?'],
'solutions':['Nonlinear dynamics and constraints can transform symmetric local noise into asymmetric state evolution.','Known scenario interventions and exogenous forecasts, provided their availability is explicit; future target state cannot be supplied.','The model may be stable over that range, or errors may be dominated by a constant initial bias rather than compounding; inspect conditions and baselines.'],
'challenge':'Train the same transition with one-step and five-step losses. Compare horizon curves, training stability and compute. Record which objective you choose for APEX V1 and why.'
})

CHAPTERS.append({
'title':'11. Recurrent Memory and the GRU From the Inside',
'figure':'10_gru.png',
'objective':'Earn recurrent memory by exposing the limits of fixed-frame transitions, then inspect how GRU gates update hidden state.',
'problem':'''Current speed, throttle and brake may not reveal whether the car has been accelerating for two seconds, exiting a corner, heating tyres or recovering from a braking event. A fixed-frame model sees only the present. We need a mechanism that carries a learned summary of the past.''',
'prediction':'''Two sequences end with the same final frame `[speed=50, throttle=0.5, brake=0]`. Sequence A accelerated steadily; sequence B braked hard and recovered. Should a recurrent model be able to produce different next-state predictions? What must differ internally?''',
'intuition':'''A recurrent neural network updates hidden memory as each frame arrives. The final hidden state is not a literal copy of history; it is a learned summary optimized for the training objective. A vanilla recurrent cell can struggle when useful information must survive many updates because gradients repeatedly pass through the same transition.

A GRU adds gates. The update gate decides how much old memory to keep versus replace. The reset gate controls how much previous memory influences the candidate update. These are soft, feature-wise decisions, not binary switches. The same hidden dimension can retain long-term tyre information while rapidly updating braking state.

Using `nn.GRU` does not guarantee meaningful memory. You still need enough history, correct ordering, no hidden-state leakage across independent sequences, and evaluation that tests whether memory improves the target horizon.''',
'concepts':[
{'name':'Hidden state','meaning':'A learned vector carried across sequence steps.','apex':'Compressed recent driving and unobserved dynamical context.'},
{'name':'Update gate','meaning':'Controls interpolation between old memory and candidate memory.','apex':'Lets some information persist while other information changes.'},
{'name':'Reset gate','meaning':'Controls how previous memory contributes to the candidate update.','apex':'Allows rapid forgetting when current evidence changes regime.'},
{'name':'Sequence boundary','meaning':'The point where hidden memory must be reset or intentionally transferred.','apex':'Driver/session windows cannot share hidden state accidentally.'},
],
'worked':'''A simplified update is

\[h_t=(1-z_t)h_{t-1}+z_t\tilde h_t.\]

If old memory is `h=0.8`, candidate memory is `−0.2`:

- With update gate `z=0.1`: `h_t=0.9(0.8)+0.1(−0.2)=0.70`. Most old memory survives.
- With `z=0.9`: `h_t=0.1(0.8)+0.9(−0.2)=−0.10`. The new evidence largely overwrites memory.

This interpolation makes a gate interpretable at the mechanism level, although individual learned dimensions may not map cleanly to human concepts.''',
'lab':'12_gru_gates',
'build':'Feed three simple one-hot-like inputs through a GRUCell and print hidden state after each step. The goal is to see memory as a changing vector rather than a black box.',
'line_notes':[
{'code':'cell=torch.nn.GRUCell(2,4)','meaning':'Create a transition from a 2-feature input and 4-value memory to new memory.','watch':'The hidden size is model capacity, not a known physical variable count.'},
{'code':'h=torch.zeros(1,4)','meaning':'Initialize memory for one sequence.','watch':'Initial-state policy affects early predictions.'},
{'code':'h=cell(x,h)','meaning':'Combine current observation and previous memory into next memory.','watch':'Sequence order changes the result.'},
],
'code_explanation':'Run the same three inputs in reversed order. The final memory differs even though the multiset of inputs is identical.',
'trace':'''```text
x₁ + h₀=0  → h₁
x₂ + h₁    → h₂
x₃ + h₂    → h₃
                 ↓
          decoder predicts future
```

For batched sequences, PyTorch commonly uses `[batch, time, features]` when `batch_first=True`. The returned hidden state is typically `[layers, batch, hidden]`. Name these axes every time.''',
'break_it':'Reuse the hidden state from one session as the initial state for an unrelated session. Also shuffle time within each sequence while preserving rows.',
'diagnose':'If validation varies with dataloader order or batch grouping, inspect hidden-state lifetime. Hidden memory should reset at independent sequence boundaries unless stateful streaming is an explicit design.',
'repair':'Add a test where two sequences processed separately match the same sequences processed in a batch with zero initial states. Add session-boundary reset logic and make stateful mode explicit.',
'choices':[
{'option':'Vanilla RNN','choose':'Tiny educational tasks and very short dependencies.','avoid':'Long/noisy telemetry histories.'},
{'option':'GRU','choose':'Strong compact recurrent baseline with fewer parameters than LSTM.','avoid':'You have evidence that longer structured memory or parallel training is required.'},
{'option':'LSTM','choose':'You value an explicit cell state and gates and have sufficient compute/data.','avoid':'Extra complexity provides no measured gain.'},
{'option':'Temporal convolution','choose':'Dependencies fit a fixed receptive field and parallel computation matters.','avoid':'You need adaptive unbounded recurrence or stateful streaming.'},
],
'decision':'The GRU is APEX V1’s primary deterministic world model because it is understandable, stable, compact and strong enough to establish the pipeline. SSM and RSSM models are challengers, not automatic replacements.',
'apex':'Trace the GRU world model from history encoder to autoregressive decoder. Print hidden shape, decoder input shape and output state at each horizon for a batch of one.',
'paths':'labs/11_rnn_from_scratch/solution.py\nlabs/12_gru_gates/solution.py\nprojects/06_gru_forecaster/main.py\napex_engine/src/apexsim/models/gru_world_model.py\ndebugging_cases/07_hidden_state_reuse',
'research':'Recurrent state is a deterministic belief summary. Dreamer’s RSSM retains a recurrent deterministic state while adding a stochastic latent variable to represent uncertainty and ambiguity.',
'questions':['Why can two sequences with the same final observed frame produce different hidden states?','Does a larger hidden size always improve memory?','When should hidden state persist across API requests?'],
'solutions':['The recurrence applies ordered updates, so earlier frames alter the memory entering later frames.','No. It increases capacity but may overfit, slow training or store irrelevant detail; history, objective and optimization also limit memory.','Only in an explicitly stateful stream with stable entity/session identity, ordering guarantees and reset rules. Stateless scenario requests should rebuild from supplied history.'],
'challenge':'Implement a GRU forecaster and a frame-only MLP with matched parameter counts. Create a synthetic target dependent on an event ten steps ago and compare performance as history length changes.'
})

CHAPTERS.append({
'title':'12. Classical State-Space Models: Dynamics as Memory',
'figure':'11_ssm.png',
'objective':'Understand state-space recurrence mathematically, inspect stability, and connect classical dynamical systems to modern sequence models.',
'problem':'''GRUs learn memory through generic gates. State-space models begin with an explicit dynamical view: a hidden state evolves under a transition and receives input. This structure can represent long memory efficiently, but an unstable transition can explode over repeated steps.''',
'prediction':'''For the scalar recurrence `x_t = 1.05 x_{t-1} + u_t`, what happens after inputs become zero? What changes if the transition coefficient is 0.95?''',
'intuition':'''A discrete linear state-space model is

\[x_t=Ax_{t-1}+Bu_t,\qquad y_t=Cx_t+Du_t.\]

The hidden state `x` is memory; `A` controls how it persists and mixes; `B` writes input; `C` reads output. Repeated powers of `A` determine whether past information decays, persists, oscillates or explodes.

Many modern SSMs begin from continuous-time dynamics and discretize them for sampled sequences. This connects model behaviour to the time step. A change from 5 Hz to 20 Hz should not be treated as an arbitrary tensor resize when the transition is supposed to represent time.

Linear recurrence alone cannot model all nonlinear racing dynamics, but it exposes memory timescales and stability more directly than a generic black box.''',
'concepts':[
{'name':'State matrix A','meaning':'Controls hidden-state propagation between steps.','apex':'Determines memory decay, coupling and stability.'},
{'name':'Input matrix B','meaning':'Controls how current telemetry writes into memory.','apex':'Maps actions/context into dynamical state.'},
{'name':'Readout C','meaning':'Maps hidden memory to predicted output.','apex':'Produces next-state features from SSM memory.'},
{'name':'Spectral radius','meaning':'Largest absolute eigenvalue of A; a key discrete stability indicator.','apex':'Values above one can amplify state without bound.'},
],
'worked':'''For `x_t = a x_{t-1}` after input stops:

- If `a=1.05`, then after 20 steps `x` is multiplied by `1.05²⁰ ≈ 2.65`.
- If `a=0.95`, it is multiplied by `0.95²⁰ ≈ 0.358`.
- If `a=1`, memory persists exactly.
- If `a=−0.95`, memory alternates sign while decaying.

For a matrix, eigenvalues play the role of these scalar factors along different modes. Stability does not guarantee usefulness: a transition that decays too quickly forgets everything.''',
'lab':'13_linear_ssm',
'build':'Run a two-dimensional linear SSM under an input pulse and observe one state component react immediately while another integrates it more slowly.',
'line_notes':[
{'code':'A=np.array([[0.95,0.0],[0.1,0.85]])','meaning':'Define decay and coupling of two hidden modes.','watch':'Diagonal values set persistence; off-diagonal 0.1 transfers state.'},
{'code':'B=np.array([[0.2],[0.05]])','meaning':'Define how the scalar input writes into both modes.','watch':'Different modes receive different input strength.'},
{'code':'x=A@x+B[:,0]*u','meaning':'Apply one state-space transition.','watch':'Repeated multiplication reveals stability and memory.'},
],
'code_explanation':'After the input becomes zero, state continues evolving because memory remains in `x`.',
'trace':'''```text
u₀=1 → immediate mode rises strongly; slow mode rises slightly
u₁=1 → both accumulate
u₂=0 → immediate mode decays; slow mode still receives coupled memory
u₃=0 → both decay on different timescales
```

Plot each hidden dimension. A hidden state is useful because its dynamics differ, not because it has many numbers.''',
'break_it':'Change a diagonal value in `A` to 1.2 and roll for 100 zero-input steps. Then set both diagonal values to 0.1.',
'diagnose':'Measure hidden-state norm and eigenvalues. Explosion points to unstable propagation; rapid collapse points to memory that decays faster than the required dependency.',
'repair':'Parameterize stable decay, constrain eigenvalues or add normalization/clipping as appropriate. Add tests that hidden state stays finite under bounded inputs for the intended horizon.',
'choices':[
{'option':'Fixed linear SSM','choose':'System identification, interpretability and approximately linear dynamics.','avoid':'Strong context-dependent nonlinear transitions dominate.'},
{'option':'Nonlinear readout','choose':'Memory dynamics are simple but state-to-output mapping is nonlinear.','avoid':'Input must alter the memory law itself.'},
{'option':'Input-dependent SSM','choose':'Different telemetry regimes require selective writing/forgetting.','avoid':'A fixed transition already works and simplicity matters.'},
{'option':'GRU','choose':'You need a proven generic nonlinear recurrent baseline.','avoid':'Long-sequence efficiency or structured timescales are the measured bottleneck.'},
],
'decision':'APEX includes a small SSM-style challenger with bounded decay and input-dependent updates. It is taught as a selective recurrent model, not represented as a complete optimized Mamba implementation.',
'apex':'Inspect the SSM cell parameters and plot hidden norms across a full session. Compare horizon curves and latency with the GRU under the same data and budget.',
'paths':'labs/13_linear_ssm/solution.py\nprojects/07_selective_ssm/main.py\napex_engine/src/apexsim/models/ssm_world_model.py\ndebugging_cases/10_exploding_ssm',
'research':'S4 and related structured SSMs use mathematical parameterizations and efficient convolution/recurrent forms to handle long sequences. The classical equation here is the conceptual root that makes those designs readable.',
'questions':['Why can a stable SSM still be a bad memory model?','What does an off-diagonal element of A do?','How does sample rate affect a transition intended to represent physical time?'],
'solutions':['It may decay too quickly, ignore relevant inputs or lack nonlinear/selective behaviour.','It transfers information from one hidden component into another during propagation.','A smaller time step represents less elapsed time per transition; continuous-time parameterization/discretization can adjust accordingly, while a fixed discrete A changes physical meaning.'],
'challenge':'Construct a three-mode SSM with fast, medium and slow decay. Feed braking pulses of different duration and show which hidden mode retains each timescale.'
})

CHAPTERS.append({
'title':'13. Selective State-Space Models and What Mamba Changes',
'figure':'12_selective_ssm.png',
'objective':'Build an input-dependent memory cell, understand selection, and separate the core Mamba idea from implementation hype.',
'problem':'''A fixed SSM remembers every input according to the same transition. Racing telemetry is regime dependent: a yellow flag, braking spike or rain change may deserve a strong memory write, while repetitive straight-line frames may be compressed or forgotten.''',
'prediction':'''Imagine a memory of “recent heavy braking.” Should the same decay apply during ten ordinary straight-line frames and during a sudden lock-up indicator? How could the current input alter write and forget behaviour?''',
'intuition':'''Selection means model parameters or gates depend on the current input. Instead of one fixed `A` and `B`, the sequence determines how strongly memory persists and what content is written. This gives content-aware recurrence while preserving a state-space perspective.

Mamba combines selective state-space dynamics with hardware-aware computation so long sequences can be processed efficiently. The important conceptual move for this curriculum is not “replace everything with Mamba.” It is: **make memory propagation conditional on the token when fixed dynamics are insufficient.**

A small selective cell can be written as `h_t = a(x_t) ⊙ h_{t-1} + (1−a(x_t)) ⊙ b(x_t)`. It resembles a gated recurrent update. The difference between educational cell and research architecture must remain explicit.''',
'concepts':[
{'name':'Selection','meaning':'Current input changes how memory is written, retained or read.','apex':'Braking, weather or geometry can trigger different memory behaviour.'},
{'name':'Input-dependent decay','meaning':'The retention factor is computed from the current token.','apex':'Adaptive timescales across race regimes.'},
{'name':'Scan','meaning':'Efficiently apply a recurrence across sequence positions.','apex':'Important for long histories and GPU throughput.'},
{'name':'Mamba block','meaning':'A complete architecture combining projections, selective SSM computation and implementation details.','apex':'A future challenger; not identical to the toy selective cell.'},
],
'worked':'''Let old memory be `h=0.9`.

- Ordinary input produces retention `a=0.95` and candidate `b=0.2`: `h'=0.95(0.9)+0.05(0.2)=0.865`.
- Critical braking input produces retention `a=0.2` and candidate `b=−0.8`: `h'=0.2(0.9)+0.8(−0.8)=−0.46`.

The same memory dimension changes slowly during routine input and rapidly under a meaningful event. Selection is useful only if training learns gates that correspond to predictive needs rather than arbitrary noise.''',
'lab':'14_selective_ssm',
'build':'Implement a small PyTorch selective cell where decay and candidate write are functions of each input token. Feed basis vectors and inspect hidden updates.',
'line_notes':[
{'code':'a=torch.sigmoid(self.decay(x))*0.99','meaning':'Compute bounded input-dependent retention.','watch':'Multiplying by 0.99 prevents exact unit retention in this toy cell.'},
{'code':'b=torch.tanh(self.write(x))','meaning':'Compute candidate content to write.','watch':'Tanh bounds the candidate but can saturate.'},
{'code':'return a*h+(1-a)*b','meaning':'Interpolate between persistent memory and new content per dimension.','watch':'Inspect gate distributions across regimes.'},
],
'code_explanation':'The cell is educational. It demonstrates selection and stability but omits the full Mamba block, convolutional path and optimized selective-scan implementation.',
'trace':'''```text
input x_t
  ├─► decay network ─► retention a_t ─┐
  └─► write network ─► candidate b_t ─┼─► h_t
previous h_{t-1} ──────────────────────┘
```

Log `a_t` by feature regime. A gate that is always 0.5 is technically selective but may not be learning meaningful specialization.''',
'break_it':'Remove the sigmoid/bound and allow retention greater than one. Then initialize decay so gates saturate near zero or one.',
'diagnose':'Track hidden norm, gate histograms, gradient norms and horizon errors. Explosion, frozen memory and always-overwritten memory have different signatures.',
'repair':'Use stable parameterization, sensible initialization and regular diagnostic plots. Add tests for finite bounded-state behaviour under bounded inputs, but do not force gates to a preferred distribution without evidence.',
'choices':[
{'option':'Toy selective cell','choose':'Learning the mechanism and testing whether input-dependent memory helps.','avoid':'Claiming Mamba-equivalent speed or quality.'},
{'option':'Official Mamba implementation','choose':'Long sequences and benchmarks justify the dependency and hardware path.','avoid':'Your data are small, horizons short, or environment support is fragile.'},
{'option':'GRU','choose':'A stable gated recurrent baseline is sufficient.','avoid':'Measured long-context/throughput limitations motivate another architecture.'},
{'option':'Transformer','choose':'Global content interactions and parallel token processing dominate.','avoid':'Quadratic attention cost is unjustified and recurrent deployment state is useful.'},
],
'decision':'APEX V1 retains a GRU primary and an SSM-style challenger. Fine-tuning or replacing with a full Mamba model should begin only after sequence length, data scale and latency measurements establish the need.',
'apex':'Compare GRU and SSM models with identical windows, splits, normalization, hidden size budget and evaluation. Add gate plots to the SSM run artifacts.',
'paths':'labs/14_selective_ssm/solution.py\nprojects/07_selective_ssm/main.py\napex_engine/src/apexsim/models/ssm_world_model.py\napex_engine/configs/ssm_fast.yaml',
'research':'The Mamba paper motivates selection because content-dependent reasoning is a weakness of fixed linear time-invariant SSMs. Its efficiency claims depend on the complete algorithm and hardware-aware implementation, not merely using a gate.',
'questions':['What makes a state update selective?','Why is bounded retention helpful but not sufficient?','What evidence would justify a full Mamba dependency in APEX?'],
'solutions':['The current input changes parameters controlling memory propagation, writing or reading.','It reduces explosion risk, but the model can still forget too quickly, ignore inputs or learn useless gates.','Long histories where GRU/Transformer baselines fail or are too slow, sufficient data, reproducible gains by horizon, and deployment hardware that benefits from the implementation.'],
'challenge':'Create a dataset with rare event tokens that determine a target many steps later. Compare fixed linear SSM, selective cell and GRU while plotting learned retention around events.'
})

CHAPTERS.append({
'title':'14. Autoencoders and Variational Latent State',
'figure':'13_latent.png',
'objective':'Learn representation compression by building it, then add probabilistic latent variables without confusing reconstruction with useful world modelling.',
'problem':'''Raw observations can contain redundant or noisy dimensions. A world model may benefit from a compact latent state, but compression can discard precisely the small variable needed for future prediction. A good reconstruction is not automatically a good predictive representation.''',
'prediction':'''A telemetry vector has 12 features, but only speed, curvature and tyre age determine the next state. If an autoencoder compresses to three dimensions, will those three necessarily correspond to the three causal variables? Why or why not?''',
'intuition':'''An autoencoder learns an encoder `z=f(x)` and decoder `x̂=g(z)` by minimizing reconstruction error. The bottleneck pressures the latent to preserve common information. Nothing requires each dimension to align with a human variable, and high-variance nuisance features may dominate.

A variational autoencoder predicts a distribution—usually mean and log variance—rather than one code. Sampling uses `z = μ + σ⊙ε`, which keeps the path differentiable with respect to `μ` and `σ`. A KL term regularizes the posterior toward a prior, enabling sampling but creating a tradeoff: too weak and the latent is irregular; too strong and it can ignore observations.

For world models, the latent should preserve information useful for dynamics and reward, not only instantaneous reconstruction. Temporal prediction losses or task probes test this.''',
'concepts':[
{'name':'Encoder','meaning':'Maps a high-dimensional observation into a compact representation.','apex':'Compresses telemetry/history into latent state.'},
{'name':'Decoder','meaning':'Reconstructs or predicts observable state from latent representation.','apex':'Produces interpretable future telemetry.'},
{'name':'Reparameterization','meaning':'Express stochastic sampling as differentiable transformation of parameter-free noise.','apex':'Allows RSSM/VAE posterior training.'},
{'name':'KL divergence','meaning':'Penalty measuring difference between posterior and prior distributions.','apex':'Regularizes stochastic latent state and aligns imagination with inference.'},
],
'worked':'''For one latent dimension with `μ=0.2`, `log variance=-1`:

1. Variance: `exp(-1)=0.3679`.
2. Standard deviation: `exp(-0.5)=0.6065`.
3. If sampled noise `ε=1.0`, then `z=0.2+0.6065=0.8065`.
4. KL to standard normal is `−0.5(1 + logvar − μ² − exp(logvar))`.
5. Substitute: `−0.5(1−1−0.04−0.3679)=0.20395`.

The KL is zero only when posterior mean is zero and variance is one. Driving every posterior to that point would erase observation information.''',
'lab':'16_vae_reparameterization',
'build':'Compute posterior standard deviation, sample with reparameterization, and calculate KL for a tiny batch. Pair it with the autoencoder lab to compare deterministic and stochastic codes.',
'line_notes':[
{'code':'std=torch.exp(0.5*logvar)','meaning':'Convert log variance into standard deviation.','watch':'The factor 0.5 appears because std is square root of variance.'},
{'code':'eps=torch.randn_like(std)','meaning':'Sample parameter-free standard normal noise.','watch':'Random seed affects the sampled latent, not posterior parameters.'},
{'code':'z=mu+std*eps','meaning':'Create a stochastic sample with gradients flowing through μ and std.','watch':'Inspect multiple samples to see uncertainty.'},
{'code':'kl=...','meaning':'Measure posterior departure from the unit Gaussian prior.','watch':'Monitor KL by dimension for collapse or overuse.'},
],
'code_explanation':'Reparameterization moves randomness into `eps`, allowing standard backpropagation through distribution parameters.',
'trace':'''```text
observation x
   ↓ encoder
μ(x), logσ²(x)
   ↓ sample ε ~ N(0,I)
z = μ + σ ε
   ↓ decoder
reconstruction x̂

loss = reconstruction error + β × KL
```

Print latent means, standard deviations and KL—not only total loss.''',
'break_it':'Set KL weight extremely high and inspect whether reconstructions become generic. Then set it to zero and sample from the prior at inference.',
'diagnose':'High KL with poor reconstruction suggests excessive regularization. Near-zero KL in every dimension plus decoder independence from `z` suggests posterior collapse. Good reconstruction with nonsensical prior samples suggests an unstructured latent.',
'repair':'Use KL warm-up/free-nats or capacity control only after measuring the failure. Add latent probes for future speed, curvature and tyre state, and compare reconstruction versus predictive usefulness.',
'choices':[
{'option':'Deterministic autoencoder','choose':'Compression and reconstruction matter; uncertainty is not required.','avoid':'You need coherent sampling or probabilistic belief.'},
{'option':'VAE','choose':'A smooth sampleable latent distribution is useful.','avoid':'KL tradeoffs add complexity without serving the downstream task.'},
{'option':'Predictive encoder','choose':'Future-relevant structure matters more than reconstructing every input detail.','avoid':'You still require high-fidelity observation generation.'},
{'option':'No bottleneck','choose':'State is already small and semantically meaningful.','avoid':'High-dimensional noisy observations overwhelm dynamics learning.'},
],
'decision':'APEX telemetry is already compact, so V1 can predict state directly. The RSSM uses stochastic latent state to study uncertainty and imagination, not because compression is automatically necessary.',
'apex':'Run autoencoder and VAE labs, then inspect RSSM posterior statistics. Create a probe predicting future speed from latent state and compare it with reconstruction loss.',
'paths':'labs/15_autoencoder/solution.py\nlabs/16_vae_reparameterization/solution.py\napex_engine/src/apexsim/models/rssm.py\ndebugging_cases/11_kl_collapse',
'research':'JEPA-style approaches challenge the need to reconstruct raw observations, arguing that useful representations can be learned by predicting abstract target embeddings. This is especially relevant when raw detail is unpredictable or irrelevant.',
'questions':['Why can low reconstruction error coexist with poor future prediction?','What is the purpose of the KL term?','Why does reparameterization enable gradients?'],
'solutions':['The encoder may preserve visually/statistically dominant current detail while discarding small causal variables needed later.','It regularizes the posterior toward the prior so latent space can support coherent prior sampling/imagination.','The random variable is expressed as a deterministic differentiable function of parameters and independent noise, so gradients pass through μ and σ.'],
'challenge':'Train an autoencoder on synthetic telemetry with nuisance noise. Compare latent probes for future speed under reconstruction-only and reconstruction-plus-future-prediction objectives.'
})

CHAPTERS.append({
'title':'15. RSSMs and Dreamer: Learning to Imagine Without Observations',
'figure':'14_rssm.png',
'objective':'Implement the logic of a recurrent state-space model, distinguish posterior training from prior imagination, and understand Dreamer as a system rather than a buzzword.',
'problem':'''A deterministic recurrent model predicts one future. Real driving contains unobserved factors, noisy evidence and multiple plausible outcomes. An RSSM maintains deterministic memory plus a stochastic latent belief. The hardest requirement is that imagination must continue when future observations are absent.''',
'prediction':'''During training you know the next observation; during planning you do not. Which distribution may use the observation: the prior, posterior, both or neither? What would happen if imagination secretly used posterior information?''',
'intuition':'''An RSSM commonly has deterministic state `h_t` and stochastic state `z_t`. The transition updates `h_t` from previous latent/action. The prior predicts a distribution over `z_t` from `h_t`. During training, an encoder provides observation evidence and a posterior refines that distribution. The decoder predicts observation/state from `h_t,z_t`.

The KL term teaches the prior to resemble the posterior enough that prior-only imagination remains useful. Reconstruction or prediction terms teach the latent to represent evidence. These objectives can conflict. Posterior collapse, overconfident priors and compounding uncertainty are practical failures, not footnotes.

Dreamer adds reward/continuation models and learns actor/critic behaviour from trajectories imagined by the world model. Before trusting control, APEX must establish that interventions produce realistic, calibrated rollouts.''',
'concepts':[
{'name':'Deterministic state h','meaning':'Recurrent memory summarizing past latent/action sequence.','apex':'Carries stable temporal context.'},
{'name':'Prior','meaning':'Latent distribution predicted without current observation.','apex':'Used during imagination and planning.'},
{'name':'Posterior','meaning':'Latent distribution conditioned on current observation evidence.','apex':'Used during training/state inference.'},
{'name':'Imagination','meaning':'Rollout using learned prior dynamics without future observations.','apex':'Generates counterfactual telemetry trajectories.'},
],
'worked':'''Suppose posterior is `N(μ_q=1, σ_q=0.5)` and prior is `N(μ_p=0, σ_p=1)`. The one-dimensional Gaussian KL `KL(q||p)` is

\[\log(\sigma_p/\sigma_q)+\frac{\sigma_q^2+(\mu_q-\mu_p)^2}{2\sigma_p^2}-\frac12.\]

Substitute:

- `log(1/0.5)=0.693`
- numerator `0.25 + 1 = 1.25`
- divide by 2 gives `0.625`
- subtract 0.5
- total `0.818`

The gap signals that the prior cannot yet reproduce the posterior belief. Reducing it by making both distributions uninformative would also be bad; reconstruction/prediction must remain strong.''',
'lab':'17_rssm_step',
'build':'Construct one RSSM step: update deterministic memory, compute prior statistics, then compute posterior statistics using observation embedding. Inspect all shapes.',
'line_notes':[
{'code':'h=cell(torch.cat([prev_z,action],-1),h)','meaning':'Advance deterministic memory using previous latent and current action.','watch':'Current observation is intentionally absent from this transition.'},
{'code':'prior_stats=prior(h)','meaning':'Predict latent distribution using only imagined memory.','watch':'This path must work at inference with no future observation.'},
{'code':'post_stats=posterior(torch.cat([h,obs_embed],-1))','meaning':'Refine latent belief using current evidence during training.','watch':'Posterior information must not leak into prior-only evaluation.'},
],
'code_explanation':'The lab outputs four numbers for each distribution; typically these are split into two means and two log variances.',
'trace':'''```text
training step:
prev z + action → h_t → prior p(z_t|h_t)
                         + observation embedding → posterior q(z_t|h_t,o_t)
posterior sample + h_t → decode target

imagination step:
prev z + action → h_t → prior sample → decode prediction
(no observation branch)
```

Evaluate both posterior reconstruction and prior rollout. They answer different questions.''',
'break_it':'Use posterior samples during test rollout. Then set KL weight to zero and compare prior imagination with posterior reconstruction.',
'diagnose':'If posterior metrics are good but prior rollout is poor, inspect prior–posterior KL by horizon and latent dimension. If KL is near zero but outputs ignore observations, inspect collapse.',
'repair':'Separate evaluation functions for posterior reconstruction and prior imagination. Add a test that imagination accepts no future observation tensor. Tune KL with explicit diagnostics, not only total loss.',
'choices':[
{'option':'Deterministic GRU world model','choose':'One likely future and stable V1 forecasting are sufficient.','avoid':'Uncertainty/multi-modal futures are central.'},
{'option':'RSSM','choose':'You need a learned belief state and prior imagination.','avoid':'Data/budget cannot support stable latent training or benefits are unmeasured.'},
{'option':'Ensemble deterministic models','choose':'You want practical epistemic uncertainty with simple training.','avoid':'Compute or storage prevents multiple models.'},
{'option':'Full Dreamer actor-critic','choose':'Dynamics, reward and continuation models are validated and control is the target.','avoid':'The world model can still be exploited or interventions are poorly represented.'},
],
'decision':'APEX includes a compact RSSM challenger and preserves its weaker short-budget result as a debugging lesson. The deterministic GRU remains V1 primary until stochastic imagination demonstrates decision value and calibration.',
'apex':'Train GRU and RSSM under the same session split. Compare posterior reconstruction, prior horizon error, KL, physical violations and scenario sensitivity—not just total training loss.',
'paths':'projects/08_rssm_imagination/main.py\napex_engine/src/apexsim/models/rssm.py\napex_engine/configs/rssm_fast.yaml\ndebugging_cases/11_kl_collapse',
'research':'DreamerV3 is an integrated agent: world model, imagined trajectories, reward/continuation prediction and actor-critic learning. Copying an RSSM cell is not equivalent to reproducing Dreamer’s training system or robustness.',
'questions':['Why must the prior exclude current observation evidence?','What does good posterior reconstruction but poor prior rollout mean?','Why might a deterministic model outperform an RSSM on APEX V1?'],
'solutions':['The future observation is unavailable during imagination; including it leaks the answer and invalidates the simulator.','The latent encoder can explain observed frames, but learned dynamics cannot predict the corresponding latent beliefs without evidence.','Small data, short training, near-deterministic telemetry, KL optimization difficulty and evaluation focused on mean trajectory can all favour the simpler model.'],
'challenge':'Implement a two-dimensional RSSM on a stochastic toy car. Plot posterior and prior distributions over time, then show a case where uncertainty widens under an unseen control sequence.'
})

CHAPTERS.append({
'title':'16. JEPA, LeWorldModel and Fine-Tuning Existing Representations',
'figure':'16_jepa.png',
'objective':'Understand predictive representation learning, decide when not to reconstruct raw observations, and build a disciplined fine-tuning strategy.',
'problem':'''Pixel or telemetry reconstruction forces a model to spend capacity on every observable detail, including noise that may not matter for future decisions. JEPA-style methods predict target representations instead. LeWorldModel-style work explores efficient latent world modelling and planning. The engineering question is not which acronym is newest; it is what target contains the information APEX needs.''',
'prediction':'''Suppose two future telemetry frames differ only in an unpredictable sensor-noise feature. A raw reconstruction loss treats them as different. Should a predictive representation loss treat them as different? What determines the answer?''',
'intuition':'''Joint-embedding predictive architectures encode context and target views, then train a predictor to infer the target representation from context. The target encoder defines what counts as meaningful similarity. Because the loss is in representation space, the model can ignore some raw variation—if the representation has learned to ignore it.

This creates a new failure possibility: representation collapse or shortcuts. Stop-gradient/target-encoder design, masking strategy and representation diagnostics matter. In telemetry, a future-latent target could emphasize dynamics while de-emphasizing sensor noise, but it might also discard rare safety-critical events.

Fine-tuning an existing model makes sense when its input semantics, sequence structure and learned invariances transfer. Adaptation choices range from a frozen encoder plus new head, through parameter-efficient adapters, to full fine-tuning. Start with the least invasive option that can represent the domain shift, and compare against training a small model from scratch.''',
'concepts':[
{'name':'Representation target','meaning':'The encoded feature vector the predictor must infer.','apex':'Potential future-dynamics target instead of raw telemetry.'},
{'name':'Stop gradient / target encoder','meaning':'Prevents both sides from trivially co-adapting in unstable ways.','apex':'Part of a non-collapsing predictive objective.'},
{'name':'Linear probe','meaning':'A simple supervised head used to test what information a representation contains.','apex':'Measures speed, curvature, tyre or event information in latent state.'},
{'name':'Fine-tuning','meaning':'Adapt pretrained parameters to a new domain/task.','apex':'Possible when a relevant sequence/world model checkpoint exists.'},
],
'worked':'''Compare two losses for target vector `y=[10.0, 0.02]` where the second feature is pure noise. Prediction A is `[9.8, 0.50]`; prediction B is `[9.8, −0.40]`. Raw MSE differs because of noise.

If a target encoder maps both raw targets to a dynamics representation `[speed_bin=10, regime=straight]`, their representation loss can be identical. This is desirable only if the discarded noise truly has no predictive or decision value.

For fine-tuning, suppose a pretrained encoder has one million parameters. A frozen-head experiment trains 5,000 parameters; an adapter trains 50,000; full tuning changes all million. These are nested hypotheses about how much the representation must change.''',
'lab':'15_autoencoder',
'build':'Use the autoencoder lab as a concrete representation baseline, then modify its objective conceptually: predict a future latent code rather than reconstruct the current input. Add a linear probe for a known future variable.',
'line_notes':[
{'code':'z=torch.tanh(enc(x))','meaning':'Produce a learned representation through a bottleneck.','watch':'Inspect variance and pairwise similarity to detect collapse.'},
{'code':'recon=dec(z)','meaning':'The original lab asks the latent to reconstruct raw input.','watch':'Replace/augment this with future-target representation prediction.'},
{'code':'loss=((recon-x)**2).mean()','meaning':'Raw reconstruction values every feature according to scale and frequency.','watch':'Normalize or weight features, or choose a different target.'},
],
'code_explanation':'To build a JEPA-like toy, create context and target encoders, mask future portions, stop gradients through the target branch, and predict the target embedding.',
'trace':'''```text
context history ─► context encoder ─► predictor ─► predicted target embedding
future target ───► target encoder ───────────────► target embedding
                                                ↓
                                      latent-space loss
```

After training, freeze the encoder and probe whether latent state predicts physical variables and future events.''',
'break_it':'Train both context and target encoders with no asymmetry or variance checks until they output nearly constant vectors. Observe low latent loss and useless probes.',
'diagnose':'Track per-dimension variance, embedding covariance, nearest-neighbour diversity and probe accuracy. Low loss with collapsed variance is not successful representation learning.',
'repair':'Use an appropriate target/stop-gradient design, masking that prevents shortcuts, normalization, and diagnostic probes. Add rare-event retrieval tests so abstraction does not erase critical evidence.',
'choices':[
{'option':'Raw reconstruction','choose':'Exact observation generation or interpretable state recovery matters.','avoid':'Unpredictable detail dominates and decisions depend on abstract dynamics.'},
{'option':'Predictive latent loss','choose':'Future-relevant representation is the main goal.','avoid':'You cannot validate what information the latent discarded.'},
{'option':'Frozen pretrained encoder','choose':'Source and target semantics align and data are limited.','avoid':'The representation lacks essential F1 variables.'},
{'option':'Full fine-tuning','choose':'You have sufficient data/compute and major domain adaptation is needed.','avoid':'Small data risks catastrophic overfitting or a small scratch model is already competitive.'},
],
'decision':'APEX V1 trains small models from scratch because the canonical telemetry state is compact and no assumed checkpoint perfectly matches its action/context semantics. The curriculum nevertheless prepares an adapter/probe-first fine-tuning experiment for future larger datasets.',
'apex':'Add a latent probe suite to GRU, SSM and RSSM hidden states. If using a pretrained sequence encoder, freeze it first, train the same prediction head, and compare data efficiency and horizon curves.',
'paths':'labs/15_autoencoder/solution.py\napex_engine/src/apexsim/models/\napex_engine/src/apexsim/evaluation.py\nresearch_reading/',
'research':'I-JEPA predicts representations of target image regions from context rather than reconstructing pixels. LeWorldModel explores latent world modelling and planning efficiency. Transfer their design principles only after mapping observation, action, target and evaluation semantics to the F1 domain.',
'questions':['Why can latent loss be low under representation collapse?','What should a linear probe tell you?','What is the safest first fine-tuning experiment?'],
'solutions':['If both target and prediction are nearly constant, they match without containing information.','Whether a simple readout can recover a specified physical or predictive variable, revealing what information is accessible in the representation.','Freeze the pretrained backbone, train a small task head under the same split, and compare with simple baselines before unfreezing parameters.'],
'challenge':'Build a future-latent predictor on synthetic telemetry. Evaluate reconstruction, future-state probes, rare-event retrieval and rollout value. Write a decision record comparing it with an RSSM objective.'
})

CHAPTERS.append({
'title':'17. Evaluation, Ablation and Out-of-Distribution Testing',
'figure':'17_evaluation.png',
'objective':'Build an evaluation matrix that reveals where a world model works, why it works, and when it should refuse to be trusted.',
'problem':'''A single average MAE can hide catastrophic braking failures, worsening long-horizon error, impossible speeds, or performance limited to one track. A simulation engine needs evidence across horizons, features, conditions and interventions.''',
'prediction':'''Model A has lower average speed MAE than Model B, but A predicts negative speed in 2% of wet-braking rollouts while B never does. Which model is better? State the missing operational information required to decide.''',
'intuition':'''Evaluation begins with the decision. If a race engineer uses the simulator to compare a six-second throttle scenario, horizon-six causal sensitivity and physical validity matter more than one-step average fit. Metrics are measurements of requirements, not a scoreboard detached from use.

Ablation removes or changes one information source while holding other factors fixed. It answers causal questions about the implementation: Does weather context help? Does VH-like second channel—here, perhaps curvature or tyre age—matter? Randomly changing many settings answers nothing cleanly.

Out-of-distribution tests define shifts deliberately: unseen track, heavier rain, longer tyre age, unusual controls, different sample rate. Failure under OOD is expected; the goal is to detect and quantify it, then decide whether to abstain, retrain or constrain use.''',
'concepts':[
{'name':'Horizon metric','meaning':'Error measured separately at each future step.','apex':'Defines useful simulation duration.'},
{'name':'Guardrail metric','meaning':'A metric that must remain within a safety/validity limit even if primary error improves.','apex':'Negative speed, progress bounds and control sensitivity.'},
{'name':'Ablation','meaning':'A controlled removal or replacement testing one hypothesis.','apex':'State-only, no weather, no geometry, model-family comparisons.'},
{'name':'OOD test','meaning':'Evaluation under a deliberately shifted distribution.','apex':'Unseen circuits, weather or control regimes.'},
],
'worked':'''Suppose Model A and B have:

| Metric | A | B |
|---|---:|---:|
| 1-step MAE | 0.4 | 0.5 |
| 20-step MAE | 8.0 | 5.0 |
| Negative-speed rate | 2% | 0% |
| Scenario latency | 30 ms | 12 ms |

If the UI serves 20-step scenarios, B is stronger despite worse one-step fit. If only one-step filtering is needed, A may be acceptable if violations are constrained. The “best model” is a vector of requirement tradeoffs plus thresholds, not one scalar.''',
'lab':'09_loss_comparison',
'build':'Compare loss functions on controlled predictions, then connect optimization loss to evaluation metrics. The loss trains parameters; the metric judges the product and need not be identical.',
'line_notes':[
{'code':'mse = ...','meaning':'Penalize squared residuals, emphasizing large errors.','watch':'Sensitive to scale and outliers.'},
{'code':'mae = ...','meaning':'Measure average absolute physical error.','watch':'More robust but less smooth at zero.'},
{'code':'compare losses','meaning':'Reveal how optimization priorities differ on the same predictions.','watch':'Do not select by training loss alone.'},
],
'code_explanation':'A model optimized with one loss can be evaluated with many operational metrics, including hard validity checks that are not differentiable.',
'trace':'''```text
run artifact
  ├─ overall metrics
  ├─ horizon curves
  ├─ per-feature errors
  ├─ subgroup tables
  ├─ physical violations
  ├─ intervention sensitivity
  └─ baseline-relative improvement
```

Every plot should include sample count and split identity.''',
'break_it':'Average all horizons and all conditions into one MAE. Then remove weather from inputs but accidentally change random seed and training epochs too.',
'diagnose':'Ask whether compared runs share dataset hash, split, normalizer, seed set, budget and evaluation code. If multiple variables changed, the result is not an ablation.',
'repair':'Store experiment manifests and compare matched runs. Add confidence intervals across seeds/sessions where feasible. Make promotion gates explicit: primary metric, guardrails, latency and artifact completeness.',
'choices':[
{'option':'MAE/RMSE','choose':'Continuous state error in interpretable units.','avoid':'They are the only evidence for a simulator.'},
{'option':'Horizon curves','choose':'Autoregressive use or planning matters.','avoid':'Never; at least inspect them for rollouts.'},
{'option':'Physical penalties','choose':'Known invalid regions can be expressed and monitored.','avoid':'They replace empirical outcome evaluation.'},
{'option':'Human scenario review','choose':'Qualitative causal behaviour and UI trust matter.','avoid':'It substitutes for reproducible quantitative tests.'},
],
'decision':'APEX reports baseline-relative error by horizon, per-feature metrics, physical violations, scenario sensitivity and run metadata. Model promotion is a documented decision, not automatic best-MAE selection.',
'apex':'Run the GRU, SSM and RSSM references. Build one comparison report with matched data and budgets, then explain why the simplest winning model remains primary.',
'paths':'apex_engine/src/apexsim/evaluation.py\napex_engine/src/apexsim/pipeline/stages.py\napex_engine/artifacts/runs/\nfield_workbook/',
'research':'World-model papers choose benchmarks and metrics that reflect their claims. When adapting a paper to F1, reproduce the mechanism but redefine evaluation around telemetry dynamics, interventions, uncertainty and deployment conditions.',
'questions':['What makes an experiment a true ablation?','Why should error be normalized as well as reported in physical units?','What is an abstention policy?'],
'solutions':['One targeted component changes while data, split, budget, evaluation and other variables remain fixed.','Physical units are interpretable; normalized error helps compare features with different scales. Both are useful.','A rule that withholds or flags predictions when evidence is outside trusted conditions or uncertainty/violations exceed thresholds.'],
'challenge':'Design a complete APEX evaluation matrix across three horizons, three tracks, wet/dry conditions and five metrics. Define promotion and abstention criteria before seeing results.'
})

CHAPTERS.append({
'title':'18. Planning With MPC and the Cross-Entropy Method',
'figure':'18_cem.png',
'objective':'Use a world model to compare action sequences, understand CEM search, and learn why planners exploit model and reward defects.',
'problem':'''Prediction answers “what happens if we do this?” Planning asks “what should we do?” A planner proposes action sequences, imagines outcomes through the world model, scores them, and improves its proposal. This creates a powerful adversary: it actively searches for unrealistic trajectories that maximize the score.''',
'prediction':'''A reward gives +1 for speed and no penalty for leaving the track or braking instability. What action sequence will a planner prefer? Why is this not primarily a planner bug?''',
'intuition':'''Model predictive control repeatedly plans over a finite horizon, executes only the first action, observes the new state, and replans. This feedback limits drift compared with committing to a long open-loop sequence.

The cross-entropy method maintains a distribution over action sequences. It samples candidates, rolls them through the model, keeps an elite fraction, and refits mean/variance toward those elites. Repetition concentrates search around high-scoring actions.

Planner quality is bounded by world-model validity and reward completeness. Optimization pressure finds loopholes humans do not notice in average evaluation. Therefore planning tests should include adversarial actions, uncertainty penalties, constraints and real-environment verification before control is trusted.''',
'concepts':[
{'name':'Model predictive control','meaning':'Plan over a horizon, execute a short prefix, observe, and replan.','apex':'Future scenario/strategy layer after dynamics validation.'},
{'name':'CEM','meaning':'Sampling optimizer that iteratively refits an action distribution to elite candidates.','apex':'Simple derivative-free planner through imagined telemetry.'},
{'name':'Reward model','meaning':'Function scoring predicted trajectories for the decision objective.','apex':'Could combine progress, stability, tyre use and constraint penalties.'},
{'name':'Model exploitation','meaning':'Planner finds actions that score well because the learned model is wrong.','apex':'A major risk under unusual controls.'},
],
'worked':'''Suppose CEM samples 500 six-step throttle sequences. It scores final-speed error to a target plus smoothness. It keeps 50 elites (top 10%). New mean and standard deviation are the elite sample statistics.

If initial mean is 0.5 and standard deviation 0.3, one iteration may shift the early-step means toward 0.8 where acceleration helps. After several iterations variance shrinks. Too-rapid variance collapse can trap search; a minimum standard deviation preserves exploration.

MPC then applies only the first action, receives new evidence and replans. The remaining five actions are proposals, not a fixed command commitment.''',
'lab':'18_cem_planning',
'build':'Run CEM against a tiny differentiable-free speed simulator. Watch mean action sequence and best score improve over five iterations.',
'line_notes':[
{'code':'actions=np.clip(rng.normal(mean,std,(500,horizon)),0,1)','meaning':'Sample bounded candidate action sequences from the current proposal.','watch':'Clipping changes the distribution near limits.'},
{'code':'score=...','meaning':'Evaluate imagined outcome and smoothness under the toy world model.','watch':'Every omitted constraint becomes a possible exploit.'},
{'code':'elite=actions[np.argsort(score)[-50:]]','meaning':'Select the highest-scoring candidate sequences.','watch':'Elite fraction controls search pressure.'},
{'code':'mean,std=elite.mean(0),elite.std(0)+1e-3','meaning':'Refit proposal distribution and preserve minimum exploration.','watch':'Monitor premature variance collapse.'},
],
'code_explanation':'CEM does not need gradients through the simulator, making it useful with complex or stochastic rollouts, but it may require many model evaluations.',
'trace':'''```text
proposal distribution over action sequences
      ↓ sample N candidates
world model rollout for each candidate
      ↓ reward + constraints
select top K elites
      ↓ fit new mean/std
repeat → execute first action → observe → replan
```

Log the best candidate, elite diversity, uncertainty and physical violations each iteration.''',
'break_it':'Remove the smoothness term and allow throttle beyond one. Add a model region where extreme throttle incorrectly increases speed without penalty. Watch CEM discover it.',
'diagnose':'Replay planned trajectories under a trusted simulator or held-out real transitions. Compare planner actions with the training action distribution. Large OOD actions and low predicted uncertainty are red flags.',
'repair':'Enforce hard action bounds, add physically justified constraints, penalize uncertainty/OOD distance, and use receding-horizon verification. Create adversarial planner tests as part of model evaluation.',
'choices':[
{'option':'Grid search','choose':'Action space and horizon are tiny.','avoid':'Combinatorial sequences.'},
{'option':'CEM','choose':'Continuous bounded actions, no gradients required and batch rollout is cheap.','avoid':'Model evaluations are extremely expensive or multi-modal search collapses.'},
{'option':'Gradient planning','choose':'World model/reward are differentiable and smooth.','avoid':'Discrete actions, poor local optima or unstable gradients.'},
{'option':'Actor network','choose':'Fast repeated decisions justify amortizing planning through policy learning.','avoid':'World model/reward is not validated or policy can exploit it unseen.'},
],
'decision':'APEX V1 exposes manual counterfactual controls and includes a latent MPC project, but does not claim autonomous race control. Planning becomes a later stage after dynamics and reward validation.',
'apex':'Connect CEM to the scenario rollout interface using bounded throttle/brake actions. Evaluate planned sequences against the synthetic ground-truth environment before any live integration.',
'paths':'labs/18_cem_planning/solution.py\nprojects/09_latent_mpc/main.py\napex_engine/src/apexsim/simulation.py\ndebugging_cases/12_planner_exploitation',
'research':'Dreamer replaces repeated online search with an actor and critic trained from imagined trajectories, but the exploitation problem remains. Better optimization can make model defects more dangerous, not less.',
'questions':['Why does MPC execute only the first planned action?','What does elite variance tell you?','How can uncertainty be used in planning?'],
'solutions':['New observations correct model drift and changing conditions before the next action.','How concentrated high-scoring candidates are; rapid collapse can indicate convergence or premature loss of exploration.','Penalize uncertain trajectories, constrain planning to trusted regions, or trigger abstention/human review.'],
'challenge':'Add braking and curvature constraints to the CEM lab. Create a hidden model defect, show the planner exploit it, then design an evaluation that catches the exploit before deployment.'
})

CHAPTERS.append({
'title':'19. Production Pipelines, Airflow, Registry and Monitoring',
'figure':'19_pipeline.png',
'objective':'Refactor experimental code into idempotent stages with observable lineage, then understand when orchestration becomes necessary.',
'problem':'''A notebook can ingest, train and plot once. A production system must retry failed downloads, validate versions, reproduce models, backfill sessions, avoid overwriting artifacts, and tell operators which stage failed. Orchestration should coordinate trustworthy functions, not rescue tangled code.''',
'prediction':'''A pipeline fails after training but before publication. On retry, should it retrain from scratch, reuse the checkpoint, or overwrite the run directory? What information is needed to choose safely?''',
'intuition':'''A stage has explicit inputs, outputs, configuration, failure modes and idempotency policy. Ingestion writes canonical data; validation writes a report; training writes a checkpoint; evaluation writes metrics; publication writes UI/API products. Each artifact is immutable within a run and linked by identifiers/hashes.

Airflow schedules and tracks task dependencies, retries and backfills. Business logic should remain in ordinary tested Python functions so the same stage runs locally, in tests and under orchestration. Passing large arrays through orchestration metadata is a smell; pass durable artifact references.

A registry records runs, configurations, dataset versions, metrics and status. Monitoring then covers pipeline health, data drift, model behaviour and product delivery. Logging without stable run IDs and structured fields is not lineage.''',
'concepts':[
{'name':'Idempotency','meaning':'Repeating a stage with the same inputs yields the same result or safely reuses it.','apex':'Enables retries and backfills.'},
{'name':'Artifact lineage','meaning':'Trace which data, code and configuration produced an output.','apex':'Every UI prediction links to model run and dataset.'},
{'name':'Orchestrator','meaning':'Coordinates when stages run and how failures/retries are managed.','apex':'Airflow DAG wraps tested stage functions.'},
{'name':'Registry','meaning':'Queryable record of runs, statuses, metrics and artifact locations.','apex':'SQLite V1, expandable to a service/database.'},
],
'worked':'''Assume training checkpoint hash `abc123` exists and evaluation failed because disk was temporarily full.

A safe retry checks:

1. Same run ID and immutable configuration hash.
2. Same dataset/normalizer hashes.
3. Checkpoint exists, is complete and matches metadata.
4. Training stage status is succeeded.
5. Evaluation output is absent or marked failed.

Then retry evaluation only. If configuration changed, create a new run rather than silently reusing the checkpoint. If checkpoint integrity is uncertain, retrain in a new or repaired stage path.''',
'lab':'20_pipeline_contract',
'build':'Use the miniature stage artifact writer to learn explicit stage boundaries, then trace the production APEX runner and Airflow DAG that call the same business functions.',
'line_notes':[
{'code':'run.mkdir(parents=True,exist_ok=True)','meaning':'Create a stable run namespace for artifacts.','watch':'A production run directory should not mix different configuration hashes.'},
{'code':'path.write_text(json.dumps(...))','meaning':'Persist machine-readable stage evidence.','watch':'Use atomic temporary-file replacement for critical artifacts.'},
{'code':'stages=[...]','meaning':'Make dependencies visible and independently testable.','watch':'Do not create one giant “do everything” task.'},
],
'code_explanation':'The production runner adds status transitions, configuration, data/model artifacts, metrics and reports. Airflow should call these functions rather than duplicate them.',
'trace':'''```text
CLI / Airflow / test
        ↓
ordinary Python stage function
        ↓
durable artifact + metadata
        ↓
registry status transition
        ↓
next stage receives artifact path
```

A retry should start from the last valid durable boundary.''',
'break_it':'Write every run to `latest/`, pass a large tensor through Airflow XCom, and combine ingestion/training/publication in one task. Simulate a publication failure.',
'diagnose':'Look for overwritten evidence, ambiguous status and work that must repeat unnecessarily. The earliest failed design is usually the artifact/stage contract, not the scheduler.',
'repair':'Use immutable run IDs, atomic writes, explicit stage manifests and small task messages containing paths/IDs. Add pipeline tests that run twice and assert safe reuse or deterministic replacement.',
'choices':[
{'option':'Local Python runner','choose':'Development, CI and small reproducible workflows.','avoid':'Complex schedules, backfills and multi-worker operations.'},
{'option':'Airflow','choose':'Batch dependencies, retries, schedules and historical backfills matter.','avoid':'You need low-latency event streaming or have only one trivial script.'},
{'option':'Experiment tracker','choose':'Comparing many model runs and artifacts.','avoid':'You assume it replaces data/version contracts and orchestration.'},
{'option':'Model registry','choose':'Promotion, rollback and serving require a governed model identity.','avoid':'A notebook checkpoint with no deployment lifecycle.'},
],
'decision':'APEX implements a local runner as the source of truth, a thin Airflow DAG, a run registry and immutable run artifacts. The full Airflow service is an optional deployment layer, not required for learning core models.',
'apex':'Run the same configuration twice under different IDs. Compare manifests, then deliberately fail publication and resume from the last successful stage. Inspect API/UI links back to the run directory.',
'paths':'apex_engine/src/apexsim/pipeline/stages.py\napex_engine/src/apexsim/pipeline/runner.py\napex_engine/src/apexsim/registry.py\napex_engine/dags/apexsim_dag.py\ndebugging_cases/13_artifact_overwrite\ndebugging_cases/14_airflow_payload',
'research':'Reproducible world-model research depends on production habits: immutable datasets, exact split policies, seeds, configuration, checkpoints and evaluation code. Without them, architecture comparisons are anecdotes.',
'questions':['Why should Airflow tasks pass paths instead of arrays?','What makes a stage idempotent?','What four layers should monitoring cover?'],
'solutions':['Durable storage survives retries/workers, avoids metadata-size limits and preserves lineage.','Same logical inputs/config produce the same content or a safely detected reusable artifact without duplicating side effects.','Pipeline execution, input data/contract, model behaviour/drift and delivered product/API/UI health.'],
'challenge':'Create a two-run backfill that ingests two sessions, trains one model per session and publishes reports. Kill the process mid-run, restart it, and prove no successful work is corrupted or needlessly repeated.'
})

CHAPTERS.append({
'title':'20. Build Project APEX V1 End to End—and Then Outgrow It',
'figure':'20_apex.png',
'objective':'Assemble the complete system, run a verified world-model simulation, use the UI responsibly, and define the research path toward F1 25 and an original architecture.',
'problem':'''The final challenge is integration. Correct individual pieces can still form a wrong system: adapters may disagree with windows, normalizers may differ between training and UI, scenario controls may overwrite state, or a beautiful interface may present false precision. We now build one traceable path from evidence to an imagined future.''',
'prediction':'''Before running anything, list the artifacts that must exist for a UI scenario to be reproducible: data, split, normalizer, model, evaluation, scenario inputs and software identity. Which of these should the UI be allowed to modify?''',
'intuition':'''APEX V1 is a historical telemetry world-simulation engine. It does not claim complete car physics or autonomous strategy. It answers a narrower, testable question: given recent canonical telemetry and an explicit sequence of future controls/context, can a learned transition model generate plausible short-horizon future state?

The system begins with synthetic data so every causal rule is inspectable and offline tests always run. It accepts FastF1/OpenF1 canonical data when available. A deterministic GRU is primary; an SSM-style model and RSSM are challengers. Evaluation determines the trusted horizon. The scenario engine modifies only designated future controls/context. The UI displays recorded and imagined trajectories with model/run identity and limitations.

The next stages are research, not feature accumulation: improve state observability, calibrate uncertainty, add track/generalization splits, ingest F1 25 UDP, learn richer latent dynamics, and validate planning. An original architecture should be proposed only after a measured failure cannot be fixed by data, objective or simpler model choices.''',
'concepts':[
{'name':'Scenario contract','meaning':'Exactly which future controls/context may be changed and how.','apex':'Throttle, brake, rain/grip and tyre assumptions under bounded transformations.'},
{'name':'Trusted horizon','meaning':'Maximum forecast duration meeting error and guardrail criteria.','apex':'Displayed with every scenario rather than claiming unlimited simulation.'},
{'name':'Product provenance','meaning':'User-visible link from prediction to run/model/data/config.','apex':'Prevents anonymous, irreproducible UI output.'},
{'name':'Research hypothesis','meaning':'A falsifiable explanation for a measured failure and proposed change.','apex':'The basis for new world-model architecture work.'},
],
'worked':'''A UI scenario uses history length 32 at 5 Hz (6.4 seconds) and predicts 8 frames (1.6 seconds). Suppose speed MAE by horizon is `[1.0,1.3,1.8,2.5,3.4,4.6,6.2,8.5] km/h`, with a guardrail of MAE ≤5 km/h and zero physical violations. The trusted horizon is step 6, or 1.2 seconds, even though the model emits 1.6 seconds.

This is not failure. The system should shade or label steps 7–8 as exploratory, refuse high-stakes conclusions, and direct research toward the compounding error observed after step 6.''',
'lab':'20_pipeline_contract',
'build':'Run the production APEX fast configuration, inspect every artifact, launch the UI, modify one scenario control, and trace the resulting prediction back through normalizer, model and run metadata.',
'line_notes':[
{'code':'apexsim run --config configs/fast.yaml --run-id ...','meaning':'Execute the complete source-independent pipeline.','watch':'Use a new immutable run ID and inspect stage logs.'},
{'code':'apexsim ui --run-dir ...','meaning':'Launch the race-engineering interface from verified artifacts.','watch':'The UI must load the same normalizer/model/config used in evaluation.'},
{'code':'apexsim run-canonical --input-path ...','meaning':'Feed adapter-produced canonical data through the identical pipeline.','watch':'Validate source and split semantics before comparing runs.'},
],
'code_explanation':'The commands are entry points; the source companion traces each call into configuration, stages, models, evaluation, simulation, registry and UI.',
'trace':'''```text
FastF1 / OpenF1 / synthetic / future UDP
           ↓ canonical contract + quality report
session split → windows → train-only normalizer
           ↓
GRU / SSM / RSSM checkpoint
           ↓ matched evaluation + trusted horizon
scenario controls → autoregressive rollout
           ↓
artifact bundle → registry → API/UI
```

For one UI point, record: source frame indices, normalized input, scenario transform, model output, inverse transform, plotted value and run ID.''',
'break_it':'Load a checkpoint with the wrong normalizer, let the UI modify future target speed directly, hide the model identity, or display more decimal precision than validation supports.',
'diagnose':'Reproduce the scenario outside the UI using the same artifact paths. Compare canonical input, normalized tensor and raw model output. If CLI and UI differ, the serving boundary is broken; if both fail, move earlier.',
'repair':'Bundle model, normalizer, feature order and config; validate hashes on load. Make scenario fields allow-listed. Display uncertainty/trusted horizon and provenance. Add end-to-end tests comparing UI callback output with direct simulation.',
'choices':[
{'option':'Gradio UI','choose':'Rapid educational interactive scenarios with Python integration.','avoid':'You require a highly customized production frontend at scale.'},
{'option':'FastAPI + web frontend','choose':'Stable service contracts, multiple clients and custom UX.','avoid':'The API/model contract is still changing daily.'},
{'option':'Synthetic-first','choose':'Offline causality, testing and controlled failure injection.','avoid':'You confuse synthetic accuracy with real F1 fidelity.'},
{'option':'F1 25 UDP migration','choose':'Game packets are available and canonical mapping/latency tests are ready.','avoid':'You let packet-specific fields leak through the entire core architecture.'},
],
'decision':'The delivered V1 is a complete learning and research platform, not the final Dreamer-for-F1 system. Its value is that every future architecture competes inside a tested data, rollout, evaluation and product framework.',
'apex':'Follow `START_HERE.md`, run tests, execute a fast reference, launch the UI, complete Projects 1–9, then rebuild one core module without reading the solution. Use the source companion only after your own attempt.',
'paths':'apex_engine/START_HERE.md\napex_engine/src/apexsim/\napex_engine/notebooks/\napex_engine/tests/\nprojects/10_project_apex/\nsource_code_companion/',
'research':'The path toward a Dreamer-like F1 system is staged: validated dynamics → probabilistic belief/calibration → reward/continuation model → planning under constraints → actor/critic imagination → F1 25 online data → cross-domain fine-tuning. Each arrow needs evidence.',
'questions':['Why must the UI use the training normalizer?','What should determine the displayed simulation horizon?','When is a new architecture justified?'],
'solutions':['The model learned parameters in that transformed feature space; a different transform changes the meaning of every input/output.','Matched held-out horizon error, physical guardrails, uncertainty and operational tolerance—not the configured output length.','When a specific measured failure survives data/contract fixes, objective improvements and simpler baselines, and the proposed mechanism directly targets that failure.'],
'challenge':'Rebuild APEX from an empty repository using only the canonical contract, acceptance tests and architecture diagram. Then propose one original model change with a falsifiable hypothesis, matched ablation and rollback condition.'
})
