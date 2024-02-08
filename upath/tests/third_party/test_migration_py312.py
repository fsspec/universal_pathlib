import os
from os import getenv

import pytest

from upath import UPath
from upath.registry import get_upath_class
from upath.registry import register_implementation


@pytest.fixture(scope="function")
def clean_registry():
    from upath.registry import _registry

    try:
        yield
    finally:
        _registry._m.maps.clear()
        get_upath_class.cache_clear()


@pytest.fixture(scope="function")
def github_subclass_old_style(clean_registry):
    # GitHubPath code from:
    # https://github.com/juftin/textual-universal-directorytree/blob/110770f2ee40ab5afff7eade635caad644d80848/textual_universal_directorytree/alternate_paths.py#L15-L27

    from upath.core import _FSSpecAccessor

    class _GitHubAccessor(_FSSpecAccessor):
        def __init__(self, *args, **kwargs):
            token = getenv("GITHUB_TOKEN")
            if token is not None:
                kwargs.update({"username": "Bearer", "token": token})
            super().__init__(*args, **kwargs)

    class GitHubPath(UPath):
        _default_accessor = _GitHubAccessor

        def __new__(cls, *args, **kwargs):
            file_path = cls.handle_github_url(*args[0:1], storage_options=kwargs)
            return super().__new__(cls, file_path, *args[1:], **kwargs)

        @property
        def path(self):
            return super().path.strip("/")

        @property
        def name(self):
            if self.path == "":
                org = self._accessor._fs.org
                repo = self._accessor._fs.repo
                sha = self._accessor._fs.storage_options["sha"]
                github_name = f"{org}:{repo}@{sha}"
                return github_name
            else:
                return super().name

        @classmethod
        def handle_github_url(cls, url, storage_options):
            import requests  # type: ignore[import]

            url = str(url)
            gitub_prefix = "github://"
            if gitub_prefix in url and "@" not in url:
                _, user_password = url.split("github://")
                if "org" in storage_options and "repo" in storage_options:
                    org = storage_options["org"]
                    repo = storage_options["repo"]
                    _, *args = user_password.rpartition(":")[2].split("/")
                else:
                    org, repo_str = user_password.split(":")
                    repo, *args = repo_str.split("/")
            elif gitub_prefix in url and "@" in url:
                return url
            else:
                raise ValueError(f"Invalid GitHub URL: {url}")
            token = getenv("GITHUB_TOKEN")
            auth = {"auth": ("Bearer", token)} if token is not None else {}
            resp = requests.get(
                f"https://api.github.com/repos/{org}/{repo}",
                headers={"Accept": "application/vnd.github.v3+json"},
                **auth,  # type: ignore[arg-type]
            )
            resp.raise_for_status()
            default_branch = resp.json()["default_branch"]
            arg_str = "/".join(args)
            github_uri = (
                f"{gitub_prefix}{org}:{repo}@{default_branch}/{arg_str}".rstrip("/")
            )
            return github_uri

    register_implementation("github", GitHubPath, clobber=True)


@pytest.mark.skipif("GITHUB_TOKEN" not in os.environ, reason="No GITHUB_TOKEN found")
def test_migration_for_github_subclass(github_subclass_old_style):

    readme = UPath("github://fsspec:universal_pathlib@main/README.md").read_text()
    assert "universal_pathlib" in readme
    rst_files = list(UPath("github://fsspec:universal_pathlib@main/").glob("*.rst"))
    assert len(rst_files) == 2
