from pathlib import Path
import sys
ROOT=Path('/mnt/data/Project_APEX_Engineering_Apprenticeship')
sys.path.insert(0,str(ROOT/'textbook'))
from chapter_data import CHAPTERS
OUT=ROOT/'textbook'/'output'
parts=['''---
title: "Project APEX Tensor, Memory and Data-Flow Visual Atlas"
subtitle: "Twenty diagrams for tracing the complete simulation system"
author: "OpenAI"
date: "August 2026"
toc: true
---

# How to use a systems diagram

Do not look at a diagram and say “I get it.” Cover the right half. For each arrow, predict the data type, shape, unit, source and whether gradients can cross it. Then reveal the next block. A diagram becomes understanding when you can reconstruct the implementation and name the failure created by breaking one arrow.

For every atlas plate:

1. Read the blocks left to right.
2. Write the contract at each arrow.
3. Trace one numerical example.
4. Mark observed, supplied, learned and generated values.
5. Mark training-only and deployment-available information.
6. Identify one invariant and one failure probe.
7. Locate the corresponding APEX source path.
''']
for i,c in enumerate(CHAPTERS,1):
    concepts='\n'.join(f"- **{x['name']}:** {x['meaning']} In APEX: {x['apex']}" for x in c['concepts'])
    choices='\n'.join(f"- **{x['option']}:** choose when {x['choose'].lower()} Avoid when {x['avoid'].lower()}" for x in c['choices'][:3])
    parts.append(f'''# Plate {i}: {c['title']}

![{c['title']}](../figures/{c['figure']})

## What the picture is claiming

{c['objective']}

{c['intuition']}

## Label every block

{concepts}

## Walk one value through it

{c['worked']}

Now repeat the trace using one value from the packaged lab. Write its shape and unit before and after every transformation. If a block contains a learned model, distinguish its parameters from its temporary activation/state.

## What crosses each arrow?

Use this checklist:

- persistent state or temporary activation;
- observation, action, context, target or identifier;
- raw or normalized units;
- deterministic value or distribution parameters/sample;
- training-time evidence or deployment-time evidence;
- in-memory tensor or durable artifact reference.

## Break one arrow

{c['break_it']}

The first visible symptom may occur several blocks later. The debugging objective is to identify the earliest arrow whose actual contract differs from the diagram.

## Choosing a different route

{choices}

## APEX implementation map

```text
{c['paths']}
```

Open those files and redraw the diagram with exact function names and tensor shapes. Then add one missing production block—validation, logging, registry, monitoring or UI provenance—that the conceptual diagram intentionally omits.

## Explain it without vocabulary

Explain the plate to a five-year-old using objects moving through boxes. Then explain it to an engineer using contracts, shapes, units and failure modes. If both explanations are accurate, the idea is becoming durable.

''')
text='\n'.join(parts).replace('\t','\\t').replace('\x0c','\\f').replace('\x07','\\a')
path=OUT/'Project_APEX_Tensor_Memory_and_Data_Flow_Visual_Atlas.md'; path.write_text(text); print(path,len(path.read_text().split()))
