from pathlib import Path
import subprocess, textwrap, json, shutil, re
from chapter_data import CHAPTERS

ROOT=Path(__file__).resolve().parent
CH=ROOT/'chapters'; OUT=ROOT/'output'; FIG=ROOT/'figures'
CH.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
LAB_ROOT=ROOT.parent/'labs'

HEADER='''---
title: "Project APEX Engineering Apprenticeship"
subtitle: "Hands-on world models, state-space models, F1 telemetry and production simulation engineering"
author: "OpenAI"
date: "August 2026"
lang: en-CA
toc: true
toc-depth: 3
numbersections: true
---

# How to use this apprenticeship

This is not a catalogue of topics. Every chapter begins with a failure or engineering need, makes you predict an outcome, builds the smallest working system, inspects its internal state, breaks it deliberately, repairs it with a regression test, compares alternatives, and then transfers the idea into Project APEX.

Use a split screen: the book on one side and the repository on the other. Type the code. Do not merely read it. Before every output, write down what you expect. When your expectation is wrong, that gap is the lesson.

## The teaching loop

**Problem → Prediction → Small build → Visible trace → Deliberate failure → Diagnosis → Repair → Comparison → APEX integration → Independent challenge**

## Repository map

- `labs/` contains small isolated experiments.
- `projects/01...09/` contains progressively larger builds.
- `apex_engine/` is the production-structured capstone.
- `debugging_cases/` contains failures that should be investigated before reading the explanation.
- `source_code_companion/` contains line-numbered explanations of the production source.
- `field_workbook/` is where you record predictions, experiment plans, and architecture decisions.

'''


def run_lab(lab):
    if not lab: return ''
    p=LAB_ROOT/lab/'solution.py'
    if not p.exists(): return f'Lab file not found: {p}'
    try:
        r=subprocess.run(['python',str(p)],cwd=str(p.parent),text=True,capture_output=True,timeout=40)
        return (r.stdout+r.stderr).strip()
    except Exception as e:
        return f'Execution unavailable: {e}'


def code_block(path):
    if not path: return ''
    p=LAB_ROOT/path/'solution.py'
    return p.read_text() if p.exists() else ''


def md_table(rows, headers):
    # Render as compact teaching cards rather than wide tables; this keeps
    # long code and explanations readable in A4/Letter DOCX output.
    out=[]
    for row in rows:
        vals=[str(x).replace('\n',' ') for x in row]
        out.append(f"**{headers[0]}: {vals[0]}**")
        for h,v in zip(headers[1:],vals[1:]):
            out.append(f"- **{h}:** {v}")
        out.append('')
    return '\n'.join(out)


def chapter_md(i,c):
    img=f"../figures/{c['figure']}"
    lab=c.get('lab')
    code=code_block(lab)
    output=run_lab(lab)
    concept_rows=[[x['name'],x['meaning'],x['apex']] for x in c['concepts']]
    choice_rows=[[x['option'],x['choose'],x['avoid']] for x in c['choices']]
    line_rows=[[x['code'],x['meaning'],x['watch']] for x in c.get('line_notes',[])]
    q='\n'.join([f"{n+1}. {x}" for n,x in enumerate(c['questions'])])
    sol='\n'.join([f"**{n+1}.** {x}" for n,x in enumerate(c['solutions'])])
    return f'''# {c['title']}

> **Instructor objective:** {c['objective']}

![{c['title']}]({img})

## The problem that earns this chapter

{c['problem']}

### Predict before reading

{c['prediction']}

Write your answer in the Field Workbook. A prediction is valuable even when it is wrong, because it exposes the mental model we need to repair.

## Build the intuition from the system outward

{c['intuition']}

## Vocabulary that now has a job

{md_table(concept_rows,['Concept','Meaning in plain language','Role inside APEX'])}

## Worked example: calculate it by hand

{c['worked']}

Do not skip the arithmetic. When a later tensor produces a surprising value, this hand calculation is the ground truth you can return to.

## Guided lab

**Lab folder:** `labs/{lab or 'see chapter'}`

### What we are about to build

{c['build']}

### Runnable implementation

```python
{code}
```

### Observed output from the packaged solution

```text
{output}
```

### Read the important lines like English

{md_table(line_rows,['Code','What the line is doing','What to inspect']) if line_rows else c['code_explanation']}

### State and tensor trace

{c['trace']}

The rule is simple: never accept a tensor merely because the code runs. Name every axis, check every unit, and connect every number to a physical or statistical meaning.

## Break it on purpose

{c['break_it']}

### Diagnose from the earliest failed contract

{c['diagnose']}

### Repair and lock the repair with a test

{c['repair']}

A fix without a regression test is only a temporary memory of the bug.

## Choosing between implementations

{md_table(choice_rows,['Implementation','Choose it when','Do not choose it when'])}

{c['decision']}

## Transfer the lesson into Project APEX

{c['apex']}

### Repository path to inspect

```text
{c['paths']}
```

## Connection to research

{c['research']}

## Check your understanding before continuing

{q}

## Solutions and reasoning

{sol}

## Independent build challenge

{c['challenge']}

Do this without copying the solution. Your goal is not identical code; your goal is an implementation whose assumptions you can explain and test.

---
'''

parts=[HEADER]
for i,c in enumerate(CHAPTERS,1):
    md=chapter_md(i,c)
    (CH/f'{i:02d}_{re.sub(r"[^a-z0-9]+","_",c["title"].lower()).strip("_")}.md').write_text(md)
    parts.append(md)

# Append project ladder and references
parts.append('''# Ten-project ladder

The small labs teach one idea in isolation. The projects force multiple ideas to coexist.

1. One-dimensional car integrator
2. Telemetry quality laboratory
3. Lap physics sandbox
4. Nonlinear transition model
5. Track segment encoder
6. GRU telemetry forecaster
7. Selective SSM memory laboratory
8. RSSM imagination laboratory
9. Latent MPC planner
10. Project APEX production F1 world-simulation engine

For every project, write an Architecture Decision Record before opening the supplied solution. Record the problem, options, evidence, decision, and revisit condition.

# Primary references

- Hafner et al., *Mastering Diverse Domains through World Models (DreamerV3)*, arXiv:2301.04104.
- Gu and Dao, *Mamba: Linear-Time Sequence Modeling with Selective State Spaces*, arXiv:2312.00752.
- Assran et al., *Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture*, arXiv:2301.08243.
- LeWorldModel authors, project paper and official implementation.
- FastF1 official documentation.
- OpenF1 official documentation.
- Electronic Arts, *F1 25 Data Output Specification*.
- PyTorch official documentation for Dataset, DataLoader, GRU, autograd and optimization.
''')
combined='\n'.join(parts)
# Repair Python escape control characters from LaTeX commands in chapter strings.
combined=combined.replace('\t','\\t').replace('\x0c','\\f').replace('\x07','\\a')
md_path=OUT/'Project_APEX_Engineering_Apprenticeship_Teaching_Core.md'
md_path.write_text(combined)
print(md_path)
