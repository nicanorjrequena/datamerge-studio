import json
from io import BytesIO
from pathlib import Path
import pandas as pd
import pytest
from src.engine import load, default_config, propose, consolidate, read_config, excel_bytes, validate_limits, preview_rows, Source


def example_config():
    """Explicit test-only choices; never used as application defaults."""
    config = default_config()
    config.update(name='Test port reports', trace=True, columns=[
        {'name': 'Vessel Name', 'type': 'Text', 'required': True},
        {'name': 'Port', 'type': 'Text', 'required': True},
        {'name': 'Arrival Date', 'type': 'Date', 'required': False},
        {'name': 'Cargo Weight', 'type': 'Number', 'required': False},
        {'name': 'Status', 'type': 'Text', 'required': False}],
        approved={'Vessel': 'Vessel Name', 'Ship Name': 'Vessel Name', 'ETA': 'Arrival Date', 'Tonnes': 'Cargo Weight'},
        rejected={'Vessel ID': ['Vessel Name']})
    return config


def test_header_and_actual_rows():
    source = load(b'\n A ,B\n1,2\n,\n3,4\n', 'a.csv')
    assert source.header == 2
    assert list(source.frame.columns) == ['A', 'B']
    assert list(source.frame.index) == [3, 5]


def test_csv_preserves_multiline_and_literal_na():
    source = load(b'A,B\n"line one\nline two",NA\n', 'a.csv')
    assert source.frame.iloc[0, 0] == 'line one\nline two'
    assert source.frame.iloc[0, 1] == 'NA'


@pytest.mark.parametrize('content', [b'A,A\n1,2', b'A,\n1,2'])
def test_invalid_headers(content):
    with pytest.raises(ValueError):
        load(content, 'a.csv')


def test_mapping_priority_and_rejection():
    config = example_config()
    assert propose('Vessel Name', config)[0] == 'Vessel Name'
    assert propose('Vessel', config)[0] == 'Vessel Name'
    assert propose('Vessel_Name', config)[0] is None
    assert 'Vessel Name' not in propose('Vessel ID', config)[1]
    config['rejected']['Vessel'] = ['Vessel Name']
    assert propose('Vessel', config)[0] is None


def demo():
    config = example_config()
    fixtures = [
        ('01_mobile.csv', b'Vessel Name,Port,Arrival Date,Cargo Weight,Status\nAtlantic Star,Mobile,2026-09-01,12500,Arrived\nOcean Pearl,Mobile,2026-09-02,8400,Arrived\nBlue Horizon,Mobile,2026-09-03,6200,Expected'),
        ('02_houston.csv', b'Vessel,Port,ETA,Tonnes,Status\nPacific Dawn,Houston,2026-09-04,9800,Arrived\nCoral Wind,Houston,check date,4500,Expected\nSilver Tide,Houston,2026-09-06,7100,Expected'),
        ('03_new_orleans.csv', b'Ship Name,Port,Arrival Date,Cargo Weight\nNorth Star,New Orleans,2026-09-07,11300\nRiver Queen,New Orleans,2026-09-08,5600\nRiver Queen,New Orleans,2026-09-08,5600')]
    sources = [load(content, name) for name, content in fixtures]
    mappings = {s.name: {h: propose(h, config)[0] for h in s.frame.columns} for s in sources}
    return sources, config, mappings


def test_demo_consolidation_and_reporting():
    sources, config, mappings = demo()
    master, issues, summary = consolidate(sources, config, mappings)
    assert summary['output_rows'] == summary['input_rows'] == 9
    assert not summary['blocked']
    assert list(master.columns[:5]) == [c['name'] for c in config['columns']]
    assert {'Invalid date', 'Missing column', 'Duplicate record'} <= set(issues['Issue type'])
    assert 'check date' in master['Arrival Date'].values
    assert len(issues[issues['Issue type'] == 'Duplicate record']) == 2
    assert len(pd.read_excel(BytesIO(excel_bytes(master, issues)))) == 9


@pytest.mark.parametrize('kind', ['unknown', 'collision', 'required', 'rejected', 'missing-stop'])
def test_blockers(kind):
    sources, config, mappings = demo()
    first = sources[0].name
    if kind == 'unknown': mappings[first]['Port'] = None
    if kind == 'collision': mappings[first]['Port'] = 'Vessel Name'
    if kind == 'required': mappings[first]['Port'] = '__IGNORE__'
    if kind == 'rejected': config['rejected']['Port'] = ['Port']
    if kind == 'missing-stop': config['missing'] = 'Stop'
    master, issues, summary = consolidate(sources, config, mappings)
    assert summary['blocked'] and master.empty
    assert 'Error' in issues['Severity'].values
    assert all(c['Rows included'] == 0 for c in summary['sources'])


def test_config_roundtrip():
    config = example_config()
    assert read_config(json.dumps(config)) == config
    config['columns'][1]['name'] = 'Vessel Name'
    with pytest.raises(ValueError): read_config(json.dumps(config))


def test_excel_manual_header():
    data = BytesIO()
    pd.DataFrame([['Report', None], ['A', 'B'], [1, 2]]).to_excel(data, index=False, header=False)
    source = load(data.getvalue(), 'report.xlsx', 'Sheet1', 1)
    assert len(source.frame) == 1 and source.header == 2


def test_invalid_number_and_required_value():
    source = load(b'Vessel Name,Port,Cargo Weight\nShip,Mobile,oops\n,Mobile,10', 'a.csv')
    config = example_config()
    mapping = {h: h for h in source.frame.columns}
    _, issues, summary = consolidate([source], config, {'a.csv': mapping})
    assert summary['blocked']
    assert {'Invalid number', 'Missing required value'} <= set(issues['Issue type'])




@pytest.mark.parametrize('files,records', [(0, 0), (10, 1_000_001), (1, 10_000_000)])
def test_limit_boundaries_allowed(files, records):
    validate_limits(files, records)


@pytest.mark.parametrize('files,records', [(11, 0), (11, 1_000_001), (12, 10_000_000)])
def test_limits_reject_without_truncating(files, records):
    with pytest.raises(ValueError):
        validate_limits(files, records)


def test_engine_accepts_over_one_million_records_and_enforces_file_limit():
    config = default_config()
    config['columns'] = [{'name': 'ID', 'type': 'Text', 'required': False}]
    frame = pd.DataFrame({'ID': range(500_001)})
    sources = [Source('a.csv', '', 1, frame), Source('b.csv', '', 1, pd.DataFrame({'ID': range(500_001, 1_000_002)}))]
    master, _, summary = consolidate(sources, config, {s.name: {'ID': 'ID'} for s in sources})
    assert not summary['blocked']
    assert len(master) == summary['input_rows'] == 1_000_002
    with pytest.raises(ValueError, match='10 files'):
        consolidate([Source(str(i), '', 1, pd.DataFrame()) for i in range(11)], config, {})


def test_preview_defaults_and_override():
    source = Source('a.csv', '', 1, pd.DataFrame({'ID': range(25)}))
    assert len(preview_rows(source)) == 10
    assert list(preview_rows(source, 3)['ID']) == [0, 1, 2]
    assert len(source.frame) == 25








def test_invalid_export_format():
    config = example_config()
    config['export_format'] = 'exe'
    with pytest.raises(ValueError, match='file type'):
        read_config(json.dumps(config))
