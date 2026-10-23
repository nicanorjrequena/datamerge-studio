"""Acceptance coverage for the optional match/drop review workflow."""
from io import BytesIO
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.simple_workflow import inspect_uploads, prepare_output, master_excel_bytes


def sources():
    result, errors = inspect_uploads([('a.csv', b'Name,Value\nAlice,10\nAlice,10'),
                                     ('b.csv', b'Customer,Value\nBob,20')])
    assert not errors
    return result


def test_match_drop_and_output_values_without_source_mutation():
    original = sources()
    changes = [{'kind': 'merge', 'columns': ['Name', 'Customer'], 'name': 'Name'},
               {'kind': 'drop', 'columns': ['Value']}]
    output = prepare_output(original, changes)
    assert list(output.columns) == ['Name']
    assert output['Name'].tolist() == ['Alice', 'Alice', 'Bob']
    assert list(original[0].frame.columns) == ['Name', 'Value']
    assert list(original[1].frame.columns) == ['Customer', 'Value']
    assert prepare_output(original, changes[:1])['Value'].tolist() == ['10', '10', '20']
    assert list(prepare_output(original, []).columns) == ['Name', 'Value', 'Customer']
    assert pd.read_excel(BytesIO(master_excel_bytes(output)))['Name'].tolist() == ['Alice', 'Alice', 'Bob']
    assert pd.read_csv(BytesIO(output.to_csv(index=False).encode()))['Name'].tolist() == ['Alice', 'Alice', 'Bob']


def test_drop_all_fields_from_one_dataset_preserves_its_rows():
    original, _ = inspect_uploads([('a.csv', b'A\n1\n2'), ('b.csv', b'B\n3')])
    output = prepare_output(original, [{'kind': 'drop', 'columns': ['A']}])
    assert len(output) == 3
    assert output['B'].isna().tolist() == [True, True, False]


@pytest.mark.parametrize('change', [
    {'kind': 'drop', 'columns': ['Name', 'Customer', 'Value']},
    {'kind': 'drop', 'columns': ['Missing']},
    {'kind': 'merge', 'columns': ['Name', 'Value'], 'name': 'Name'},
    {'kind': 'merge', 'columns': ['Name', 'Customer'], 'name': 'Other'},
])
def test_unsafe_changes_block_without_modifying_sources(change):
    original = sources()
    with pytest.raises(ValueError):
        prepare_output(original, [change])
    assert prepare_output(original, []).shape == (3, 3)


def test_selected_sheets_and_empty_selection():
    content = BytesIO()
    with pd.ExcelWriter(content, engine='openpyxl') as writer:
        pd.DataFrame({'ID': [1]}).to_excel(writer, sheet_name='One', index=False)
        pd.DataFrame({'ID': [2, 3]}).to_excel(writer, sheet_name='Two', index=False)
    original, errors = inspect_uploads([('book.xlsx', content.getvalue())], {'book.xlsx': ['Two']})
    assert not errors
    assert [s.sheet for s in original] == ['Two']
    assert prepare_output(original, [])['ID'].tolist() == [2, 3]
    for selection in [[], ['Missing']]:
        _, errors = inspect_uploads([('book.xlsx', content.getvalue())], {'book.xlsx': selection})
        assert errors


def app_with_files():
    script = '''
from unittest.mock import patch
from io import BytesIO
import runpy
a = BytesIO(b'Name,Value\\nAlice,10\\nAlice,10'); a.name = 'a.csv'
b = BytesIO(b'Customer,Value\\nBob,20'); b.name = 'b.csv'
with patch('streamlit.file_uploader', return_value=[a,b]):
    runpy.run_path('app.py', run_name='__main__')
'''
    return AppTest.from_string(script, default_timeout=15).run()


def test_next_back_match_drop_undo_and_export():
    app = app_with_files()
    next(b for b in app.button if b.label == 'Next: Review data →').click().run()
    assert app.radio[0].value == 'Data Mapping'
    next(m for m in app.multiselect if m.label == 'Columns that mean the same thing').set_value(['Name', 'Customer']).run()
    next(b for b in app.button if b.label == 'Treat as the same column').click().run()
    assert not app.exception and not app.error, [e.value for e in app.error]
    assert app.dataframe[-1].value['Name'].tolist() == ['Alice', 'Alice', 'Bob']
    next(m for m in app.multiselect if m.label == 'Columns to drop').set_value(['Value']).run()
    next(b for b in app.button if b.label == 'Drop column').click().run()
    assert list(app.dataframe[-1].value.columns) == ['Name']
    assert any('3 input rows' in c.value and '3 output rows' in c.value for c in app.caption)
    next(b for b in app.button if b.label == 'Next: Export →').click().run()
    assert app.radio[0].value == 'Export' and not app.error
    assert len(app.get('download_button')) == 1
    next(b for b in app.button if b.label == '← Back to Data Mapping').click().run()
    assert list(app.dataframe[-1].value.columns) == ['Name']
    next(b for b in app.button if b.label == 'Undo last change').click().run()
    assert list(app.dataframe[-1].value.columns) == ['Name', 'Value']
    next(b for b in app.button if b.label == 'Undo last change').click().run()
    assert list(app.dataframe[-1].value.columns) == ['Name', 'Value', 'Customer']
    next(b for b in app.button if b.label == '← Back to Upload').click().run()
    assert app.radio[0].value == 'Upload' and len(app.session_state.selected_inputs) == 2


def test_ui_conflict_does_not_apply_change():
    app = app_with_files()
    app.radio[0].set_value('Data Mapping').run()
    next(m for m in app.multiselect if m.label == 'Columns that mean the same thing').set_value(['Name', 'Value']).run()
    next(b for b in app.button if b.label == 'Treat as the same column').click().run()
    assert any('overwrite' in e.value for e in app.error), [e.value for e in app.error]
    assert not app.session_state.column_changes
    assert list(app.dataframe[-1].value.columns) == ['Name', 'Value', 'Customer']


def test_worksheet_selection_ui_and_column_edit_reset():
    data = BytesIO()
    with pd.ExcelWriter(data, engine='openpyxl') as writer:
        pd.DataFrame({'ID': [1], 'Value': [10]}).to_excel(writer, sheet_name='One', index=False)
        pd.DataFrame({'ID': [2, 3], 'Value': [20, 30]}).to_excel(writer, sheet_name='Two', index=False)
    # Uploaded bytes stay fixed across reruns, like a real browser upload.
    script = f'''
from unittest.mock import patch
from io import BytesIO
import runpy
data = BytesIO({data.getvalue()!r})
data.name = 'book.xlsx'
with patch('streamlit.file_uploader', return_value=[data]):
    runpy.run_path('app.py', run_name='__main__')
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    assert app.multiselect[0].value == ['One', 'Two']
    app.multiselect[0].set_value(['Two']).run()
    next(b for b in app.button if b.label == 'Next: Review data →').click().run()
    assert app.dataframe[-1].value['ID'].tolist() == [2, 3]
    next(m for m in app.multiselect if m.label == 'Columns to drop').set_value(['Value']).run()
    next(b for b in app.button if b.label == 'Drop column').click().run()
    next(b for b in app.button if b.label == '← Back to Upload').click().run()
    assert app.multiselect[0].value == ['Two']
    app.multiselect[0].set_value(['One']).run()
    assert not app.session_state.column_changes
    next(b for b in app.button if b.label == 'Next: Review data →').click().run()
    assert app.dataframe[-1].value['ID'].tolist() == [1]
    assert list(app.dataframe[-1].value.columns) == ['ID', 'Value']
