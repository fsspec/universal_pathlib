import setuptools

from upath import __version__

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="universal_pathlib",
    version=__version__,
    author="Andrew Fulton",
    author_email="andrewfulton9@gmail.com",
    url="https://github.com/fsspec/universal_pathlib",
    packages=setuptools.find_packages(),
    python_requires=">=3.7",
    description="pathlib api extended to use fsspec backends",
    long_description=long_description,
    long_description_content_type="text/markdown",
)
