from decorator import contextmanager
from flask import Flask
from flask_restx import Api

from test.common_helper import create_test_file_object, create_test_firmware

from ..code.qemu_exec import PLUGIN_NAME
from ..routes import routes


class MockAnalysisEntry:
    def __init__(self, analysis_result=None):
        self.result = analysis_result or {}


class DbInterfaceMock:
    def __init__(self):
        self.fw = create_test_firmware()
        self.fw.uid = 'parent_uid'
        self.fw.processed_analysis[PLUGIN_NAME] = {
            'result': {
                'included_file_results': [
                    {'uid': 'foo', 'is_executable': False},
                    {
                        'uid': 'bar',
                        'is_executable': True,
                        'path': '/some/path',
                        'extended_results': [
                            {
                                'architecture': 'some-arch',
                                'error': None,
                                'parameter_results': [
                                    {
                                        'parameters': '-h',
                                        'stdout': 'stdout result',
                                        'stderr': 'stderr result',
                                        'return_code': '1337',
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        'uid': 'error-inside',
                        'is_executable': False,
                        'path': '/some/path',
                        'extended_results': [
                            {
                                'architecture': 'some-arch',
                                'error': 'some error',
                                'parameter_results': [],
                            },
                        ],
                    },
                ],
            }
        }

        self.fo = create_test_file_object()
        self.fo.uid = 'foo'
        self.fo.parents = ['parent_uid']

    def get_object(self, uid):
        if uid == 'parent_uid':
            return self.fw
        if uid in ['foo', 'bar', 'error-outside', 'error-inside']:
            return self.fo
        return None

    def get_analysis(self, uid, plugin):
        if uid == self.fo.uid:
            return self.fo.processed_analysis.get(plugin)
        if uid == self.fw.uid:
            return self.fw.processed_analysis[PLUGIN_NAME]
        return None

    def shutdown(self):
        pass

    @contextmanager
    def get_read_only_session(self):
        yield None


class TestQemuExecRoutesStatic:
    def test_get_results_for_included(self):
        result = routes.get_analysis_results_for_included_uid('foo', DbInterfaceMock())
        assert result is not None
        assert result != {}
        assert 'parent_uid' in result
        assert result['parent_uid']['is_executable'] is False

    def test_get_results_from_parent_fo(self):
        expected_result = {'uid': 'foo', 'is_executable': False}
        analysis = {'result': {'included_file_results': [expected_result]}}
        result = routes._get_results_from_parent_fo(analysis, 'foo')
        assert result == expected_result

    def test_no_results_from_parent(self):
        result = routes._get_results_from_parent_fo({'result': {'included_file_results': []}}, 'foo')
        assert result is None


class DbMock:
    frontend = DbInterfaceMock()


class TestQemuExecRoutes:
    def setup_method(self):
        app = Flask(__name__)
        app.config.from_object(__name__)
        app.config['TESTING'] = True
        app.jinja_env.filters['replace_uid_with_hid'] = lambda x: x
        self.plugin_routes = routes.PluginRoutes(app, db=DbMock, intercom=None, status=None)
        self.test_client = app.test_client()

    def test_not_executable(self):
        response = self.test_client.get('/plugins/qemu_exec/ajax/foo').data.decode()
        assert 'Results for this File' in response
        assert 'Executable in QEMU' in response
        assert '<td>False</td>' in response

    def test_executable(self):
        response = self.test_client.get('/plugins/qemu_exec/ajax/bar').data.decode()
        assert 'Results for this File' in response
        assert 'Executable in QEMU' in response
        assert '<td>True</td>' in response
        for item in ['some-arch', 'stdout result', 'stderr result', '1337', '/some/path']:
            assert item in response

    def test_error_inside(self):
        response = self.test_client.get('/plugins/qemu_exec/ajax/error-inside').data.decode()
        assert 'some-arch' in response
        assert 'some error' in response


class TestQemuExecRoutesRest:
    def setup_method(self):
        app = Flask(__name__)
        app.config.from_object(__name__)
        app.config['TESTING'] = True
        api = Api(app)
        endpoint, methods = routes.PluginRestRoutes.ENDPOINTS[0]
        api.add_resource(
            routes.PluginRestRoutes,
            endpoint,
            methods=methods,
            resource_class_kwargs={'db': DbMock},
        )
        self.test_client = app.test_client()

    def test_get_rest(self):
        result = self.test_client.get('/plugins/qemu_exec/rest/foo').json
        assert PLUGIN_NAME in result
        assert 'parent_uid' in result[PLUGIN_NAME]
        assert result[PLUGIN_NAME]['parent_uid']['is_executable'] is False

    def test_get_rest_no_result(self):
        result = self.test_client.get('/plugins/qemu_exec/rest/not_found').json
        assert PLUGIN_NAME in result
        assert result[PLUGIN_NAME] == {}
