import tempfile

import pytest

from test.common_helper import TEST_FW

from ..code import cve_lookup
from ..internal.database.db_connection import DbConnection
from ..internal.database.db_setup import DbSetup
from ..internal.helper_functions import CveEntry

# Set the temp path for the DB
temp_dir = tempfile.TemporaryDirectory()
db_path = temp_dir.name

# Update the DB_PATH variable
cve_lookup.DB_PATH = f'{db_path}/test.db'

SOFTWARE_COMPONENTS_ANALYSIS_RESULT = {
    'result': {
        'software_components': [
            {'name': 'Dnsmasq', 'versions': ['2.40']},
            {
                'name': 'OpenSSL',
                'description': 'SSL library',
                'open_source': True,
                'versions': [],
                'website': 'https://www.openssl.org',
                'rule': 'OpenSSL',
                'matching_strings': [{'offset': 7194, 'identifier': '$a', 'string': 'T1BFTlNTTA=='}],
            },
        ],
    },
    'analysis_date': 1563453634.37708,
    'plugin_version': '0.3.2',
    'summary': ['OpenSSL ', 'Dnsmasq 2.40'],
    'system_version': '3.7.1_1560435912',
}

CVE_ENTRY1 = CveEntry(
    cve_id='CVE-2013-0198',
    summary='Dnsmasq before 2.66test2, when used with certain libvirt configurations, replies to queries from prohibited interfaces, which allows remote attackers to cause a denial of service (traffic amplification) via spoofed TCP based DNS queries. NOTE: this vulnerability exists because of an incomplete fix for CVE-2012-3411.',  # noqa: E501
    impact={'cvssMetricV2': 5.0},
    cpe_entries=[('cpe:2.3:a:thekelleys:dnsmasq:*:*:*:*:*:*:*:*', '', '', '2.65', '')],
)

CVE_ENTRY2 = CveEntry(
    cve_id='CVE-2017-14493',
    summary='Stack-based buffer overflow in dnsmasq before 2.78 allows remote attackers to cause a denial of service (crash) or execute arbitrary code via a crafted DHCPv6 request.',  # noqa: E501
    impact={'cvssMetricV2': 7.5, 'cvssMetricV30': 9.8},
    cpe_entries=[
        ('cpe:2.3:o:canonical:ubuntu_linux:14.04:*:*:*:lts:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:canonical:ubuntu_linux:16.04:*:*:*:lts:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:canonical:ubuntu_linux:17.04:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:debian:debian_linux:7.0:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:debian:debian_linux:7.1:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:debian:debian_linux:9.0:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:opensuse:leap:42.2:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:opensuse:leap:42.3:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:redhat:enterprise_linux_desktop:7.0:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:redhat:enterprise_linux_server:7.0:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:o:redhat:enterprise_linux_workstation:7.0:*:*:*:*:*:*:*', '', '', '', ''),
        ('cpe:2.3:a:thekelleys:dnsmasq:*:*:*:*:*:*:*:*', '', '', '2.77', ''),
    ],
)


@pytest.mark.AnalysisPluginTestConfig(plugin_class=cve_lookup.AnalysisPlugin)
class TestCveLookup:
    def test_process_object(self, analysis_plugin):
        connection_string = f'sqlite:///{db_path}/test.db'
        connection = DbConnection(connection_string)
        db_setup = DbSetup(connection)
        db_setup.add_cve_items([CVE_ENTRY1, CVE_ENTRY2])
        TEST_FW.processed_analysis['software_components'] = SOFTWARE_COMPONENTS_ANALYSIS_RESULT
        result = analysis_plugin.process_object(TEST_FW).processed_analysis['cve_lookup']
        assert 'Dnsmasq 2.40 (CRITICAL)' in result['summary']
        assert 'Dnsmasq 2.40' in result['cve_results']
        assert 'CVE-2013-0198' in result['cve_results']['Dnsmasq 2.40']

    @pytest.mark.parametrize(('cve_score', 'should_be_tagged'), [('9.9', True), ('5.5', False)])
    def test_add_tags(self, analysis_plugin, cve_score, should_be_tagged):
        TEST_FW.processed_analysis['cve_lookup'] = {}
        cve_results = {'component': {'cve_id': {'scores': {'V2': cve_score, 'V3.1': 'N/A'}}}}
        analysis_plugin.add_tags(cve_results, TEST_FW)
        if should_be_tagged:
            assert 'tags' in TEST_FW.processed_analysis['cve_lookup']
            tags = TEST_FW.processed_analysis['cve_lookup']['tags']
            assert 'CVE' in tags
            assert tags['CVE']['value'] == 'critical CVE'
        else:
            assert 'tags' not in TEST_FW.processed_analysis['cve_lookup']

    @pytest.mark.parametrize(
        ('cve_results_dict', 'expected_output'),
        [
            ({}, []),
            ({'component': {'cve_id': {'scores': {'V2': '6.4', 'V3.1': 'N/A'}}}}, ['component']),
            ({'component': {'cve_id': {'scores': {'V2': '9.4', 'V3.1': 'N/A'}}}}, ['component (CRITICAL)']),
            (
                {
                    'component': {
                        'cve_id': {'scores': {'V2': '1.1', 'V3.1': '9.9'}},
                        'cve_id2': {'scores': {'V2': '1.1', 'V3.1': '0.0'}},
                    }
                },
                ['component (CRITICAL)'],
            ),
        ],
    )
    def test_create_summary(self, cve_results_dict, expected_output, analysis_plugin):
        assert analysis_plugin._create_summary(cve_results_dict) == expected_output
