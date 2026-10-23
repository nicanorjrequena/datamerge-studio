"""Run from the project root: python -m scripts.benchmark."""
import json
import platform
import time
import tracemalloc
from pathlib import Path
import pandas as pd
from src.engine import Source, consolidate, default_config

results = []
for size in [1000, 10000, 100000]:
    frame = pd.DataFrame({'Vessel Name': [f'Vessel {i}' for i in range(size)], 'Port': 'Mobile',
                          'Arrival Date': '2026-09-01', 'Cargo Weight': 1000, 'Status': 'Arrived'})
    sources = [Source(f'partition-{i}.csv', '', 1, part) for i, part in enumerate([frame.iloc[:size//2], frame.iloc[size//2:]])]
    mappings = {s.name: {c: c for c in frame.columns} for s in sources}
    tracemalloc.start()
    started = time.perf_counter()
    config = default_config()
    config['columns'] = [{'name': c, 'type': 'Text', 'required': False} for c in frame.columns]
    master, issues, summary = consolidate(sources, config, mappings)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert len(master) == size
    results.append({'files': 2, 'input_rows': size, 'output_rows': len(master), 'seconds': round(elapsed, 4),
                    'peak_traced_mb': round(peak / 1024**2, 2), 'exceptions': len(issues)})
output = {'python': platform.python_version(), 'platform': platform.platform(), 'scope': 'In-memory engine only; excludes file loading and downloads. Tracemalloc measures Python allocations, not total process memory.', 'results': results}
Path('docs/benchmarks.json').write_text(json.dumps(output, indent=2))
print(json.dumps(output, indent=2))
