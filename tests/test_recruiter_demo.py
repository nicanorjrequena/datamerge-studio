"""A documented portfolio demonstration with known expected output."""
from io import StringIO
import pandas as pd
from src.simple_workflow import inspect_uploads, prepare_output


def test_recruiter_demo_expected_artifact():
    inputs = [
        ('north.csv', b'Order Number,Supplier,Part Number,Quantity,Internal Note\nPO-1001,Example Supply,PART-001,120,North\nPO-1002,Example Supply,PART-002,80,North\nPO-1003,Example Supply,PART-003,45,North'),
        ('south.csv', b'Purchase Order,Supplier,Part Number,Quantity,Internal Note\nPO-1004,Example Supply,PART-004,60,South\nPO-1005,Example Supply,PART-005,150,South')]
    sources, errors = inspect_uploads(inputs)
    assert len(sources) == 2 and not errors
    output = prepare_output(sources, [
        {'kind': 'merge', 'columns': ['Order Number', 'Purchase Order'], 'name': 'Order Number'},
        {'kind': 'drop', 'columns': ['Internal Note']}])
    expected = pd.read_csv(StringIO('Order Number,Supplier,Part Number,Quantity\nPO-1001,Example Supply,PART-001,120\nPO-1002,Example Supply,PART-002,80\nPO-1003,Example Supply,PART-003,45\nPO-1004,Example Supply,PART-004,60\nPO-1005,Example Supply,PART-005,150'), dtype=str)
    pd.testing.assert_frame_equal(output, expected)
    assert len(output) == 5 and output['Quantity'].astype(int).sum() == 455
