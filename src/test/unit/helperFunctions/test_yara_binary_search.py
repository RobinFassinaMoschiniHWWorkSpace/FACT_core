import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock
from unittest.mock import patch

import pytest

from helperFunctions import yara_binary_search
from test.common_helper import get_test_data_dir

TEST_FILE_1 = 'binary_search_test'
TEST_FILE_2 = 'binary_search_test_2'
TEST_FILE_3 = 'binary_search_test_3'
MATCH_DATA_KEYS = {'condition', 'match', 'offset'}


class MockCommonDbInterface:
    @staticmethod
    def get_all_files_in_fw(uid):
        if uid == 'single_firmware':
            return [TEST_FILE_2, TEST_FILE_3]
        return []


def mock_check_output(call, *_, shell=True, stderr=None, **__):  # noqa: ARG001
    raise CalledProcessError(1, call, b'', stderr)


@pytest.mark.backend_config_overwrite(
    {'firmware_file_storage_directory': str(get_test_data_dir() / TEST_FILE_1)},
)
class TestHelperFunctionsYaraBinarySearch(unittest.TestCase):
    @mock.patch('helperFunctions.yara_binary_search.DbInterfaceCommon', MockCommonDbInterface)
    def setUp(self):
        self.yara_rule = b'rule test_rule {strings: $a = "test1234" condition: $a}'
        self.yara_binary_scanner = yara_binary_search.YaraBinarySearchScanner()

    def test_get_binary_search_result(self):
        result = self.yara_binary_scanner.get_binary_search_result((self.yara_rule, None))
        assert TEST_FILE_1 in result
        assert 'test_rule' in result[TEST_FILE_1]
        match_data = result[TEST_FILE_1]['test_rule']
        assert len(match_data) == 1
        assert all(k in m for k in MATCH_DATA_KEYS for m in match_data)

    def test_get_binary_search_result_for_single_firmware(self):
        yara_rule = b'rule test_rule_2 {strings: $a = "TEST_STRING!" condition: $a}'
        result = self.yara_binary_scanner.get_binary_search_result((yara_rule, 'single_firmware'))
        assert TEST_FILE_2 in result
        assert 'test_rule_2' in result[TEST_FILE_2]
        match_data = result[TEST_FILE_2]['test_rule_2']
        assert len(match_data) == 1
        assert all(k in m for k in MATCH_DATA_KEYS for m in match_data)

        result = self.yara_binary_scanner.get_binary_search_result((yara_rule, 'foobar'))
        assert result == {}

    def test_get_binary_search_rule_error(self):
        result = self.yara_binary_scanner.get_binary_search_result((b'no valid rule', 'foobar'))
        assert isinstance(result, str)
        assert 'There seems to be an error in the rule file' in result

    @patch('helperFunctions.yara_binary_search.subprocess.run', side_effect=mock_check_output)
    def test_get_binary_search_yara_error(self, _):  # noqa: PT019
        result = self.yara_binary_scanner.get_binary_search_result((self.yara_rule, None))
        assert isinstance(result, str)
        assert 'Error when calling YARA' in result

    def test_parse_raw_result(self):
        raw_result = (
            'rule_1 /media/data/fact_fw_data/00/uid1\n'
            '0x123:$a: foo\n'
            '0x456:$a: bar\n'
            'rule_1 /media/data/fact_fw_data/99/uid2\n'
            '0x321:$b: test123\n'
            'rule_2 /media/data/fact_fw_data/00/uid1\n'
            '0x666:$c: deadbeef\n'
        )
        result = self.yara_binary_scanner._parse_raw_result(raw_result)
        assert result == {
            'uid1': {
                'rule_1': [
                    {'condition': '$a', 'match': 'foo', 'offset': '0x123'},
                    {'condition': '$a', 'match': 'bar', 'offset': '0x456'},
                ],
                'rule_2': [
                    {'condition': '$c', 'match': 'deadbeef', 'offset': '0x666'},
                ],
            },
            'uid2': {
                'rule_1': [
                    {'condition': '$b', 'match': 'test123', 'offset': '0x321'},
                ],
            },
        }

    def test_execute_yara_search(self):
        test_rule_path = get_test_data_dir() / 'yara_binary_search_test_rule'
        result = self.yara_binary_scanner._execute_yara_search(test_rule_path)
        assert 'test_rule' in result

    def test_execute_yara_search_for_single_file(self):
        test_rule_path = get_test_data_dir() / 'yara_binary_search_test_rule'
        result = self.yara_binary_scanner._execute_yara_search(
            test_rule_path,
            target_path=get_test_data_dir() / TEST_FILE_1 / TEST_FILE_1,
        )
        assert 'test_rule' in result

    def test_get_file_paths_of_files_included_in_fo(self):
        result = self.yara_binary_scanner._get_file_paths_of_files_included_in_fw('single_firmware')
        assert len(result) == 2
        assert Path(result[0]).name == TEST_FILE_2
        assert Path(result[1]).name == TEST_FILE_3
