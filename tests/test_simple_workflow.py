"""Acceptance tests for the reduced upload/preview/export interface."""
from io import BytesIO
import pandas as pd
import pytest
from openpyxl import load_workbook
from streamlit.testing.v1 import AppTest
from src.simple_workflow import inspect_uploads, append_sources, master_excel_bytes


def test_exact_headers_only_union_order_and_duplicate_retention():
    sources, errors = inspect_uploads([('a.csv', b'Name,Value\nAlice,10\nAlice,10'),
                                      ('b.csv', b'Customer,Value\nBob,20')])
    assert not errors
    master = append_sources(sources)
    assert list(master.columns) == ['Name', 'Value', 'Customer']
    assert len(master) == 3
    assert master['Value'].tolist() == ['10', '10', '20']
    assert pd.isna(master.iloc[0]['Customer'])
    assert pd.isna(master.iloc[2]['Name'])
    assert len(pd.read_csv(BytesIO(master.to_csv(index=False).encode()))) == 3
    output = master_excel_bytes(master)
    assert pd.ExcelFile(BytesIO(output)).sheet_names == ['Master']
    assert len(pd.read_excel(BytesIO(output))) == 3


def test_every_excel_worksheet_is_included():
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        pd.DataFrame({'Name': ['Alice', 'Bob']}).to_excel(writer, sheet_name='One', index=False)
        pd.DataFrame({'Name': ['Carol']}).to_excel(writer, sheet_name='Two', index=False)
    sources, errors = inspect_uploads([('a.xlsx', buffer.getvalue())])
    assert not errors
    assert [s.sheet for s in sources] == ['One', 'Two']
    assert append_sources(sources)['Name'].tolist() == ['Alice', 'Bob', 'Carol']


def test_file_errors_and_limits():
    _, errors = inspect_uploads([('a.csv', b'A,A\n1,2'), ('b.xlsx', b'broken'), ('c.txt', b'abc')])
    assert len(errors) == 3
    with pytest.raises(ValueError, match='10 files'):
        inspect_uploads([(f'{i}.csv', b'A\n1') for i in range(11)])
    _, errors = inspect_uploads([('a.csv', b'A\n1'), ('a.csv', b'A\n2')])
    assert len(errors) == 1 and 'Duplicate filename' in errors[0]


def test_excel_formula_text_and_capacity():
    book = load_workbook(BytesIO(master_excel_bytes(pd.DataFrame({'Name': ['=1+1']}))))
    assert book['Master']['A2'].value == '=1+1'
    assert book['Master']['A2'].data_type == 's'
    with pytest.raises(ValueError, match='CSV'):
        master_excel_bytes(pd.DataFrame(index=pd.RangeIndex(1_048_576)))


def test_minimal_empty_interface():
    from pathlib import Path
    app = AppTest.from_file(Path('app.py').resolve()).run()
    assert not app.exception
    assert app.radio[0].value == 'Upload'
    assert not app.session_state.selected_inputs
    assert [b.label for b in app.button] == ['Clear data']
    assert not app.multiselect and not app.selectbox
    app.radio[0].set_value('Data Mapping').run()
    assert not app.exception and not app.dataframe
    assert not app.text_input and not app.multiselect and not app.selectbox


def test_upload_preview_export_with_no_mapping_controls():
    script = '''
from unittest.mock import patch
from io import BytesIO
import runpy
a = BytesIO(b'Name,Value\\n' + b'Alice,10\\n' * 12); a.name = 'a.csv'
b = BytesIO(b'Customer,Value\\nBob,20'); b.name = 'b.csv'
with patch('streamlit.file_uploader', return_value=[a,b]):
    runpy.run_path('app.py', run_name='__main__')
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    assert not app.exception and not app.error
    app.radio[0].set_value('Data Mapping').run()
    assert not app.exception
    assert len(app.dataframe) == 3 and len(app.dataframe[-1].value) == 10
    assert list(app.dataframe[-1].value.columns) == ['Name', 'Value', 'Customer']
    assert [e.label for e in app.expander] == ['a.csv', 'b.csv', 'Match or drop columns']
    assert all(not e.proto.expanded for e in app.expander)
    assert list(app.dataframe[0].value.columns) == ['Name', 'Value']
    assert len(app.dataframe[1].value) == 1
    assert not app.text_input
    assert len(app.multiselect) == 2
    assert all(s.label == 'Keep this column name' for s in app.selectbox)
    app.radio[0].set_value('Export').run()
    assert not app.exception and not app.error
    assert app.selectbox[0].options == ['Excel (.xlsx)', 'CSV (.csv)']
    assert len(app.get('download_button')) == 1
    app.selectbox[0].set_value('CSV (.csv)').run()
    assert not app.exception and not app.error
    assert len(app.get('download_button')) == 1
    app.radio[0].set_value('Upload').run()
    assert len(app.session_state.selected_inputs) == 2


def test_duplicate_contents_are_flagged_without_silently_dropping():
    sources, errors = inspect_uploads([('a.csv', b'ID\n1'), ('copy.csv', b'ID\n1')])
    assert not sources and len(errors) == 1
    assert 'a.csv' in errors[0] and 'copy.csv' in errors[0]
    sources, errors = inspect_uploads([('A.csv', b'ID\n1'), ('a.csv', b'ID\n2')])
    assert not sources and 'Duplicate filename' in errors[0]
    sources, errors = inspect_uploads([('a.csv', b'ID\n1\n1'), ('b.csv', b'ID\n2')])
    assert not errors and len(append_sources(sources)) == 3


def test_duplicate_upload_blocks_preview_and_export_ui():
    script = '''
from unittest.mock import patch
from io import BytesIO
import runpy
a = BytesIO(b'ID\\n1'); a.name = 'a.csv'
b = BytesIO(b'ID\\n1'); b.name = 'copy.csv'
with patch('streamlit.file_uploader', return_value=[a,b]):
    runpy.run_path('app.py', run_name='__main__')
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    assert not app.exception
    assert any('Duplicate upload' in e.value for e in app.error)
    app.radio[0].set_value('Export').run()
    assert not app.exception and app.error
    assert not app.get('download_button')


def test_excel_sheet_previews_start_closed_above_output():
    script = '''
from unittest.mock import patch
from io import BytesIO
import pandas as pd
import runpy
data = BytesIO()
with pd.ExcelWriter(data, engine='openpyxl') as writer:
    pd.DataFrame({'ID': [1,2]}).to_excel(writer, sheet_name='One', index=False)
    pd.DataFrame({'ID': [3]}).to_excel(writer, sheet_name='Two', index=False)
data.name = 'book.xlsx'
with patch('streamlit.file_uploader', return_value=[data]):
    runpy.run_path('app.py', run_name='__main__')
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    app.radio[0].set_value('Data Mapping').run()
    assert not app.exception
    assert [e.label for e in app.expander] == ['book.xlsx', 'One', 'Two', 'Match or drop columns']
    assert all(not e.proto.expanded for e in app.expander)
    assert [len(d.value) for d in app.dataframe] == [2, 1, 3]


def test_clear_data_resets_uploader_and_all_derived_state():
    script = '''
from unittest.mock import patch
from io import BytesIO
import runpy
data = BytesIO(b'ID,Value\\n1,10'); data.name = 'test.csv'
with patch('streamlit.file_uploader', side_effect=lambda *a, **k: [data] if k.get('key') == 'datasets-0' else []):
    runpy.run_path('app.py', run_name='__main__')
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    assert len(app.session_state.selected_inputs) == 1
    app.radio[0].set_value('Data Mapping').run()
    next(m for m in app.multiselect if m.label == 'Columns to drop').set_value(['Value']).run()
    next(b for b in app.button if b.label == 'Drop column').click().run()
    assert app.session_state.column_changes
    app.radio[0].set_value('Upload').run()
    app.session_state.sheet_choices = {'old-file': ['Old Sheet']}
    next(b for b in app.button if b.label == 'Clear data').click().run()
    assert not app.exception and not app.error
    assert not app.session_state.selected_inputs
    assert not app.session_state.column_changes
    assert not app.session_state.sheet_choices
    assert app.session_state.upload_revision == 1
    assert 'input_signature' not in app.session_state
    assert app.radio[0].value == 'Upload'
    app.radio[0].set_value('Export').run()
    assert not app.get('download_button')
