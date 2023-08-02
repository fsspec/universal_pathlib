import pytest

try:
    from pydantic import BaseConfig
    from pydantic_settings import BaseSettings
except ImportError:
    BaseConfig = BaseSettings = None
    pytestmark = pytest.mark.skip(reason="requires pydantic")

from upath.core import UPath


def test_pydantic_settings_local_upath():
    class MySettings(BaseSettings):
        example_path: UPath = UPath(__file__)

    assert isinstance(MySettings().example_path, UPath)
