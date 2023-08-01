import sys

import pytest

BASE_URL = "https://raw.githubusercontent.com/python/cpython/{}/Lib/test/test_pathlib.py"  # noqa

# current origin of pathlib tests:
TEST_FILES = {
    "test_pathlib_38.py": "7475aa2c590e33a47f5e79e4079bca0645e93f2f",
    "test_pathlib_39.py": "d718764f389acd1bf4a5a65661bb58862f14fb98",
    "test_pathlib_310.py": "b382bf50c53e6eab09f3e3bf0802ab052cb0289d",
    "test_pathlib_311.py": "846a23d0b8f08e62a90682c51ce01301eb923f2e",
    "test_pathlib_312.py": "97a6a418167f1c8bbb014fab813e440b88cf2221",  # 3.12.0b4
}


def pytest_ignore_collect(collection_path, path, config):
    """prevents pathlib tests from other python version than the current to be collected

    (otherwise we see a lot of skipped tests in the pytest output)
    """
    v2 = sys.version_info[:2]
    return {
        "test_pathlib_38.py": v2 != (3, 8),
        "test_pathlib_39.py": v2 != (3, 9),
        "test_pathlib_310.py": v2 != (3, 10),
        "test_pathlib_311.py": v2 != (3, 11),
        "test_pathlib_312.py": v2 != (3, 12),
    }.get(collection_path.name, False)


def pytest_collection_modifyitems(config, items):
    """mark all tests in this folder as pathlib tests"""
    for item in items:
        item.add_marker(pytest.mark.pathlib)
