import json
from io import BytesIO
import pytest
from streamlit.testing.v1 import AppTest
from src.column_groups import assign_group
from src.engine import default_config, load, consolidate, read_config


def test_groups_combine_equivalent_fields_and_keep_others_separate():
    sources = [load(b'Customer,Customer ID\nAlice,100', 'a.csv'),
               load(b'Client,Client ID\nBob,200', 'b.csv')]
    config = assign_group(default_config(), [('a.csv', 'Customer'), ('b.csv', 'Client')], 'Customer Name')
    config = assign_group(config, [('a.csv', 'Customer ID')], 'Local ID')
    config = assign_group(config, [('b.csv', 'Client ID')], 'External ID')
    config = read_config(json.dumps(config))
    master, _, summary = consolidate(sources, config, config['mappings'])
    assert not summary['blocked'] and len(master) == 2
    assert master['Customer Name'].tolist() == ['Alice', 'Bob']
    assert list(master.columns) == ['Customer Name', 'Local ID', 'External ID']
    assert master['Local ID'].iloc[0] == '100'
    assert master['External ID'].iloc[1] == '200'
    assert config['approved'] == {}


@pytest.mark.parametrize('members,name', [([], 'Name'), ([('a', 'A')], ''), ([('a', 'A'), ('a', 'B')], 'Name')])
def test_invalid_groups_do_not_modify_configuration(members, name):
    config = default_config()
    with pytest.raises(ValueError):
        assign_group(config, members, name)
    assert config == default_config()


def test_group_conflict_and_explicit_reassignment():
    config = assign_group(default_config(), [('a', 'A')], 'Name')
    with pytest.raises(ValueError):
        assign_group(config, [('a', 'B')], 'Name')
    config = assign_group(config, [('a', 'A')], 'Separate')
    config = assign_group(config, [('a', 'B')], 'Name')
    assert config['mappings']['a'] == {'A': 'Separate', 'B': 'Name'}
