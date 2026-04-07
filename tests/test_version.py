from importlib.metadata import version as installed_version

from mempalace import __version__
from mempalace.mcp_server import handle_request


def test_runtime_version_matches_package_metadata_and_mcp():
    response = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert installed_version("mempalace") == __version__
    assert response["result"]["serverInfo"]["version"] == __version__
