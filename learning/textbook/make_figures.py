from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Circle

OUT=Path(__file__).parent/'figures'; OUT.mkdir(exist_ok=True)
BG='#07111f'; PANEL='#10233b'; ACC='#48d6c7'; ACC2='#ffcc66'; TXT='#f5f7fb'; MUT='#a9b7c8'; RED='#ff6b6b'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})

def save(name):
    plt.savefig(OUT/name, dpi=180, bbox_inches='tight', facecolor=BG); plt.close()

def flow(name,title,items,sub=None):
    fig,ax=plt.subplots(figsize=(11,3.8),facecolor=BG); ax.set_facecolor(BG); ax.axis('off')
    xs=np.linspace(.08,.92,len(items))
    for i,(x,item) in enumerate(zip(xs,items)):
        box=FancyBboxPatch((x-.065,.42),.13,.25,boxstyle='round,pad=.02,rounding_size=.02',fc=PANEL,ec=ACC,lw=1.8)
        ax.add_patch(box); ax.text(x,.545,item,ha='center',va='center',color=TXT,weight='bold',wrap=True)
        if i<len(items)-1:
            ax.add_patch(FancyArrowPatch((x+.07,.545),(xs[i+1]-.07,.545),arrowstyle='-|>',mutation_scale=16,color=ACC2,lw=2))
    ax.text(.5,.88,title,ha='center',color=TXT,fontsize=18,weight='bold')
    if sub: ax.text(.5,.15,sub,ha='center',color=MUT,fontsize=11)
    save(name)

flow('01_simulation_loop.png','A simulator is a transition repeated in time',['Current state','Driver action','Transition rule','Next state','Repeat'],'The first world model can be a hand-written equation. Learning comes later.')
flow('02_state_action_context.png','Separate what the world is, what you do, and what you cannot control',['State','Action','Context','Next state'], 'Speed is state; throttle is action; rain is context.')
flow('03_physics_integrator.png','From forces to the next telemetry frame',['Engine force','Brake + drag','Acceleration','Velocity','Position'],'Units are part of the contract, not a cosmetic detail.')
flow('04_sampling.png','Continuous driving becomes discrete evidence',['Continuous world','Sensor timestamps','Alignment','Uniform grid','Model sequence'],'Every interpolation choice inserts an assumption.')
flow('05_contract.png','All sources must cross one canonical boundary',['FastF1','OpenF1','Adapter','Canonical frame','Validation'],'Models should not know which website supplied the telemetry.')
flow('06_windows.png','A training example is a carefully cut slice of time',['Session','History window','Future actions','Future target','Example'],'Split sessions before cutting windows to prevent leakage.')
flow('07_baseline.png','The baseline is a scientific control',['Features','Scale','Linear rule','Prediction','Residual'],'A neural model must beat this under the same split and horizon.')
flow('08_autograd.png','Training is repeated measurement and correction',['Forward pass','Loss','Backward pass','Gradients','Update'],'The optimizer changes parameters; backward only computes gradients.')
flow('09_rollout.png','One-step accuracy is not simulation quality',['History','Predict t+1','Feed prediction back','Predict t+2','Horizon error'],'Small errors alter the next input and can compound.')
flow('10_gru.png','A GRU learns what to retain and what to overwrite',['Input frame','Reset gate','Candidate memory','Update gate','New memory'],'The gates are soft values between zero and one.')
flow('11_ssm.png','A state-space model carries compact dynamical memory',['Input uₜ','State update','Hidden state xₜ','Readout','Output yₜ'],'Stability comes from controlling how hidden state propagates.')
flow('12_selective_ssm.png','Selection makes memory input dependent',['Telemetry token','Selective gate','Write / forget','Persistent state','Prediction'],'Different inputs can demand different memory timescales.')
flow('13_latent.png','Compress observations without discarding predictive structure',['Telemetry frame','Encoder','Latent z','Decoder','Reconstruction'],'Compression is useful only if the latent preserves what future prediction needs.')
flow('14_rssm.png','RSSM separates deterministic memory from stochastic uncertainty',['Previous latent','Action','Deterministic h','Prior / posterior z','Decoded state'],'Training uses posterior evidence; imagination must survive on the prior.')
flow('15_dreamer.png','Dreamer improves behaviour inside learned imagination',['World model','Imagine rollouts','Predict rewards','Actor / critic','Better actions'],'APEX first validates dynamics before trusting imagined control.')
flow('16_jepa.png','Predict representations, not every raw detail',['Context','Encoder','Predictor','Target representation','Latent loss'],'The target must contain useful future structure without trivial shortcuts.')
flow('17_evaluation.png','Evaluation is a matrix, not one number',['Horizons','Conditions','Metrics','Violations','Decisions'],'Report where the model fails, not only its average score.')
flow('18_cem.png','CEM searches action sequences through the model',['Sample actions','Imagine futures','Score','Keep elites','Refit distribution'],'A planner will exploit any unrealistic weakness in the model or reward.')
flow('19_pipeline.png','Production stages make failures local and recoverable',['Ingest','Validate','Train','Evaluate','Publish'],'Each stage should have explicit inputs, outputs, retries, and lineage.')
flow('20_apex.png','Project APEX V1: historical evidence to interactive imagined futures',['Data sources','Canonical contract','World model','Scenario engine','Race engineer UI'],'The UI is the last consumer of a verified system, not the first prototype.')

# Numeric trace figure
fig,ax=plt.subplots(figsize=(10,5),facecolor=BG); ax.set_facecolor(BG)
t=np.arange(8); throttle=np.array([0.2,.4,.7,1,1,.5,.1,0]); brake=np.array([0,0,0,0,0,.1,.6,1]); speed=[40]
for i in range(7): speed.append(speed[-1]+3*throttle[i]-5*brake[i]-.02*speed[-1])
ax.plot(t,speed,marker='o',label='speed'); ax.step(t,throttle*50,where='post',label='throttle × 50'); ax.step(t,brake*50,where='post',label='brake × 50');
ax.set_title('A tiny causal trace: actions change the next state',color=TXT,fontsize=17,weight='bold'); ax.set_xlabel('step',color=TXT); ax.tick_params(colors=MUT); ax.grid(alpha=.2); ax.legend();
for s in ax.spines.values(): s.set_color(MUT)
save('numeric_trace.png')
