"""Controlled multi-worksheet consolidation and UI acceptance tests."""
from io import BytesIO
import json
import pandas as pd
from streamlit.testing.v1 import AppTest
from src.engine import load, worksheets, default_config, consolidate, read_config


def workbook():
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Customer': ['Alice', 'Bob'], 'Total': [10, 20]}).to_excel(writer, sheet_name='January', index=False)
        pd.DataFrame({'Client': ['Carol'], 'Amount': [30]}).to_excel(writer, sheet_name='February', index=False)
    return buffer.getvalue()


def test_independent_sheet_mappings_provenance_and_template():
    content = workbook()
    sources = [load(content, 'reports.xlsx', sheet) for sheet in worksheets(content)]
    config = default_config()
    config.update(trace=True, columns=[{'name': 'Customer', 'type': 'Text', 'required': True},
                                      {'name': 'Total', 'type': 'Number', 'required': True}])
    config['mappings'] = {sources[0].key: {'Customer': 'Customer', 'Total': 'Total'},
                          sources[1].key: {'Client': 'Customer', 'Amount': 'Total'}}
    config['worksheets'] = {'reports.xlsx': ['January', 'February']}
    config['headers'] = {'reports.xlsx': {'January': None, 'February': None}}
    restored = read_config(json.dumps(config))
    master, issues, summary = consolidate(sources, restored, restored['mappings'])
    assert not summary['blocked'] and issues.empty
    assert master['Customer'].tolist() == ['Alice', 'Bob', 'Carol']
    assert master['Source Worksheet'].tolist() == ['January', 'January', 'February']
    assert master['Source Row'].tolist() == [2, 3, 2]
    assert summary['files'] == 1 and summary['datasets'] == 2
    assert [s['Rows included'] for s in summary['sources']] == [2, 1]
    _, issues, summary = consolidate(sources, restored, {sources[0].key: config['mappings'][sources[0].key]})
    assert summary['blocked']
    assert 'February' in issues['Worksheet'].tolist()


def test_more_than_ten_sheets_count_as_one_file():
    source = load(workbook(), 'reports.xlsx', 'January')
    sources = [type(source)(source.name, str(i), source.header, source.frame) for i in range(11)]
    config = default_config()
    config['columns'] = [{'name': 'Customer', 'type': 'Text', 'required': True}]
    mappings = {s.key: {'Customer': 'Customer', 'Total': '__IGNORE__'} for s in sources}
    master, _, summary = consolidate(sources, config, mappings)
    assert not summary['blocked'] and len(master) == 22
    assert summary['files'] == 1
