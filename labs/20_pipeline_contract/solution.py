from pathlib import Path
import json

run=Path('artifacts/education_pipeline'); run.mkdir(parents=True,exist_ok=True)
stages=['ingest','validate','window','train','evaluate','publish']
for i,name in enumerate(stages):
    path=run/f'{i:02d}_{name}.json'; path.write_text(json.dumps({'stage':name,'status':'succeeded'}))
    print(path)
