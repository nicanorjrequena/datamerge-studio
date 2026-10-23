"""Explicit user-defined groups of equivalent source fields."""
from copy import deepcopy
from src.engine import validate_config


def assign_group(config: dict, members: list[tuple[str, str]], output_name: str) -> dict:
    """Map selected dataset/header pairs to one output field, without coalescing cells."""
    target = output_name.strip()
    if not members:
        raise ValueError('Select at least one source column.')
    datasets = [dataset for dataset, _ in members]
    if len(datasets) != len(set(datasets)):
        raise ValueError('A group can contain only one column from each dataset. Keep other columns separate to avoid overwriting values.')
    candidate = deepcopy(config)
    if target not in [c['name'] for c in candidate['columns']]:
        candidate['columns'].append({'name': target, 'type': 'Text', 'required': False})
    validate_config(candidate)
    for dataset, header in members:
        mapping = candidate['mappings'].setdefault(dataset, {})
        if any(h != header and value == target for h, value in mapping.items()):
            raise ValueError('Another column in this dataset already belongs to that output field. Reassign it first.')
        mapping[header] = target
        # An explicit grouping decision supersedes an older rejection of that pair.
        candidate['rejected'][header] = [n for n in candidate['rejected'].get(header, []) if n != target]
    return candidate
