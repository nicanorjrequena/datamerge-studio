"""Minimal upload-to-export workflow with no configurable mappings."""
from io import BytesIO
from hashlib import sha256
import pandas as pd
from src.engine import Source, load, worksheets, validate_limits


def inspect_uploads(inputs: list[tuple[str, bytes]], selected_sheets: dict[str, list[str]] | None = None) -> tuple[list[Source], list[str]]:
    """Read files and selected Excel worksheets, reporting all failures."""
    validate_limits(len(inputs))
    names, contents, duplicates = {}, {}, []
    for name, content in inputs:
        normalized = name.casefold()
        digest = sha256(content).digest()
        if normalized in names:
            duplicates.append(f'Duplicate filename: {name} (already uploaded as {names[normalized]}). Filenames must be unique.')
        elif digest in contents:
            duplicates.append(f'Duplicate upload: {name} has identical file contents to {contents[digest]}. Remove one copy.')
        names.setdefault(normalized, name)
        contents.setdefault(digest, name)
    if duplicates:
        return [], duplicates
    sources, errors = [], []
    for name, content in inputs:
        try:
            if not name.lower().endswith(('.csv', '.xlsx')):
                raise ValueError('Only CSV and XLSX files are supported.')
            sheets = worksheets(content) if name.lower().endswith('.xlsx') else [None]
            if name.lower().endswith('.xlsx') and selected_sheets is not None and name in selected_sheets:
                requested = selected_sheets[name]
                if not requested:
                    raise ValueError('Select at least one worksheet or remove this file.')
                if any(sheet not in sheets for sheet in requested):
                    raise ValueError('A selected worksheet is missing from this workbook.')
                sheets = [sheet for sheet in sheets if sheet in requested]
            for sheet in sheets:
                try:
                    sources.append(load(content, name, sheet))
                except Exception as exc:
                    label = f'{name} / {sheet}' if sheet else name
                    errors.append(f'{label}: {exc}')
        except Exception as exc:
            errors.append(f'{name}: {exc}')
    return sources, errors


def append_sources(sources: list[Source]) -> pd.DataFrame:
    """Stack every record, matching only identical detected column names."""
    if not sources:
        raise ValueError('Upload at least one dataset.')
    master = pd.concat([s.frame for s in sources], ignore_index=True, sort=False)
    expected = sum(len(s.frame) for s in sources)
    if len(master) != expected:
        raise ValueError('Output row count does not match the input. Export stopped.')
    return master


def prepare_output(sources: list[Source], changes: list[dict]) -> pd.DataFrame:
    """Apply explicit column drops/matches without altering inputs or losing rows."""
    frames = [s.frame.copy(deep=False) for s in sources]
    for change in changes:
        columns = change.get('columns', [])
        current = list(dict.fromkeys(col for frame in frames for col in frame.columns))
        if not columns or len(columns) != len(set(columns)) or any(c not in current for c in columns):
            raise ValueError('Selected columns are no longer available. Undo the change and review again.')
        if change['kind'] == 'drop':
            if not set(current) - set(columns):
                raise ValueError('Keep at least one output column.')
            frames = [frame.drop(columns=columns, errors='ignore') for frame in frames]
        elif change['kind'] == 'merge':
            target = change.get('name')
            if len(columns) < 2 or target not in columns:
                raise ValueError('Choose at least two columns and retain one of their names.')
            for source, frame in zip(sources, frames):
                if sum(col in frame.columns for col in columns) > 1:
                    label = f'{source.name} / {source.sheet}' if source.sheet else source.name
                    raise ValueError(f'{label}: these columns coexist in the same dataset. Combining them could overwrite values; keep them separate.')
            frames = [frame.rename(columns={c: target for c in columns}) for frame in frames]
        else:
            raise ValueError('Unknown column action.')
    revised = [Source(s.name, s.sheet, s.header, frame, s.header_end) for s, frame in zip(sources, frames)]
    return append_sources(revised)


def master_excel_bytes(master: pd.DataFrame) -> bytes:
    """Export one Master worksheet with formula-like strings stored as text."""
    if len(master) > 1_048_575 or len(master.columns) > 16_384:
        raise ValueError('This dataset exceeds Excel worksheet capacity. Choose CSV instead.')
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        master.to_excel(writer, sheet_name='Master', index=False)
        for row in writer.sheets['Master']:
            for cell in row:
                if cell.data_type == 'f':
                    cell.data_type = 's'
    return buffer.getvalue()
