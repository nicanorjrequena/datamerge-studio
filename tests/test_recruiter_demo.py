"""A documented portfolio demonstration with known expected output."""
from pathlib import Path
import pandas as pd
from src.simple_workflow import inspect_uploads, prepare_output


def test_recruiter_demo_expected_artifact():
    root = Path(__file__).resolve().parents[1]
    inputs = [(p.name, p.read_bytes()) for p in sorted((root / 'data/recruiter_demo').glob('*.csv'))]
    sources, errors = inspect_uploads(inputs)
    assert len(sources) == 2 and not errors
    output = prepare_output(sources, [
        {'kind': 'merge', 'columns': ['Order Number', 'Purchase Order'], 'name': 'Order Number'},
        {'kind': 'drop', 'columns': ['Internal Note']}])
    expected = pd.read_csv(root / 'docs/examples/recruiter-master.csv', dtype=str)
    pd.testing.assert_frame_equal(output, expected)
    assert len(output) == 5 and output['Quantity'].astype(int).sum() == 455
