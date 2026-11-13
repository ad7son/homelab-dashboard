"""健康規則是純函式：閒置為正常，無效讀值與首次取樣各自有明確狀態。"""
import pytest
from monitor_backend import module
rules = module('domain.health_rules')


@pytest.mark.parametrize('value,expected', [(0, 'healthy'), (100, 'healthy'), (-1, 'issues'), (101, 'issues'), (None, 'issues'), (float('nan'), 'issues'), (True, 'issues')])
def test_cpu_rule_validates_data_instead_of_load(value, expected):
    status, _ = rules.check_cpu({'usage_percent': value, 'physical_cores': 4, 'logical_cores': 8})
    assert status == expected


@pytest.mark.parametrize('age,expected', [(90_000, 'healthy'), (90_001, 'issues'), (-5001, 'issues'), (None, 'issues')])
def test_history_freshness_boundary(age, expected):
    data = {'sample_age_ms': age, 'latest_sample_at_ms': 1000, 'collector': None}
    assert rules.check_history_write(data)[0] == expected


def test_empty_history_query_is_success_independent_of_writer():
    assert rules.check_history_query({'samples': []})[0] == 'healthy'
